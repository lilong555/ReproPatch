import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analyze_context_opportunities import (
    add_cross_observation_candidates,
    aggregate,
    audit_one,
    enrich_observations,
    literal_candidates,
    repair_pressure_points,
    threshold_profile,
    token_proxy,
)


def appearance(step, tokens=1000):
    return {
        "sequence": step,
        "purpose": "repair",
        "step_id": step,
        "bytes": 3000,
        "proxy_tokens_o200k": tokens,
        "proxy_tokens_utf8_div3": 1000,
    }


def observation(appearances):
    return {
        "step_id": 1,
        "provider_call_id": "call-1",
        "tool": "read_file",
        "tool_ok": True,
        "test_passed": None,
        "source_tree_sha256": "a" * 64,
        "raw_ref": {"path": "worker/runs/run/agent/tool-results/t1.json"},
        "raw_canonical_bytes": 3000,
        "appearances": appearances,
    }


def test_delay_protects_two_consumption_steps_and_counts_actual_presence():
    obs = observation([appearance(2), appearance(3), appearance(4), appearance(6)])
    requests = [appearance(step) for step in range(1, 7)]
    enrich_observations([obs], requests, {})
    assert obs["delayed_500_candidate_o200k"]
    assert obs["delayed_first_repair_sequence"] == 4
    assert obs["delayed_actual_repair_appearances"] == 2
    assert obs["later_repair_requests_after_two_completed_steps"] == 3
    assert obs["delayed_repair_exposure_proxy_tokens_o200k"] == 2000


def test_raw_length_does_not_make_short_visible_output_a_candidate():
    obs = observation([appearance(2, 300), appearance(4, 300)])
    obs["raw_canonical_bytes"] = 1_000_000
    enrich_observations([obs], [appearance(2), appearance(4)], {})
    assert not obs["delayed_500_candidate_o200k"]
    assert obs["delayed_mask_envelope_savings_proxy_tokens_o200k"] == 0
    assert obs["delayed_500_candidate_utf8_div3"]


def test_unconsumed_final_tool_output_has_no_online_exposure():
    obs = observation([])
    enrich_observations([obs], [appearance(1)], {})
    assert obs["first_visible_bytes"] is None
    assert not obs["delayed_500_candidate_o200k"]
    assert obs["observed_in_repair_requests"] == 0


def test_future_overlap_counts_only_requests_carrying_both_receipts():
    old = dict(observation([appearance(2), appearance(4), appearance(6)]), tool_id="old")
    newer = dict(observation([appearance(6)]), tool_id="new", step_id=5)
    old["later_same_file_version_reads"] = [{"tool_id": "new", "step_id": 5}]
    enrich_observations([old, newer], [appearance(s) for s in range(1, 7)], {})
    assert old["later_same_file_version_reads"][0]["qualifying_repair_coappearances"] == 1
    newer["appearances"] = []
    enrich_observations([old, newer], [appearance(s) for s in range(1, 7)], {})
    assert old["later_same_file_version_reads"][0]["qualifying_repair_coappearances"] == 0


def test_runtime_threshold_uses_runtime_estimate_and_keeps_last_compaction():
    requests = [
        {
            "sequence": 1,
            "step_id": 1,
            "purpose": "repair",
            "runtime_estimated_input_tokens": 47000,
            "provider_input_tokens": 50000,
        }
    ]
    assert not threshold_profile(requests, [], 48000)["reached"]
    result = threshold_profile(
        requests, [{"sequence": 2, "step_id": None, "pre_compact_tokens": 48182}], 48000
    )
    assert result["reached"]
    assert result["first"]["kind"] == "pre_compaction_plan"
    assert result["later_repair_requests"] == 0


def test_repair_pressure_excludes_the_auxiliary_compaction_prompt():
    requests = [
        {
            "sequence": 1,
            "step_id": 1,
            "purpose": "repair",
            "runtime_estimated_input_tokens": 47000,
        },
        {
            "sequence": 2,
            "step_id": None,
            "purpose": "compact",
            "runtime_estimated_input_tokens": 51617,
        },
    ]
    compactions = [{"sequence": 2, "step_id": 2, "pre_compact_tokens": 48182}]
    points = repair_pressure_points(requests, compactions)
    assert max(p["value"] for p in points) == 48182
    assert not threshold_profile(requests, compactions, 50000)["reached"]
    assert threshold_profile(requests, compactions, 48000)["later_repair_requests"] == 0


def test_test_progress_preserves_unfinished_run_and_failure_lines():
    text = (
        "[ RUN      ] suite.good\n[       OK ] suite.good (0 ms)\n"
        "[ RUN      ] suite.bad\n[  FAILED  ] suite.bad\n"
        "[1/2] Building CXX object target.o\n"
    )
    result = literal_candidates({"stdout": text}, "run_command")
    expected = len(b"[ RUN      ] suite.good\n[       OK ] suite.good (0 ms)\n")
    assert result["passing_test_progress_bytes"] == expected
    assert result["build_progress_bytes"] > 0
    assert literal_candidates({"text": text}, "read_file")["passing_test_progress_bytes"] == 0


def file_observation(identity, digest, start, text, step):
    return {
        "tool_id": identity,
        "tool": "read_file",
        "source_tree_sha256": digest,
        "data_sha256": identity,
        "file_path": "file.cc",
        "file_sha256": digest,
        "start_line": start,
        "end_line": start + len(text) - 1,
        "_file_lines": {start + i: line for i, line in enumerate(text)},
        "step_id": step,
    }


def test_overlap_requires_same_file_version_and_tracks_superseding_read():
    old = file_observation("old", "a", 10, ["line ten\n", "line eleven\n"], 1)
    overlap = file_observation("overlap", "a", 11, ["line eleven\n"], 2)
    changed = file_observation("changed", "b", 10, ["updated ten\n", "updated eleven\n"], 3)
    add_cross_observation_candidates([old, overlap, changed])
    assert overlap["same_file_version_overlap_bytes"] == len("line eleven\n")
    assert changed["same_file_version_overlap_bytes"] == 0
    assert old["new_file_version_successor"]["fully_covers_old_range"]
    assert old["later_same_file_version_overlap_bytes"] == len("line eleven\n")
    assert old["later_same_file_version_reads"][0]["tool_id"] == "overlap"


def test_patch_anchor_requires_version_match_and_full_containment_in_read():
    read = file_observation("read", "a", 10, ["original ten\n", "original eleven\n"], 1)
    edit = {
        "tool_id": "edit",
        "tool": "edit_file",
        "tool_ok": True,
        "step_id": 2,
        "edited_file_path": "file.cc",
        "edit_before_sha256": "a",
        "edit_after_sha256": "b",
        "arguments": {"old": "original eleven\n", "new": "updated eleven\n"},
    }
    wrong_version = dict(edit, tool_id="wrong-version", edit_before_sha256="c")
    outside_range = dict(edit, tool_id="outside", arguments={"old": "line outside\n"})
    add_cross_observation_candidates([read, edit, wrong_version, outside_range])
    assert [r["tool_id"] for r in read["later_matching_edits"]] == ["edit"]
    assert read["later_matching_edits"][0]["old_anchor_bytes"] == len("original eleven\n")


def test_identical_empty_data_preserves_distinct_query_identity():
    base = {"tool": "search_code", "source_tree_sha256": "tree", "data_sha256": "empty"}
    rows = [
        dict(base, tool_id=str(i), arguments={"query": query})
        for i, query in enumerate(("x", "y", "x"))
    ]
    add_cross_observation_candidates(rows)
    assert rows[1]["same_source_exact_data_previous"] == "0"
    assert rows[1]["same_source_arguments_data_previous"] is None
    assert rows[2]["same_source_arguments_data_previous"] == "0"


def test_successor_check_keeps_tool_completion_separate_from_test_outcome():
    common = {
        "tool": "run_command",
        "source_tree_sha256": "tree",
        "arguments": {"name": "verify"},
        "check_mode": "verify",
        "tool_ok": True,
        "evaluation_role": "agent_check",
    }
    old = dict(common, tool_id="old", step_id=1, test_passed=False)
    new = dict(common, tool_id="new", step_id=2, test_passed=True)
    add_cross_observation_candidates([old, new])
    successor = old["later_check_successor"]
    assert successor["old_tool_ok"] and successor["new_tool_ok"]
    assert successor["old_test_passed"] is False
    assert successor["new_test_passed"] is True
    assert successor["check_mode"] == "verify"


def test_missing_and_corrupt_archives_retain_trial_denominator(tmp_path):
    attempt = {
        "job_key": "trial-001",
        "attempt_id": "attempt-1",
        "instance_id": "task",
        "arm": "baseline",
        "repeat": 1,
        "accepted": False,
    }
    artifact = {"name": "archive-1", "digest": "sha256:" + "a" * 64}
    missing = audit_one((attempt, artifact, str(tmp_path)))
    assert missing["trial"]["status"] == "missing_archive"
    directory = tmp_path / "archive-1"
    directory.mkdir()
    (directory / "context-attempt.tar.gz").write_bytes(b"corrupt gzip")
    corrupt = audit_one((attempt, artifact, str(tmp_path)))
    assert corrupt["trial"]["status"] == "audit_error"
    result = aggregate([missing["trial"], corrupt["trial"]], [], [])
    assert result["expected_trials"] == 2
    assert result["audited_trials"] == 0


def test_oversized_tar_member_is_rejected_without_extraction(tmp_path):
    artifact = {"name": "archive", "digest": "sha256:" + "a" * 64}
    directory = tmp_path / "archive"
    directory.mkdir()
    path = directory / "context-attempt.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo("huge.bin")
        member.size = 33 * 1024 * 1024
        # Header-only fixture reaches the member-size guard before body reads.
        archive.fileobj.write(member.tobuf())
    attempt = {
        "job_key": "trial-001",
        "attempt_id": "attempt",
        "instance_id": "task",
        "arm": "baseline",
        "repeat": 1,
        "accepted": False,
    }
    result = audit_one((attempt, artifact, str(tmp_path)))
    assert "member_size_limit" in result["trial"]["error"]


def test_proxy_handles_special_token_text_as_evidence():
    assert token_proxy("<|endoftext|>") > 0
