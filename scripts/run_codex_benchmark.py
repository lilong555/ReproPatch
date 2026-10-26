"""在统一只读源码容器内运行原生 Codex CLI，并保存限额模型流和候选补丁。"""

import argparse
import asyncio
import hashlib
import http.client
import http.server
import json
import os
import shlex
import socket
import socketserver
import subprocess
import sys
import threading
import time
import uuid
from contextlib import AsyncExitStack
from pathlib import Path

from repropatch.context import (
    SUMMARY_INSTRUCTIONS,
    ContextLimit,
    encoded,
    proxy_error,
    stop_reason,
)

COMPACT_MARKER = "You are performing a CONTEXT CHECKPOINT COMPACTION."


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def native_settings(reasoning_effort="max", model_timeout_seconds=90, policy=None):
    """原生 CLI 的固定配置，推理强度同时由上游请求留证。"""
    values = {
        "model_provider": "benchmark",
        "model": "gpt-6-luna",
        "approval_policy": "never",
        "model_reasoning_effort": reasoning_effort,
        "web_search": "disabled",
        "model_providers.benchmark.name": "CPA isolated metered relay",
        "model_providers.benchmark.base_url": "http://127.0.0.1:8318/v1",
        "model_providers.benchmark.env_key": "BENCHMARK_MODEL_KEY",
        "model_providers.benchmark.wire_api": "responses",
        "model_providers.benchmark.request_max_retries": 0,
        "model_providers.benchmark.stream_max_retries": 0,
        "model_providers.benchmark.stream_idle_timeout_ms": (model_timeout_seconds + 10) * 1000,
        "model_providers.benchmark.supports_websockets": False,
    }
    if policy and policy.compaction_enabled:
        values.update(
            model_context_window=policy.context_window_tokens,
            model_auto_compact_token_limit=policy.compact_trigger_tokens,
            compact_prompt=(
                COMPACT_MARKER
                + "\n"
                + SUMMARY_INSTRUCTIONS
                + "\nThe next context must fit within "
                + str(policy.compact_target_tokens)
                + " tokens including fixed instructions."
            ),
        )
    return values


def request_kind(body):
    """固定 CLI 的本地摘要具有空工具集和末尾专用用户提示。"""
    items = body.get("input") or []
    if not isinstance(items, list) or not items or body.get("tools"):
        return "repair"
    last = items[-1]
    content = last.get("content", "")
    text = (
        content
        if isinstance(content, str)
        else "\n".join(item.get("text", "") for item in content if isinstance(item, dict))
    )
    return "compact" if last.get("role") == "user" and text.startswith(COMPACT_MARKER) else "repair"


def prepare_cli_request(ledger, attempt, raw, declared_size, trace):
    """完整或部分 CLI 正文先留证；有效请求再统一输出额度并记录上游载荷。"""
    policy = ledger.policy
    try:
        if declared_size > policy.transport_max_bytes:
            raise ContextLimit("LOCAL_TRANSPORT_LIMIT")
        if declared_size != len(raw) or declared_size <= 0:
            raise ContextLimit("BENCHMARK_REQUEST_INVALID")
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError("MODEL_REQUEST_OBJECT")
        purpose = request_kind(body)
    except (ContextLimit, ValueError, TypeError, AttributeError) as error:
        identity = ledger.record_pre_send_telemetry(
            attempt, raw, declared_transport_bytes=declared_size
        )
        (trace / (identity + "-cli-request.partial")).write_bytes(raw)
        reason = error.reason if isinstance(error, ContextLimit) else "BENCHMARK_REQUEST_INVALID"
        ledger.reject(identity, reason, "Codex.Model.do_POST")
        raise ContextLimit(reason, detail=identity) from error
    body["max_output_tokens"] = policy.max_output_tokens
    payload = encoded(body)
    identity = ledger.record_pre_send_telemetry(attempt, payload, request_purpose=purpose)
    (trace / (identity + "-cli-request.json")).write_bytes(raw)
    (trace / (identity + "-request.json")).write_bytes(payload)
    return identity, purpose, body, payload


async def read_model_stream_async(
    client,
    url,
    payload,
    headers,
    trace,
    identity,
    ledger,
    *,
    first_byte_timeout,
    idle_timeout,
    total_timeout,
):
    """总期限覆盖连接和全部流读取；关闭传输、结算后才允许返回可执行事件。"""
    started = time.monotonic()
    metadata = {
        "request_id": identity,
        "http_status": None,
        "first_byte_seconds": None,
        "last_byte_seconds": None,
        "received_bytes": 0,
        "response_completed_seen": False,
        "usage_complete": False,
        "error_type": None,
        "cause_type": None,
        "timeout_phase": None,
        "first_byte_timeout_seconds": first_byte_timeout,
        "idle_timeout_seconds": idle_timeout,
        "total_timeout_seconds": total_timeout,
    }
    data = bytearray()
    completed, status = None, None
    phase = "first_byte"
    parsed_lines = 0

    def parse():
        nonlocal completed, parsed_lines
        lines = data.split(b"\n")
        for line in lines[parsed_lines:-1]:
            if line.startswith(b"data: ") and line.strip() != b"data: [DONE]":
                event = json.loads(line[6:])
                if event.get("type") in {
                    "response.completed",
                    "response.incomplete",
                    "response.failed",
                }:
                    completed = event.get("response")
                    metadata["response_completed_seen"] = event["type"] == "response.completed"
        parsed_lines = len(lines) - 1

    try:
        with (trace / (identity + "-response.sse")).open("xb") as evidence:
            async with asyncio.timeout(total_timeout):
                async with AsyncExitStack() as resources:
                    async with asyncio.timeout(first_byte_timeout):
                        response = await resources.enter_async_context(
                            client.stream("POST", url, content=payload, headers=headers)
                        )
                    status = response.status_code
                    metadata["http_status"] = status
                    content_type = response.headers.get("Content-Type", "text/event-stream")
                    iterator = response.aiter_bytes().__aiter__()
                    while True:
                        remaining = (
                            first_byte_timeout - (time.monotonic() - started)
                            if metadata["first_byte_seconds"] is None
                            else idle_timeout
                        )
                        try:
                            chunk = await asyncio.wait_for(anext(iterator), max(0.001, remaining))
                        except StopAsyncIteration:
                            break
                        if not chunk:
                            continue
                        now = time.monotonic() - started
                        if metadata["first_byte_seconds"] is None:
                            metadata["first_byte_seconds"] = now
                        metadata["last_byte_seconds"] = now
                        metadata["received_bytes"] += len(chunk)
                        evidence.write(chunk)
                        evidence.flush()
                        data.extend(chunk)
                        if len(data) > ledger.policy.response_max_bytes:
                            raise ContextLimit("MODEL_SERVER_ERROR", detail="响应流超过物理上限")
                        if status == 200:
                            parse()
                        phase = "stream_idle"
            if status == 200 and not metadata["response_completed_seen"]:
                raise ContextLimit("MODEL_SERVER_ERROR", detail="SSE缺少完成事件")
        return status, bytes(data), content_type, completed
    except Exception as error:
        metadata["error_type"] = type(error).__name__
        metadata["cause_type"] = type(error.__cause__).__name__ if error.__cause__ else None
        if stop_reason(error) == "MODEL_TIMEOUT":
            metadata["timeout_phase"] = (
                "total" if time.monotonic() - started >= total_timeout else phase
            )
            raise ContextLimit("MODEL_TIMEOUT", detail=metadata["timeout_phase"]) from error
        raise
    finally:
        usage = (completed or {}).get("usage") or {}
        metadata["usage_complete"] = status == 200 and all(
            type(usage.get(key)) is int and usage[key] >= 0
            for key in ("input_tokens", "output_tokens")
        )
        content = encoded(completed) if completed else bytes(data)
        (trace / (identity + "-response.json")).write_bytes(content)
        save(trace / (identity + "-transport.json"), metadata)
        ledger.settle(identity, content, status if status is not None else 0)


def read_model_stream(client, url, payload, headers, trace, identity, ledger):
    """逐块持久化 SSE，完整响应完成计量后再交给工具准入。"""
    started = time.monotonic()
    metadata = {
        "request_id": identity,
        "http_status": None,
        "first_byte_seconds": None,
        "last_byte_seconds": None,
        "received_bytes": 0,
        "response_completed_seen": False,
        "usage_complete": False,
        "error_type": None,
        "cause_type": None,
    }
    data = bytearray()
    status = None
    completed = None
    content_type = "text/event-stream"
    try:
        with (trace / (identity + "-response.sse")).open("xb") as evidence:
            with client.stream("POST", url, content=payload, headers=headers) as response:
                status = response.status_code
                metadata["http_status"] = status
                content_type = response.headers.get("Content-Type", content_type)
                for chunk in response.iter_bytes():
                    if not chunk:
                        continue
                    received = time.monotonic() - started
                    if metadata["first_byte_seconds"] is None:
                        metadata["first_byte_seconds"] = received
                    metadata["last_byte_seconds"] = received
                    evidence.write(chunk)
                    evidence.flush()
                    data.extend(chunk)
                    metadata["received_bytes"] += len(chunk)
        for line in data.splitlines():
            if not line.startswith(b"data: ") or line == b"data: [DONE]":
                continue
            event = json.loads(line[6:])
            if event.get("type") in {
                "response.completed",
                "response.incomplete",
                "response.failed",
            }:
                completed = event.get("response")
                metadata["response_completed_seen"] = event["type"] == "response.completed"
        if status == 200 and not metadata["response_completed_seen"]:
            raise ValueError("MODEL_RESPONSE_INCOMPLETE")
        return status, bytes(data), content_type, completed
    except Exception as error:
        metadata["error_type"] = type(error).__name__
        metadata["cause_type"] = type(error.__cause__).__name__ if error.__cause__ else None
        raise
    finally:
        usage = (completed or {}).get("usage") or {}
        metadata["usage_complete"] = status == 200 and all(
            type(usage.get(key)) is int and usage[key] >= 0
            for key in ("input_tokens", "output_tokens")
        )
        content = json.dumps(completed, ensure_ascii=False).encode() if completed else bytes(data)
        (trace / (identity + "-response.json")).write_bytes(content)
        save(trace / (identity + "-transport.json"), metadata)
        # 传输异常使用本地状态 0 完成一次结算，HTTP 状态仍在元数据中保留未知。
        ledger.settle(identity, content, status if status is not None else 0)


def admit_tools(completed, admitted, maximum):
    """整批检查后返回累计额度，调用者随后才转发可执行事件。"""
    from benchmark_budget import BudgetLimit

    calls = sum(
        item.get("type") in {"function_call", "custom_tool_call"}
        for item in (completed or {}).get("output", [])
    )
    if calls > 8:
        raise BudgetLimit("TOOL_BATCH_LIMIT")
    if admitted + calls > maximum:
        raise BudgetLimit("TOOL_BUDGET")
    return admitted + calls


def stop_container(name):
    """终止本次拥有的容器及其进程，确认删除后允许读取候选。"""
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)
    left = subprocess.check_output(
        ["docker", "ps", "-aq", "--filter", "name=^/" + name + "$"], timeout=30
    )
    if left.strip():
        raise RuntimeError("CODEX_CONTAINER_CLEANUP_UNCONFIRMED")


def export_candidate(source, output):
    """容器停止后保存候选字节及身份。"""
    from run_benchmark_agent import candidate_metadata

    patch = subprocess.check_output(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-C",
            str(source),
            "diff",
            "--binary",
            "HEAD",
            "--",
        ],
        timeout=30,
    )
    (output / "candidate.patch").write_bytes(patch)
    return candidate_metadata(patch)


class UnixHTTP(http.client.HTTPConnection):
    """容器仅连接挂载的模型代理套接字。"""

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect("/model/socket")


def relay():
    class Relay(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            connection = UnixHTTP(
                "localhost", timeout=int(os.environ.get("BENCHMARK_RELAY_TIMEOUT_SECONDS", "100"))
            )
            try:
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                connection.request("POST", self.path, body, {"Content-Type": "application/json"})
                response = connection.getresponse()
                data = response.read()
                self.send_response(response.status)
                self.send_header(
                    "Content-Type", response.getheader("Content-Type", "application/json")
                )
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            finally:
                connection.close()

    http.server.HTTPServer(("127.0.0.1", 8318), Relay).serve_forever()


def main():
    import httpx2
    from benchmark_budget import BudgetLimit, LocalUsageLedger, validate_task_budget
    from run_benchmark_agent import attempt_identity, candidate_metadata, mini_inputs

    from repropatch.task import Task

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--mini-source", type=Path, required=True)
    parser.add_argument("--mini-environment", type=Path, required=True)
    parser.add_argument("--common-input", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--agent-seconds", type=int, required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        default="max",
        help="Codex 原生推理强度，默认 max；实际请求参数逐次保存",
    )
    args = parser.parse_args()
    task = Task.load(args.task)
    ledger = LocalUsageLedger(args.ledger)
    validate_task_budget(task, request_cap=ledger.request_cap(args.attempt))
    config, common, source = mini_inputs(args, task)
    subprocess.run(
        ["git", "-C", str(source), "diff", "--quiet", "HEAD", "--"], check=True, timeout=30
    )
    binary = args.binary.resolve(strict=True)
    code_host = binary.with_name("codex-code-mode-host").resolve(strict=True)
    version = subprocess.check_output([str(binary), "--version"], timeout=10).decode().strip()
    if version != "codex-cli 0.163.0":
        parser.error("CODEX_VERSION_MISMATCH")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "task.original.yaml").write_bytes(task.source_bytes)
    relay_file = output / "adapter.py"
    relay_file.write_bytes(Path(__file__).read_bytes())
    relay_file.chmod(0o644)
    (output / "common-input.json").write_bytes(args.common_input.read_bytes())
    (output / "task.yaml").write_bytes(args.task.read_bytes())
    trace = output / "http-native"
    trace.mkdir()
    transport = output / "transport"
    transport.mkdir(mode=0o755)
    # 容器用户需要遍历挂载目录；显式权限保持独立于宿主 umask。
    transport.chmod(0o755)
    socket_path = transport / "socket"
    key = None if args.check_only else os.environ["OPENAI_API_KEY"]
    policy = ledger.policy
    state = {
        "tool_calls_admitted": 0,
        "observed_request_reasoning": [],
        "errors": [],
        "compactions": [],
        "closing": False,
    }

    async def upstream_request(payload, identity):
        async with httpx2.AsyncClient(
            trust_env=True, follow_redirects=False, timeout=task.budget.model_timeout_seconds
        ) as client:
            return await read_model_stream_async(
                client,
                "https://cpa.liyinlong.me/v1/responses",
                payload,
                {
                    "Authorization": "Bearer " + key,
                    "Content-Type": "application/json",
                    "User-Agent": "ReproPatch-Codex-Benchmark/1",
                    "Accept-Encoding": "identity",
                },
                trace,
                identity,
                ledger,
                first_byte_timeout=task.budget.model_timeout_seconds,
                idle_timeout=task.budget.model_timeout_seconds,
                total_timeout=task.budget.model_timeout_seconds,
            )

    class Model(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, data, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            identity = None
            purpose = "repair"
            compact_record = None
            try:
                if self.path == "/health":
                    self.reply(200, b'{"transport":"ok"}')
                    return
                if args.check_only or state["closing"] or self.path != "/v1/responses":
                    raise ValueError("MODEL_ROUTE_REJECTED")
                size = int(self.headers.get("Content-Length", "0"))
                self.connection.settimeout(30)
                raw = self.rfile.read(max(0, min(size, policy.transport_max_bytes + 1)))
                identity, purpose, body, payload = prepare_cli_request(
                    ledger, args.attempt, raw, size, trace
                )
                state["observed_request_reasoning"].append(body.get("reasoning"))
                if body.get("model") != "gpt-6-luna" or body.get("stream") is not True:
                    raise ValueError("MODEL_SETTINGS_MISMATCH")
                if any(t.get("type") not in {"function", "custom"} for t in body.get("tools", [])):
                    raise ValueError("EXTERNAL_TOOL_REJECTED")
                if not policy.compaction_enabled and (
                    len(json.dumps(body.get("input"), ensure_ascii=False).encode())
                    > policy.transport_max_bytes
                ):
                    raise BudgetLimit("CONTEXT_LIMIT")
                # CLI 保留原生提示与工具协议；代理统一每请求输出上限并记录原始请求。
                ledger.reserve(args.attempt, payload, identity=identity)
                if purpose == "compact":
                    compact_record = {
                        "request_id": identity,
                        "started": time.monotonic(),
                        "pre_compact_tokens": ledger.estimator(args.attempt).estimate(body)[
                            "estimated_input_tokens"
                        ],
                        "pre_transport_bytes": len(payload),
                        "cli_event_offset": (output / "events.jsonl").stat().st_size,
                        "status": "started",
                    }
                    state["compactions"].append(compact_record)
                # 共用 ReproPatch 的 HTTP 客户端与宿主代理配置，保留原始 SSE 字节。
                status, data, content_type, completed = asyncio.run(
                    upstream_request(payload, identity)
                )
                if status != 200 and purpose != "compact":
                    try:
                        response_error = json.loads(data).get("error", {})
                    except ValueError:
                        response_error = {}
                    code = (
                        "MODEL_CONTEXT_EXCEEDED"
                        if response_error.get("code") == "context_length_exceeded"
                        else "MODEL_RATE_LIMIT"
                        if status == 429
                        else "MODEL_SERVER_ERROR"
                        if status >= 500
                        else "MODEL_REQUEST_FAILED"
                    )
                    state["errors"].append(
                        {
                            "request_id": identity,
                            "code": code,
                            "upstream_status": status,
                        }
                    )
                    self.reply(status, data, content_type)
                    return
                if purpose == "compact":
                    if (
                        status != 200
                        or not completed
                        or any(
                            item.get("type") not in {"message", "reasoning"}
                            for item in completed.get("output", [])
                        )
                    ):
                        raise ContextLimit("COMPACTION_FAILED")
                    compact_record.update(
                        status="completed",
                        duration_seconds=time.monotonic() - compact_record.pop("started"),
                    )
                elif (
                    state["compactions"] and "post_transport_bytes" not in state["compactions"][-1]
                ):
                    state["compactions"][-1].update(
                        post_transport_bytes=len(payload),
                        post_compact_tokens=(completed or {}).get("usage", {}).get("input_tokens"),
                        response_has_tools=any(
                            item.get("type") in {"function_call", "custom_tool_call"}
                            for item in (completed or {}).get("output", [])
                        ),
                    )
                state["tool_calls_admitted"] = admit_tools(
                    completed, state["tool_calls_admitted"], task.budget.max_tool_calls
                )
                self.reply(status, data, content_type)
            except Exception as error:
                # 异常仅记录类型和本地稳定码，供应商敏感正文保存在私有原始证据中。
                code = (
                    stop_reason(error)
                    if isinstance(error, ContextLimit)
                    else str(error)
                    if isinstance(error, ValueError)
                    else stop_reason(error)
                )
                if identity is None and isinstance(error, ContextLimit):
                    identity = error.detail
                if compact_record is not None and compact_record["status"] == "started":
                    compact_record.update(
                        status="failed",
                        duration_seconds=time.monotonic() - compact_record.pop("started"),
                        cause=code,
                    )
                    if code not in {"REQUEST_BUDGET_EXHAUSTED", "LOCAL_TRANSPORT_LIMIT"}:
                        code = "COMPACTION_FAILED"
                if identity is not None:
                    ledger.reject(identity, code, "Codex.Model.do_POST")
                state["errors"].append(
                    {
                        "request_id": identity,
                        "code": code,
                        "cause_type": type(error.__cause__).__name__ if error.__cause__ else None,
                    }
                )
                http_status, api_code = proxy_error(code)
                try:
                    self.reply(
                        http_status,
                        encoded(
                            {
                                "error": {
                                    "message": code,
                                    "type": "benchmark_limit",
                                    "code": api_code,
                                }
                            }
                        ),
                    )
                except (BrokenPipeError, ConnectionResetError):
                    state["errors"].append({"request_id": identity, "code": "CLIENT_DISCONNECTED"})

    class Server(socketserver.UnixStreamServer):
        allow_reuse_address = False

    server = Server(str(socket_path), Model)
    socket_path.chmod(0o666)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    name = "repropatch-codex-" + uuid.uuid4().hex[:12]
    started = time.monotonic()
    result = {
        "schema": "repropatch.benchmark-attempt.v1",
        "agent": "codex",
        "attempt": args.attempt,
        **attempt_identity(task, args.attempt),
        **candidate_metadata(b""),
        "internal_verification_status": "not_performed",
        "version": version,
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "code_host_sha256": hashlib.sha256(code_host.read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "provider": {"model": "gpt-6-luna", "base_url": "https://cpa.liyinlong.me/v1"},
        "host_transport": "httpx2; trust_env=True; follow_redirects=False; timeout="
        + str(task.budget.model_timeout_seconds),
        "check_only": args.check_only,
        "context_policy": policy.to_dict(),
        "provider_compaction_mode": "local_summary_via_responses",
        "provider_capabilities": "unsupported",
        "codex_source_commit": "83086188ae0614bd882818ff1aa23f3194962012",
        "container_deleted": False,
        "differences": [
            "原生 Codex 提示、Shell 与补丁工具；持久容器及完整源码可读",
            "CLI 原生 SSE 逐块留证，整响应准入后转发；输出上限由代理设为8192",
            "容器断网，通过固定模型专用 Unix 套接字连接宿主计量代理",
        ],
    }
    try:
        run = [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            *config["run_args"],
            "--mount",
            f"type=bind,source={binary},target=/opt/codex,readonly",
            "--mount",
            f"type=bind,source={code_host},target=/opt/codex-code-mode-host,readonly",
            "--mount",
            f"type=bind,source={relay_file},target=/opt/adapter.py,readonly",
            "--mount",
            f"type=bind,source={transport},target=/model,readonly",
            "--env",
            "HOME=/tmp",
            "--env",
            "CODEX_HOME=/build/.codex-home",
            "--env",
            "BENCHMARK_MODEL_KEY=isolated-proxy",
            "--env",
            "BENCHMARK_RELAY_TIMEOUT_SECONDS=" + str(task.budget.model_timeout_seconds + 10),
            "--env",
            "CMAKE_BUILD_PARALLEL_LEVEL=2",
            "--workdir",
            "/src",
            task.environment.image,
            "sleep",
            str(args.agent_seconds + 120),
        ]
        subprocess.run(run, check=True, capture_output=True, timeout=30)
        readable = json.loads(common)["readable"]
        probe = (
            "import pathlib,os; assert os.getuid()==65534; "
            + "; ".join("pathlib.Path(" + repr("/src/" + p) + ").read_bytes()" for p in readable)
            + "; print('SOURCE_READABLE')"
        )
        check = subprocess.run(
            ["docker", "exec", name, "python3", "-c", probe], capture_output=True, timeout=30
        )
        save(
            output / "source-readability.json",
            {"returncode": check.returncode, "readable_files": len(readable)},
        )
        check.check_returncode()
        native_config = native_settings(
            args.reasoning_effort, task.budget.model_timeout_seconds, policy
        )
        save(output / "native-config.json", native_config)
        cli = [
            "/opt/codex",
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
        for setting, value in native_config.items():
            cli.extend(["-c", setting + "=" + json.dumps(value)])
        cli.append("-")
        # 模型进程只接触虚拟密钥；真实密钥留在宿主代理进程。
        relay_probe = "from urllib.request import Request,urlopen; print(urlopen(Request('http://127.0.0.1:8318/health',data=b'')).read().decode())"
        command = "mkdir -p /build/.codex-home; python3 /opt/adapter.py --relay & " + (
            "exec python3 -c " + shlex.quote(relay_probe)
            if args.check_only
            else "exec " + shlex.join(cli)
        )
        # 等待回环监听启动，避免首个模型请求与中继启动竞争。
        command = command.replace(" & exec ", " & sleep 1; exec ")
        with (output / "events.jsonl").open("wb") as out, (output / "stderr.log").open("wb") as err:
            try:
                process = subprocess.run(
                    ["docker", "exec", "-i", name, "bash", "-c", command],
                    input=common.encode(),
                    stdout=out,
                    stderr=err,
                    timeout=args.agent_seconds,
                )
                result["exit_code"] = process.returncode
            except subprocess.TimeoutExpired:
                result["stop_reason"] = "AGENT_TIME_LIMIT"
    except KeyboardInterrupt:
        result.update(producer_status="CANCELLED", stop_reason="USER_CANCELLED")
    except Exception as error:
        result.update(producer_status="ENVIRONMENT_ERROR", error_type=type(error).__name__)
    finally:
        state["closing"] = True
        try:
            stop_container(name)
            result["container_deleted"] = True
            result.update(export_candidate(source, output))
        except Exception as error:
            result["cleanup_error_type"] = type(error).__name__
            result["producer_status"] = "ENVIRONMENT_ERROR"
        # 等待有总期限的处理器结算，随后冻结结果快照。
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        event_file = output / "events.jsonl"
        if event_file.is_file():
            events = event_file.read_bytes()
            for compact in state["compactions"]:
                following = []
                for line in events[compact["cli_event_offset"] :].splitlines():
                    try:
                        following.append(json.loads(line))
                    except ValueError:
                        continue
                compact["continued_with_tools"] = any(
                    event.get("type") == "item.completed"
                    and event.get("item", {}).get("type") in {"command_execution", "file_change"}
                    for event in following
                )
        if "producer_status" not in result:
            budget_reason = next(
                (
                    error["code"]
                    for error in state["errors"]
                    if error["code"]
                    in {
                        "BENCHMARK_REQUEST_LIMIT",
                        "TOOL_BATCH_LIMIT",
                        "TOOL_BUDGET",
                        "CONTEXT_LIMIT",
                        "REQUEST_BUDGET_EXHAUSTED",
                        "CONTEXT_BUDGET_EXHAUSTED",
                        "LOCAL_TRANSPORT_LIMIT",
                        "COMPACTION_FAILED",
                        "MODEL_TIMEOUT",
                        "MODEL_SERVER_ERROR",
                        "MODEL_RATE_LIMIT",
                        "MODEL_CONTEXT_EXCEEDED",
                        "MODEL_REQUEST_FAILED",
                    }
                ),
                None,
            )
            result["producer_status"] = (
                result.get("stop_reason")
                or budget_reason
                or ("MODEL_REQUEST_ERROR" if state["errors"] else None)
                or ("FINISHED" if result.get("exit_code") == 0 else "CLI_ERROR")
            )
        result.update(
            duration_seconds=time.monotonic() - started,
            usage=ledger.summary(args.attempt),
            internal_acceptance=None,
            oracle_status=None,
            **state,
        )
        result.update(ledger.summary(args.attempt))
        result["compaction_count"] = sum(c["status"] == "completed" for c in state["compactions"])
        result["native_status"] = result["producer_status"]
        result["native_reason"] = result.get("stop_reason") or result["producer_status"]
        result["stop_reason"] = (
            "COMPLETED" if result["native_reason"] == "FINISHED" else result["native_reason"]
        )
        save(output / "result.json", result)
        socket_path.unlink(missing_ok=True)
    print(json.dumps(result, ensure_ascii=False))
    if args.check_only:
        return 0 if result.get("exit_code") == 0 else 2
    return 1 if result["native_status"] in {"ENVIRONMENT_ERROR", "CANCELLED", "CLI_ERROR"} else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--relay"]:
        relay()
    else:
        raise SystemExit(main())
