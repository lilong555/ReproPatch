"""验证跨批次结果承接、失败保留和真实请求计数。"""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from summarize_context_campaign import ARMS, consolidate, row_sha, totals


def fixture_data():
    usage = {
        "issued_requests": 1,
        "unknown_usage_requests": 0,
        "known_input_tokens": 10,
        "known_output_tokens": 2,
        "cached_input_tokens": 4,
        "reasoning_tokens": 1,
        "repair_requests": 1,
        "compact_requests": 0,
        "retry_requests": 0,
    }
    rows = [
        {
            "instance_id": "task",
            "arm": arm,
            "attempt_id": "first/" + arm,
            "usage": copy.deepcopy(usage),
            "oracle_result": "PASS",
            "stop_reason": "COMPLETED",
        }
        for arm in ARMS
    ]
    protocol = {
        "model": "gpt-6-luna",
        "endpoint": "supplier",
        "reasoning_effort": "max",
        "model_timeout_seconds": 180,
        "context_policy": {},
        "task_contracts": {"task": {}},
        "execution_source_commit": "code1",
        "execution_sha256": "execution1",
        "implementation_sha256": "implementation1",
    }
    sources = [(1, protocol, {"protocol_sha256": "p1", "attempts": rows}, "p1")]
    records = [
        {
            "attempt_id": row["attempt_id"],
            "usage": copy.deepcopy(usage),
            "request_ids": ["request/" + row["arm"]],
            "interrupted": False,
            "archive_sha256": "archive/" + row["arm"],
            "source_row_sha256": row_sha(row),
        }
        for row in rows
    ]
    verification = {"passed": True, "failures": [], "records": records, "issued_requests": 5}
    historical = {"attempts": copy.deepcopy(rows)}
    return sources, verification, historical


def test_cancelled_attempt_preserves_oracle_and_usage():
    sources, verification, historical = fixture_data()
    row = sources[0][2]["attempts"][0]
    row["oracle_result"] = "FAIL"
    verification["records"][0]["interrupted"] = True
    verification["records"][0]["source_row_sha256"] = row_sha(row)
    result = consolidate(sources, verification, historical)
    cancelled = result["attempts"][0]
    assert cancelled["stop_reason"] == "USER_CANCELLED"
    assert cancelled["original_stop_reason"] == "COMPLETED"
    assert cancelled["oracle_result"] == "FAIL"
    assert result["campaign_usage"]["issued_requests"] == 5
    assert result["paired_tasks"] == []


def test_duplicate_request_id_rejected_across_attempts():
    sources, verification, historical = fixture_data()
    verification["records"][1]["request_ids"] = verification["records"][0]["request_ids"]
    with pytest.raises(ValueError, match="DUPLICATE_ISSUED_REQUEST_ID"):
        consolidate(sources, verification, historical)


def test_cached_and_reasoning_tokens_remain_subtotals():
    sources, verification, historical = fixture_data()
    result = consolidate(sources, verification, historical)["campaign_usage"]
    assert result["input_tokens"] == 50
    assert result["cached_input_tokens"] == 20
    assert result["output_tokens"] == 10
    assert result["reasoning_tokens"] == 5


def test_unknown_usage_preserves_known_totals():
    result = totals(
        [
            {
                "usage": {
                    "issued_requests": 2,
                    "unknown_usage_requests": 1,
                    "known_input_tokens": 10,
                    "known_output_tokens": 2,
                }
            }
        ]
    )
    assert result["issued_requests"] == 2
    assert result["input_tokens"] is result["output_tokens"] is None
    assert result["known_input_tokens"] == 10


def add_replacement(sources, verification, allowed):
    previous = sources[0][2]["attempts"][0]
    previous["stop_reason"] = "CONTEXT_BUDGET_EXHAUSTED"
    verification["records"][0]["source_row_sha256"] = row_sha(previous)
    next_row = {
        **copy.deepcopy(previous),
        "attempt_id": "second/full",
        "original_attempt_id": previous["attempt_id"],
        "stop_reason": "COMPLETED",
        "oracle_result": "FAIL",
    }
    protocol = {**sources[0][1], "parent_run_id": 1, "parent_protocol_sha256": "p1"}
    if allowed:
        protocol["estimator_corrections"] = {
            previous["attempt_id"]: {"archive_sha256": verification["records"][0]["archive_sha256"]}
        }
    sources.append((2, protocol, {"protocol_sha256": "p2", "attempts": [next_row]}, "p2"))
    verification["records"].append(
        {
            **copy.deepcopy(verification["records"][0]),
            "attempt_id": next_row["attempt_id"],
            "request_ids": ["second-request"],
            "source_row_sha256": row_sha(next_row),
        }
    )
    verification["issued_requests"] += 1


def test_declared_correction_keeps_latest_failure_and_old_pass():
    sources, verification, historical = fixture_data()
    add_replacement(sources, verification, True)
    result = consolidate(sources, verification, historical)
    assert result["attempts"][0]["oracle_result"] == "FAIL"
    assert result["campaign_paid_history"][0]["oracle_result"] == "PASS"
    assert result["campaign_usage"]["issued_requests"] == 6


def test_unapproved_paid_replacement_rejected():
    sources, verification, historical = fixture_data()
    add_replacement(sources, verification, False)
    with pytest.raises(ValueError, match="PAID_ATTEMPT_REPLACEMENT_UNAUTHORIZED"):
        consolidate(sources, verification, historical)


def test_protocol_contract_change_rejected():
    sources, verification, historical = fixture_data()
    add_replacement(sources, verification, True)
    sources[1][1]["context_policy"] = {"different": True}
    with pytest.raises(ValueError, match="TASK_OR_CONTEXT_CONTRACT_CHANGED"):
        consolidate(sources, verification, historical)


def test_missing_paid_evidence_rejected():
    sources, verification, historical = fixture_data()
    verification["records"].pop()
    verification["issued_requests"] -= 1
    with pytest.raises(ValueError, match="ATTEMPT_EVIDENCE_MISSING"):
        consolidate(sources, verification, historical)


def test_changed_oracle_result_rejected():
    sources, verification, historical = fixture_data()
    sources[0][2]["attempts"][0]["oracle_result"] = "FAIL"
    with pytest.raises(ValueError, match="SOURCE_RESULT_CHANGED"):
        consolidate(sources, verification, historical)
