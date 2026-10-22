"""只覆盖真实模型费用控制的跨请求边界，不重复 Agent 执行契约。"""

import importlib.util
import json
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime
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
        ledger.summary()["committed_upper_bound_cny"]
        > 2 * budget.request_reservation() / budget.NANO_PER_CNY
    )


def test_http_request_limit_applies_even_when_measured_usage_is_zero(tmp_path):
    ledger = budget.BudgetLedger.create(tmp_path / "cost.sqlite3")
    for _ in range(12):
        identity = ledger.reserve("same-attempt", b"request")
        ledger.settle(identity, b'{"usage":{"input_tokens":0,"output_tokens":0}}', 200)
    with pytest.raises(budget.BudgetLimit):
        ledger.reserve("same-attempt", b"request")
    assert ledger.summary()["requests"] == 12


def test_policy_price_change_updates_reservation_and_settlement(tmp_path, monkeypatch):
    monkeypatch.setitem(budget.POLICY, "peak_input_nano_per_token", 3000)
    monkeypatch.setitem(budget.POLICY, "peak_cached_input_nano_per_token", 60)
    monkeypatch.setitem(budget.POLICY, "peak_output_nano_per_token", 10000)
    monkeypatch.setattr(
        budget, "POLICY_JSON", json.dumps(budget.POLICY, sort_keys=True, separators=(",", ":"))
    )
    ledger = budget.BudgetLedger.create(tmp_path / "changed-price.sqlite3")
    identity = ledger.reserve("changed-price", b"request")
    with ledger.connect() as db:
        assert db.execute("SELECT reserved FROM requests").fetchone()[0] == 3_227_648_000
    ledger.settle(
        identity,
        b'{"usage":{"input_tokens":1000,"output_tokens":100,'
        b'"input_tokens_details":{"cached_tokens":100}}}',
        200,
    )
    assert ledger.summary()["known_usage_cost_upper_bound_cny"] == 0.003706


def test_check_only_validates_inputs_without_model_or_budget_side_effects(
    task, tmp_path, monkeypatch, capsys
):
    import yaml

    from repropatch.task import Task
    from repropatch.workspace import git_tree

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    monkeypatch.setitem(sys.modules, "benchmark_budget", budget)
    worker_spec = importlib.util.spec_from_file_location(
        "benchmark_worker_check",
        Path(__file__).resolve().parents[1] / "scripts/run_benchmark_agent.py",
    )
    worker = importlib.util.module_from_spec(worker_spec)
    worker_spec.loader.exec_module(worker)

    verified_today = budget.POLICY["verified_date"]

    class FrozenDate(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromisoformat(verified_today + "T12:00:00+00:00")

    monkeypatch.setattr(budget, "datetime", FrozenDate)

    def forbidden(*args, **kwargs):
        raise AssertionError("只读预检不能创建模型、运行目录或费用预留")

    for name in ("repropatch_agent", "mini_agent", "BudgetHooks"):
        monkeypatch.setattr(worker, name, forbidden)
    monkeypatch.setattr(budget.BudgetLedger, "reserve", forbidden)
    original_get = worker.os.environ.get

    def environment_get(key, *args):
        if key in {"DEEPSEEK_API_KEY", "OPENAI_API_KEY"}:
            forbidden()
        return original_get(key, *args)

    monkeypatch.setattr(worker.os.environ, "get", environment_get)
    value = yaml.safe_load(task.source_bytes)
    value["budget"].update(
        max_steps=12, max_tool_calls=24, max_output_tokens=8192, model_timeout_seconds=90
    )
    task_path = tmp_path / "frozen-task.yaml"
    task_path.write_text(yaml.safe_dump(value))
    frozen = Task.load(task_path)
    ledger = budget.BudgetLedger.create(tmp_path / "preflight.sqlite3")
    output = tmp_path / "must-not-exist"
    base = [
        "run_benchmark_agent.py",
        "--check-only",
        "--task",
        str(task_path),
        "--ledger",
        str(ledger.path),
        "--attempt",
        "preflight",
        "--output",
        str(output),
    ]

    def check(agent, extra=()):
        monkeypatch.setattr(sys, "argv", [*base, "--agent", agent, *extra])
        code = worker.main()
        result = json.loads(capsys.readouterr().out)
        assert not output.exists()
        with ledger.connect() as db:
            assert db.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 0
        return code, result

    assert check("repropatch")[0] == 0
    for field, wrong in [
        ("max_steps", 11),
        ("max_output_tokens", 2048),
        ("model_timeout_seconds", 45),
    ]:
        old = value["budget"][field]
        value["budget"][field] = wrong
        task_path.write_text(yaml.safe_dump(value))
        assert check("repropatch")[1]["error_code"] == "BENCHMARK_TASK_BUDGET_MISMATCH"
        value["budget"][field] = old
    task_path.write_text(yaml.safe_dump(value))
    missing = tmp_path / "missing.sqlite3"
    assert check("repropatch", ["--ledger", str(missing)])[0] == 2
    assert not missing.exists()
    bad_policy = tmp_path / "bad-policy.sqlite3"
    bad_policy.write_bytes(ledger.path.read_bytes())
    with sqlite3.connect(bad_policy) as db:
        db.execute("UPDATE budget SET policy='{}'")
    assert check("repropatch", ["--ledger", str(bad_policy)])[1]["error_code"] == (
        "BENCHMARK_BUDGET_POLICY_MISMATCH"
    )
    with monkeypatch.context() as local:
        local.setitem(budget.POLICY, "verified_date", "2000-01-01")
        assert check("repropatch")[1]["error_code"] == "BENCHMARK_PRICING_REVIEW_REQUIRED"
    assert check("mini")[1]["error_code"] == "BENCHMARK_MINI_ARGUMENT_MISSING"

    import prepare_mini_environment

    monkeypatch.setattr(prepare_mini_environment, "MINI_COMMIT", frozen.revision)
    native = frozen.repository / "src/minisweagent/agents/default.py"
    native.parent.mkdir(parents=True)
    native.write_text("# 预检源码样本，不导入执行。\n")
    environment = tmp_path / "environment.json"
    preparation = tmp_path / "preparation.json"
    environment.write_text(json.dumps({"image": frozen.environment.image, "forward_env": []}))
    preparation.write_text(
        json.dumps(
            {
                "mini_commit": frozen.revision,
                "base_commit": frozen.revision,
                "image_id": frozen.environment.image,
                "editable_files": list(frozen.editable_paths),
                "native_source_sha256": {
                    "agents/default.py": worker.hashlib.sha256(native.read_bytes()).hexdigest()
                },
            }
        )
    )
    tracked = {entry.path for entry in git_tree(frozen.repository, frozen.revision)}
    common = {
        "task": frozen.prompt,
        "base_commit": frozen.revision,
        "image_id": frozen.environment.image,
        "editable": sorted(frozen.editable_paths),
        "budget": asdict(frozen.budget),
        "readable": sorted(
            path
            for path in tracked
            if any(
                path == name or (name.endswith("/") and path.startswith(name))
                for name in frozen.readable_paths
            )
        ),
    }
    common_path = tmp_path / "common.json"

    def save_common():
        common_path.write_text(
            json.dumps({"input": [{"role": "user", "content": json.dumps(common)}]})
        )

    save_common()
    extra = [
        "--mini-source",
        str(frozen.repository),
        "--mini-environment",
        str(environment),
        "--common-input",
        str(common_path),
    ]
    assert check("mini", extra)[0] == 0
    common["budget"]["max_steps"] = 11
    save_common()
    assert check("mini", extra)[1]["error_code"] == "COMMON_TASK_MISMATCH"
    common["budget"]["max_steps"] = 12
    save_common()
    native.write_text("# 不同的源码。\n")
    assert check("mini", extra)[1]["error_code"] == "MINI_NATIVE_SOURCE_CHANGED"
