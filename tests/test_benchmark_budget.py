"""只覆盖真实模型费用控制的跨请求边界，不重复 Agent 执行契约。"""

import importlib.util
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "benchmark_budget", Path(__file__).resolve().parents[1] / "scripts/benchmark_budget.py"
)
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)


def test_parallel_unknown_requests_cannot_overdraw_or_recreate_budget(tmp_path):
    path = tmp_path / "cost.sqlite3"
    ledger = budget.BudgetLedger.create(path)

    def reserve(number):
        try:
            ledger.reserve(str(number), b"request")
            return True
        except budget.BudgetLimit:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(30))) == 9
    summary = ledger.summary()
    assert summary["unknown_usage_requests"] == 9
    assert 19 < summary["committed_upper_bound_cny"] <= 20
    with pytest.raises(FileExistsError):
        budget.BudgetLedger.create(path)
    path.unlink()
    with pytest.raises(sqlite3.OperationalError):
        ledger.reserve("later", b"request")


def test_settlement_requires_provider_usage_and_is_not_repeatable(tmp_path):
    ledger = budget.BudgetLedger.create(tmp_path / "cost.sqlite3")
    first = ledger.reserve("mini", b"request")
    content = json.dumps(
        {
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 100,
                "total_tokens": 1100,
                "input_tokens_details": {"cached_tokens": 100},
            }
        }
    ).encode()
    ledger.settle(first, content, 200)
    assert ledger.summary()["known_usage_cost_upper_bound_cny"] == 0.002604
    with pytest.raises(budget.BudgetLimit):
        ledger.settle(first, content, 200)
    second = ledger.reserve("rp", b"request")
    ledger.settle(second, b'{"usage":{}}', 200)
    third = ledger.reserve("rp", b"request")
    ledger.settle(third, b'{"error":"denied"}', 401)
    assert ledger.summary()["unknown_usage_requests"] == 2
    assert (
        ledger.summary()["committed_upper_bound_cny"] > 2 * budget.RESERVATION / budget.NANO_PER_CNY
    )


def test_http_request_limit_applies_even_when_measured_usage_is_zero(tmp_path):
    ledger = budget.BudgetLedger.create(tmp_path / "cost.sqlite3")
    for _ in range(12):
        identity = ledger.reserve("same-attempt", b"request")
        ledger.settle(identity, b'{"usage":{"input_tokens":0,"output_tokens":0}}', 200)
    with pytest.raises(budget.BudgetLimit):
        ledger.reserve("same-attempt", b"request")
    assert ledger.summary()["requests"] == 12
