"""原生上下文、开放累计额度与持续计量的离线合同。"""

import copy
import importlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from repropatch.context import ContextPolicy, encoded


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return tuple(
        importlib.import_module(name)
        for name in ("benchmark_budget", "run_benchmark_agent", "run_codex_benchmark")
    )


def native_policy():
    return ContextPolicy(
        request_cap=None,
        compaction_enabled=False,
        context_policy_version="native-executors-v1",
    )


def body():
    return {
        "model": "gpt-6-luna",
        "reasoning": {"effort": "max"},
        "max_output_tokens": 8192,
        "input": [{"role": "user", "content": "离线任务"}],
    }


def test_unlimited_allocation_preserves_counting_errors_and_registration(modules, tmp_path, task):
    budget, _, codex = modules
    ledger = budget.LocalUsageLedger.create_scoped(
        tmp_path / "usage.sqlite3", {"full": None}, context_policy=native_policy()
    )
    request = encoded(body())
    unlimited_task = replace(
        task,
        budget=replace(
            task.budget,
            max_steps=None,
            max_tool_calls=None,
            max_output_tokens=8192,
            model_timeout_seconds=180,
        ),
    )
    budget.validate_task_budget(unlimited_task, request_cap=None)
    first = ledger.reserve("full", request)
    with pytest.raises(budget.BudgetLimit, match="FORMAL_USAGE_UNSETTLED"):
        ledger.reserve("full", request)
    ledger.settle(first, b'{"error":{"code":"server_error"}}', 502)
    for number in range(30):
        purpose = "retry" if number == 0 else "repair"
        identity = ledger.reserve("full", request, request_purpose=purpose)
        ledger.settle(identity, b'{"usage":{"input_tokens":10,"output_tokens":2}}', 200)
    with pytest.raises(budget.BudgetLimit, match="UNREGISTERED_FORMAL_ATTEMPT"):
        ledger.reserve("unregistered", request)
    summary = ledger.summary("full")
    assert summary["request_cap"] is None
    assert summary["issued_requests"] == 31
    assert summary["retry_requests"] == 1
    assert summary["repair_requests"] == 30
    assert summary["unknown_usage_requests"] == 1
    assert summary["input_tokens"] is None and summary["known_input_tokens"] == 300
    assert summary["local_rejections"] == 1
    assert codex.admit_tools({"output": [{"type": "function_call"}] * 8}, 240, None) == 248
    with pytest.raises(budget.BudgetLimit, match="TOOL_BATCH_LIMIT"):
        codex.admit_tools({"output": [{"type": "function_call"}] * 9}, 0, None)


def test_unlimited_requires_explicit_policy_and_finite_allocations_keep_caps(modules, tmp_path):
    budget, _, _ = modules
    with pytest.raises(budget.BudgetLimit, match="INVALID_SCOPED_ALLOCATION"):
        budget.LocalUsageLedger.create_scoped(tmp_path / "invalid.sqlite3", {"a": None})
    for value in (0, -1, True, "unlimited"):
        with pytest.raises(budget.BudgetLimit, match="INVALID_SCOPED_ALLOCATION"):
            budget.LocalUsageLedger.create_scoped(
                tmp_path / "invalid.sqlite3", {"a": value}, context_policy=native_policy()
            )
    ledger = budget.LocalUsageLedger.create_scoped(
        tmp_path / "finite.sqlite3", {"a": 1}, context_policy=native_policy()
    )
    identity = ledger.reserve("a", encoded(body()))
    ledger.settle(identity, b'{"usage":{"input_tokens":1,"output_tokens":1}}', 200)
    with pytest.raises(budget.BudgetLimit, match="BENCHMARK_REQUEST_LIMIT"):
        ledger.reserve("a", encoded(body()))


@pytest.mark.parametrize("summary_limit", [None, 32768])
def test_codex_native_summary_payload_and_configuration_are_preserved(
    modules, tmp_path, summary_limit
):
    budget, _, codex = modules
    settings = codex.native_settings("max", 180, ContextPolicy(), native_context=True)
    for name in ("model_context_window", "model_auto_compact_token_limit", "compact_prompt"):
        assert name not in settings
    assert settings["model_reasoning_effort"] == "max"
    ledger = budget.LocalUsageLedger.create_scoped(
        tmp_path / "native.sqlite3", {"codex": None}, context_policy=native_policy()
    )
    request = {
        "model": "gpt-6-luna",
        "reasoning": {"effort": "low"},
        "stream": True,
        "tools": [],
        "input": [
            {"role": "assistant", "content": "已定位的修复状态"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": codex.COMPACT_MARKER
                        + " Create a handoff summary for another LLM that will resume the task.",
                    }
                ],
            },
        ],
    }
    if summary_limit is not None:
        request["max_output_tokens"] = summary_limit
    raw = json.dumps(request, ensure_ascii=False, indent=2).encode()
    identity, purpose, prepared, payload = codex.prepare_cli_request(
        ledger, "codex", raw, len(raw), tmp_path, native_context=True
    )
    assert payload == raw and prepared == request and purpose == "compact"
    ledger.reserve("codex", payload, identity=identity)
    ledger.settle(identity, b'{"usage":{"input_tokens":20,"output_tokens":3}}', 200)
    repair = json.dumps({**body(), "input": "摘要后的继续修复", "stream": True}).encode()
    identity, purpose, _, payload = codex.prepare_cli_request(
        ledger, "codex", repair, len(repair), tmp_path, native_context=True
    )
    ledger.reserve("codex", payload, identity=identity)
    ledger.settle(identity, b'{"usage":{"input_tokens":5,"output_tokens":1}}', 200)
    assert purpose == "repair" and ledger.summary("codex")["compact_requests"] == 1
    assert ledger.summary("codex")["repair_requests"] == 1
    assert (tmp_path / (identity + "-cli-request.json")).read_bytes() == repair


def test_native_body_limit_records_rejection_without_token_admission(modules, tmp_path):
    budget, _, codex = modules
    policy = replace(native_policy(), transport_max_bytes=400_000)
    ledger = budget.LocalUsageLedger.create_scoped(
        tmp_path / "native.sqlite3", {"codex": None}, context_policy=policy
    )
    request = body()
    request["input"] = [
        {"role": "user", "content": "x" * 270_000},
        {"type": "reasoning", "encrypted_content": "y" * 20_000},
    ]
    raw = encoded(request)
    identity, _, _, payload = codex.prepare_cli_request(
        ledger, "codex", raw, len(raw), tmp_path, native_context=True
    )
    ledger.reserve("codex", payload, identity=identity)
    ledger.settle(identity, b'{"usage":{"input_tokens":1000,"output_tokens":3}}', 200)
    assert ledger.summary("codex")["issued_requests"] == 1
    with pytest.raises(budget.BudgetLimit, match="LOCAL_TRANSPORT_LIMIT"):
        ledger.reserve("codex", encoded({**body(), "input": "x" * 400_000}))
    assert ledger.summary("codex")["local_rejections"] == 1
    assert ledger.summary("codex")["issued_requests"] == 1


def test_mini_native_history_and_large_outputs_reach_following_model_step(
    modules, monkeypatch, tmp_path, task
):
    """穿过 worker 的完整原生入口，确认 27 步后历史与工具输出仍由上游拥有。"""
    import yaml

    budget, worker, _ = modules
    ledger = budget.LocalUsageLedger.create_scoped(
        tmp_path / "mini.sqlite3", {"mini": None}, context_policy=native_policy()
    )
    hooks = budget.BudgetHooks(ledger, "mini", tmp_path / "http", local_luna=True)
    task = replace(
        task,
        budget=replace(task.budget, max_steps=None, max_tool_calls=None),
    )
    output = tmp_path / "attempt"
    output.mkdir()
    source = tmp_path / "source"
    source.mkdir()
    mini = tmp_path / "mini"
    templates = mini / "src/minisweagent/config/mini.yaml"
    templates.parent.mkdir(parents=True)
    templates.write_text(
        yaml.safe_dump(
            {"agent": {"system_template": "原生系统提示", "instance_template": "{{ task }}"}}
        )
    )
    args = SimpleNamespace(
        provider="local-luna",
        reasoning_effort="max",
        mini_source=mini,
        output=output,
        agent_seconds=60,
        native_context=True,
    )
    monkeypatch.setattr(
        worker, "mini_inputs", lambda *a: ({}, json.dumps({"readable": []}), source)
    )
    captured = []
    agent_config = {}

    class NativeModel:
        def __init__(self, **kwargs):
            pass

        def _prepare_messages_for_api(self, messages):
            pytest.fail("原生模式由上游 query 拥有载荷构造")

        def query(self, messages, **kwargs):
            captured.append(copy.deepcopy(messages))
            return {
                "role": "assistant",
                "content": "原生动作",
                "extra": {"actions": [{"command": "原生检查"}]},
            }

    class NativeAgent:
        def __init__(self, model, env, **kwargs):
            self.model, self.env = model, env
            self.n_calls = 0
            agent_config.update(kwargs)

        def run(self, task_input):
            messages = [{"role": "user", "content": task_input}]
            for _ in range(27):
                result = self.model.query(messages)
                self.n_calls += 1
                messages.append(result)
                observation = self.env.execute(result["extra"]["actions"][0])
                messages.append({"role": "user", "content": observation["output"]})
            return {"exit_status": "Submitted"}

    class NativeEnvironment:
        container_id = "offline-mini"
        calls = 0

        def execute(self, action, **kwargs):
            if action["command"].startswith("python3 -c"):
                return {"output": "", "returncode": 0}
            self.calls += 1
            return {
                "output": "完整原生输出" * 20_000 if self.calls == 1 else "原生观察",
                "returncode": 0,
            }

        def cleanup(self):
            pass

    class Interrupt(Exception):
        pass

    class OfflineHTTP:
        def __init__(self, **kwargs):
            pass

        def send(self, *args, **kwargs):
            pytest.fail("原生历史合同测试使用离线模型")

        def close(self):
            pass

    def module(name, **values):
        item = ModuleType(name)
        item.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, item)

    module("httpx", Client=OfflineHTTP)
    module("litellm", register_model=lambda *a: None)
    module("litellm.llms.custom_httpx.http_handler", HTTPHandler=lambda **kw: kw["client"])
    module("minisweagent.agents.default", DefaultAgent=NativeAgent)
    module("minisweagent.environments", get_environment=lambda *a: NativeEnvironment())
    module("minisweagent.exceptions", InterruptAgentFlow=Interrupt, LimitsExceeded=Interrupt)
    module("minisweagent.models.litellm_response_model", LitellmResponseModel=NativeModel)
    module("minisweagent.models.utils.actions_toolcall_response", BASH_TOOL_RESPONSE_API={})
    for key in (
        "MSWEA_GLOBAL_CONFIG_DIR",
        "MSWEA_SILENT_STARTUP",
        "MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT",
        "MSWEA_GLOBAL_COST_LIMIT",
        "MSWEA_GLOBAL_CALL_LIMIT",
        "MSWEA_COST_TRACKING",
        "LITELLM_LOCAL_MODEL_COST_MAP",
    ):
        monkeypatch.setenv(key, worker.os.environ.get(key, ""))

    def command(argv, **kwargs):
        if argv[:2] == ["docker", "inspect"]:
            return encoded(
                [
                    {
                        "HostConfig": {
                            "NetworkMode": "none",
                            "ReadonlyRootfs": True,
                            "CapDrop": ["ALL"],
                            "SecurityOpt": ["no-new-privileges:true"],
                            "Memory": task.environment.memory_mib * 1024 * 1024,
                            "MemorySwap": task.environment.memory_mib * 1024 * 1024,
                            "PidsLimit": task.environment.pids_limit,
                            "NanoCpus": round(task.environment.cpu_limit * 1_000_000_000),
                        },
                        "Config": {"User": "65534:65534"},
                        "Mounts": [
                            {"Destination": "/src/" + p, "Type": "bind", "RW": True}
                            for p in task.editable_paths
                        ],
                    }
                ]
            )
        if argv[:2] == ["docker", "ps"]:
            return b""
        if argv[0] == "git":
            return b"diff --git a/a.cpp b/a.cpp\n"
        pytest.fail(f"意外进程: {argv}")

    monkeypatch.setattr(worker.subprocess, "check_output", command)
    monkeypatch.setattr(worker.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0))
    monkeypatch.setattr(
        worker,
        "MiniContextAdapter",
        lambda *a: pytest.fail("原生 mini 使用自己的上下文处理"),
    )
    result = worker.mini_agent(args, hooks, task)
    assert agent_config["step_limit"] == 0
    assert result["model_steps"] == 27 and result["tool_calls_admitted"] == 27
    assert result["stop_reason"] == "COMPLETED" and result["context"] is None
    assert captured[-1][2]["content"] == "完整原生输出" * 20_000
    assert not (output / "tool-outputs").exists()
    assert not (output / "context").exists()
