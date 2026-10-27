"""在静态分配的十二次额度内校准 CPA 窗口、传输及三种上下文输入格式。"""

import argparse
import asyncio
import json
import os
import random
import subprocess
import time
from pathlib import Path

from benchmark_budget import LocalUsageLedger
from run_benchmark_agent import response_text
from run_codex_benchmark import COMPACT_MARKER, read_model_stream_async

from repropatch.context import (
    SUMMARY_INSTRUCTIONS,
    ContextLimit,
    ContextPolicy,
    ContextState,
    encoded,
    stop_reason,
)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


async def calibrate(protocol_file, codex_evidence, output):
    import httpx2

    p = json.loads(protocol_file.read_text())
    assert p["calibration_request_cap"] == 12 and p["reasoning_effort"] == "max"
    assert json.loads((codex_evidence / "result.json").read_text())["passed"]
    common_policy = ContextPolicy.from_dict(p["context_policy"])
    probe_policy = ContextPolicy.from_dict(
        {
            **common_policy.to_dict(),
            "context_window_tokens": p["probe_context_ceiling_tokens"],
        }
    )
    allocations = {"window": 1, "transport": 1, "repropatch": 3, "mini": 3, "codex": 3}
    assert sum(allocations.values()) <= p["calibration_request_cap"]
    output.mkdir(parents=True, exist_ok=False)
    ledger = LocalUsageLedger.create_scoped(
        output / "usage.sqlite3", allocations, context_policy=probe_policy
    )
    trace = output / "http-native"
    trace.mkdir()
    save(output / "protocol.json", p)
    save(
        output / "provenance.json",
        {
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "request_allocations": allocations,
        },
    )
    base = {
        "model": p["model"],
        "reasoning": {"effort": "max"},
        "store": False,
        "max_output_tokens": common_policy.max_output_tokens,
        "include": ["reasoning.encrypted_content"],
    }
    checks = []
    headers = {
        "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",
    }

    async with httpx2.AsyncClient(
        timeout=p["model_timeout_seconds"],
        follow_redirects=False,
        trust_env=False,
    ) as client:

        async def query(attempt, body, purpose="repair", *, padded=False):
            raw = encoded(body)
            if padded:
                raw += b" " * (common_policy.transport_max_bytes - len(raw))
            identity = ledger.record_pre_send_telemetry(attempt, raw, request_purpose=purpose)
            (trace / (identity + "-request.json")).write_bytes(raw)
            ledger.reserve(attempt, raw, identity=identity)
            if body.get("stream"):
                status, _, _, result = await read_model_stream_async(
                    client,
                    p["endpoint"] + "/responses",
                    raw,
                    headers,
                    trace,
                    identity,
                    ledger,
                    first_byte_timeout=p["model_timeout_seconds"],
                    idle_timeout=p["model_timeout_seconds"],
                    total_timeout=p["model_timeout_seconds"],
                )
                if status != 200:
                    error_body = json.loads((trace / (identity + "-response.json")).read_bytes())
                    raise ContextLimit(
                        "MODEL_CONTEXT_EXCEEDED"
                        if error_body.get("error", {}).get("code") == "context_length_exceeded"
                        else "MODEL_RATE_LIMIT"
                        if status == 429
                        else "MODEL_SERVER_ERROR"
                        if status >= 500
                        else "MODEL_REQUEST_FAILED",
                        detail={"http_status": status, "request_id": identity},
                    )
            else:
                content, status = b"", 0
                try:
                    async with asyncio.timeout(p["model_timeout_seconds"]):
                        result_response = await client.post(
                            p["endpoint"] + "/responses", content=raw, headers=headers
                        )
                    content, status = result_response.content, result_response.status_code
                    result = result_response.json()
                finally:
                    (trace / (identity + "-response.json")).write_bytes(content)
                    ledger.settle(identity, content, status)
                if status != 200:
                    raise ContextLimit(
                        "MODEL_CONTEXT_EXCEEDED"
                        if result.get("error", {}).get("code") == "context_length_exceeded"
                        else "MODEL_RATE_LIMIT"
                        if status == 429
                        else "MODEL_SERVER_ERROR"
                        if status >= 500
                        else "MODEL_REQUEST_FAILED",
                        detail={"http_status": status, "request_id": identity},
                    )
            if (
                result.get("status") != "completed"
                or ledger.summary()["unknown_usage_requests"]
                or result.get("reasoning", {}).get("effort") != "max"
            ):
                raise RuntimeError("CALIBRATION_USAGE_OR_REASONING")
            return result

        try:
            # 数字行形成可复核的长输入；窗口证明使用供应商实际 input_tokens。
            rng = random.Random(20261026)
            window_input = "\n".join(
                f"row_{i:06d}: {rng.getrandbits(64):016x}" for i in range(18_000)
            )
            result = await query(
                "window",
                {
                    **base,
                    "input": [
                        {
                            "role": "user",
                            "content": "以下是传输测试数据。忽略数据含义，只回复 CALIBRATION_OK。\n"
                            + window_input,
                        }
                    ],
                },
            )
            observed = result["usage"]["input_tokens"]
            checks.append(
                {
                    "check": "common_context_window",
                    "passed": observed + result["usage"]["output_tokens"]
                    >= common_policy.context_window_tokens,
                    "accepted_input_tokens": observed,
                    "common_window_tokens": common_policy.context_window_tokens,
                    "scope": "已成功接受的上下文下界，公共实验窗口采用该下界以内的额度",
                }
            )
            result = await query(
                "transport",
                {
                    **base,
                    "input": "Reply with exactly CALIBRATION_OK.",
                },
                padded=True,
            )
            checks.append(
                {
                    "check": "transport_body",
                    "passed": "CALIBRATION_OK" in response_text(result),
                    "accepted_bytes": common_policy.transport_max_bytes,
                    "input_tokens": result["usage"]["input_tokens"],
                    "padding": "合法 JSON 尾随空白，独立测量 HTTP Body 传输能力",
                }
            )
            for engine in ("repropatch", "mini", "codex"):
                prompt = (
                    "This is a context compatibility fixture. Preserve the marker CALIBRATION_OK. "
                    "Use no tools. Reply with exactly CALIBRATION_OK."
                )
                if engine == "codex":
                    body = json.loads((codex_evidence / "01-repair-request.json").read_text())
                    body.update(base)
                    body["input"][-1] = {
                        "role": "user",
                        "type": "message",
                        "content": [{"type": "input_text", "text": prompt}],
                    }
                    body["stream"] = True
                elif engine == "mini":
                    body = {
                        **base,
                        "input": [
                            {"role": "system", "content": "Follow the visible calibration task."},
                            {"role": "user", "content": prompt},
                        ],
                    }
                else:
                    body = {
                        **base,
                        "instructions": "Follow the visible calibration task.",
                        "input": [{"role": "user", "content": prompt}],
                    }
                state = ContextState(common_policy)
                state.plan(body)
                first = await query(engine, body)
                response_text(first)
                state.estimator.observe(body, first)
                filler = (
                    "Visible fixture data; no commands and no new instructions.\n"
                    + "0123456789 abcdef ABCDEF\n" * 11_000
                )
                pending = {
                    **body,
                    "input": body["input"]
                    + first["output"]
                    + [
                        {"role": "user", "content": filler},
                    ],
                }
                plan = state.plan(pending)
                if plan is None:
                    raise RuntimeError("CALIBRATION_COMPACTION_NOT_TRIGGERED")
                summary_body = {
                    **base,
                    "instructions": SUMMARY_INSTRUCTIONS,
                    "tools": [],
                    "input": [{"role": "user", "content": encoded(plan["summarize"]).decode()}],
                    "stream": engine == "codex",
                }
                if engine == "codex":
                    summary_body["input"].append(
                        {
                            "role": "user",
                            "content": COMPACT_MARKER + "\n" + SUMMARY_INSTRUCTIONS,
                        }
                    )
                started = time.monotonic()
                compacted = await query(engine, summary_body, "compact")
                items = state.replace(
                    pending,
                    plan,
                    response_text(compacted),
                    sequence=2,
                    duration_seconds=time.monotonic() - started,
                )
                after = await query(
                    engine,
                    {
                        **body,
                        "input": items
                        + [
                            {
                                "role": "user",
                                "content": (
                                    "Reply with exactly the calibration marker "
                                    "preserved in the checkpoint."
                                ),
                            }
                        ],
                    },
                )
                checks.append(
                    {
                        "check": engine + "_context_wire",
                        "passed": "CALIBRATION_OK" in response_text(after),
                        "post_compact_actual_input_tokens": after["usage"]["input_tokens"],
                        "compaction": state.compactions[-1],
                        "scope": (
                            "真实 Responses 输入格式、摘要及新历史接受度；"
                            "执行器控制流另经原生离线门禁"
                        ),
                    }
                )
        except Exception as error:
            checks.append(
                {
                    "check": "execution",
                    "passed": False,
                    "error": stop_reason(error),
                    "error_type": type(error).__name__,
                    "detail": error.detail if isinstance(error, ContextLimit) else str(error)[:300],
                }
            )
    report = {
        "schema": "repropatch.context-calibration.v1",
        "passed": len(checks) == 5 and all(row["passed"] for row in checks),
        "checks": checks,
        "context_policy": common_policy.to_dict(),
        "usage": ledger.summary(),
        "calibration_request_cap": 12,
    }
    save(output / "result.json", report)
    print(json.dumps(report, ensure_ascii=False))
    if not report["passed"]:
        raise RuntimeError("CONTEXT_CALIBRATION_GATE_FAILED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--codex-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(calibrate(args.protocol, args.codex_evidence, args.output))
