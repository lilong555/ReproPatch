"""Codex 对照的流证据、整批准入与稳定候选。"""

import asyncio
import hashlib
import http.server
import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    import run_codex_benchmark

    return run_codex_benchmark


@pytest.mark.sdk
@pytest.mark.parametrize("mode", ["complete", "segmented", "interrupted"])
def test_sse_evidence_and_single_settlement(adapter, tmp_path, mode):
    import httpx2
    from benchmark_budget import BudgetLimit, LocalUsageLedger

    terminal = {
        "type": "response.completed",
        "response": {"output": [], "usage": {"input_tokens": 7, "output_tokens": 2}},
    }
    prefix = b'data: {"type":"response.created"}\n\n'
    expected = prefix + b"data: " + json.dumps(terminal).encode() + b"\n\n"

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(expected)))
            self.end_headers()
            if mode == "complete":
                self.wfile.write(expected)
            else:
                self.wfile.write(prefix)
                self.wfile.flush()
                time.sleep(0.05)
                if mode == "segmented":
                    self.wfile.write(expected[len(prefix) :])
            self.wfile.flush()

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    ledger = LocalUsageLedger.create(tmp_path / "usage.sqlite3")
    identity = ledger.reserve("fixture", b"{}")
    try:
        with httpx2.Client(trust_env=False, timeout=2) as client:

            def call():
                return adapter.read_model_stream(
                    client,
                    f"http://127.0.0.1:{server.server_port}/responses",
                    b"{}",
                    {},
                    tmp_path,
                    identity,
                    ledger,
                )

            if mode == "interrupted":
                with pytest.raises(httpx2.RemoteProtocolError):
                    call()
            else:
                assert call()[1] == expected
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    evidence = (tmp_path / (identity + "-response.sse")).read_bytes()
    assert evidence == (prefix if mode == "interrupted" else expected)
    metadata = json.loads((tmp_path / (identity + "-transport.json")).read_text())
    assert metadata["received_bytes"] == len(evidence)
    assert metadata["response_completed_seen"] == (mode != "interrupted")
    assert metadata["usage_complete"] == (mode != "interrupted")
    assert metadata["last_byte_seconds"] >= metadata["first_byte_seconds"] >= 0
    assert ledger.summary()["requests"] == 1
    assert ledger.summary()["unknown_usage_requests"] == int(mode == "interrupted")
    with pytest.raises(BudgetLimit, match="SETTLEMENT_CONFLICT"):
        ledger.settle(identity, b"{}", 200)


def test_budget_and_tool_batch_admission(adapter, task):
    from benchmark_budget import BudgetLimit, validate_task_budget

    valid = replace(
        task,
        budget=replace(
            task.budget,
            max_steps=12,
            max_tool_calls=24,
            max_output_tokens=8192,
            model_timeout_seconds=90,
        ),
    )
    validate_task_budget(valid)
    with pytest.raises(BudgetLimit, match="TASK_BUDGET_MISMATCH"):
        validate_task_budget(replace(valid, budget=replace(valid.budget, max_steps=13)))

    def batch(n):
        return {"output": [{"type": "function_call"}] * n}

    assert adapter.admit_tools(batch(8), 16, 24) == 24
    with pytest.raises(BudgetLimit, match="TOOL_BATCH_LIMIT"):
        adapter.admit_tools(batch(9), 0, 24)
    with pytest.raises(BudgetLimit, match="TOOL_BUDGET"):
        adapter.admit_tools(batch(1), 24, 24)
    with pytest.raises(BudgetLimit, match="TOOL_BUDGET"):
        adapter.admit_tools(batch(3), 23, 24)
    assert adapter.admit_tools(batch(0), 24, 24) == 24


def test_native_reasoning_configuration(adapter):
    assert adapter.native_settings()["model_reasoning_effort"] == "max"
    assert adapter.native_settings("medium")["model_reasoning_effort"] == "medium"


@pytest.mark.sdk
@pytest.mark.parametrize("effort", [None, "max", "medium"])
def test_luna_sdk_request_and_ledger_preserve_reasoning(adapter, tmp_path, effort):
    import httpx2
    import run_benchmark_agent as worker
    from benchmark_budget import BudgetHooks, LocalUsageLedger
    from openai import AsyncOpenAI

    expected = effort or "max"
    ledger = LocalUsageLedger.create(tmp_path / "usage.sqlite3")
    trace = tmp_path / "http"
    hooks = BudgetHooks(ledger, "reasoning", trace, local_luna=True)
    args = SimpleNamespace(provider="local-luna", reasoning_effort=effort)
    received = []

    def respond(request):
        body = json.loads(request.content)
        received.append(request.content)
        assert body["reasoning"] == {"effort": expected}
        assert body["input"] == "离线推理配置检查"
        assert int(request.headers["Content-Length"]) == len(request.content)
        return httpx2.Response(
            200,
            json={
                "id": "resp_offline",
                "object": "response",
                "created_at": 0,
                "model": "gpt-6-luna",
                "status": "completed",
                "output": [],
                "reasoning": body["reasoning"],
                "usage": {"input_tokens": 3, "output_tokens": 1, "total_tokens": 4},
            },
        )

    async def exercise():
        async with worker.responses_client(
            args, hooks, transport=httpx2.MockTransport(respond)
        ) as client:
            async with AsyncOpenAI(
                api_key="offline-fixture",
                base_url=worker.provider(args)[1],
                http_client=client,
                max_retries=0,
            ) as api:
                result = await api.responses.create(
                    model="gpt-6-luna",
                    input="离线推理配置检查",
                    max_output_tokens=8192,
                    store=False,
                )
                assert result.reasoning.effort == expected

    asyncio.run(exercise())
    assert len(received) == 1
    assert next(trace.glob("*-request.json")).read_bytes() == received[0]
    with ledger.connect() as db:
        digest = db.execute("SELECT request_sha256 FROM requests").fetchone()[0]
    assert digest == hashlib.sha256(received[0]).hexdigest()
    assert ledger.summary()["unknown_usage_requests"] == 0


def test_explicit_reasoning_preserves_deepseek_policy(adapter):
    import run_benchmark_agent as worker
    from benchmark_budget import BudgetLimit

    args = SimpleNamespace(provider="deepseek", reasoning_effort=None)
    assert worker.reasoning_parameters(args) == {}
    args.reasoning_effort = "max"
    with pytest.raises(BudgetLimit, match="REASONING_EFFORT_REQUIRES_LUNA"):
        worker.reasoning_parameters(args)


@pytest.mark.parametrize(
    ("fallback", "expected"),
    [
        ("candidate_ref", b"reference"),
        ("patch_diff", b"patch"),
        ("unverified_diagnostics", b"diagnostic"),
        (None, b""),
    ],
)
def test_candidate_first_nonempty_source_and_corruption_are_explicit(
    adapter, tmp_path, fallback, expected
):
    from dataclasses import asdict

    import run_benchmark_agent as worker

    from repropatch.artifacts import EvidenceRef
    from repropatch.errors import InfrastructureError

    directory = tmp_path / "native"
    output = tmp_path / "producer"
    directory.mkdir()
    output.mkdir()
    reference = EvidenceRef.save(
        directory, "reference.patch", expected if fallback == "candidate_ref" else b""
    )
    report = {"outcome": "ERROR", "candidate": {"patch": asdict(reference)}}
    (directory / "patch.diff").write_bytes(b"patch" if fallback == "patch_diff" else b"")
    (directory / "diagnostics").mkdir()
    if fallback is not None:
        (directory / "diagnostics/unverified.patch").write_bytes(b"diagnostic")
    metadata = worker.export_repropatch_candidate(report, directory, output)
    assert metadata["candidate_source"] == fallback
    assert metadata["candidate_available"] == (fallback is not None)
    assert metadata["recovered_from_unverified_patch"] == (fallback == "unverified_diagnostics")
    assert metadata["candidate_bytes"] == len(expected)
    assert metadata["candidate_sha256"] == (
        hashlib.sha256(expected).hexdigest() if expected else None
    )
    assert (output / "candidate.patch").exists() == (fallback is not None)
    if expected:
        assert (output / "candidate.patch").read_bytes() == expected
    assert report["outcome"] == "ERROR"
    (directory / "reference.patch").write_bytes(b"corrupt")
    with pytest.raises(InfrastructureError, match="ARTIFACT_CORRUPT"):
        worker.export_repropatch_candidate(report, directory, output)


@pytest.mark.docker
def test_timeout_stops_writer_before_candidate_export(adapter, repository, tmp_path):
    image = "repropatch-cpp:0.1"
    if subprocess.run(["docker", "info"], capture_output=True).returncode:
        pytest.skip("需要运行中的 Docker")
    if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode:
        pytest.skip("需要演示镜像")
    name = "repropatch-codex-freeze-test-" + uuid.uuid4().hex[:12]
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--network=none",
            "--read-only",
            f"--user={os.getuid()}:{os.getgid()}",
            "--mount",
            f"type=bind,source={repository},target=/src",
            image,
            "sleep",
            "60",
        ],
        check=True,
        capture_output=True,
    )
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            subprocess.run(
                [
                    "docker",
                    "exec",
                    name,
                    "sh",
                    "-c",
                    "printf '\n// 初始\n' >> /src/src/stats.cpp; "
                    "sleep 3; printf '\n// 延迟\n' >> /src/src/stats.cpp; sleep 30",
                ],
                capture_output=True,
                timeout=1,
            )
    finally:
        adapter.stop_container(name)
    result = adapter.export_candidate(repository, tmp_path)
    patch = (tmp_path / "candidate.patch").read_bytes()
    assert result["candidate_available"] and "// 初始".encode() in patch
    time.sleep(3)
    assert adapter.export_candidate(repository, tmp_path) == result
    assert "// 延迟".encode() not in patch
