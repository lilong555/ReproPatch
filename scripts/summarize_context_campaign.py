"""从冻结协议、评分与逐请求证据重算统一上下文实验。"""

import argparse
import copy
import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

ARMS = ("full", "no-checks", "shell-only", "mini", "codex")
TOKEN_KEYS = (
    "known_input_tokens",
    "known_output_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_sha(row):
    return hashlib.sha256(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def totals(rows):
    """供应商输入、输出总量各累计一次，缓存与推理保持细分项。"""
    usages = [row.get("usage") or {} for row in rows]
    unknown = sum(value.get("unknown_usage_requests", 0) for value in usages)
    result = {
        "issued_requests": sum(value.get("issued_requests", 0) for value in usages),
        "unknown_usage_requests": unknown,
        **{key: sum(value.get(key, 0) for value in usages) for key in TOKEN_KEYS},
        **{
            key: sum(value.get(key, 0) for value in usages)
            for key in ("repair_requests", "compact_requests", "retry_requests", "local_rejections")
        },
    }
    result["input_tokens"] = result["known_input_tokens"] if unknown == 0 else None
    result["output_tokens"] = result["known_output_tokens"] if unknown == 0 else None
    return result


def metrics(rows):
    values = [row.get("metrics") or {} for row in rows]
    result = {
        "attempts": len(rows),
        "oracle_pass": sum(row.get("oracle_result") == "PASS" for row in rows),
        "oracle_results": dict(Counter(row.get("oracle_result", "NOT_EXECUTED") for row in rows)),
        "stop_reasons": dict(Counter(row.get("stop_reason", "NOT_EXECUTED") for row in rows)),
        "user_cancelled": sum(row.get("stop_reason") == "USER_CANCELLED" for row in rows),
        **totals(rows),
    }
    for name in ("worker_seconds", "self_check_seconds", "cold_oracle_seconds"):
        measured = [value[name] for value in values if value.get(name) is not None]
        result[name + "_known_sum"] = sum(measured)
        result[name + "_median"] = statistics.median(measured) if measured else None
        result[name + "_measured_attempts"] = len(measured)
    tools = [value["tool_calls"] for value in values if value.get("tool_calls") is not None]
    result["tool_calls_known_sum"] = sum(tools)
    result["tool_calls_measured_attempts"] = len(tools)
    result["peak_single_input_tokens"] = max(
        ((row.get("usage") or {}).get("peak_single_input_tokens", 0) for row in rows), default=0
    )
    result["peak_transport_bytes"] = max(
        ((row.get("usage") or {}).get("peak_transport_bytes", 0) for row in rows), default=0
    )
    compactions = [compact for value in values for compact in value.get("compactions", [])]
    result["compaction_count"] = len(compactions)
    result["verified_compaction_count"] = sum(
        compact.get("status", "completed") == "completed"
        and compact.get("continued_with_tools") is True
        and compact.get("post_transport_bytes", 0) < compact.get("pre_transport_bytes", 0)
        for compact in compactions
    )
    result["compaction_seconds"] = sum(
        compact.get("duration_seconds", 0) for compact in compactions
    )
    return result


def comparison(rows, arm):
    by_key = {(row["instance_id"], row["arm"]): row for row in rows}
    tasks = sorted({row["instance_id"] for row in rows})
    wins, losses = [], []
    for task in tasks:
        full = by_key[(task, "full")].get("oracle_result") == "PASS"
        other = by_key[(task, arm)].get("oracle_result") == "PASS"
        if full and not other:
            wins.append(task)
        elif other and not full:
            losses.append(task)
    return {
        "full_only_pass": wins,
        "other_only_pass": losses,
        "net_full_pass": len(wins) - len(losses),
    }


def consolidate(sources, verification, historical):
    """按已冻结的尝试身份承接结果，复验覆盖规则独立于补丁是否通过。"""
    if not verification.get("passed") or verification.get("failures"):
        raise ValueError("EVIDENCE_VERIFICATION_INCOMPLETE")
    verified = {row["attempt_id"]: row for row in verification["records"]}
    if len(verified) != len(verification["records"]):
        raise ValueError("DUPLICATE_ATTEMPT_ID")
    request_ids = [identity for row in verified.values() for identity in row["request_ids"]]
    if len(request_ids) != len(set(request_ids)):
        raise ValueError("DUPLICATE_ISSUED_REQUEST_ID")
    if len(request_ids) != verification["issued_requests"]:
        raise ValueError("REQUEST_COUNT_MISMATCH")
    selected, registered, source_identities = {}, {}, []
    previous_protocol = previous_run = None
    reference = None
    paid_history = []
    for run_id, protocol, result, protocol_sha in sources:
        if result["protocol_sha256"] != protocol_sha:
            raise ValueError("PROTOCOL_SHA_MISMATCH")
        contract = {
            key: protocol[key]
            for key in (
                "model",
                "endpoint",
                "reasoning_effort",
                "model_timeout_seconds",
                "context_policy",
                "task_contracts",
            )
        }
        if contract["reasoning_effort"] != "max" or contract["model_timeout_seconds"] != 180:
            raise ValueError("FORMAL_PARAMETERS_CHANGED")
        if reference is None:
            reference = contract
        elif contract != reference:
            raise ValueError("TASK_OR_CONTEXT_CONTRACT_CHANGED")
        if previous_protocol is not None and (
            protocol["parent_run_id"] != previous_run
            or protocol["parent_protocol_sha256"] != previous_protocol
        ):
            raise ValueError("SOURCE_LINEAGE_MISMATCH")
        seen = set()
        for original in result["attempts"]:
            proof = verified.get(original["attempt_id"])
            if proof and proof.get("source_row_sha256") != row_sha(original):
                raise ValueError("SOURCE_RESULT_CHANGED")
            row = copy.deepcopy(original)
            key = row["instance_id"], row["arm"]
            if key in seen or row["attempt_id"] in registered:
                raise ValueError("DUPLICATE_REGISTERED_ATTEMPT")
            seen.add(key)
            ancestor = row.get("original_attempt_id")
            if previous_protocol is not None:
                prior = registered.get(ancestor)
                if prior is None or (prior["instance_id"], prior["arm"]) != key:
                    raise ValueError("ATTEMPT_LINEAGE_MISMATCH")
                if (prior.get("usage") or {}).get("issued_requests", 0):
                    correction = protocol.get("estimator_corrections", {}).get(ancestor)
                    if not correction or prior.get("stop_reason") != "CONTEXT_BUDGET_EXHAUSTED":
                        raise ValueError("PAID_ATTEMPT_REPLACEMENT_UNAUTHORIZED")
                    if verified[ancestor]["archive_sha256"] != correction["archive_sha256"]:
                        raise ValueError("CORRECTION_EVIDENCE_CHANGED")
            row.update(
                source_run_id=run_id,
                source_protocol_sha256=protocol_sha,
                execution_source_commit=protocol["execution_source_commit"],
                implementation_sha256=protocol["implementation_sha256"],
            )
            evidence = verified.get(row["attempt_id"])
            if evidence:
                if row.get("usage") and row["usage"] != evidence["usage"]:
                    raise ValueError("SUMMARY_LEDGER_MISMATCH")
                row["usage"] = evidence["usage"]
                row["archive_sha256"] = evidence["archive_sha256"]
                if evidence["interrupted"]:
                    row["original_stop_reason"] = row.get("stop_reason")
                    row["stop_reason"] = "USER_CANCELLED"
                    row.setdefault("oracle_result", "NOT_EXECUTED")
                paid_history.append(
                    {
                        name: copy.deepcopy(row[name])
                        for name in (
                            "attempt_id",
                            "instance_id",
                            "arm",
                            "source_run_id",
                            "source_protocol_sha256",
                            "execution_source_commit",
                            "implementation_sha256",
                            "archive_sha256",
                            "usage",
                            "stop_reason",
                            "oracle_result",
                        )
                        if name in row
                    }
                )
            registered[row["attempt_id"]] = row
            selected[key] = row
        source_identities.append(
            {
                "run_id": run_id,
                "protocol_sha256": protocol_sha,
                "execution_source_commit": protocol["execution_source_commit"],
                "execution_sha256": protocol["execution_sha256"],
                "implementation_sha256": protocol["implementation_sha256"],
            }
        )
        previous_protocol, previous_run = protocol_sha, run_id
    if {row["attempt_id"] for row in paid_history} != set(verified):
        raise ValueError("PAID_HISTORY_INCOMPLETE")
    tasks = sorted(reference["task_contracts"])
    if set(selected) != {(task, arm) for task in tasks for arm in ARMS}:
        raise ValueError("REGISTERED_MATRIX_INCOMPLETE")
    rows = [selected[(task, arm)] for task in tasks for arm in ARMS]
    if any(row["attempt_id"] not in verified for row in rows):
        raise ValueError("ATTEMPT_EVIDENCE_MISSING")
    paired_tasks = [
        task
        for task in tasks
        if all(selected[(task, arm)].get("stop_reason") != "USER_CANCELLED" for arm in ARMS)
    ]
    paired_rows = [row for row in rows if row["instance_id"] in paired_tasks]
    campaign_usage = totals(paid_history)
    if campaign_usage["issued_requests"] > 2520:
        raise ValueError("CAMPAIGN_REQUEST_BUDGET_EXCEEDED")
    if campaign_usage["issued_requests"] != verification["issued_requests"]:
        raise ValueError("VERIFIED_REQUEST_BUDGET_MISMATCH")
    historical_by_key = {(row["instance_id"], row["arm"]): row for row in historical["attempts"]}
    historical_metrics = {
        arm: {
            "attempts": len(paired_tasks),
            "oracle_pass": sum(
                historical_by_key[(task, arm)]["oracle_result"] == "PASS" for task in paired_tasks
            ),
        }
        for arm in ARMS
    }
    return {
        "schema": "repropatch.unified-context-results.v1",
        "status": "completed",
        "new_model_requests": 0,
        "model": reference["model"],
        "reasoning_effort": "max",
        "model_timeout_seconds": 180,
        "context_policy": reference["context_policy"],
        "sources": source_identities,
        "tasks": tasks,
        "attempts": rows,
        "campaign_paid_history": paid_history,
        "campaign_usage": campaign_usage,
        "campaign_paid_attempts": len(paid_history),
        "registered_slots": len(rows),
        "user_cancelled": sum(row.get("stop_reason") == "USER_CANCELLED" for row in rows),
        "oracle_results": dict(Counter(row.get("oracle_result", "NOT_EXECUTED") for row in rows)),
        "all_task_metrics": {
            arm: metrics([row for row in rows if row["arm"] == arm]) for arm in ARMS
        },
        "paired_tasks": paired_tasks,
        "paired_metrics": {
            arm: metrics([row for row in paired_rows if row["arm"] == arm]) for arm in ARMS
        },
        "historical_paired_metrics": historical_metrics,
        "pairwise_full": {arm: comparison(paired_rows, arm) for arm in ARMS if arm != "full"},
        "stop_oracle_matrix": [
            {"stop_reason": stop, "oracle_result": oracle, "attempts": count}
            for (stop, oracle), count in sorted(
                Counter(
                    (
                        row.get("stop_reason", "NOT_EXECUTED"),
                        row.get("oracle_result", "NOT_EXECUTED"),
                    )
                    for row in rows
                ).items()
            )
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True, help="运行ID:结果目录")
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sources = []
    for value in args.source:
        run, name = value.split(":", 1)
        directory = Path(name)
        sources.append(
            (
                int(run),
                json.loads((directory / "protocol.json").read_text()),
                json.loads((directory / "results.json").read_text()),
                sha(directory / "protocol.json"),
            )
        )
    result = consolidate(
        sources, json.loads(args.verification.read_text()), json.loads(args.historical.read_text())
    )
    result["verification_sha256"] = sha(args.verification)
    result["historical_audit_sha256"] = sha(args.historical)
    result["analysis_script_sha256"] = sha(Path(__file__))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    with (args.output / "attempts.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            [
                "instance_id",
                "arm",
                "attempt_id",
                "source_run_id",
                "stop_reason",
                "oracle_result",
                "issued_requests",
                "unknown_usage_requests",
            ]
        )
        for row in result["attempts"]:
            writer.writerow(
                [row[key] for key in ("instance_id", "arm", "attempt_id", "source_run_id")]
                + [row.get("stop_reason"), row.get("oracle_result")]
                + [row["usage"][key] for key in ("issued_requests", "unknown_usage_requests")]
            )
    print(
        json.dumps(
            {
                "registered_slots": result["registered_slots"],
                "oracle_results": result["oracle_results"],
                "campaign_usage": result["campaign_usage"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
