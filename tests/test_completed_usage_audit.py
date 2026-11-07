import json
import sqlite3
from types import SimpleNamespace

import pytest
from audit_completed_usage import ledger_evidence, match_usage
from audit_context_triggers import digest
from report_context_results import failure_report


def metered_archive():
    db = sqlite3.connect(":memory:")
    db.executescript(
        "CREATE TABLE requests(id TEXT,attempt TEXT,sent_at TEXT,request_sha256 TEXT,"
        "usage TEXT,status_code INTEGER,response_sha256 TEXT,purpose TEXT);"
        "CREATE TABLE pre_send(id TEXT,attempt TEXT,sequence INTEGER,purpose TEXT,"
        "payload BLOB,issued INTEGER);"
    )
    files = {}
    for i, (purpose, instructions) in enumerate(
        [
            ("repair", "Repair the task."),
            ("compact", "Select source lines to retain from an older file observation."),
            ("compact", "Summarize the current repair state."),
        ]
    ):
        request = json.dumps({"instructions": instructions, "input": []}).encode()
        usage = {
            "input_tokens": (i + 1) * 100,
            "output_tokens": 10,
            "input_tokens_details": {"cached_tokens": 20 if i == 0 else 0},
        }
        response = json.dumps({"usage": usage}).encode()
        files[f"http/r{i}-request.json"] = request
        files[f"http/r{i}-response.json"] = response
        db.execute(
            "INSERT INTO requests VALUES (?,?,?,?,?,?,?,?)",
            (
                f"r{i}",
                "attempt",
                f"2026-11-07T00:00:0{i}+00:00",
                digest(request),
                json.dumps(usage),
                200,
                digest(response),
                purpose,
            ),
        )
        db.execute(
            "INSERT INTO pre_send VALUES (?,?,?,?,?,?)",
            (
                f"r{i}",
                "attempt",
                i,
                purpose,
                request,
                1,
            ),
        )
    db.commit()
    files["usage.sqlite3"] = db.serialize()
    db.close()
    return SimpleNamespace(files=files, read=files.__getitem__)


def test_all_auxiliary_calls_and_cache_are_counted_from_provider_responses():
    account, _, _ = ledger_evidence(metered_archive(), "usage.sqlite3", "attempt", "http/")
    assert account["usage"]["requests"] == 3
    assert account["usage"]["input_tokens"] == 600
    assert account["usage"]["cached_input_tokens"] == 20
    assert account["by_role"]["repair"]["input_tokens"] == 100
    assert account["by_role"]["early_selection"]["input_tokens"] == 200
    assert account["by_role"]["history_compaction"]["input_tokens"] == 300


def test_tampered_response_is_rejected():
    archive = metered_archive()
    archive.files["http/r1-response.json"] += b" "
    with pytest.raises(ValueError, match="response_hash"):
        ledger_evidence(archive, "usage.sqlite3", "attempt", "http/")


def test_omitted_compaction_usage_is_rejected():
    account, _, _ = ledger_evidence(metered_archive(), "usage.sqlite3", "attempt", "http/")
    expected = {**account["usage"], "repair_requests": 1, "compact_requests": 2}
    match_usage(account["usage"], expected)
    with pytest.raises(ValueError, match="usage_mismatch:input_tokens"):
        match_usage(account["usage"], {**expected, "input_tokens": 100})


def test_failure_report_uses_registered_arms_and_each_task_denominator():
    records = [
        {"instance_id": "task", "arm": arm, "accepted": True}
        for arm in ("baseline", "early", "early_state")
    ]
    analysis = {
        "arms": dict.fromkeys(("baseline", "early", "early_state")),
        "task_results": {"task": {"baseline": 1, "early": 1, "early_state": 1}},
    }
    report = failure_report(records, analysis)
    assert "## 1 题逐组通过数" in report
    assert "| 任务 | baseline | early | early_state |" in report
    assert "| `task` | 1/1 | 1/1 | 1/1 |" in report
