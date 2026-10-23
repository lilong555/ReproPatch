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
import urllib.error
import urllib.request
import uuid
from pathlib import Path


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


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
    from benchmark_budget import BudgetLimit, LocalUsageLedger
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
    args = parser.parse_args()
    task = Task.load(args.task)
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
    (output / "adapter.py").write_bytes(Path(__file__).read_bytes())
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
    state = {"tool_calls_admitted": 0, "errors": []}

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
                request = urllib.request.Request(
                    "https://cpa.liyinlong.me/v1/responses",
                    data=payload,
                    headers={
                        "Authorization": "Bearer " + key,
                        "Content-Type": "application/json",
                        "User-Agent": "ReproPatch-Codex-Benchmark/1",
                        "Accept-Encoding": "identity",
                    },
                )
                try:
                    with urllib.request.urlopen(request, timeout=90) as response:
                        status, data = response.status, response.read()
                        content_type = response.headers.get("Content-Type", "text/event-stream")
                except urllib.error.HTTPError as error:
                    status, data, content_type = error.code, error.read(), "application/json"
                (trace / (identity + "-response.sse")).write_bytes(data)
                completed = None
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
                content = json.dumps(completed, ensure_ascii=False).encode() if completed else data
                (trace / (identity + "-response.json")).write_bytes(content)
                ledger.settle(identity, content, status)
                calls = sum(
                    item.get("type") in {"function_call", "custom_tool_call"}
                    for item in (completed or {}).get("output", [])
                )
                if state["tool_calls_admitted"] + calls > 24:
                    raise BudgetLimit("TOOL_BUDGET")
                state["tool_calls_admitted"] += calls
                self.reply(status, data, content_type)
            except Exception as error:
                # 异常仅记录类型和本地稳定码，供应商敏感正文保存在私有原始证据中。
                code = (
                    str(error)
                    if isinstance(error, (BudgetLimit, ValueError))
                    else type(error).__name__
                )
                state["errors"].append({"request_id": identity, "code": code})
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
        "check_only": args.check_only,
        "container_deleted": False,
        "differences": [
            "原生 Codex 提示、Shell 与补丁工具；持久容器及完整源码可读",
            "CLI 原生 SSE 原字节缓冲后转发；输出上限由代理设为8192",
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
            f"type=bind,source={Path(__file__).resolve()},target=/opt/adapter.py,readonly",
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
        native_config = {
            "model_provider": "benchmark",
            "model": "gpt-6-luna",
            "approval_policy": "never",
            "model_reasoning_effort": "none",
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
        result["candidate_sha256"] = hashlib.sha256(patch).hexdigest()
        result["candidate_bytes"] = len(patch)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)
        left = subprocess.check_output(
            ["docker", "ps", "-aq", "--filter", "name=^/" + name + "$"], timeout=30
        )
        result.update(
            container_deleted=not left.strip(),
            duration_seconds=time.monotonic() - started,
            usage=ledger.summary(args.attempt),
            **state,
        )
        save(output / "result.json", result)
        server.shutdown()
        server.server_close()
        socket_path.unlink(missing_ok=True)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    if sys.argv[1:] == ["--relay"]:
        relay()
    else:
        main()
