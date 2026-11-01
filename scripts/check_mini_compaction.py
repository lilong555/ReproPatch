"""固定 mini DefaultAgent 与 Responses 模型的零供应商压缩验收。"""

import argparse
import hashlib
import inspect
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


def verify_native_source(source):
    """逐字节核对固定 Git 提交中的 Python 源码。"""
    from prepare_mini_environment import MINI_COMMIT

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(source), *args], timeout=15, stderr=subprocess.PIPE
        )

    assert git("rev-parse", "HEAD").decode().strip() == MINI_COMMIT
    untracked = git("ls-files", "--others", "--exclude-standard", "--", "src")
    assert not any(path.endswith(b".py") for path in untracked.splitlines())
    source_hashes = {}
    for entry in git("ls-tree", "-rz", "HEAD", "--", "src/minisweagent").split(b"\0"):
        if not entry:
            continue
        metadata, filename = entry.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        name = filename.decode()
        if not name.endswith(".py"):
            continue
        assert mode in {"100644", "100755"} and kind == "blob"
        path = source / name
        assert path.is_file() and not path.is_symlink()
        content = path.read_bytes()
        git_hash = hashlib.new(
            "sha1" if len(oid) == 40 else "sha256",
            f"blob {len(content)}\0".encode() + content,
        ).hexdigest()
        assert git_hash == oid, "MINI_NATIVE_SOURCE_CHANGED: " + name
        source_hashes[name] = hashlib.sha256(content).hexdigest()
    assert source_hashes
    return MINI_COMMIT, source_hashes


def check(source, output, *, native_context=True):
    mini_commit, source_hashes = verify_native_source(source)
    output.mkdir(parents=True, exist_ok=False)
    os.environ["MSWEA_GLOBAL_CONFIG_DIR"] = str(output / "mini-settings")
    os.environ["MSWEA_GLOBAL_COST_LIMIT"] = "0"
    os.environ["MSWEA_GLOBAL_CALL_LIMIT"] = "0"
    os.environ["MSWEA_COST_TRACKING"] = "ignore_errors"
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

    assert (
        Path(inspect.getfile(DefaultAgent)).resolve()
        == (source / "src/minisweagent/agents/default.py").resolve()
    )
    assert (
        Path(inspect.getfile(LitellmResponseModel)).resolve()
        == (source / "src/minisweagent/models/litellm_response_model.py").resolve()
    )
    for name in ("LiteLLM", "litellm", "httpx", "openai"):
        logging.getLogger(name).disabled = True
    litellm.telemetry = False
    litellm.num_retries = 0
    policy = (
        ContextPolicy(
            compaction_enabled=False,
            request_cap=None,
            context_policy_version="native-executors-v1",
        )
        if native_context
        else ContextPolicy(compact_trigger_tokens=12_000, compact_target_tokens=5400)
    )
    ledger = LocalUsageLedger.create_scoped(
        output / "usage.sqlite3",
        {"offline-mini": None if native_context else 8},
        context_policy=policy,
    )
    hooks = BudgetHooks(ledger, "offline-mini", output / "http-native", local_luna=True)
    purposes = []
    repair_count = 0
    executed = []
    observations = []
    complete_output = "已有日志 " * 20_000
    opaque_state = "native_opaque_fixture_" * 4096

    def respond(request):
        nonlocal repair_count
        purpose = REQUEST_PURPOSE.get()
        purposes.append(purpose)
        request_body = json.loads(request.content)
        outputs = [
            item.get("output", "")
            for item in request_body.get("input", [])
            if item.get("type") == "function_call_output"
        ]
        observations.append(
            {
                "purpose": purpose,
                "transport_bytes": len(request.content),
                "complete_output_preserved": any(complete_output in text for text in outputs),
                "opaque_state_preserved": any(
                    item.get("encrypted_content") == opaque_state
                    for item in request_body.get("input", [])
                ),
            }
        )
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
        if native_context and purpose == "repair" and repair_count == 1:
            items.insert(
                0,
                {
                    "type": "reasoning",
                    "id": "rs_native_fixture",
                    "summary": [],
                    "encrypted_content": opaque_state,
                },
            )
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

        adapter = (
            None
            if native_context
            else MiniContextAdapter(native, hooks, output, parameters, summarize)
        )
        handler = HTTPHandler(client=http, follow_redirects=False)

        class Model:
            def __getattr__(self, name):
                return getattr(native, name)

            def query(self, messages):
                if adapter is not None:
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

                if native_context:
                    (output / "complete-tool-output.txt").write_text(complete_output)
                    text = complete_output
                else:
                    text = fold_tool_output(complete_output, policy.tool_output_max_bytes, archive)
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
            step_limit=0 if native_context else 8,
            cost_limit=0,
            output_path=output / "trajectory.json",
        )
        result = agent.run("Inspect the fixture, then finish.")
    native_history_valid = (
        purposes == ["repair", "repair"]
        and observations[-1]["complete_output_preserved"]
        and observations[-1]["opaque_state_preserved"]
        and adapter is None
    )
    adapter_history_valid = (
        purposes == ["repair", "compact", "repair"]
        and adapter is not None
        and len(adapter.state.compactions) == 1
    )
    passed = (
        result["exit_status"] == "Submitted"
        and executed == ["inspect", "finish"]
        and (native_history_valid if native_context else adapter_history_valid)
        and ledger.summary("offline-mini")["unknown_usage_requests"] == 0
    )
    report = {
        "passed": passed,
        "paid_model_requests": 0,
        "fixture_requests": len(purposes),
        "usage_source": "fixed_mock_responses",
        "mini_commit": mini_commit,
        "native_source_sha256": source_hashes,
        "native_source_verified": True,
        "context_management": "native" if native_context else "benchmark_adapter",
        "step_limit": agent.config.step_limit,
        "native_observation_template": native.config.observation_template,
        "request_purposes": purposes,
        "request_observations": observations,
        "complete_output_bytes": len(complete_output.encode()),
        "executed": executed,
        "context": adapter.state.to_dict() if adapter is not None else None,
        "usage": ledger.summary("offline-mini"),
    }
    (output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in {"context", "native_source_sha256", "native_observation_template"}
            },
            ensure_ascii=False,
        )
    )
    if not passed:
        raise RuntimeError("MINI_NATIVE_COMPACTION_GATE_FAILED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mini-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context-mode", choices=("native", "adapter"), default="native")
    args = parser.parse_args()
    check(
        args.mini_source.resolve(strict=True),
        args.output.resolve(),
        native_context=args.context_mode == "native",
    )
