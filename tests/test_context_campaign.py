"""校准额度和阶段门禁通过固定响应验证。"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from repropatch.context import SUMMARY_INSTRUCTIONS, SUMMARY_KEYS, ContextPolicy, encoded

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from context_campaign import ARMS, pilot_gate, recovery_gate, validate_protocol


def pilot_fixture():
    tasks = [f"fmtlib__fmt-{n}" for n in (3158, 3537, 1390, 3750)]
    protocol = {
        "phase": "pilot",
        "context_policy": ContextPolicy().to_dict(),
        "model": "gpt-6-luna",
        "endpoint": "https://cpa.liyinlong.me/v1",
        "reasoning_effort": "max",
        "retries": 0,
        "arms": list(ARMS),
        "tasks": tasks,
        "request_cap_per_attempt": 24,
        "formal_request_cap": 480,
        "task_contracts": {task: {} for task in tasks},
        "execution_order": [{"instance_id": task, "arm": arm} for task in tasks for arm in ARMS],
    }
    rows = [
        {
            **entry,
            "score": {"accepted": False, "classification": "candidate"},
            "stop_reason": "REQUEST_BUDGET_EXHAUSTED",
            "metrics": {
                "issued_requests": 24,
                "unknown_usage_requests": 0,
                "compactions": [
                    {
                        "post_compact_actual_input_tokens": 2000,
                        "pre_transport_bytes": 100000,
                        "post_transport_bytes": 5000,
                        "continued_with_tools": True,
                    }
                ],
            },
        }
        for entry in protocol["execution_order"]
    ]
    return protocol, {
        "protocol_sha256": "frozen",
        "context_policy": protocol["context_policy"],
        "attempts": rows,
    }


def test_pilot_gate_uses_mechanism_evidence_and_preserves_oracle_failures():
    protocol, result = pilot_fixture()
    gate = pilot_gate(result, protocol, "frozen")
    assert gate["passed"] and gate["issued_requests"] == 480
    assert gate["ranking"] is False


def test_recovery_allocation_is_bounded_by_parent_budget():
    protocol, _ = pilot_fixture()
    protocol.update(
        phase="recovery",
        parent_request_cap=2520,
        prior_committed_request_upper_bound=100,
        attempts=[{**entry, "request_cap": 24} for entry in protocol["execution_order"]],
    )
    validate_protocol(protocol)
    protocol["prior_committed_request_upper_bound"] = 2050
    with pytest.raises(AssertionError):
        validate_protocol(protocol)


@pytest.mark.parametrize("failure", [None, "issued", "started_unknown"])
def test_recovery_gate_only_admits_verified_zero_request_attempts(tmp_path, failure):
    rows = [
        {
            "attempt_id": "done",
            "instance_id": "fmt-1",
            "arm": "full",
            "usage": {"issued_requests": 7},
        },
        {"attempt_id": "queued", "instance_id": "fmt-2", "arm": "codex"},
    ]
    jobs = [{"name": "fmt-2 / codex", "steps": []}]
    if failure == "issued":
        rows[1]["usage"] = {"issued_requests": 1}
    if failure == "started_unknown":
        jobs[0]["steps"] = [{"name": "Execute registered attempts"}]
    (tmp_path / "results.json").write_text(
        json.dumps({"protocol_sha256": "parent", "attempts": rows})
    )
    protocol = {
        "parent_protocol_sha256": "parent",
        "parent_request_cap": 48,
        "formal_request_cap": 24,
        "prior_committed_request_upper_bound": 10 if failure == "issued" else 9,
        "interrupted_attempt_requests": {"interrupted": 2},
        "attempts": [{"original_attempt_id": "queued", "instance_id": "fmt-2", "arm": "codex"}],
    }
    if failure:
        with pytest.raises(AssertionError):
            recovery_gate(tmp_path, protocol, jobs, {"interrupted": 2})
    else:
        gate = recovery_gate(tmp_path, protocol, jobs, {"interrupted": 2})
        assert gate["passed"] and gate["remaining_attempts"] == 1
        assert gate["prior_issued_requests"] == 7 and gate["interrupted_issued_requests"] == 2


@pytest.mark.parametrize("defect", ["unknown_usage", "no_codex_tools", "missing_attempt"])
def test_pilot_gate_requires_usage_tool_continuation_and_complete_first_runs(defect):
    protocol, result = pilot_fixture()
    if defect == "unknown_usage":
        result["attempts"][0]["metrics"]["unknown_usage_requests"] = 1
    elif defect == "no_codex_tools":
        for row in result["attempts"]:
            if row["arm"] == "codex":
                row["metrics"]["compactions"][0]["continued_with_tools"] = False
    else:
        result["attempts"].pop()
        with pytest.raises(AssertionError):
            pilot_gate(result, protocol, "frozen")
        return
    assert pilot_gate(result, protocol, "frozen")["passed"] is False


@pytest.mark.sdk
def test_calibration_uses_eleven_issued_requests_and_counts_all_three_summaries(
    tmp_path, monkeypatch
):
    import httpx2
    from calibrate_context import calibrate

    p = {
        "model": "gpt-6-luna",
        "endpoint": "https://cpa.liyinlong.me/v1",
        "reasoning_effort": "max",
        "calibration_request_cap": 12,
        "context_policy": ContextPolicy().to_dict(),
        "probe_context_ceiling_tokens": 384000,
        "model_timeout_seconds": 180,
    }
    protocol = tmp_path / "protocol.json"
    protocol.write_bytes(encoded(p))
    evidence = tmp_path / "codex"
    evidence.mkdir()
    (evidence / "result.json").write_bytes(encoded({"passed": True}))
    (evidence / "01-repair-request.json").write_bytes(
        encoded({"input": [{"role": "user", "content": "fixture"}]})
    )
    requests = []

    def serve(request):
        body = json.loads(request.content)
        requests.append(body)
        compact = body.get("instructions") == SUMMARY_INSTRUCTIONS
        text = (
            json.dumps({key: "CALIBRATION_OK" for key in SUMMARY_KEYS})
            if compact
            else "CALIBRATION_OK"
        )
        result = {
            "status": "completed",
            "reasoning": {"effort": "max"},
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": text}],
                }
            ],
            "usage": {
                "input_tokens": 140000 if len(requests) == 1 else 1000,
                "output_tokens": 100,
            },
        }
        if body.get("stream"):
            return httpx2.Response(
                200,
                content=b"data: "
                + encoded({"type": "response.completed", "response": result})
                + b"\n\n",
                headers={"Content-Type": "text/event-stream"},
            )
        return httpx2.Response(200, json=result)

    original = httpx2.AsyncClient
    monkeypatch.setattr(
        httpx2,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx2.MockTransport(serve), **kwargs),
    )
    monkeypatch.setenv("OPENAI_API_KEY", "offline-only")
    asyncio.run(calibrate(protocol, evidence, tmp_path / "output"))
    result = json.loads((tmp_path / "output/result.json").read_text())
    assert result["passed"]
    assert len(requests) == result["usage"]["issued_requests"] == 11
    assert result["usage"]["compact_requests"] == 3
    assert result["usage"]["unknown_usage_requests"] == 0
