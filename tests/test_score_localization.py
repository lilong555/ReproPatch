"""Offline labels, exact-source exposure, censored cost and paired denominators."""

import copy
import difflib
import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest
from score_localization import main

from repropatch.artifacts import EvidenceRef
from repropatch.events import EventLog, encode_json
from repropatch.localization_scoring import (
    EXPOSURE_SCHEMA,
    generate_labels,
    read_eligibility_registry,
    score_run,
    structural_eligibility,
    summarize_scores,
    validate_labels,
)
from repropatch.task import canonical_json
from repropatch.workspace import source_manifest

OLD = "int first;\nint broken = 0;\nint context;\nint other_bug = 0;\nint last;\n"
NEW = OLD.replace("broken = 0", "broken = 1").replace("other_bug = 0", "other_bug = 1")
RUN = "a" * 32


def patch(before=OLD, after=NEW, path="src/test.cpp", context=3):
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=context,
        )
    ).encode()


@pytest.fixture
def fixture(tmp_path):
    source = tmp_path / "source"
    (source / "src").mkdir(parents=True)
    (source / "src/test.cpp").write_text(OLD)
    for index in range(6):
        (source / f"src/decoy{index}.cpp").write_text("int decoy;\n")
    labels = generate_labels(patch(), source, task_id="fmt-test")
    directory = tmp_path / RUN
    directory.mkdir()
    return source, labels, directory


def envelope(seq, kind, payload, *, step=None, tool=None):
    return {
        "schema_version": 1,
        "seq": seq,
        "run_id": RUN,
        "timestamp": f"2026-11-06T12:00:{seq:02d}+00:00",
        "type": kind,
        "step_id": step,
        "tool_call_id": tool,
        "operation_id": None,
        "payload": payload,
    }


def exposure(
    directory,
    labels,
    *,
    seq=1,
    name="read_file",
    data=None,
    body=None,
    calls=1,
    ordinal=None,
    local=None,
    phase="localization",
    usage=None,
    source=None,
    step=1,
    tool=None,
):
    if name == "baseline":
        step, tool, calls = 0, "baseline", 0
    else:
        tool = tool or f"s{step:06d}.t{seq:02d}"
    if data is None:
        data = {"path": "src/test.cpp", "text": "int broken = 0;\n", "start_line": 2, "end_line": 2}
    body = {"ok": True, "data": data} if body is None else body
    reference = EvidenceRef.save(directory, f"delivered/{seq}.json", canonical_json(body))
    payload = {
        "schema": EXPOSURE_SCHEMA,
        "phase": phase,
        "carrier_phase": phase,
        "delivery_status": "confirmed",
        "produced_model_step": step,
        "tool_name": name,
        "tool_call_id": tool,
        "model_step": step + 1,
        "tool_calls_used": calls,
        "localization_tools_used": calls if local is None else local,
        "tool_ordinal": calls if ordinal is None else ordinal,
        "elapsed_seconds": seq * 1.25,
        "cumulative_usage": usage,
        "source_tree_sha256": source or labels["source_tree_sha256"],
        "source_files": {
            item["path"]: item["sha256"] for item in labels["source_manifest"]["files"]
        },
        "delivered_ref": asdict(reference),
    }
    return envelope(
        seq,
        "localization_exposure",
        payload,
        step=step or None,
        tool=None if name == "baseline" else tool,
    )


def write_trace(directory, events, *, confirm=True):
    expanded = []
    for item in copy.deepcopy(events):
        if confirm and item["type"] == "localization_exposure":
            expanded.append(
                envelope(
                    1,
                    "model_finished",
                    {"cumulative_usage": item["payload"].get("cumulative_usage")},
                    step=item["payload"].get("model_step", 1),
                )
            )
        expanded.append(item)
    for number, event in enumerate(expanded, 1):
        event["seq"] = number
        event["timestamp"] = f"2026-11-06T12:00:{number:02d}+00:00"
    (directory / "events.jsonl").write_bytes(
        b"".join(encode_json(event) + b"\n" for event in expanded)
    )


def error_codes(result):
    return {error["code"] for error in result["errors"]}


def test_labels_exclude_context_and_bind_exact_runtime_manifest(fixture):
    source, labels, _ = fixture
    assert labels["files"][0]["gold_old_spans"] == [[2, 2], [4, 4]]
    assert labels["files"][0]["old_lines"] == {"2": "int broken = 0;", "4": "int other_bug = 0;"}
    assert labels["source_tree_sha256"] == source_manifest(source).sha256
    assert validate_labels(labels) == labels


def test_multiple_zero_context_hunks(fixture):
    source, _, _ = fixture
    labels = generate_labels(patch(context=0), source, task_id="test")
    assert labels["files"][0]["gold_old_spans"] == [[2, 2], [4, 4]]


@pytest.mark.parametrize(
    "before,after,anchors",
    [
        ("one\ntwo\n", "one\nadded\ntwo\n", [[1, 2]]),
        ("one\ntwo\n", "added\none\ntwo\n", [[1, 1]]),
        ("one\ntwo\n", "one\ntwo\nadded\n", [[2, 2]]),
        ("", "added\n", []),
    ],
)
def test_pure_insertion_is_separate(fixture, before, after, anchors):
    source, _, directory = fixture
    (source / "src/test.cpp").write_text(before)
    labels = generate_labels(patch(before, after, context=0), source, task_id="insert")
    assert labels["eligible"] is False
    assert labels["files"][0]["reason"] == "pure_insertion"
    assert labels["files"][0]["gold_old_spans"] == []
    assert labels["files"][0]["insertion_anchors"][0]["anchor_spans"] == anchors
    scored = score_run(directory, labels)
    assert scored["capped_first_hit_tools"] is None
    assert scored["hit_within_budget"] is None


def test_insertion_anchor_hit_does_not_count_as_changed_span(fixture):
    source, _, directory = fixture
    labels = generate_labels(patch(OLD, "added\n" + OLD), source, task_id="insertion")
    event = exposure(
        directory,
        labels,
        data={"path": "src/test.cpp", "start_line": 1, "end_line": 1, "text": "int first;\n"},
    )
    write_trace(directory, [event])
    result = score_run(directory, labels)
    assert result["hit_event"] is None
    assert result["insertion_anchor"]["hit_event"] is True


def test_new_file_has_ineligible_reason(fixture):
    source, _, _ = fixture
    new = (
        b"diff --git a/new.cpp b/new.cpp\nnew file mode 100644\n"
        b"--- /dev/null\n+++ b/new.cpp\n@@ -0,0 +1 @@\n+int x;\n"
    )
    labels = generate_labels(new, source, task_id="new")
    assert labels["eligible"] is False
    assert labels["files"][0]["reason"] == "new_file"


def test_deleted_file_labels_all_removed_lines(fixture):
    source, _, _ = fixture
    removed = b"--- a/src/test.cpp\n+++ /dev/null\n@@ -1,5 +0,0 @@\n" + b"".join(
        b"-" + line for line in OLD.encode().splitlines(keepends=True)
    )
    labels = generate_labels(removed, source, task_id="delete")
    assert labels["files"][0]["gold_old_spans"] == [[1, 5]]


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda p: p.replace(b"int broken = 0", b"int absent = 0"), "base_content_mismatch"),
        (lambda p: p.replace(b"src/test.cpp", b"src/missing.cpp"), "missing_base_file"),
        (
            lambda p: p.replace(b"@@ -1,5", b"@@ -500,5").replace(b"int first", b"absent"),
            "unmappable_old_range",
        ),
    ],
)
def test_unmappable_label_preserves_task(fixture, change, reason):
    source, _, _ = fixture
    labels = generate_labels(change(patch()), source, task_id="bad")
    assert labels["eligible"] is False
    assert labels["files"][0]["reason"] == reason


@pytest.mark.parametrize("insertion", [False, True])
def test_reference_offset_replayed_on_isolated_index(fixture, insertion):
    source, _, _ = fixture
    before = "\n".join(f"int line_{i};" for i in range(1, 31)) + "\n"
    after = before.replace(
        "int line_15;", "int inserted;\nint line_15;" if insertion else "int fixed;"
    )
    reference = patch(before, after)
    (source / "src/test.cpp").write_text("int prefix;\n" + before)
    original = (source / "src/test.cpp").read_bytes()
    labels = generate_labels(reference, source, task_id="offset")
    assert labels["mapping"]["method"] == "git_index_replay"
    assert labels["patch_sha256"] == hashlib.sha256(reference).hexdigest()
    assert labels["eligible"] is not insertion
    if insertion:
        assert labels["label_type"] == "pure_insertion"
        assert labels["files"][0]["insertion_anchors"][0]["anchor_spans"] == [[15, 16]]
    else:
        assert labels["files"][0]["gold_old_spans"] == [[16, 16]]
    assert (source / "src/test.cpp").read_bytes() == original
    assert not (source / ".git").exists()
    validate_labels(labels)


@pytest.mark.parametrize(
    "bad",
    [
        b"--- a/../outside\n+++ b/../outside\n@@ -1 +1 @@\n-x\n+y\n",
        b"--- a/x\n+++ b/x\n@@ -1,2 +1,2 @@\n-x\n+y\n",
        b"--- a/x\n+++ b/x\n@@ malformed @@\n-x\n+y\n",
        b"--- a/x\n+++ b/x\n@@ -1 +1 @@\n-x\n+y\n+extra\n",
        b"",
    ],
)
def test_malformed_patch_fails_closed(fixture, bad):
    source, _, _ = fixture
    from repropatch.errors import ReproPatchError

    with pytest.raises((ValueError, ReproPatchError)):
        generate_labels(bad, source, task_id="bad")


def test_git_metadata_excluded_and_quoted_path_supported(fixture):
    source, _, _ = fixture
    (source / ".git").mkdir()
    (source / ".git/config").write_text("private metadata")
    (source / "src/with space.cpp").write_text("old\n")
    quoted = b'--- "a/src/with space.cpp"\n+++ "b/src/with space.cpp"\n@@ -1 +1 @@\n-old\n+new\n'
    labels = generate_labels(quoted, source, task_id="space")
    assert labels["files"][0]["path"] == "src/with space.cpp"
    assert all(not file["path"].startswith(".git") for file in labels["source_manifest"]["files"])


def test_label_hash_tampering_rejected(fixture):
    _, labels, directory = fixture
    labels["files"][0]["gold_old_spans"] = [[1, 5]]
    with pytest.raises(ValueError, match="LABEL_HASH_MISMATCH"):
        score_run(directory, labels)


def test_first_hit_uses_actual_body_and_admitted_batch_cost(fixture):
    _, labels, directory = fixture
    events = [
        exposure(
            directory,
            labels,
            seq=1,
            calls=4,
            ordinal=1,
            local=1,
            data={"path": "src/test.cpp", "start_line": 1, "end_line": 1, "text": "int first;\n"},
        ),
        exposure(
            directory,
            labels,
            seq=2,
            calls=4,
            ordinal=2,
            local=2,
            usage={"input_tokens": 31, "output_tokens": None, "synthetic": False},
        ),
    ]
    write_trace(directory, events)
    score = score_run(directory, labels)
    assert score["evidence_status"] == "complete"
    assert score["hit_event"] is True and score["first_hit"]["seq"] == 4
    assert score["capped_first_hit_tools"] == 4
    assert score["first_hit"]["tool_ordinal"] == 2
    assert score["provider_usage"]["input_tokens"] == 31
    assert score["provider_usage"]["output_tokens"] is None
    assert score["covered_spans"] == 1 and score["span_coverage"] == 0.5


def test_search_code_actual_body_counts(fixture):
    _, labels, directory = fixture
    event = exposure(
        directory,
        labels,
        name="search_code",
        data={"matches": [{"path": "src/test.cpp", "line": 4, "text": "int other_bug"}]},
    )
    write_trace(directory, [event])
    result = score_run(directory, labels)
    assert result["hit_event"] is True
    assert result["candidate_top5"] == []


def test_candidate_paths_never_imply_source(fixture):
    _, labels, directory = fixture
    event = exposure(
        directory,
        labels,
        name="search_files",
        data={"candidates": [{"path": "src/test.cpp", "hit_lines": [2, 4]}]},
    )
    write_trace(directory, [event])
    result = score_run(directory, labels)
    assert result["candidate_top5_hit"] is True
    assert result["hit_event"] is False and result["censored"] is True
    assert result["first_hit"] is None and result["capped_first_hit_tools"] == 8


def test_candidate_top5_uses_unique_paths_in_delivered_order(fixture):
    _, labels, directory = fixture
    event = exposure(
        directory,
        labels,
        name="search_files",
        data={
            "candidates": [
                *[{"path": f"src/decoy{i}.cpp"} for i in range(5)],
                {"path": "src/test.cpp"},
            ]
        },
    )
    write_trace(directory, [event])
    result = score_run(directory, labels)
    assert result["candidate_top5_hit"] is False
    assert len(result["candidate_top5"]) == 5


@pytest.mark.parametrize(
    "body",
    [
        {"folded": True, "preview": '{"data":{"path":"src/test.cpp","start_line":2}}'},
        {
            "ok": False,
            "data": {
                "path": "src/test.cpp",
                "text": "int broken = 0;",
                "start_line": 2,
                "end_line": 2,
            },
        },
        {"ok": True, "data": {"path": "src/test.cpp", "text": "", "start_line": 2, "end_line": 1}},
        {"ok": True, "data": {"path": "src/test.cpp", "start_line": 2, "end_line": 2}},
        {
            "ok": True,
            "data": {"path": "src/test.cpp", "text": "\n", "start_line": 2, "end_line": 2},
        },
    ],
)
def test_zero_byte_zero_span_and_folded_receipts_do_not_hit(fixture, body):
    _, labels, directory = fixture
    write_trace(directory, [exposure(directory, labels, body=body)])
    score = score_run(directory, labels)
    assert score["hit_event"] is False
    assert score["capped_first_hit_tools"] == 8


def test_baseline_diagnostic_is_feedback_only(fixture):
    _, labels, directory = fixture
    event = exposure(
        directory,
        labels,
        name="baseline",
        body={
            "diagnostic": "src/test.cpp:2: error",
            "data": {
                "path": "src/test.cpp",
                "text": "int broken = 0;\n",
                "start_line": 2,
                "end_line": 2,
            },
        },
    )
    write_trace(directory, [event])
    result = score_run(directory, labels)
    assert result["evidence_status"] == "complete"
    assert result["hit_event"] is False and result["candidate_top5"] == []


def test_post_edit_source_and_repair_phase_are_separate(fixture):
    _, labels, directory = fixture
    changed = exposure(directory, labels, source="b" * 64)
    repaired = exposure(directory, labels, seq=2, calls=2, phase="repair")
    write_trace(directory, [changed, repaired])
    result = score_run(directory, labels)
    assert result["hit_event"] is False
    assert len(result["post_edit_exposures"]) == 1
    assert score_run(directory, labels, phase="all")["hit_event"] is True


@pytest.mark.parametrize(
    "modify,code",
    [
        (lambda e: e["payload"].update(schema="unknown"), "INVALID_EXPOSURE_SCHEMA"),
        (lambda e: e["payload"].pop("localization_tools_used"), "INVALID_EXPOSURE_SCHEMA"),
        (lambda e: e["payload"].pop("delivery_status"), "INVALID_EXPOSURE_SCHEMA"),
        (lambda e: e["payload"].update(delivery_status="prepared"), "UNCONFIRMED_EXPOSURE"),
        (lambda e: e["payload"].update(tool_calls_used=True), "INVALID_EXPOSURE_COUNTER"),
        (lambda e: e["payload"].update(tool_ordinal=3), "INVALID_EXPOSURE_BUDGET"),
        (lambda e: e["payload"].update(elapsed_seconds=-1), "INVALID_ELAPSED_SECONDS"),
        (
            lambda e: e["payload"].update(cumulative_usage={"input_tokens": -1}),
            "INVALID_TOKEN_COUNT",
        ),
        (
            lambda e: e["payload"]["source_files"].update({"src/test.cpp": "b" * 64}),
            "SOURCE_FILE_IDENTITY_MISMATCH",
        ),
        (lambda e: e["payload"]["source_files"].pop("src/test.cpp"), "UNAUTHORIZED_EXPOSURE_PATH"),
        (lambda e: e["payload"]["delivered_ref"].update(sha256="b" * 64), "ARTIFACT_CORRUPT"),
        (lambda e: e["payload"]["delivered_ref"].update(path="../outside"), "ARTIFACT_CORRUPT"),
        (lambda e: e["payload"].update(tool_call_id="wrong"), "EXPOSURE_TOOL_ID_MISMATCH"),
    ],
)
def test_invalid_exposure_fails_closed(fixture, modify, code):
    _, labels, directory = fixture
    event = exposure(directory, labels)
    modify(event)
    write_trace(directory, [event])
    score = score_run(directory, labels)
    assert score["hit_event"] is False
    assert score["eligible"] is True
    assert score["capped_first_hit_tools"] == 8
    assert score["evidence_status"] == "incomplete"
    assert code in error_codes(score)


@pytest.mark.parametrize(
    "data,code",
    [
        (
            {"path": "src/test.cpp", "text": "int fake;\n", "start_line": 2, "end_line": 2},
            "DELIVERED_SOURCE_TEXT_MISMATCH",
        ),
        (
            {"path": "src/test.cpp", "text": "int broken = 0;\n", "start_line": 2, "end_line": 20},
            "SOURCE_WINDOW_COUNT_MISMATCH",
        ),
        (
            {"path": "src/test.cpp", "text": "", "start_line": 2, "end_line": 2},
            "SOURCE_WINDOW_COUNT_MISMATCH",
        ),
    ],
)
def test_wrong_text_and_inflated_window_do_not_score(fixture, data, code):
    _, labels, directory = fixture
    write_trace(directory, [exposure(directory, labels, data=data)])
    result = score_run(directory, labels)
    assert result["hit_event"] is False and code in error_codes(result)


def test_missing_and_duplicate_json_fields(fixture):
    _, labels, directory = fixture
    event = exposure(directory, labels)
    raw = b'{"ok":false,"ok":true,"data":{}}'
    event["payload"]["delivered_ref"] = asdict(EvidenceRef.save(directory, "duplicate.json", raw))
    write_trace(directory, [event])
    score = score_run(directory, labels)
    assert score["hit_event"] is False and score["errors"]


def test_symlink_receipt_rejected(fixture, tmp_path):
    _, labels, directory = fixture
    event = exposure(directory, labels)
    path = directory / event["payload"]["delivered_ref"]["path"]
    copied = tmp_path / "outside.json"
    copied.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(copied)
    write_trace(directory, [event])
    assert score_run(directory, labels)["hit_event"] is False


def test_budget_censoring_and_early_stop_full_denominator(fixture):
    _, labels, directory = fixture
    write_trace(directory, [exposure(directory, labels, calls=9)])
    late = score_run(directory, labels)
    assert late["hit_event"] is True and late["hit_within_budget"] is False
    assert late["capped_first_hit_tools"] == 8
    write_trace(directory, [envelope(1, "agent_stopped", {"reason": "MODEL_ERROR"})])
    early = score_run(directory, labels)
    assert early["stop_reason"] == "MODEL_ERROR"
    assert early["eligible"] is True and early["capped_first_hit_tools"] == 8


def test_missing_trace_keeps_eligible_task_and_null_provider_usage(fixture):
    _, labels, directory = fixture
    score = score_run(directory, labels)
    assert score["eligible"] is True and score["hit_within_budget"] is False
    assert score["stop_reason"] == "missing_trace"
    assert score["provider_usage"]["input_tokens"] is None
    assert score["provider_usage"]["output_tokens"] is None


def test_synthetic_usage_stays_out_of_provider_metrics(fixture):
    _, labels, directory = fixture
    write_trace(
        directory, [exposure(directory, labels, usage={"input_tokens": 100, "synthetic": True})]
    )
    result = score_run(directory, labels)
    assert result["provider_usage"]["input_tokens"] is None
    assert result["provider_usage"]["raw"]["input_tokens"] == 100


def test_phase_cost_and_cold_verification_preserved(fixture):
    _, labels, directory = fixture
    phase = {
        "schema": "repropatch.localization.session.v1",
        "reason": "model_step_budget",
        "localization_tools_used": 1,
        "localization_model_steps": 4,
        "model_step": 4,
        "tool_calls_used": 1,
        "elapsed_seconds": 12.0,
        "source_tree_sha256": labels["source_tree_sha256"],
        "cumulative_usage": {"input_tokens": 90},
    }
    write_trace(
        directory, [exposure(directory, labels), envelope(2, "localization_phase_finished", phase)]
    )
    cold = {
        "schema": "repropatch.benchmark-score.v1",
        "accepted": False,
        "status": "REJECTED",
        "classification": "test_failed",
    }
    result = score_run(directory, labels, cold_score=cold)
    assert result["phase_finished"]["reason"] == "model_step_budget"
    assert result["cold_verification"] == cold


def test_sqlite_is_authoritative_and_corruption_never_falls_back(fixture):
    _, labels, directory = fixture
    event = exposure(directory, labels)
    write_trace(directory, [event])
    with sqlite3.connect(directory / "events.sqlite3") as db:
        db.execute(
            "CREATE TABLE events (seq INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, "
            "type TEXT NOT NULL, envelope_json TEXT NOT NULL)"
        )
        db.execute("PRAGMA user_version = 1")
        for item in (
            json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()
        ):
            db.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?)",
                (item["seq"], item["timestamp"], item["type"], encode_json(item).decode()),
            )
    result = score_run(directory, labels)
    assert result["trace_source"] == "sqlite" and result["hit_event"] is True
    with sqlite3.connect(directory / "events.sqlite3") as db:
        db.execute("UPDATE events SET timestamp = 'corrupt'")
    assert score_run(directory, labels)["hit_event"] is False


def test_native_eventlog_roundtrip(fixture):
    from conftest import created_payload

    _, labels, directory = fixture
    event = exposure(directory, labels)
    log = EventLog(directory, RUN)
    try:
        log.emit("run_created", created_payload())
        log.emit("localization_exposure", event["payload"], step_id=1, tool_call_id="s000001.t01")
    finally:
        log.close()
    result = score_run(directory, labels)
    assert result["trace_source"] == "sqlite" and result["hit_event"] is False
    assert "UNCONFIRMED_CARRIER_RESPONSE" in error_codes(result)


def test_aggregate_19_tasks_114_rows_and_task_paired_cost(fixture):
    _, labels, directory = fixture
    base = score_run(directory, labels)
    scores = []
    for task in range(19):
        for arm in "ABC":
            for repeat in (1, 2):
                score = copy.deepcopy(base)
                score.update(task_id=f"task-{task}", arm=arm, repeat_id=repeat)
                score["capped_first_hit_tools"] = (2 if arm == "B" else 6) + repeat
                scores.append(score)
    summary = summarize_scores(scores, task_ids=[f"task-{n}" for n in range(19)])
    assert summary["total_tasks"] == summary["eligible_tasks"] == 19
    assert summary["expected_runs"] == summary["observed_runs"] == 114
    pair = next(
        p
        for p in summary["paired"]
        if p["contrast"] == "B-A" and p["metric"] == "capped_first_hit_tools"
    )
    assert pair["mean_difference"] == -4 and pair["task_denominator"] == 19
    assert summary["tasks"][0]["arms"]["A"]["provider_input_tokens"] is None


def test_missing_repeat_gets_capped_cost_and_null_usage(fixture):
    _, labels, directory = fixture
    score = score_run(directory, labels)
    score.update(arm="A", repeat_id=1)
    score["capped_first_hit_tools"] = 2
    summary = summarize_scores([score], task_ids=[labels["task_id"], "missing-task"])
    assert summary["expected_runs"] == 12 and summary["observed_runs"] == 1
    assert summary["tasks"][0]["arms"]["A"]["capped_first_hit_tools"] == 5
    assert summary["tasks"][0]["arms"]["B"]["capped_first_hit_tools"] == 8
    assert summary["missing_label_tasks"] == 1
    with pytest.raises(ValueError, match="DUPLICATE_ATTEMPT_SCORE"):
        summarize_scores([score, score], task_ids=[labels["task_id"]])


def test_cli_sample_smoke(fixture, tmp_path, capsys):
    source, _, directory = fixture
    patch_path, labels_path, score_path = (
        tmp_path / name for name in ("reference.patch", "labels.json", "score.json")
    )
    patch_path.write_bytes(patch())
    assert (
        main(
            [
                "labels",
                "--patch",
                str(patch_path),
                "--source-root",
                str(source),
                "--task-id",
                "smoke",
                "--output",
                str(labels_path),
            ]
        )
        == 0
    )
    labels = json.loads(labels_path.read_text())
    events = [
        exposure(
            directory,
            labels,
            name="search_files",
            data={"candidates": [{"path": "src/test.cpp", "hit_lines": [2]}]},
        ),
        exposure(directory, labels, seq=2, calls=2),
    ]
    write_trace(directory, events)
    assert (
        main(
            [
                "score",
                "--run-dir",
                str(directory),
                "--labels",
                str(labels_path),
                "--tool-budget",
                "8",
                "--arm",
                "B",
                "--repeat-id",
                "1",
                "--output",
                str(score_path),
            ]
        )
        == 0
    )
    result = json.loads(score_path.read_text())
    assert result["candidate_top5_hit"] and result["hit_within_budget"]
    assert result["first_hit"]["tool_calls_used"] == 2
    assert result["provider_usage"]["input_tokens"] is None
    assert result["scoring_model_requests"] == 0
    assert result["arm"] == "B" and result["repeat_id"] == 1
    assert "repropatch.localization-score.v1" in capsys.readouterr().out


def test_cli_prevents_source_evidence_and_input_overwrite(fixture, tmp_path):
    source, labels, directory = fixture
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(json.dumps(labels))
    for output in (labels_path, directory / "score.json"):
        with pytest.raises(SystemExit) as error:
            main(
                [
                    "score",
                    "--run-dir",
                    str(directory),
                    "--labels",
                    str(labels_path),
                    "--output",
                    str(output),
                ]
            )
        assert error.value.code == 2
    patch_path = tmp_path / "reference.patch"
    patch_path.write_bytes(patch())
    with pytest.raises(SystemExit):
        main(
            [
                "labels",
                "--patch",
                str(patch_path),
                "--source-root",
                str(source),
                "--output",
                str(source / "labels.json"),
            ]
        )


def test_cli_campaign_request_smoke(fixture, tmp_path, monkeypatch):
    source, _, original_dir = fixture
    worker_dir = tmp_path / "worker"
    (worker_dir / "runs").mkdir(parents=True)
    directory = worker_dir / "runs" / RUN
    original_dir.rename(directory)
    labels = generate_labels(patch(), source, task_id="fmt__test")
    write_trace(directory, [exposure(directory, labels)])
    task_path = tmp_path / "task.yaml"
    task_path.write_text("task")
    task = SimpleNamespace(
        id="fmt-test", source_bytes=b"task", repository=source, revision="a" * 40
    )
    monkeypatch.setattr("score_localization.Task.load", lambda path: task)
    monkeypatch.setattr(
        "score_localization.git", lambda repo, *args: b"a" * 40 if args[0] == "rev-parse" else b""
    )
    monkeypatch.setattr(
        "qualify_cpp_batch.records",
        lambda path: [{"instance_id": "fmt__test", "fix_patch": patch().decode()}],
    )
    worker = {
        "schema": "repropatch.benchmark-attempt.v1",
        "agent": "repropatch",
        "attempt_id": "attempt-A-1",
        "task_id": "fmt-test",
        "prepared_commit": task.revision,
        "task_sha256": hashlib.sha256(b"task").hexdigest(),
        "native_run_id": RUN,
    }
    worker_path = worker_dir / "result.json"
    worker_path.write_text(json.dumps(worker))
    request = {
        "schema": "repropatch.localization-score.request.v1",
        "attempt_id": "attempt-A-1",
        "instance_id": "fmt__test",
        "arm": "A",
        "repeat": 1,
        "worker_result": str(worker_path),
        "dataset": str(tmp_path),
        "execution_task": str(task_path),
        "prepared_commit": task.revision,
        "source_sha256": "b" * 64,
        "protocol_sha256": "c" * 64,
        "budgets": {"localization_tools": 8},
    }
    request_path, output = tmp_path / "request.json", tmp_path / "score.json"
    request_path.write_text(json.dumps(request))
    assert main(["score", "--request", str(request_path), "--output", str(output)]) == 0
    result = json.loads(output.read_text())
    assert result["status"] == "scored" and result["attempt_id"] == "attempt-A-1"
    assert result["hit_within_budget"] is True
    assert (tmp_path / result["labels_file"]).is_file()
    request["attempt_id"] = "wrong"
    request_path.write_text(json.dumps(request))
    with pytest.raises(SystemExit):
        main(["score", "--request", str(request_path), "--output", str(output)])


def test_prepared_receipt_does_not_count_as_model_exposure(fixture, monkeypatch):
    _, labels, directory = fixture
    event = exposure(directory, labels)
    event["type"] = "localization_receipt_prepared"
    from repropatch.events import EVENT_TYPES

    monkeypatch.setattr(
        "repropatch.localization_scoring.EVENT_TYPES", EVENT_TYPES | {event["type"]}
    )
    write_trace(directory, [event])
    result = score_run(directory, labels)
    assert result["hit_event"] is False
    assert result["first_hit"] is None
    assert result["capped_first_hit_tools"] == 8


def test_consuming_model_step_and_sparse_source_files(fixture):
    _, labels, directory = fixture
    event = exposure(directory, labels)
    event["payload"].update(carrier_phase="repair", model_step=2)
    event["payload"]["source_files"] = {"src/test.cpp": labels["files"][0]["source_sha256"]}
    write_trace(directory, [event])
    result = score_run(directory, labels)
    assert result["hit_event"] is True
    assert result["first_hit"]["model_step"] == 2
    assert result["first_hit"]["phase"] == "localization"
    assert result["first_hit"]["carrier_phase"] == "repair"


def test_entire_missing_task_remains_in_frozen_label_denominator(fixture):
    _, labels, _ = fixture
    summary = summarize_scores(
        [], task_ids=[labels["task_id"]], labels_by_task={labels["task_id"]: labels}
    )
    assert summary["eligible_tasks"] == 1 and summary["expected_runs"] == 6
    assert summary["arms"]["A"]["hit_within_budget"] == {"mean": 0.0, "task_denominator": 1}
    assert summary["arms"]["A"]["capped_first_hit_tools"]["mean"] == 8


@pytest.mark.sdk
def test_actual_sdk_runtime_confirmation_scores_consuming_request(task, tmp_path):
    from agents.testing import ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    from repropatch.harness import Harness

    path = "src/stats.cpp"
    before = (task.repository / path).read_text()
    after = before.replace("int best = 0;", "int best = samples.front();")
    labels = generate_labels(patch(before, after, path=path), task.repository, task_id=task.id)
    model = ScriptedModel(
        [
            [function_call("read_file", {"path": path}, call_id="read")],
            [assistant_message("Source reviewed.")],
        ]
    )
    harness = Harness(
        task,
        model,
        tmp_path / "actual-runs",
        sandbox_factory=SimulatedSandbox,
        candidate_only=True,
        localization_tool_budget=1,
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "MODEL_FINISHED"
    result = score_run(harness.directory, labels)
    assert result["evidence_status"] == "complete", result["errors"]
    assert result["hit_event"] is True
    assert result["first_hit"]["model_step"] == 2
    assert result["first_hit"]["carrier_phase"] == "repair"
    assert result["first_hit"]["phase"] == "localization"
    assert result["provider_usage"]["input_tokens"] is None


def test_confirmed_carrier_requires_successful_response(fixture):
    _, labels, directory = fixture
    event = exposure(directory, labels)
    event["payload"].update(
        delivery_status="confirmed", produced_model_step=1, carrier_phase="repair", model_step=2
    )
    event.update(step_id=None, tool_call_id=None)
    write_trace(directory, [event], confirm=False)
    result = score_run(directory, labels)
    assert result["hit_event"] is False
    assert "UNCONFIRMED_CARRIER_RESPONSE" in error_codes(result)
    finished = envelope(1, "model_finished", {"cumulative_usage": None}, step=2)
    event["seq"] = 2
    event["timestamp"] = "2026-11-06T12:00:02+00:00"
    write_trace(directory, [finished, event])
    assert score_run(directory, labels)["hit_event"] is True


def frozen_eligibility():
    root = Path(__file__).resolve().parents[1]
    spec = json.loads((root / "benchmarks/localization-ablation/protocol.json").read_text())
    parent = json.loads((root / spec["parent_protocol"]).read_text())
    scoring = spec["scoring"]
    registrations = read_eligibility_registry(
        root / scoring["eligibility_file"],
        scoring["eligibility_sha256"],
        instance_ids=parent["tasks"],
        task_contracts=parent["task_contracts"],
        qualification_archive_sha256=parent["qualification_archive_sha256"],
        source_protocol_sha256=spec["parent_protocol_sha256"],
    )
    return root, spec, parent, registrations


def registered_score(registration, arm, repeat):
    eligible = registration["eligible"]
    return {
        "schema": "repropatch.localization-score.v1",
        "status": "scored",
        "task_id": registration["task_id"],
        "arm": arm,
        "repeat_id": repeat,
        "labels_sha256": hashlib.sha256(registration["task_id"].encode()).hexdigest(),
        "reference_patch_sha256": registration["reference_patch_sha256"],
        "label_type": registration["label_type"],
        "eligible": eligible,
        "tool_budget": 8,
        "phase": "localization",
        "evidence_status": "complete",
        "hit_within_budget": True if eligible else None,
        "capped_first_hit_tools": 2 if eligible else None,
        "candidate_top5_hit": False if eligible else None,
        "provider_usage": {"input_tokens": 100, "output_tokens": 2},
        "cold_verification": {"accepted": True},
        "insertion_anchor": {"hit_within_budget": None if eligible else True},
    }


def test_registry_freeze_reproduces_all_19_qualification_archives():
    from freeze_localization_eligibility import freeze_registry

    root, spec, _, registrations = frozen_eligibility()
    registry = freeze_registry(
        root / spec["parent_protocol"],
        list((root / "benchmarks/context-ablation/inputs").glob("*.tar.gz")),
    )
    assert registry == json.loads((root / spec["scoring"]["eligibility_file"]).read_text())
    assert registry["total_tasks"] == 19 and registry["eligible_tasks"] == 14
    assert {
        key.rsplit("-", 1)[-1] for key, row in registrations.items() if not row["eligible"]
    } == {"2070", "3537", "3713", "3734", "3819"}
    for row in registry["tasks"]:
        assert set(row) == {
            "task_id",
            "instance_id",
            "eligible",
            "label_type",
            "reference_patch_sha256",
            "prepared_commit",
            "qualification_archive_sha256",
            "qualification_result_sha256",
            "qualification_task_sha256",
        }


def test_structural_insertion_ignores_nonzero_hunk_context():
    inserted = patch(OLD, OLD.replace("int context;", "int inserted;\nint context;"))
    assert b"@@ -1,5" in inserted
    assert structural_eligibility(inserted) == (False, "pure_insertion")
    assert structural_eligibility(patch()) == (True, "changed_existing_old_lines")


def test_corrupt_qualification_archive_fails_before_registry_write(tmp_path):
    from freeze_localization_eligibility import verified_archive

    path = tmp_path / "corrupt.tar.gz"
    path.write_bytes(b"damaged")
    with pytest.raises(ValueError, match="QUALIFICATION_ARCHIVE_SHA256_MISMATCH"):
        verified_archive(path, ["0" * 64])


def test_registered_denominator_keeps_eligible_task_with_all_six_scores_missing():
    _, _, _, registrations = frozen_eligibility()
    missing = next(task for task, row in registrations.items() if row["eligible"])
    scores = [
        registered_score(row, arm, repeat)
        for task, row in registrations.items()
        if task != missing
        for arm in "ABC"
        for repeat in (1, 2)
    ]
    result = summarize_scores(
        scores, task_ids=list(registrations), eligibility_by_task=registrations
    )
    assert result["total_tasks"] == 19 and result["eligible_tasks"] == 14
    assert result["observed_runs"] == 108 and result["expected_runs"] == 114
    assert result["missing_label_tasks"] == 1 and result["missing_registration_tasks"] == 0
    assert result["complete_actual_scores"] == 108 and not result["all_actual_scores_complete"]
    row = next(row for row in result["tasks"] if row["task_id"] == missing)
    assert row["registered_eligible"] and not row["actual_label_available"]
    assert row["arms"]["A"]["hit_within_budget"] == 0
    assert row["arms"]["A"]["capped_first_hit_tools"] == 8
    assert result["arms"]["A"]["hit_within_budget"]["task_denominator"] == 14
    assert result["arms"]["A"]["hit_within_budget"]["mean"] == pytest.approx(13 / 14)
    assert len(result["insertion_only_tasks"]) == 5 and len(result["full_overview"]) == 19
    assert all(
        row["arms"]["A"]["hit_within_budget"] is None for row in result["insertion_only_tasks"]
    )
    assert all(
        row["arms"]["A"]["provider_input_tokens"] == 100 for row in result["insertion_only_tasks"]
    )


def test_registered_denominator_with_zero_actual_scores_remains_14():
    _, _, _, registrations = frozen_eligibility()
    result = summarize_scores([], task_ids=list(registrations), eligibility_by_task=registrations)
    assert result["eligible_tasks"] == result["registered_eligible_tasks"] == 14
    assert result["missing_label_tasks"] == result["missing_score_tasks"] == 19
    assert result["missing_score_runs"] == 114 and result["complete_actual_scores"] == 0
    assert not result["all_actual_scores_complete"]
    assert result["arms"]["A"]["hit_within_budget"] == {"mean": 0, "task_denominator": 14}
    assert result["arms"]["A"]["capped_first_hit_tools"] == {"mean": 8, "task_denominator": 14}
    assert len(result["full_overview"]) == 19 and len(result["insertion_only_tasks"]) == 5


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("eligible", False, "REGISTERED_ELIGIBILITY_CONTRACT_MISMATCH"),
        ("label_type", "pure_insertion", "REGISTERED_LABEL_CONTRACT_MISMATCH"),
        ("reference_patch_sha256", "0" * 64, "REGISTERED_LABEL_CONTRACT_MISMATCH"),
        ("capped_first_hit_tools", None, "ELIGIBLE_SCORE_METRICS_MISSING"),
    ],
)
def test_observed_label_never_silently_changes_registered_eligibility(field, value, reason):
    _, _, _, registrations = frozen_eligibility()
    row = next(row for row in registrations.values() if row["eligible"])
    score = registered_score(row, "A", 1)
    score[field] = value
    with pytest.raises(ValueError, match=reason):
        summarize_scores([score], task_ids=list(registrations), eligibility_by_task=registrations)


def test_registry_can_be_combined_with_full_private_labels(fixture):
    _, labels, _ = fixture
    registration = {
        "task_id": labels["task_id"],
        "eligible": True,
        "label_type": "changed_existing_old_lines",
        "reference_patch_sha256": labels["patch_sha256"],
        "prepared_commit": "1" * 40,
    }
    result = summarize_scores(
        [],
        task_ids=[labels["task_id"]],
        labels_by_task={labels["task_id"]: labels},
        eligibility_by_task={labels["task_id"]: registration},
    )
    assert result["eligible_tasks"] == 1 and result["missing_label_tasks"] == 0
    registration.update(eligible=False, label_type="pure_insertion")
    with pytest.raises(ValueError, match="REGISTERED_FROZEN_LABEL_CONTRACT_MISMATCH"):
        summarize_scores(
            [],
            task_ids=[labels["task_id"]],
            labels_by_task={labels["task_id"]: labels},
            eligibility_by_task={labels["task_id"]: registration},
        )


def test_campaign_statistics_reads_hash_bound_registry_and_preserves_fullgate():
    import localization_ablation as campaign

    p = campaign.read_protocol()
    result = campaign.localization_statistics([], p, "full")
    assert result["eligible_tasks"] == 14 and len(result["full_overview"]) == 19
    assert result["complete_score_runs"] == 0 and not result["all_actual_scores_complete"]
    corrupted = copy.deepcopy(p)
    corrupted["scoring"]["eligibility_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="ELIGIBILITY_REGISTRY_HASH_MISMATCH"):
        campaign.localization_statistics([], corrupted, "full")


def test_campaign_preserves_known_cost_and_cold_result_when_localization_score_missing():
    import localization_ablation as campaign

    _, _, _, registrations = frozen_eligibility()
    missing = next(task for task, row in registrations.items() if row["eligible"])
    rows = []
    for task, registration in registrations.items():
        for arm in campaign.ARMS:
            for repeat in (1, 2):
                rows.append(
                    {
                        "instance_id": registration["instance_id"],
                        "arm": arm,
                        "repeat": repeat,
                        "localization_score": registered_score(registration, arm, repeat)
                        if task != missing
                        else None,
                        "usage": {"input_tokens": 300, "output_tokens": 4},
                        "score": {"accepted": True},
                    }
                )
    result = campaign.localization_statistics(rows, campaign.read_protocol(), "full")
    task = next(row for row in result["tasks"] if row["task_id"] == missing)
    assert task["arms"]["native"]["capped_first_hit_tools"] == 8
    assert task["arms"]["native"]["provider_input_tokens"] == 300
    assert task["arms"]["native"]["cold_accepted"] == 1
    assert result["arms"]["native"]["cold_accepted"]["task_denominator"] == 19
    assert result["complete_score_runs"] == 108 and not result["all_actual_scores_complete"]


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda r: r["tasks"].pop(), "ELIGIBILITY_TASK_SET_MISMATCH"),
        (
            lambda r: r["tasks"][0].update(prepared_commit="0" * 40),
            "ELIGIBILITY_PREPARED_COMMIT_MISMATCH",
        ),
        (
            lambda r: r.update(source_protocol_sha256="0" * 64),
            "ELIGIBILITY_SOURCE_PROTOCOL_MISMATCH",
        ),
    ],
)
def test_registry_semantic_identity_is_verified_beyond_file_hash(tmp_path, mutation, reason):
    root, spec, parent, _ = frozen_eligibility()
    registry = json.loads((root / spec["scoring"]["eligibility_file"]).read_text())
    mutation(registry)
    registry["registry_sha256"] = hashlib.sha256(
        canonical_json({k: v for k, v in registry.items() if k != "registry_sha256"})
    ).hexdigest()
    raw = canonical_json(registry)
    path = tmp_path / "registry.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError, match=reason):
        read_eligibility_registry(
            path,
            hashlib.sha256(raw).hexdigest(),
            instance_ids=parent["tasks"],
            task_contracts=parent["task_contracts"],
            qualification_archive_sha256=parent["qualification_archive_sha256"],
            source_protocol_sha256=spec["parent_protocol_sha256"],
        )


def test_formal_folded_text_is_complete_evidence_with_zero_source(fixture):
    from repropatch.context import fold_tool_output

    _, labels, directory = fixture
    full = canonical_json({"ok": True, "data": {"path": "src/test.cpp", "text": "x" * 10000}})
    raw_ref = EvidenceRef.save(directory, "original.json", full)
    folded = fold_tool_output(full.decode(), 400, lambda _: raw_ref.path)
    event = exposure(directory, labels)
    event["payload"].update(
        receipt_format="folded_text",
        delivered_ref=asdict(EvidenceRef.save(directory, "folded.txt", folded.encode())),
    )
    write_trace(directory, [event])
    result = score_run(directory, labels)
    assert result["evidence_status"] == "complete", result["errors"]
    assert result["hit_event"] is False and result["capped_first_hit_tools"] == 8
    assert result["exposures"][0]["source_lines"] == 0 and result["candidate_top5"] == []


@pytest.mark.parametrize(
    "format,text,reason",
    [
        ("unparsed_text", "damaged response", "UNPARSED_DELIVERED_TEXT"),
        ("json", "damaged response", "UNPARSED_DELIVERED_TEXT"),
        ("folded_text", "damaged response", "INVALID_FOLDED_NOTICE"),
        ("folded_text", '{"ok":true}', "RECEIPT_FORMAT_MISMATCH"),
        ("unparsed_text", '{"ok":true}', "RECEIPT_FORMAT_MISMATCH"),
    ],
)
def test_receipt_format_and_content_must_agree(fixture, format, text, reason):
    _, labels, directory = fixture
    event = exposure(directory, labels)
    event["payload"].update(
        receipt_format=format,
        delivered_ref=asdict(EvidenceRef.save(directory, "opaque.txt", text.encode())),
    )
    write_trace(directory, [event])
    result = score_run(directory, labels)
    assert result["evidence_status"] == "incomplete" and result["hit_event"] is False
    assert reason in error_codes(result)
