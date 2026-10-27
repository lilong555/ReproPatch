"""统一计量、历史替换、配对边界和跨压缩预算的零模型测试。"""

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from repropatch.context import (
    SUMMARY_KEYS,
    ContextLimit,
    ContextPolicy,
    ContextState,
    TokenEstimator,
    complete_rounds,
    encoded,
    estimate_plain,
    fingerprint,
    fold_tool_output,
    proxy_error,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_budget import BudgetLimit, LocalUsageLedger


def policy(**overrides):
    return ContextPolicy(
        **{
            "context_window_tokens": 40_000,
            "compact_trigger_tokens": 12_000,
            "compact_target_tokens": 5400,
            "tool_growth_tokens": 4000,
            "estimation_margin_tokens": 1000,
            **overrides,
        }
    )


def payload(items=None):
    return {
        "model": "gpt-6-luna",
        "reasoning": {"effort": "max"},
        "max_output_tokens": 8192,
        "input": items or [{"role": "user", "content": "修复授权文件 src/stats.cpp"}],
    }


def summary():
    return json.dumps({key: "仅保留当前可见记录。" for key in SUMMARY_KEYS})


def response(output=None, incoming=100, outgoing=20, reasoning=0):
    return {
        "status": "completed",
        "output": output or [],
        "usage": {
            "input_tokens": incoming,
            "output_tokens": outgoing,
            "total_tokens": incoming + outgoing,
            "input_tokens_details": {"cached_tokens": incoming // 2},
            "output_tokens_details": {"reasoning_tokens": reasoning},
        },
    }


def test_opaque_state_uses_real_usage_anchor_and_survives_partial_history():
    estimator = TokenEstimator()
    first = payload()
    output = [
        {"type": "reasoning", "encrypted_content": "a" * 100_000},
        {"type": "function_call", "call_id": "c1", "name": "bash", "arguments": "{}"},
    ]
    estimator.observe(first, response(output, incoming=2000, outgoing=5010, reasoning=5000))
    delta = [{"type": "function_call_output", "call_id": "c1", "output": "已查看代码"}]
    next_body = {**first, "input": first["input"] + output + delta}
    measured = estimator.estimate(next_body)
    assert measured["opaque_state_bytes"] == 100_000
    assert measured["estimated_input_tokens"] == 7010 + estimate_plain(delta)
    assert not measured["opaque_attribution_unknown"]
    estimator.reset()
    retained = estimator.estimate(payload(output))
    assert 5000 <= retained["estimated_input_tokens"] < 6000


def fragmented_reasoning(count=17):
    return [
        {
            "type": "reasoning",
            "id": f"r-{index}",
            "summary": [],
            "encrypted_content": f"state-{index}-" + "a" * 6000,
            "content": [{"type": "reasoning_text", "text": "供应商内部推理"}],
            "metadata": {"provider": "cpa"},
            "internal_chat_message_metadata_passthrough": {"segment": index},
        }
        for index in range(count)
    ]


def cli_items(output):
    return [
        {
            key: value
            for key, value in item.items()
            if key not in {"metadata", "internal_chat_message_metadata_passthrough", "content"}
        }
        for item in output
    ]


def test_cli_normalized_reasoning_and_custom_call_keep_real_usage_anchor():
    first = payload()
    output = fragmented_reasoning() + [
        {
            "type": "custom_tool_call",
            "call_id": "edit",
            "name": "apply_patch",
            "input": "补丁",
            "metadata": {"provider": "cpa"},
            "internal_chat_message_metadata_passthrough": "opaque",
        }
    ]
    delta = [{"type": "custom_tool_call_output", "call_id": "edit", "output": "已应用补丁"}]
    estimator = TokenEstimator()
    estimator.observe(first, response(output, incoming=24654, outgoing=8529, reasoning=7858))
    body = {**first, "input": first["input"] + cli_items(output) + delta}
    measured = estimator.estimate(body)
    assert (
        measured["estimation_basis"]
        == "previous_actual_usage_plus_retained_output_plus_plain_delta"
    )
    assert measured["estimated_input_tokens"] == 24654 + 8529 + estimate_plain(delta)
    assert measured["estimated_input_tokens"] < 48000
    assert not measured["opaque_attribution_unknown"]
    assert fingerprint(cli_items(output)[-1]) != fingerprint(
        {**cli_items(output)[-1], "input": "另一补丁"}
    )
    assert fingerprint(cli_items(output)[0]) != fingerprint(
        {**cli_items(output)[0], "encrypted_content": "另一状态"}
    )


def test_partial_history_counts_each_response_reasoning_bound_once_after_restore():
    estimator = TokenEstimator()
    first = fragmented_reasoning()
    second = [{"type": "reasoning", "encrypted_content": "second-state"}]
    estimator.observe(payload(), response(first, outgoing=8010, reasoning=8000))
    estimator.observe(payload(), response(second, outgoing=8010, reasoning=8000))
    estimator = TokenEstimator(**json.loads(encoded(estimator.to_dict())))
    estimator.reset()
    retained = cli_items(first) + second
    body = payload(retained)
    measured = estimator.estimate(body)
    head = {key: value for key, value in body.items() if key != "input"}
    assert (
        measured["estimated_input_tokens"]
        == estimate_plain(head) + estimate_plain(retained) + 16000
    )
    subset = payload([retained[0]])
    assert (
        estimator.estimate(subset)["estimated_input_tokens"]
        == estimate_plain(head) + estimate_plain(subset["input"]) + 8000
    )
    assert not measured["opaque_attribution_unknown"]
    assert estimator.estimate(
        payload([{"type": "reasoning", "encrypted_content": "unknown-state"}])
    )["opaque_attribution_unknown"]


def test_normalized_multi_reasoning_compact_request_keeps_ledger_budget(tmp_path):
    ledger = LocalUsageLedger.create_scoped(
        tmp_path / "ledger.sqlite3", {"attempt": 24}, context_policy=policy()
    )
    first = payload()
    output = fragmented_reasoning()
    identity = ledger.reserve("attempt", encoded(first))
    ledger.settle(
        identity, encoded(response(output, incoming=2000, outgoing=8010, reasoning=8000)), 200
    )
    ledger = LocalUsageLedger(ledger.path)
    compact = {
        **first,
        "input": first["input"] + cli_items(output) + [{"role": "user", "content": "生成摘要"}],
    }
    identity = ledger.reserve("attempt", encoded(compact), request_purpose="compact")
    ledger.settle(identity, encoded(response(incoming=10050, outgoing=100)), 200)
    usage = ledger.summary()
    assert usage["issued_requests"] == 2 and usage["compact_requests"] == 1
    assert usage["local_rejections"] == 0 and usage["unknown_usage_requests"] == 0


def test_all_tool_results_must_be_present_before_compaction():
    calls = [
        {"type": "function_call", "call_id": name, "name": "bash", "arguments": "{}"}
        for name in ("a", "b")
    ]
    outputs = [
        {"type": "function_call_output", "call_id": name, "output": "ok"} for name in ("a", "b")
    ]
    with pytest.raises(ContextLimit, match="COMPACTION_UNSAFE"):
        complete_rounds(calls + outputs[:1])
    assert complete_rounds(calls + outputs) == [4]
    with pytest.raises(ContextLimit, match="COMPACTION_FAILED"):
        complete_rounds(outputs)


def test_rejections_have_full_body_before_admission_and_do_not_spend_requests(tmp_path):
    ledger = LocalUsageLedger.create_scoped(
        tmp_path / "ledger.sqlite3",
        {"attempt": 24},
        context_policy=policy(transport_max_bytes=1000),
    )
    raw = encoded(payload([{"role": "user", "content": "x" * 2000}]))
    with pytest.raises(BudgetLimit, match="LOCAL_TRANSPORT_LIMIT"):
        ledger.reserve("attempt", raw)
    with ledger.connect() as db:
        stored, meta, issued = db.execute(
            "SELECT payload,telemetry,issued FROM pre_send"
        ).fetchone()
    assert stored == raw and issued == 0
    assert json.loads(meta)["transport_bytes"] == len(raw)
    assert json.loads(meta)["rejection_layer"] == "LocalUsageLedger.reserve"
    assert ledger.summary()["local_rejections"] == 1 and ledger.summary()["issued_requests"] == 0
    context_ledger = LocalUsageLedger.create_scoped(
        tmp_path / "context.sqlite3",
        {"attempt": 24},
        context_policy=policy(),
    )
    with pytest.raises(BudgetLimit, match="CONTEXT_BUDGET_EXHAUSTED"):
        context_ledger.reserve(
            "attempt", encoded(payload([{"role": "user", "content": "x" * 120_000}]))
        )
    assert context_ledger.summary()["issued_requests"] == 0


def test_compaction_and_repair_share_cap_and_usage_subtotals(tmp_path):
    ledger = LocalUsageLedger.create_scoped(
        tmp_path / "ledger.sqlite3", {"attempt": 24}, context_policy=policy()
    )
    for index in range(24):
        identity = ledger.reserve(
            "attempt",
            encoded(payload()),
            request_purpose="compact" if index % 3 == 0 else "repair",
        )
        ledger.settle(identity, encoded(response(incoming=100, outgoing=10, reasoning=8)), 200)
        ledger = LocalUsageLedger(ledger.path)
    with pytest.raises(BudgetLimit, match="BENCHMARK_REQUEST_LIMIT"):
        ledger.reserve("attempt", encoded(payload()))
    result = ledger.summary()
    assert result["issued_requests"] == 24
    assert result["repair_requests"] == 16 and result["compact_requests"] == 8
    assert result["input_tokens"] == 2400 and result["cached_input_tokens"] == 1200
    assert result["output_tokens"] == 240 and result["reasoning_tokens"] == 192


def test_unscoped_ledger_uses_frozen_context_request_cap(tmp_path):
    ledger = LocalUsageLedger.create(tmp_path / "ledger.sqlite3", context_policy=policy())
    assert ledger.request_cap("attempt") == 24
    for _ in range(24):
        identity = ledger.reserve("attempt", encoded(payload()))
        ledger.settle(identity, encoded(response()), 200)
    with pytest.raises(BudgetLimit, match="BENCHMARK_REQUEST_LIMIT"):
        ledger.reserve("attempt", encoded(payload()))


@pytest.mark.parametrize("raw,declared", [(b"{", 1), (b"{}", 3), (b"", 0), (b"[]", 2)])
def test_codex_invalid_body_is_preserved_without_upstream_issue(tmp_path, raw, declared):
    from run_codex_benchmark import prepare_cli_request

    ledger = LocalUsageLedger.create(tmp_path / "ledger.sqlite3", context_policy=policy())
    with pytest.raises(ContextLimit, match="BENCHMARK_REQUEST_INVALID"):
        prepare_cli_request(ledger, "attempt", raw, declared, tmp_path)
    with ledger.connect() as db:
        stored, meta = db.execute("SELECT payload,telemetry FROM pre_send").fetchone()
    assert stored == raw
    assert json.loads(meta)["rejection_layer"] == "Codex.Model.do_POST"
    assert ledger.summary()["issued_requests"] == 0
    assert ledger.summary()["local_rejections"] == 1


def test_codex_declared_oversize_body_is_bounded_and_has_explicit_partial_evidence(tmp_path):
    from run_codex_benchmark import prepare_cli_request

    ledger = LocalUsageLedger.create(
        tmp_path / "ledger.sqlite3", context_policy=policy(transport_max_bytes=1000)
    )
    with pytest.raises(ContextLimit, match="LOCAL_TRANSPORT_LIMIT"):
        prepare_cli_request(ledger, "attempt", b"x" * 1001, 10_000_000, tmp_path)
    with ledger.connect() as db:
        meta = json.loads(db.execute("SELECT telemetry FROM pre_send").fetchone()[0])
    assert meta["transport_bytes"] == 10_000_000
    assert meta["captured_transport_bytes"] == 1001 and meta["body_complete"] is False
    assert ledger.summary()["issued_requests"] == 0


def test_state_replacement_removes_old_outputs_and_opaque_items():
    state = ContextState(policy())
    fixed = [{"role": "user", "content": "授权：src/stats.cpp"}]
    state.plan(payload(fixed))
    items = fixed + [
        {"type": "reasoning", "encrypted_content": "a" * 100_000},
        {"type": "function_call", "call_id": "a", "name": "bash", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "a", "output": "旧日志" * 30_000},
    ]
    body = payload(items)
    plan = state.plan(body)
    replacement = state.replace(body, plan, summary(), sequence=4, duration_seconds=0.1)
    assert len(encoded(replacement)) < len(encoded(items)) // 10
    assert "encrypted_content" not in encoded(replacement).decode()
    restored = ContextState.restore(state.policy, json.loads(encoded(state.to_dict())))
    assert restored.compacted_up_to_seq == 4
    assert restored.summary_state == state.summary_state
    assert restored.plan(payload(replacement)) is None


def test_oversize_tool_output_is_archived_in_full(tmp_path):
    text = "FIRST\n" + "构建日志\n" * 10_000 + "\nLAST"
    path = tmp_path / "output.log"

    def archive(raw):
        path.write_bytes(raw)
        return "/build/output.log"

    folded = fold_tool_output(text, 2048, archive)
    assert path.read_text() == text
    assert "FIRST" in folded and "LAST" in folded and "/build/output.log" in folded
    assert len(folded.encode()) <= 2060


@pytest.mark.sdk
@pytest.mark.parametrize("arm", ["full", "no-checks", "shell-only"])
def test_repropatch_modes_compact_replace_and_continue_tools(task, tmp_path, arm):
    from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox
    from run_benchmark_agent import intermediate_checks
    from test_shell_runtime import ScriptedRepairSandbox, shell_call

    from repropatch.harness import Harness

    edit = (
        shell_call("edit", "edit")
        if arm == "shell-only"
        else function_call(
            "edit_file",
            {
                "path": "src/stats.cpp",
                "old": "int best = 0;",
                "new": "int best = samples.front();",
            },
            call_id="edit",
        )
    )
    follow = (
        shell_call("inspect", "inspect")
        if arm == "shell-only"
        else function_call("read_file", {"path": "src/stats.cpp"}, call_id="read")
    )
    model = ScriptedModel(
        [
            ModelStep(
                output=[assistant_message("旧的大型诊断 " * 10_000), edit],
                raw_usage={"input_tokens": 10_000, "output_tokens": 5000, "total_tokens": 15_000},
            ),
            ModelStep(
                output=[assistant_message(summary())],
                raw_usage={"input_tokens": 1000, "output_tokens": 100, "total_tokens": 1100},
            ),
            ModelStep(
                output=[follow],
                raw_usage={"input_tokens": 2000, "output_tokens": 100, "total_tokens": 2100},
            ),
            [assistant_message("完成")],
        ]
    )
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        tool_mode="shell-only" if arm == "shell-only" else "legacy",
        repair_sandbox_factory=ScriptedRepairSandbox,
        context_policy=policy(),
        candidate_only=True,
    )
    with intermediate_checks(harness, enabled=arm != "no-checks"):
        report = harness.run()
    assert report["reason_code"] == "EXTERNAL_ORACLE_REQUIRED", report
    assert report["agent_stop_reason"] == "MODEL_FINISHED"
    assert report["model_steps"] == 4 and report["tool_calls"] == 2
    assert len(report["context"]["compactions"]) == 1
    assert len(encoded(model.calls[2].input)) < len(encoded(model.calls[1].input))
    assert "旧的大型诊断" not in encoded(model.calls[2].input).decode()
    assert len(model.calls[1].tools) == 0
    if arm == "no-checks":
        assert {t.name for t in model.calls[2].tools}.isdisjoint({"run_command", "run_shell"})
        assert len(report["evaluations"]) == 1
    model.assert_complete()


@pytest.mark.sdk
@pytest.mark.parametrize("failure", ["timeout", "invalid"])
def test_compaction_failure_freezes_existing_candidate(task, tmp_path, failure):
    from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call
    from conftest import SimulatedSandbox

    from repropatch.harness import Harness

    async def fail(call):
        raise TimeoutError("受控摘要超时")

    model = ScriptedModel(
        [
            ModelStep(
                output=[
                    assistant_message("原始记录 " * 20_000),
                    function_call(
                        "edit_file",
                        {
                            "path": "src/stats.cpp",
                            "old": "int best = 0;",
                            "new": "int best = samples.front();",
                        },
                        call_id="edit",
                    ),
                ],
                raw_usage={"input_tokens": 10_000, "output_tokens": 5000, "total_tokens": 15_000},
            ),
            ModelStep(responder=fail)
            if failure == "timeout"
            else [assistant_message("invalid json")],
        ]
    )
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        context_policy=policy(),
        candidate_only=True,
    )
    result = harness.run()
    assert result["agent_stop_reason"] == "COMPACTION_FAILED", result
    assert result["cleanup_confirmed"]
    assert (harness.directory / "patch.diff").read_bytes()
    assert result["model_steps"] == 2 and result["tool_calls"] == 1


def test_mini_adapter_replaces_public_messages_and_counts_summary(tmp_path):
    from run_benchmark_agent import MiniContextAdapter

    ledger = LocalUsageLedger.create_scoped(
        tmp_path / "ledger.sqlite3", {"attempt": 24}, context_policy=policy()
    )
    hooks = SimpleNamespace(ledger=ledger, attempt="attempt")
    native = SimpleNamespace(_prepare_messages_for_api=lambda messages: list(messages))
    calls = []

    def summarize(items):
        calls.append(items)
        identity = ledger.reserve("attempt", encoded(payload()), request_purpose="compact")
        ledger.settle(identity, encoded(response()), 200)
        return summary()

    adapter = MiniContextAdapter(native, hooks, tmp_path, payload(), summarize)
    messages = payload()["input"]
    adapter.prepare(messages)
    messages.extend(
        [
            {"type": "function_call", "call_id": "c", "name": "bash", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "c", "output": "原始日志 " * 30_000},
        ]
    )
    adapter.prepare(messages)
    assert len(calls) == 1 and len(messages) == 2
    assert "Visible state checkpoint" in messages[-1]["content"]
    adapter.prepare(messages)
    assert ledger.summary()["compact_requests"] == 1
    assert (tmp_path / "context/0001-original-history.json").is_file()


def test_codex_config_and_compact_request_are_recognized():
    from run_codex_benchmark import COMPACT_MARKER, native_settings, request_kind

    settings = native_settings("max", 180, policy())
    assert settings["model_context_window"] == 40_000
    assert settings["model_auto_compact_token_limit"] == 12_000
    assert (
        request_kind(
            {
                "tools": [],
                "input": [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": settings["compact_prompt"]}],
                    },
                ],
            }
        )
        == "compact"
    )
    assert (
        request_kind(
            {
                "tools": [{"type": "function"}],
                "input": [
                    {"role": "user", "content": COMPACT_MARKER},
                ],
            }
        )
        == "repair"
    )
    assert proxy_error("LOCAL_TRANSPORT_LIMIT")[0] == 413
    assert proxy_error("REQUEST_BUDGET_EXHAUSTED")[0] == 400
    assert proxy_error("MODEL_RATE_LIMIT")[0] == 429


@pytest.mark.sdk
def test_codex_total_deadline_closes_and_settles_stream(tmp_path):
    import httpx2
    from run_codex_benchmark import read_model_stream_async

    ledger = LocalUsageLedger.create(tmp_path / "ledger.sqlite3")
    identity = ledger.reserve("attempt", encoded(payload()))

    class Endless(httpx2.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            while True:
                yield b'data: {"type":"response.created"}\n\n'
                await asyncio.sleep(0.01)

        async def aclose(self):
            self.closed = True

    stream = Endless()

    async def exercise():
        async with httpx2.AsyncClient(
            transport=httpx2.MockTransport(lambda request: httpx2.Response(200, stream=stream))
        ) as client:
            with pytest.raises(ContextLimit, match="MODEL_TIMEOUT"):
                await read_model_stream_async(
                    client,
                    "http://offline.invalid",
                    encoded(payload()),
                    {},
                    tmp_path,
                    identity,
                    ledger,
                    first_byte_timeout=0.1,
                    idle_timeout=0.1,
                    total_timeout=0.08,
                )

    asyncio.run(exercise())
    assert stream.closed
    meta = json.loads((tmp_path / (identity + "-transport.json")).read_text())
    assert meta["timeout_phase"] == "total" and meta["received_bytes"] > 0
    assert ledger.summary()["unknown_usage_requests"] == 1


@pytest.mark.sdk
@pytest.mark.parametrize("intermediate", [True, False])
def test_resume_uses_compacted_checkpoint_and_remaining_budget(
    task, tmp_path, monkeypatch, intermediate
):
    from agents.testing import assistant_message, function_call
    from conftest import SimulatedSandbox
    from run_benchmark_agent import intermediate_checks

    from repropatch.artifacts import EvidenceRef
    from repropatch.events import read_events
    from repropatch.harness import Harness
    from repropatch.models import load_sdk_script
    from repropatch.recovery import read_checkpoint, resume_run

    outputs = [
        [
            assistant_message("可见旧轨迹 " * 10_000),
            function_call(
                "edit_file",
                {
                    "path": "src/stats.cpp",
                    "old": "int best = 0;",
                    "new": "int best = samples.front();",
                },
                call_id="edit",
            ),
        ],
        [assistant_message(summary())],
        [function_call("read_file", {"path": "src/stats.cpp"}, call_id="read")],
        [assistant_message("完成")],
    ]
    script = {
        "version": 1,
        "steps": [
            {
                "output": [item.model_dump(mode="json", exclude_none=True) for item in items],
                "usage": {
                    "input_tokens": 10_000 if index == 0 else 1000,
                    "output_tokens": 5000 if index == 0 else 100,
                    "total_tokens": 15_000 if index == 0 else 1100,
                },
            }
            for index, items in enumerate(outputs)
        ],
    }
    path = tmp_path / "script.json"
    path.write_bytes(encoded(script))
    harness = Harness(
        task,
        load_sdk_script(path),
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        context_policy=policy(),
        pause_after_step=2,
        script_source=path.read_bytes(),
    )
    with intermediate_checks(harness, enabled=intermediate):
        paused = harness.run()
    assert paused["paused"], paused
    manifest, _ = read_checkpoint(harness.directory)
    assert manifest["schema_version"] == 2
    state = json.loads(
        EvidenceRef(**manifest["context_state"]).read(harness.directory, limit=100_000)
    )
    assert state["compacted_up_to_seq"] == 2
    native = json.loads(
        EvidenceRef(**manifest["native_next_input"]).read(harness.directory, limit=100_000)
    )
    assert "可见旧轨迹" not in encoded(native).decode()
    before = read_events(harness.directory, harness.directory.name).run
    import repropatch.agent_runtime as runtime

    original = runtime.run_sdk
    observed = []

    async def capture(**kwargs):
        observed.append((kwargs["input_items"], kwargs["max_turns"]))
        return await original(**kwargs)

    monkeypatch.setattr(runtime, "run_sdk", capture)
    result = resume_run(harness.directory, sandbox_factory=SimulatedSandbox)
    assert result["outcome"] == "ACCEPTED", result
    assert observed == [(native["input"], task.max_steps - 2)]
    assert result["model_steps"] == 4 and result["tool_calls"] == 2
    assert len(result["context"]["compactions"]) == 1
    after = read_events(harness.directory, harness.directory.name).run
    assert after["deadline_at"] == before["deadline_at"]


@pytest.mark.parametrize("size", [263_986, 263_166])
def test_full_rejection_geometry_is_preserved_and_new_policy_admits(tmp_path, size):
    body = payload([{"role": "user", "content": ""}])
    body["input"][0]["content"] = "a" * (size - len(encoded(body)))
    raw = encoded(body)
    assert len(raw) == size
    old = LocalUsageLedger.create_scoped(tmp_path / "old.sqlite3", {"attempt": 24})
    with pytest.raises(BudgetLimit, match="LOCAL_TRANSPORT_LIMIT"):
        old.reserve("attempt", raw)
    with old.connect() as db:
        stored = db.execute("SELECT payload FROM pre_send").fetchone()[0]
    assert stored == raw and old.summary()["requests"] == 0
    new = LocalUsageLedger.create_scoped(
        tmp_path / "new.sqlite3", {"attempt": 24}, context_policy=ContextPolicy()
    )
    new.reserve("attempt", raw)
    assert new.summary()["requests"] == 1


@pytest.mark.sdk
def test_full_ledger_rejection_keeps_domain_stop_reason_and_candidate(task, tmp_path):
    from agents.testing import ModelStep, ScriptedModel, function_call
    from conftest import SimulatedSandbox

    from repropatch.harness import Harness

    def reject(call):
        raise BudgetLimit("LOCAL_TRANSPORT_LIMIT")

    model = ScriptedModel(
        [
            [
                function_call(
                    "edit_file",
                    {
                        "path": "src/stats.cpp",
                        "old": "int best = 0;",
                        "new": "int best = samples.front();",
                    },
                    call_id="edit",
                )
            ],
            ModelStep(responder=reject),
        ]
    )
    harness = Harness(
        task,
        model,
        tmp_path / "runs",
        sandbox_factory=SimulatedSandbox,
        candidate_only=True,
        context_policy=policy(),
    )
    report = harness.run()
    assert report["agent_stop_reason"] == "LOCAL_TRANSPORT_LIMIT", report
    assert report["reason_code"] == "EXTERNAL_ORACLE_REQUIRED"
    assert report["candidate"]
