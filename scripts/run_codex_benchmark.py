"""在统一只读源码容器内运行原生 Codex CLI，并保存限额模型流和候选补丁。"""

import argparse
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
from pathlib import Path


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def native_settings(reasoning_effort="max"):
    """原生 CLI 的固定配置，推理强度同时由上游请求留证。"""
    return {
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
        "model_providers.benchmark.stream_idle_timeout_ms": 100000,
        "model_providers.benchmark.supports_websockets": False,
    }


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
    return {
        "candidate_sha256": hashlib.sha256(patch).hexdigest(),
        "candidate_bytes": len(patch),
        "candidate_available": bool(patch),
    }


class UnixHTTP(http.client.HTTPConnection):
    """容器仅连接挂载的模型代理套接字。"""

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(100)
        self.sock.connect("/model/socket")


def relay():
    class Relay(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            connection = UnixHTTP("localhost", timeout=100)
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
    from run_benchmark_agent import mini_inputs

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
    validate_task_budget(task)
    config, common, source = mini_inputs(args, task)
    subprocess.run(
        ["git", "-C", str(source), "diff", "--quiet", "HEAD", "--"], check=True, timeout=30
    )
    ledger = LocalUsageLedger(args.ledger)
    binary = args.binary.resolve(strict=True)
    code_host = binary.with_name("codex-code-mode-host").resolve(strict=True)
    version = subprocess.check_output([str(binary), "--version"], timeout=10).decode().strip()
    if version != "codex-cli 0.163.0":
        parser.error("CODEX_VERSION_MISMATCH")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
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
    upstream = (
        None
        if args.check_only
        else httpx2.Client(trust_env=True, follow_redirects=False, timeout=90)
    )
    state = {"tool_calls_admitted": 0, "observed_request_reasoning": [], "errors": []}

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
            try:
                if self.path == "/health":
                    self.reply(200, b'{"transport":"ok"}')
                    return
                if args.check_only or self.path != "/v1/responses":
                    raise ValueError("MODEL_ROUTE_REJECTED")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 1024 * 1024:
                    raise ValueError("MODEL_REQUEST_SIZE")
                raw = self.rfile.read(size)
                body = json.loads(raw)
                state["observed_request_reasoning"].append(body.get("reasoning"))
                if body.get("model") != "gpt-6-luna" or body.get("stream") is not True:
                    raise ValueError("MODEL_SETTINGS_MISMATCH")
                if any(t.get("type") not in {"function", "custom"} for t in body.get("tools", [])):
                    raise ValueError("EXTERNAL_TOOL_REJECTED")
                if len(json.dumps(body.get("input"), ensure_ascii=False).encode()) > 262144:
                    raise BudgetLimit("CONTEXT_LIMIT")
                # CLI 保留原生提示与工具协议；代理统一每请求输出上限并记录原始请求。
                body["max_output_tokens"] = 8192
                payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
                identity = ledger.reserve(args.attempt, payload)
                (trace / (identity + "-cli-request.json")).write_bytes(raw)
                (trace / (identity + "-request.json")).write_bytes(payload)
                # 共用 ReproPatch 的 HTTP 客户端与宿主代理配置，保留原始 SSE 字节。
                status, data, content_type, completed = read_model_stream(
                    upstream,
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
                )
                state["tool_calls_admitted"] = admit_tools(
                    completed, state["tool_calls_admitted"], task.budget.max_tool_calls
                )
                self.reply(status, data, content_type)
            except Exception as error:
                # 异常仅记录类型和本地稳定码，供应商敏感正文保存在私有原始证据中。
                code = (
                    str(error)
                    if isinstance(error, (BudgetLimit, ValueError))
                    else type(error).__name__
                )
                state["errors"].append(
                    {
                        "request_id": identity,
                        "code": code,
                        "cause_type": type(error.__cause__).__name__ if error.__cause__ else None,
                    }
                )
                self.reply(
                    429 if isinstance(error, BudgetLimit) else 502,
                    json.dumps({"error": {"message": code, "type": "benchmark_limit"}}).encode(),
                )

    class Server(socketserver.UnixStreamServer):
        allow_reuse_address = False

    server = Server(str(socket_path), Model)
    socket_path.chmod(0o666)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    name = "repropatch-codex-" + uuid.uuid4().hex[:12]
    started = time.monotonic()
    result = {
        "agent": "codex",
        "attempt": args.attempt,
        "version": version,
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "code_host_sha256": hashlib.sha256(code_host.read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "provider": {"model": "gpt-6-luna", "base_url": "https://cpa.liyinlong.me/v1"},
        "host_transport": "httpx2; trust_env=True; follow_redirects=False; timeout=90",
        "check_only": args.check_only,
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
        native_config = native_settings(args.reasoning_effort)
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
    finally:
        try:
            stop_container(name)
            result["container_deleted"] = True
            result.update(export_candidate(source, output))
        except Exception as error:
            result["cleanup_error_type"] = type(error).__name__
            result["producer_status"] = "ENVIRONMENT_ERROR"
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
        save(output / "result.json", result)
        server.shutdown()
        server.server_close()
        if upstream is not None:
            upstream.close()
        socket_path.unlink(missing_ok=True)
    print(json.dumps(result, ensure_ascii=False))
    if args.check_only:
        return 0 if result.get("exit_code") == 0 else 2
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--relay"]:
        relay()
    else:
        raise SystemExit(main())
