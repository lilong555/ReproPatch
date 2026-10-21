"""只读使用历史自检数据检查 SDK 上下文边界；不恢复任务、不执行容器或请求模型。"""

import argparse
import asyncio
import json
import socket
import sqlite3
from pathlib import Path
from unittest.mock import patch

from repropatch.agent_runtime import AgentStop, run_sdk
from repropatch.artifacts import EvidenceRef
from repropatch.harness import implementation_sha256
from repropatch.models import prepare_sdk
from repropatch.task import canonical_json
from repropatch.tools import model_evaluation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.run_dir.resolve(strict=True)
    report = json.loads((root / "report.json").read_bytes())
    if report["agent"]["agent_stop_reason"] != "CONTEXT_LIMIT":
        parser.error("本检查需要保存完整自检结果的 CONTEXT_LIMIT 样本")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    inputs = [r for r in report["native_trace"] if r["path"].endswith("-input.json")]
    last = inputs[-1]
    following = next(
        r for r in report["native_trace"] if r["path"] == last["path"].replace("-input", "-output")
    )
    native = json.loads(EvidenceRef(**last).read(root, limit=4 * 1024 * 1024))
    response = json.loads(EvidenceRef(**following).read(root, limit=4 * 1024 * 1024))
    call = next(item for item in response["output"] if item["type"] == "function_call")
    if call["name"] != "run_command" or json.loads(call["arguments"])["name"] != "verify":
        parser.error("最后一次响应不是预期的单条 verify 自检调用")
    with sqlite3.connect((root / "events.sqlite3").as_uri() + "?mode=ro", uri=True) as db:
        events = [json.loads(row[0]) for row in db.execute("SELECT envelope_json FROM events")]
    finished = next(
        event
        for event in events
        if event["type"] == "tool_finished"
        and event["payload"]["provider_call_id"] == call["call_id"]
    )
    original_ref = finished["payload"]["result_ref"]
    original = json.loads(EvidenceRef(**original_ref).read(root, limit=4 * 1024 * 1024))
    evaluation = next(
        item for item in report["evaluations"] if item["evaluation_role"] == "agent_check"
    )
    evidence = evaluation["evidence"]
    full = json.loads(EvidenceRef(**evidence).read(root, limit=4 * 1024 * 1024))
    # evaluation.json 写入时尚未拥有自身引用，由已核验的报告引用补全模型视图。
    full["evidence"] = evidence
    compact = {"ok": True, "data": {"passed": original["data"]["passed"], **model_evaluation(full)}}
    prepare_sdk()
    from agents import function_tool
    from agents.testing import ModelStep, ScriptedModel, assistant_message
    from openai.types.responses import ResponseFunctionToolCall, ResponseReasoningItem

    native_output = [
        (ResponseFunctionToolCall if item["type"] == "function_call" else ResponseReasoningItem)(
            **item
        )
        for item in response["output"]
    ]

    async def scenario(name, value):
        observed = []

        @function_tool(failure_error_function=None)
        async def run_command(name: str) -> str:
            """仅返回已保存的反馈，不运行命令。"""
            assert name == "verify"
            return canonical_json(value).decode()

        async def boundary(data):
            current = {
                "instructions": data.model_data.instructions,
                "input": data.model_data.input,
            }
            observed.append(current)
            if len(canonical_json(current)) > 256 * 1024:
                raise AgentStop("CONTEXT_LIMIT")
            return data.model_data

        model = ScriptedModel(
            [ModelStep(output=native_output), ModelStep(output=[assistant_message("离线检查结束")])]
        )
        stopped = None
        try:
            await run_sdk(
                model=model,
                input_items=native["input"],
                instructions=native["instructions"],
                tools=[run_command],
                hooks=None,
                input_filter=boundary,
                max_turns=2,
                max_output_tokens=8192,
                model_timeout=5,
                run_timeout=15,
            )
        except AgentStop as error:
            stopped = str(error)
        if stopped is None:
            model.assert_complete()
        assert observed[0] == native
        assert observed[1]["input"][: len(native["input"])] == native["input"]
        for number, current in enumerate(observed, 1):
            (output / f"{name}-{number}-input.json").write_bytes(canonical_json(current) + b"\n")
        return {
            "tool_result_bytes": len(canonical_json(value)),
            "input_bytes": [len(canonical_json(item)) for item in observed],
            "scripted_model_calls": len(model.calls),
            "stop_reason": stopped,
            "history_prefix_unchanged": True,
        }

    def deny_network(*args, **kwargs):
        raise AssertionError("离线反馈检查禁止网络")

    async def scenarios():
        return {
            "original": await scenario("original", original),
            "compact": await scenario("compact", compact),
        }

    with (
        patch.object(socket.socket, "connect", deny_network),
        patch.object(socket.socket, "connect_ex", deny_network),
        patch.object(socket, "create_connection", deny_network),
    ):
        results = asyncio.run(scenarios())
    assert results["original"]["stop_reason"] == "CONTEXT_LIMIT"
    assert results["compact"]["stop_reason"] is None
    assert len(compact["data"]["tests"]) == len(full["tests"])
    summary = {
        "scope": "历史数据的离线 SDK 输入边界检查，不是修复重跑或产品 Execution Replay",
        "implementation_sha256": implementation_sha256(),
        "historical_provenance": report["provenance"],
        "historical_tool_result": original_ref,
        "historical_evaluation": evidence,
        "test_observations_retained": len(full["tests"]),
        "failure_command_previews_retained": len(compact["data"]["failed_commands"]),
        "model_http_requests": 0,
        "results": results,
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
