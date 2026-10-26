"""固定 mini DefaultAgent 与 Responses 模型的零供应商压缩验收。"""

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from benchmark_budget import BudgetHooks, LocalUsageLedger
from run_benchmark_agent import MiniContextAdapter, response_text

from repropatch.context import (
    REQUEST_PURPOSE,
    SUMMARY_INSTRUCTIONS,
    SUMMARY_KEYS,
    ContextPolicy,
    encoded,
    fold_tool_output,
)


def check(source, output):
    from prepare_mini_environment import MINI_COMMIT

    assert (
        subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True, timeout=15
        ).strip()
        == MINI_COMMIT
    )
    output.mkdir(parents=True, exist_ok=False)
    os.environ["MSWEA_SILENT_STARTUP"] = "1"
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    os.environ["MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT"] = "1"
    sys.path.insert(0, str(source / "src"))
    import httpx
    import litellm
    from litellm.llms.custom_httpx.http_handler import HTTPHandler
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.exceptions import Submitted
    from minisweagent.models.litellm_response_model import LitellmResponseModel
    from minisweagent.models.utils.actions_toolcall_response import BASH_TOOL_RESPONSE_API

    for name in ("LiteLLM", "litellm", "httpx", "openai"):
        logging.getLogger(name).disabled = True
    litellm.telemetry = False
    litellm.num_retries = 0
    policy = ContextPolicy(
        compact_trigger_tokens=12_000,
        compact_target_tokens=5400,
    )
    ledger = LocalUsageLedger.create_scoped(
        output / "usage.sqlite3", {"offline-mini": 8}, context_policy=policy
    )
    hooks = BudgetHooks(ledger, "offline-mini", output / "http-native", local_luna=True)
    purposes = []
    repair_count = 0
    executed = []

    def respond(request):
        nonlocal repair_count
        purpose = REQUEST_PURPOSE.get()
        purposes.append(purpose)
        if purpose == "compact":
            items = [
                {
                    "type": "message",
                    "role": "assistant",
                    "id": "summary",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {key: "当前可见状态已保存。" for key in SUMMARY_KEYS}
                            ),
                            "annotations": [],
                        }
                    ],
                    "status": "completed",
                }
            ]
        else:
            repair_count += 1
            items = [
                {
                    "type": "function_call",
                    "name": "bash",
                    "id": f"fc_{repair_count}",
                    "call_id": f"c_{repair_count}",
                    "status": "completed",
                    "arguments": json.dumps(
                        {"command": "inspect" if repair_count == 1 else "finish"}
                    ),
                }
            ]
        incoming, outgoing = (10_000, 5000) if len(purposes) == 1 else (1000, 100)
        return httpx.Response(
            200,
            json={
                "id": f"resp_{len(purposes)}",
                "object": "response",
                "created_at": 0,
                "model": "gpt-6-luna",
                "reasoning": {"effort": "max"},
                "status": "completed",
                "output": items,
                "usage": {
                    "input_tokens": incoming,
                    "output_tokens": outgoing,
                    "total_tokens": incoming + outgoing,
                },
            },
        )

    parameters = {
        "model": "gpt-6-luna",
        "reasoning": {"effort": "max"},
        "max_output_tokens": 8192,
        "store": False,
        "stream": False,
        "tools": [BASH_TOOL_RESPONSE_API],
    }
    with httpx.Client(
        transport=httpx.MockTransport(respond),
        trust_env=False,
        event_hooks={"request": [hooks.request], "response": [hooks.response]},
    ) as http:
        native = LitellmResponseModel(
            model_name="openai/gpt-6-luna",
            cost_tracking="ignore_errors",
            model_kwargs={
                "api_base": "https://cpa.liyinlong.me/v1",
                "api_key": "offline-fixture",
                "max_output_tokens": 8192,
                "stream": False,
                "store": False,
                "num_retries": 0,
                "reasoning": {"effort": "max"},
            },
        )

        def summarize(items):
            result = http.post(
                "https://cpa.liyinlong.me/v1/responses",
                content=encoded(
                    {
                        **parameters,
                        "tools": [],
                        "instructions": SUMMARY_INSTRUCTIONS,
                        "input": [{"role": "user", "content": encoded(items).decode()}],
                    }
                ),
            )
            return response_text(result.json())

        adapter = MiniContextAdapter(native, hooks, output, parameters, summarize)
        handler = HTTPHandler(client=http, follow_redirects=False)

        class Model:
            def __getattr__(self, name):
                return getattr(native, name)

            def query(self, messages):
                adapter.prepare(messages)
                return native.query(messages, client=handler)

        class Environment:
            def execute(self, action):
                executed.append(action["command"])
                if action["command"] == "finish":
                    raise Submitted(
                        {
                            "role": "exit",
                            "content": "done",
                            "extra": {
                                "exit_status": "Submitted",
                                "submission": "done",
                            },
                        }
                    )

                def archive(raw):
                    (output / "complete-tool-output.txt").write_bytes(raw)
                    return "/build/complete-tool-output.txt"

                text = fold_tool_output("已有日志 " * 20_000, policy.tool_output_max_bytes, archive)
                return {"returncode": 0, "output": text, "exception_info": None}

            def get_template_vars(self):
                return {}

            def serialize(self):
                return {}

        agent = DefaultAgent(
            Model(),
            Environment(),
            system_template="Follow the supplied fixture task.",
            instance_template="{{task}}",
            step_limit=8,
            cost_limit=0,
            output_path=output / "trajectory.json",
        )
        result = agent.run("Inspect the fixture, then finish.")
    passed = (
        result["exit_status"] == "Submitted"
        and purposes == ["repair", "compact", "repair"]
        and executed == ["inspect", "finish"]
        and len(adapter.state.compactions) == 1
        and ledger.summary()["unknown_usage_requests"] == 0
    )
    report = {
        "passed": passed,
        "paid_model_requests": 0,
        "mini_commit": MINI_COMMIT,
        "request_purposes": purposes,
        "executed": executed,
        "context": adapter.state.to_dict(),
        "usage": ledger.summary(),
    }
    (output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "context"}, ensure_ascii=False))
    if not passed:
        raise RuntimeError("MINI_NATIVE_COMPACTION_GATE_FAILED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mini-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(args.mini_source.resolve(strict=True), args.output.resolve())
