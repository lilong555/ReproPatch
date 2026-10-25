"""正式批次固定额度、真实用量闭合与参数准入。"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_budget import BudgetLimit, LocalUsageLedger


def payload(effort="max"):
    return json.dumps(
        {
            "model": "gpt-6-luna",
            "reasoning": {"effort": effort},
            "input": "test",
            "max_output_tokens": 8192,
        }
    ).encode()


def test_formal_allocations_are_closed_and_cannot_be_transferred(tmp_path):
    ledger = LocalUsageLedger.create_scoped(tmp_path / "usage.sqlite3", {"first": 1, "second": 1})
    with pytest.raises(BudgetLimit, match="UNREGISTERED_FORMAL_ATTEMPT"):
        ledger.reserve("third", payload())
    with pytest.raises(BudgetLimit, match="FORMAL_REQUEST_PARAMETERS"):
        ledger.reserve("first", payload("medium"))
    identity = ledger.reserve("first", payload())
    with pytest.raises(BudgetLimit, match="FORMAL_USAGE_UNSETTLED"):
        ledger.reserve("second", payload())
    ledger.settle(identity, b'{"usage":{"input_tokens":1,"output_tokens":1}}', 200)
    with pytest.raises(BudgetLimit, match="BENCHMARK_REQUEST_LIMIT"):
        ledger.reserve("first", payload())
    second = ledger.reserve("second", payload())
    ledger.settle(second, b'{"usage":{"input_tokens":2,"output_tokens":2}}', 200)
    assert ledger.summary()["requests"] == 2


def test_unknown_provider_usage_stops_new_calls(tmp_path):
    ledger = LocalUsageLedger.create_scoped(tmp_path / "usage.sqlite3", {"first": 12})
    identity = ledger.reserve("first", payload())
    ledger.settle(identity, b'{"error":"transport"}', 502)
    with pytest.raises(BudgetLimit, match="FORMAL_USAGE_UNSETTLED"):
        ledger.reserve("first", payload())
    assert ledger.summary()["requests"] == 1
