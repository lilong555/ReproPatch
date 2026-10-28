"""十二次受控请求比较公网与 Azure SSH 路由，保存真实用量和传输时间线。"""

import argparse
import asyncio
import json
import os
from pathlib import Path

import httpx2
from benchmark_budget import LocalUsageLedger
from cpa_session import CPASession
from qualify_cpp_batch import save
from run_codex_benchmark import read_model_stream_async

from repropatch.context import ContextPolicy, encoded
from repropatch.cpa import cpa_route


async def calibrate(args):
    campaign = json.loads(args.campaign.read_text())
    if campaign["request_allocation"]["calibration"] != 12:
        raise ValueError("CROSS_CALIBRATION_ALLOCATION_CHANGED")
    args.output.mkdir(parents=True, exist_ok=False)
    cases = []
    for pair in range(6):
        routes = ["public", "azure-ssh"] if pair % 2 == 0 else ["azure-ssh", "public"]
        for route in routes:
            cases.append(
                {
                    "attempt_id": f"cross-repository-20261028/calibration/{pair + 1}/{route}",
                    "route": route,
                    "pair": pair + 1,
                }
            )
    ledger = LocalUsageLedger.create_scoped(
        args.output / "usage.sqlite3",
        {row["attempt_id"]: 1 for row in cases},
        context_policy=ContextPolicy.from_dict(campaign["context_policy"]),
    )
    trace = args.output / "http-native"
    trace.mkdir()
    results = []
    with CPASession(args.output / "cpa-session") as session:
        for row in cases:
            session.claim(row["attempt_id"], "calibration", cap=1)
            route = cpa_route(row["route"])
            body = {
                "model": "gpt-6-luna",
                "reasoning": {"effort": "max"},
                "max_output_tokens": 8192,
                "stream": True,
                "store": False,
                "input": [{"role": "user", "content": "这是网络兼容性检查，请只输出 OK。"}],
            }
            payload = encoded(body)
            identity = ledger.reserve(row["attempt_id"], payload)
            try:
                async with httpx2.AsyncClient(
                    trust_env=route.trust_env, follow_redirects=False, timeout=180
                ) as client:
                    code, _, _, completed = await read_model_stream_async(
                        client,
                        route.base_url + "/responses",
                        payload,
                        {
                            "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                            "Content-Type": "application/json",
                            "Accept-Encoding": "identity",
                            "X-Request-ID": identity,
                        },
                        trace,
                        identity,
                        ledger,
                        first_byte_timeout=180,
                        idle_timeout=180,
                        total_timeout=180,
                    )
                usage = (completed or {}).get("usage", {})
                known = all(
                    type(usage.get(key)) is int for key in ("input_tokens", "output_tokens")
                )
                result = {
                    **row,
                    "request_id": identity,
                    "http_status": code,
                    "status": "PASSED" if code == 200 and known else "FAILED",
                    "usage": usage,
                }
            except Exception as error:
                result = {
                    **row,
                    "request_id": identity,
                    "status": "FAILED",
                    "error_type": type(error).__name__,
                    "diagnostic": str(error)[:300],
                }
            results.append(result)
            save(
                args.output / "calibration.json",
                {
                    "schema": "repropatch.cross-network-calibration.v1",
                    "request_cap": 12,
                    "model": "gpt-6-luna",
                    "reasoning_effort": "max",
                    "model_timeout_seconds": 180,
                    "route": "azure-ssh",
                    "attempts": results,
                    "usage": ledger.summary(),
                    "status": "PASSED"
                    if len(results) == 12 and all(r["status"] == "PASSED" for r in results)
                    else "INCOMPLETE_OR_FAILED",
                },
            )
    return all(row["status"] == "PASSED" for row in results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign", type=Path, default=Path("benchmarks/cross-repo/campaign.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return 0 if asyncio.run(calibrate(args)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
