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
from run_codex_benchmark import native_settings, request_kind

from repropatch.context import ContextPolicy, encoded


def check(binary, output):
    output.mkdir(parents=True, exist_ok=False)
    version = subprocess.check_output([str(binary), "--version"], text=True, timeout=15).strip()
    assert version == "codex-cli 0.163.0"
    policy = ContextPolicy(compact_trigger_tokens=40_000, compact_target_tokens=18_000)
    ledger = LocalUsageLedger.create_scoped(
        output / "usage.sqlite3", {"offline-codex": 8}, context_policy=policy
    )
    requests = []
    errors = []
    repairs = 0

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            nonlocal repairs
            try:
                assert self.path == "/v1/responses"
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                body = json.loads(raw)
                body["max_output_tokens"] = 8192
                purpose = request_kind(body)
                identity = ledger.reserve("offline-codex", encoded(body), request_purpose=purpose)
                (output / f"{len(requests) + 1:02d}-{purpose}-request.json").write_bytes(raw)
                requests.append({"purpose": purpose, "input_bytes": len(encoded(body["input"]))})
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
                    incoming = 45_000
                else:
                    repairs += 1
                    incoming = 45_000 if repairs == 1 else 3000
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
    settings = native_settings("max", 30, policy)
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
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    kinds = [r["purpose"] for r in requests]
    events = (output / "events.jsonl").read_text()
    compact_at = kinds.index("compact") if "compact" in kinds else -1
    continued = compact_at >= 0 and "repair" in kinds[compact_at + 1 :]
    passed = (
        result.returncode == 0
        and not errors
        and continued
        and "CONTEXT_FIXTURE_1" in events
        and "CONTEXT_FIXTURE_2" in events
        and requests[compact_at + 1]["input_bytes"] < requests[compact_at]["input_bytes"]
        and ledger.summary()["unknown_usage_requests"] == 0
    )
    report = {
        "passed": passed,
        "paid_model_requests": 0,
        "fixture_requests": len(requests),
        "requests": requests,
        "version": version,
        "errors": errors,
        "exit_code": result.returncode,
        "continued_tools_after_compaction": continued,
        "duration_seconds": time.monotonic() - started,
        "usage": ledger.summary(),
    }
    (output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    if not passed:
        raise RuntimeError("CODEX_NATIVE_COMPACTION_GATE_FAILED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(args.binary.resolve(strict=True), args.output.resolve())
