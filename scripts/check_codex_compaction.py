"""使用固定本地 Responses 夹具验证原生 Codex 的摘要、历史替换和后续工具执行。"""

import argparse
import http.server
import json
import os
import subprocess
import threading
import time
from pathlib import Path

from benchmark_budget import LocalUsageLedger
from run_codex_benchmark import admit_tools, native_settings, prepare_cli_request

from repropatch.context import ContextPolicy, encoded


def check(binary, output, *, native_context=True):
    output.mkdir(parents=True, exist_ok=False)
    version = subprocess.check_output([str(binary), "--version"], text=True, timeout=15).strip()
    assert version == "codex-cli 0.163.0"
    policy = (
        ContextPolicy(
            request_cap=None,
            compaction_enabled=False,
            context_policy_version="native-executors-v1",
        )
        if native_context
        else ContextPolicy(compact_trigger_tokens=40_000, compact_target_tokens=18_000)
    )
    ledger = LocalUsageLedger.create_scoped(
        output / "usage.sqlite3",
        {"offline-codex": None if native_context else 8},
        context_policy=policy,
    )
    requests = []
    errors = []
    repairs = 0
    admitted = 0
    # 固定 CLI 的默认阈值由其模型元数据决定；夹具只报告触发所需的模拟 Usage。
    trigger_usage = 250_000 if native_context else 45_000

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            nonlocal repairs, admitted
            try:
                assert self.path == "/v1/responses"
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                identity, purpose, body, payload = prepare_cli_request(
                    ledger,
                    "offline-codex",
                    raw,
                    len(raw),
                    output,
                    native_context=native_context,
                )
                ledger.reserve("offline-codex", payload, identity=identity)
                (output / f"{len(requests) + 1:02d}-{purpose}-request.json").write_bytes(raw)
                requests.append(
                    {
                        "purpose": purpose,
                        "input_bytes": len(encoded(body["input"])),
                        "transport_bytes": len(payload),
                        "native_summary_body_preserved": payload == raw
                        if purpose == "compact"
                        else None,
                        "request_reasoning": body.get("reasoning"),
                        "request_max_output_tokens": body.get("max_output_tokens"),
                    }
                )
                if purpose == "compact":
                    items = [
                        {
                            "type": "message",
                            "id": "msg_summary",
                            "role": "assistant",
                            "status": "completed",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": (
                                        "The first fixture shell command completed. "
                                        "Run the next fixture shell command, then finish."
                                    ),
                                    "annotations": [],
                                }
                            ],
                        }
                    ]
                    incoming = trigger_usage
                else:
                    repairs += 1
                    incoming = trigger_usage if repairs == 1 else 3000
                    if repairs <= 2:
                        script = (
                            "const r = await tools.exec_command("
                            + json.dumps({"cmd": f"printf CONTEXT_FIXTURE_{repairs}"})
                            + "); text(r.output);"
                        )
                        items = [
                            {
                                "type": "custom_tool_call",
                                "id": f"ctc_{repairs}",
                                "call_id": f"call_{repairs}",
                                "name": "exec",
                                "input": script,
                                "status": "completed",
                            }
                        ]
                        if repairs == 1:
                            items.insert(
                                0,
                                {
                                    "type": "reasoning",
                                    "id": "rs_fixture",
                                    "summary": [],
                                    "encrypted_content": "opaque_fixture_state_" * 5000,
                                },
                            )
                    else:
                        items = [
                            {
                                "type": "message",
                                "id": "msg_final",
                                "role": "assistant",
                                "status": "completed",
                                "content": [
                                    {
                                        "type": "output_text",
                                        "text": "Fixture complete.",
                                        "annotations": [],
                                    }
                                ],
                            }
                        ]
                outgoing = 5100 if purpose == "repair" and repairs == 1 else 100
                result = {
                    "id": f"resp_{len(requests)}",
                    "object": "response",
                    "created_at": 0,
                    "model": "gpt-6-luna",
                    "status": "completed",
                    "output": items,
                    "usage": {
                        "input_tokens": incoming,
                        "output_tokens": outgoing,
                        "total_tokens": incoming + outgoing,
                        "output_tokens_details": {
                            "reasoning_tokens": 5000 if outgoing == 5100 else 0
                        },
                    },
                }
                admitted = admit_tools(result, admitted, None if native_context else 16)
                events = [
                    {
                        "type": "response.created",
                        "response": {**result, "status": "in_progress", "output": []},
                    }
                ]
                for index, item in enumerate(items):
                    events.append(
                        {"type": "response.output_item.added", "output_index": index, "item": item}
                    )
                    events.append(
                        {"type": "response.output_item.done", "output_index": index, "item": item}
                    )
                events.append({"type": "response.completed", "response": result})
                ledger.settle(identity, encoded(result), 200)
                stream = b"".join(b"data: " + encoded(event) + b"\n\n" for event in events)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(stream)))
                self.end_headers()
                self.wfile.write(stream)
            except Exception as error:
                errors.append(type(error).__name__ + ": " + str(error))
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"OFFLINE_FIXTURE_REJECTED"}}')

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    settings = native_settings("max", 30, policy, native_context=native_context)
    override_keys = ("model_context_window", "model_auto_compact_token_limit", "compact_prompt")
    if native_context:
        assert all(key not in settings for key in override_keys)
    settings["model_providers.benchmark.base_url"] = f"http://127.0.0.1:{server.server_port}/v1"
    (output / "native-config.json").write_bytes(encoded(settings))
    command = [
        str(binary),
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--sandbox",
        "danger-full-access",
        "--skip-git-repo-check",
        "--color",
        "never",
    ]
    for key, value in settings.items():
        command.extend(["-c", key + "=" + json.dumps(value)])
    command.append("Run the fixture shell commands supplied by the model and finish.")
    environment = {
        k: v
        for k, v in os.environ.items()
        if k not in {"OPENAI_API_KEY", "CPA_API_KEY", "DEEPSEEK_API_KEY"}
    }
    environment.update(CODEX_HOME=str(output / "codex-home"), BENCHMARK_MODEL_KEY="offline-fixture")
    (output / "codex-home").mkdir()
    started = time.monotonic()
    returncode = None
    try:
        with (output / "events.jsonl").open("wb") as out, (output / "stderr.log").open("wb") as err:
            result = subprocess.run(
                command,
                cwd=output,
                env=environment,
                stdout=out,
                stderr=err,
                timeout=90,
            )
            returncode = result.returncode
    except subprocess.TimeoutExpired:
        errors.append("CODEX_FIXTURE_TIMEOUT")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    kinds = [r["purpose"] for r in requests]
    events = (output / "events.jsonl").read_text()
    compact_at = kinds.index("compact") if "compact" in kinds else -1
    continued = compact_at >= 0 and "repair" in kinds[compact_at + 1 :]
    passed = (
        returncode == 0
        and not errors
        and continued
        and "CONTEXT_FIXTURE_1" in events
        and "CONTEXT_FIXTURE_2" in events
        and requests[compact_at + 1]["input_bytes"] < requests[compact_at]["input_bytes"]
        and ledger.summary("offline-codex")["unknown_usage_requests"] == 0
        and (
            not native_context
            or (
                all(key not in settings for key in override_keys)
                and all(
                    row["native_summary_body_preserved"]
                    for row in requests
                    if row["purpose"] == "compact"
                )
            )
        )
    )
    report = {
        "passed": passed,
        "paid_model_requests": 0,
        "fixture_requests": len(requests),
        "usage_source": "fixed_mock_responses",
        "context_management": "native" if native_context else "benchmark_adapter",
        "compaction_trigger": "CLI 原生默认阈值与模拟 Usage"
        if native_context
        else "夹具自定义低阈值",
        "mock_first_input_tokens": trigger_usage,
        "context_configuration_overrides": {
            key: settings[key] for key in override_keys if key in settings
        },
        "requests": requests,
        "version": version,
        "errors": errors,
        "exit_code": returncode,
        "tool_calls_admitted": admitted,
        "continued_tools_after_compaction": continued,
        "duration_seconds": time.monotonic() - started,
        "usage": ledger.summary("offline-codex"),
    }
    (output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    if not passed:
        raise RuntimeError("CODEX_NATIVE_COMPACTION_GATE_FAILED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--context-mode", choices=("native", "adapter"), default="native")
    args = parser.parse_args()
    check(
        args.binary.resolve(strict=True),
        args.output.resolve(),
        native_context=args.context_mode == "native",
    )
