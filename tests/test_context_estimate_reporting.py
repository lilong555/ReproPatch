"""Estimated peaks are derived from pre-send records, separate from provider usage."""

import json
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_budget import LocalUsageLedger

from repropatch.context import ContextPolicy, encoded


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Usage reporting tests are CPU-only")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def ledger(tmp_path):
    return LocalUsageLedger.create_scoped(
        tmp_path / "usage.sqlite3",
        {"a": 24, "b": 24},
        context_policy=ContextPolicy(),
    )


def observation(usage, estimate, *, attempt="a", issued=False):
    raw = encoded(
        {
            "input": [{"role": "user", "content": "Repair source"}],
            "model": "gpt-6-luna",
            "reasoning": {"effort": "max"},
            "max_output_tokens": 8192,
        }
    )
    identity = usage.record_pre_send_telemetry(attempt, raw)
    if issued:
        usage.reserve(attempt, raw, identity=identity)
        usage.settle(identity, encoded({"usage": {"input_tokens": 123, "output_tokens": 10}}), 200)
    with usage.connect() as db:
        telemetry = json.loads(
            db.execute(
                "SELECT telemetry FROM pre_send WHERE id=?",
                (identity,),
            ).fetchone()[0]
        )
        telemetry["estimated_input_tokens"] = estimate
        db.execute(
            "UPDATE pre_send SET telemetry=? WHERE id=?", (encoded(telemetry).decode(), identity)
        )
    return identity


def test_empty_ledger_and_legacy_missing_pre_send_report_absent_estimate(tmp_path):
    usage = ledger(tmp_path)
    for legacy in (False, True):
        if legacy:
            with usage.connect() as db:
                db.execute("DROP TABLE pre_send")
        result = usage.summary()
        assert result["peak_estimated_input_tokens"] is None
        assert result["estimated_input_coverage"] == "absent"
        assert result["estimated_input_observations"] == 0
        assert result["unknown_estimated_input_observations"] == 0
        assert result["peak_single_input_tokens"] == 0


def test_estimated_peak_is_distinct_from_actual_and_scoped_by_attempt(tmp_path):
    usage = ledger(tmp_path)
    observation(usage, 26_274, issued=True)
    observation(usage, 17_207, issued=True)
    observation(usage, 36_023, attempt="b", issued=True)
    result = usage.summary()
    assert result["peak_estimated_input_tokens"] == 36_023
    assert result["peak_single_input_tokens"] == 123
    assert result["estimated_input_observations"] == 3
    assert result["unknown_estimated_input_observations"] == 0
    assert result["estimated_input_coverage"] == "complete"
    assert usage.summary("a")["peak_estimated_input_tokens"] == 26_274
    assert usage.summary("b")["peak_estimated_input_tokens"] == 36_023


def test_unissued_pre_send_observations_are_included_without_spending_calls(tmp_path):
    usage = ledger(tmp_path)
    observation(usage, 50_063)
    result = usage.summary("a")
    assert result["peak_estimated_input_tokens"] == 50_063
    assert result["requests"] == result["issued_requests"] == 0
    assert result["peak_single_input_tokens"] == 0
    assert result["estimated_input_coverage"] == "complete"


@pytest.mark.parametrize("value", [None, -1, True, "48000", 48_000.5])
def test_unknown_or_invalid_estimate_is_visible_as_partial_coverage(tmp_path, value):
    usage = ledger(tmp_path)
    observation(usage, 12_345)
    observation(usage, value)
    result = usage.summary()
    assert result["peak_estimated_input_tokens"] == 12_345
    assert result["estimated_input_observations"] == 1
    assert result["unknown_estimated_input_observations"] == 1
    assert result["estimated_input_coverage"] == "partial"


def test_missing_estimate_is_not_replaced_with_actual_usage(tmp_path):
    usage = ledger(tmp_path)
    identity = observation(usage, None, issued=True)
    with usage.connect() as db:
        telemetry = json.loads(
            db.execute("SELECT telemetry FROM pre_send WHERE id=?", (identity,)).fetchone()[0]
        )
        telemetry.pop("estimated_input_tokens")
        db.execute(
            "UPDATE pre_send SET telemetry=? WHERE id=?", (encoded(telemetry).decode(), identity)
        )
    result = usage.summary()
    assert result["peak_estimated_input_tokens"] is None
    assert result["peak_single_input_tokens"] == 123
    assert result["estimated_input_coverage"] == "absent"
    assert result["unknown_estimated_input_observations"] == 1


def test_zero_is_a_valid_recorded_estimate(tmp_path):
    usage = ledger(tmp_path)
    observation(usage, 0)
    result = usage.summary()
    assert result["peak_estimated_input_tokens"] == 0
    assert result["estimated_input_coverage"] == "complete"


def test_live_cpu_estimator_is_reported_without_overriding_ledger(tmp_path):
    usage = ledger(tmp_path)
    raw = encoded({"input": [{"role": "user", "content": "Repair source"}]})
    identity = usage.record_pre_send_telemetry("a", raw)
    with usage.connect() as db:
        telemetry = json.loads(
            db.execute("SELECT telemetry FROM pre_send WHERE id=?", (identity,)).fetchone()[0]
        )
    assert usage.summary("a")["peak_estimated_input_tokens"] == telemetry["estimated_input_tokens"]
