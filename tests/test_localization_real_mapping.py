"""Offline reference-offset regressions on hash-frozen, licensed fmt source."""

import hashlib
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from repropatch.artifacts import EvidenceRef
from repropatch.events import encode_json
from repropatch.localization_scoring import EXPOSURE_SCHEMA, generate_labels, score_run
from repropatch.task import canonical_json
from repropatch.workspace import source_manifest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/localization-real-mapping"
INSTANCES = ("fmtlib__fmt-2317", "fmtlib__fmt-3713")
SOURCE_PATH = "include/fmt/format.h"
RUN_ID = "e" * 32
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_localization_eligibility import verified_archive  # noqa: E402
from localization_ablation import ARMS, localization_statistics, read_protocol  # noqa: E402


@pytest.fixture(scope="module")
def real_cases(tmp_path_factory):
    provenance = json.loads((FIXTURES / "provenance.json").read_text())
    protocol = read_protocol()
    archive_sha, _, contents = verified_archive(
        ROOT / provenance["qualification_archive"], protocol["qualification_archive_sha256"]
    )
    assert archive_sha == provenance["qualification_archive_sha256"]
    assert tuple(row["instance_id"] for row in provenance["fixtures"]) == INSTANCES
    cases = {}
    for row in provenance["fixtures"]:
        instance = row["instance_id"]
        prefix = f"qualification/{instance}/"
        manifest = json.loads(contents[prefix + "manifest.json"])
        result = json.loads(contents[prefix + "result.json"])
        patch = contents[prefix + "control/reference.patch"]
        for field in ("upstream_commit", "prepared_commit", "reference_patch_sha256"):
            assert row[field] == result[field]
        assert result["status"] == "QUALIFIED"
        assert row["prepared_commit"] == protocol["task_contracts"][instance]["prepared_commit"]
        assert hashlib.sha256(patch).hexdigest() == row["reference_patch_sha256"]
        assert manifest["control/reference.patch"] == {
            "size": len(patch),
            "sha256": row["reference_patch_sha256"],
        }
        for item in row["files"]:
            raw = (FIXTURES / instance / item["path"]).read_bytes()
            expected = {"size": item["size"], "sha256": item["sha256"]}
            assert {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} == expected
            assert manifest[item["manifest_key"]] == expected
            relative = item["manifest_key"].removeprefix("repository/")
            assert item["url"] == (
                f"https://raw.githubusercontent.com/fmtlib/fmt/{row['upstream_commit']}/{relative}"
            )
        source = tmp_path_factory.mktemp(instance) / "source"
        shutil.copytree(FIXTURES / instance / "source", source)
        before = source_manifest(source)
        labels = generate_labels(patch, source, task_id=instance.replace("__", "-"))
        assert source_manifest(source) == before
        assert not (source / ".git").exists()
        cases[instance] = {"source": source, "labels": labels, "patch": patch}
    return cases


@pytest.mark.parametrize("instance", INSTANCES)
def test_real_reference_maps_on_frozen_source(real_cases, instance):
    case = real_cases[instance]
    labels = case["labels"]
    assert labels["mapping"]["method"] == "git_index_replay"
    normalized_sha = labels["mapping"]["normalized_patch_sha256"]
    assert len(normalized_sha) == 64
    assert normalized_sha != labels["patch_sha256"]
    assert labels["patch_sha256"] == hashlib.sha256(case["patch"]).hexdigest()
    assert labels["scoring_model_requests"] == 0
    assert labels["source_tree_sha256"] == source_manifest(case["source"]).sha256
    assert len(labels["files"]) == 1
    file = labels["files"][0]
    assert file["path"] == SOURCE_PATH
    lines = (case["source"] / SOURCE_PATH).read_text().splitlines()
    assert all(lines[int(n) - 1] == text for n, text in file["old_lines"].items())
    if instance == "fmtlib__fmt-2317":
        assert labels["eligible"] is True
        assert labels["label_type"] == "changed_existing_old_lines"
        assert file["gold_old_spans"] == [[1311, 1311], [1314, 1318], [1800, 1800]]
        assert len(file["old_lines"]) == 7
        assert file["reason"] is None
        assert file["insertion_anchors"] == []
    else:
        assert labels["eligible"] is False
        assert labels["label_type"] == "pure_insertion"
        assert labels["insertion_eligible"] is True
        assert file["gold_old_spans"] == []
        assert file["reason"] == "pure_insertion"
        assert file["insertion_anchors"] == [
            {
                "after_old_line": 4056,
                "anchor_spans": [[4056, 4057]],
                "inserted_lines": 1,
                "eligible": True,
                "reason": None,
            }
        ]


def write_source_exposure(directory, case, line):
    text = (case["source"] / SOURCE_PATH).read_text().splitlines(keepends=True)[line - 1]
    ref = EvidenceRef.save(
        directory,
        "delivered/read.json",
        canonical_json(
            {
                "ok": True,
                "data": {"path": SOURCE_PATH, "start_line": line, "end_line": line, "text": text},
            }
        ),
    )
    labels = case["labels"]
    payload = {
        "schema": EXPOSURE_SCHEMA,
        "phase": "localization",
        "carrier_phase": "localization",
        "delivery_status": "confirmed",
        "receipt_format": "json",
        "produced_model_step": 1,
        "tool_name": "read_file",
        "tool_call_id": "s000001.t01",
        "model_step": 2,
        "tool_calls_used": 1,
        "localization_tools_used": 1,
        "tool_ordinal": 1,
        "elapsed_seconds": 1,
        "cumulative_usage": None,
        "source_tree_sha256": labels["source_tree_sha256"],
        "source_files": {SOURCE_PATH: labels["files"][0]["source_sha256"]},
        "delivered_ref": asdict(ref),
    }
    events = []
    for seq, (kind, body) in enumerate(
        [("model_finished", {"cumulative_usage": None}), ("localization_exposure", payload)], 1
    ):
        events.append(
            {
                "schema_version": 1,
                "seq": seq,
                "run_id": RUN_ID,
                "timestamp": f"2026-11-06T12:00:0{seq}+00:00",
                "type": kind,
                "step_id": 2,
                "tool_call_id": None,
                "operation_id": None,
                "payload": body,
            }
        )
    (directory / "events.jsonl").write_bytes(b"".join(encode_json(e) + b"\n" for e in events))


@pytest.mark.parametrize("line,hit", [(1307, False), (1311, True), (1312, False), (1800, True)])
def test_real_replacement_scores_actual_remapped_body(real_cases, tmp_path, line, hit):
    case = real_cases["fmtlib__fmt-2317"]
    write_source_exposure(tmp_path, case, line)
    score = score_run(tmp_path, case["labels"])
    assert score["errors"] == []
    assert score["evidence_status"] == "complete"
    assert score["hit_within_budget"] is hit
    assert score["capped_first_hit_tools"] == (1 if hit else 8)
    assert score["total_spans"] == 3
    assert score["covered_spans"] == int(hit)
    assert score["provider_usage"]["input_tokens"] is None


@pytest.mark.parametrize("line,hit", [(4056, True), (4057, False)])
def test_real_insertion_scores_nonempty_anchor_separately(real_cases, tmp_path, line, hit):
    case = real_cases["fmtlib__fmt-3713"]
    write_source_exposure(tmp_path, case, line)
    score = score_run(tmp_path, case["labels"])
    assert score["errors"] == []
    assert score["hit_within_budget"] is None
    assert score["capped_first_hit_tools"] is None
    assert score["insertion_anchor"]["hit_within_budget"] is hit
    assert score["insertion_anchor"]["capped_first_hit_tools"] == (1 if hit else 8)


@pytest.mark.parametrize("include_scores", [False, True])
def test_real_empty_traces_keep_fixed_19_task_campaign(real_cases, tmp_path, include_scores):
    protocol = read_protocol()
    (tmp_path / "events.jsonl").write_bytes(b"")
    scores = {}
    if include_scores:
        for instance, case in real_cases.items():
            score = score_run(tmp_path, case["labels"])
            assert score["evidence_status"] == "incomplete"
            assert {e["code"] for e in score["errors"]} == {"EMPTY_TRACE", "NO_VALID_EXPOSURES"}
            assert score["provider_usage"]["input_tokens"] is None
            assert score["provider_usage"]["output_tokens"] is None
            assert score["cold_verification"] is None
            scores[instance] = score
    rows = []
    for instance in protocol["tasks"]:
        for arm in ARMS:
            for repeat in (1, 2):
                rows.append(
                    {
                        "instance_id": instance,
                        "arm": arm,
                        "repeat": repeat,
                        "localization_score": {**scores[instance], "arm": arm, "repeat_id": repeat}
                        if instance in scores
                        else None,
                    }
                )
    summary = localization_statistics(rows, protocol, "full")
    assert summary["total_tasks"] == 19
    assert summary["eligible_tasks"] == summary["registered_eligible_tasks"] == 14
    assert summary["missing_registration_tasks"] == 0
    assert summary["expected_runs"] == 114
    assert summary["observed_runs"] == (12 if include_scores else 0)
    assert summary["missing_score_tasks"] == (17 if include_scores else 19)
    assert summary["actual_label_tasks"] == (2 if include_scores else 0)
    assert summary["all_actual_scores_complete"] is False
    assert summary["complete_score_runs"] == 0
    assert len(summary["full_overview"]) == 19
    assert {r["task_id"].rsplit("-", 1)[-1] for r in summary["insertion_only_tasks"]} == {
        "2070",
        "3537",
        "3713",
        "3734",
        "3819",
    }
    for arm in ARMS:
        assert summary["arms"][arm]["hit_within_budget"] == {"mean": 0, "task_denominator": 14}
        assert summary["arms"][arm]["capped_first_hit_tools"] == {"mean": 8, "task_denominator": 14}
        assert summary["arms"][arm]["provider_input_tokens"]["mean"] is None
        assert summary["arms"][arm]["cold_accepted"]["mean"] is None
        for row in summary["insertion_only_tasks"]:
            assert row["arms"][arm]["hit_within_budget"] is None
    for pair in summary["paired"]:
        if pair["metric"] == "capped_first_hit_tools":
            assert pair["task_denominator"] == 14
            assert pair["mean_difference"] == 0
