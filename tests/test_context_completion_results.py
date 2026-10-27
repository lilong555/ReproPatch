"""补充评分保留首轮事实，并对收费复验连续计量。"""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import summarize_context_completion as summary
from summarize_context_campaign import row_sha, totals


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(summary, "ROOT", tmp_path)
    protocol_path = tmp_path / "benchmarks/context-revalidation-protocol.json"
    protocol_path.parent.mkdir()
    protocol_path.write_text("{}")
    rows = []
    for arm in summary.ARMS:
        usage = {"issued_requests": 1, "unknown_usage_requests": int(arm == "full")}
        rows.append(
            {
                "attempt_id": "old/" + arm,
                "instance_id": "fmt-1",
                "arm": arm,
                "usage": usage,
                "oracle_result": "INFRASTRUCTURE_FAILED"
                if arm == "full"
                else "NOT_EXECUTED"
                if arm == "shell-only"
                else "PASS",
                "stop_reason": "USER_CANCELLED" if arm == "shell-only" else "COMPLETED",
            }
        )
    original = {
        "attempts": rows,
        "tasks": ["fmt-1"],
        "paired_tasks": [],
        "campaign_paid_history": rows,
        "campaign_usage": totals(rows),
        "campaign_paid_attempts": 5,
        "oracle_results": {"PASS": 3, "NOT_EXECUTED": 1, "INFRASTRUCTURE_FAILED": 1},
    }
    updated = {
        "attempt_id": "new/full",
        "original_attempt_id": "old/full",
        "instance_id": "fmt-1",
        "arm": "full",
        "oracle_result": "PASS",
        "stop_reason": "COMPLETED",
        "usage": {"issued_requests": 2, "unknown_usage_requests": 0},
    }
    score = {
        "attempt_id": "old/shell-only",
        "instance_id": "fmt-1",
        "arm": "shell-only",
        "oracle_result": "PASS",
        "stop_reason": "USER_CANCELLED",
        "scoring_model_requests": 0,
        "candidate_sha256": "saved-candidate",
    }
    p = {
        "attempts": [{"attempt_id": "new/full", "original_attempt_id": "old/full"}],
        "oracle_attempts": [
            {"original_attempt_id": "old/shell-only", "candidate_sha256": "saved-candidate"}
        ],
        "parent_request_cap": 2520,
        "revalidation_snapshot": {"results": {"sha256": "frozen-first-run"}},
    }
    verification = {
        "source_run_id": 10,
        "passed": True,
        "failures": [],
        "issued_requests": 2,
        "campaign_issued_requests": 7,
        "records": [
            {
                "run_id": 10,
                "attempt_id": "new/full",
                "source_row_sha256": row_sha(updated),
                "usage": updated["usage"],
                "archive_sha256": "archive",
                "request_ids": ["r1", "r2"],
            },
            {
                "attempt_id": score["attempt_id"],
                "source_row_sha256": row_sha(score),
                "candidate_sha256": "saved-candidate",
            },
        ],
    }
    reruns = {"protocol_sha256": summary.sha(protocol_path), "attempts": [updated]}
    return original, p, reruns, [score], verification


@pytest.mark.parametrize(
    "problem",
    [
        None,
        "ordinary_failure",
        "changed_score",
        "duplicate_request",
        "changed_candidate",
        "reset_budget",
    ],
)
def test_completion_keeps_failures_and_accumulates_all_paid_usage(tmp_path, monkeypatch, problem):
    arguments = fixture(tmp_path, monkeypatch)
    original, p, reruns, scores, verification = arguments
    original_copy = copy.deepcopy(original)
    if problem == "ordinary_failure":
        original["attempts"][0]["oracle_result"] = "FAIL"
    elif problem == "changed_score":
        reruns["attempts"][0]["oracle_result"] = "FAIL"
    elif problem == "duplicate_request":
        verification["records"][0]["request_ids"] = ["r1", "r1"]
    elif problem == "changed_candidate":
        p["oracle_attempts"][0]["candidate_sha256"] = "different-candidate"
    elif problem == "reset_budget":
        verification["campaign_issued_requests"] = 2
    if problem:
        with pytest.raises(AssertionError):
            summary.combine(*arguments)
    else:
        result = summary.combine(*arguments)
        assert original == original_copy
        assert result["oracle_results"] == {"PASS": 5}
        assert result["campaign_usage"]["issued_requests"] == 7
        assert result["campaign_usage"]["unknown_usage_requests"] == 1
        assert result["campaign_paid_attempts"] == 6
        recovered = next(row for row in result["attempts"] if row["arm"] == "shell-only")
        assert recovered["stop_reason"] == "USER_CANCELLED" and recovered["oracle_result"] == "PASS"


def test_multiple_revalidations_keep_cumulative_budget(tmp_path, monkeypatch):
    original, p, reruns, scores, verification = fixture(tmp_path, monkeypatch)
    first = reruns["attempts"][0]
    first["oracle_result"] = "INFRASTRUCTURE_FAILED"
    first["usage"]["unknown_usage_requests"] = 1
    verification["records"][0]["source_row_sha256"] = row_sha(first)
    intermediate = summary.combine(original, p, reruns, scores, verification)
    second = {
        **first,
        "attempt_id": "second/full",
        "original_attempt_id": "new/full",
        "oracle_result": "PASS",
        "usage": {"issued_requests": 3, "unknown_usage_requests": 0},
    }
    p["attempts"] = [{"attempt_id": "second/full", "original_attempt_id": "new/full"}]
    p["oracle_attempts"] = []
    verified = {
        "source_run_id": 11,
        "passed": True,
        "failures": [],
        "issued_requests": 3,
        "campaign_issued_requests": 10,
        "records": [
            {
                "attempt_id": "second/full",
                "run_id": 11,
                "source_row_sha256": row_sha(second),
                "usage": second["usage"],
                "archive_sha256": "second-archive",
                "request_ids": ["r3", "r4", "r5"],
            }
        ],
    }
    result = summary.combine(intermediate, p, {**reruns, "attempts": [second]}, [], verified)
    assert result["campaign_usage"]["issued_requests"] == 10
    assert result["campaign_usage"]["unknown_usage_requests"] == 2
    assert result["campaign_paid_attempts"] == 7
    assert len(result["campaign_paid_history"]) == 7
