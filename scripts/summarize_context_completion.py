"""从冻结首轮、独立复验与零模型冷评分重算当前结果。"""

import argparse
import copy
import csv
import json
from collections import Counter
from pathlib import Path

from complete_context_campaign import ROOT, snapshot
from context_campaign import save, sha
from summarize_context_campaign import ARMS, comparison, metrics, row_sha, totals


def combine(original, protocol, reruns, cold_scores, verification, protocol_sha=None):
    assert verification["passed"] and not verification["failures"]
    assert reruns["protocol_sha256"] == (
        protocol_sha or sha(ROOT / "benchmarks/context-revalidation-protocol.json")
    )
    proofs = {row["attempt_id"]: row for row in verification["records"]}
    assert len(proofs) == len(verification["records"])
    source_runs = {
        row.get("run_id", verification.get("source_run_id")) for row in verification["records"]
    }
    assert len(source_runs) == 1 and None not in source_runs
    rows = copy.deepcopy(original["attempts"])
    by_id = {row["attempt_id"]: row for row in rows}
    expected = {a["attempt_id"]: a for a in protocol["attempts"]}
    assert {row["attempt_id"] for row in reruns["attempts"]} == set(expected)
    assert len(reruns["attempts"]) == len(expected)
    for updated in reruns["attempts"]:
        registration = expected[updated["attempt_id"]]
        previous = by_id[registration["original_attempt_id"]]
        assert previous["oracle_result"] == "INFRASTRUCTURE_FAILED"
        assert (previous["instance_id"], previous["arm"]) == (
            updated["instance_id"],
            updated["arm"],
        )
        assert updated["original_attempt_id"] == previous["attempt_id"]
        proof = proofs[updated["attempt_id"]]
        assert proof["source_row_sha256"] == row_sha(updated)
        assert proof["usage"] == updated["usage"]
        replacement = copy.deepcopy(updated)
        replacement.update(
            source_run_id=proof["run_id"],
            archive_sha256=proof["archive_sha256"],
            first_record=previous,
        )
        rows[rows.index(previous)] = replacement
    expected_scores = {a["original_attempt_id"]: a for a in protocol["oracle_attempts"]}
    assert {row["attempt_id"] for row in cold_scores} == set(expected_scores)
    assert len(cold_scores) == len(expected_scores)
    for score in cold_scores:
        previous = by_id[score["attempt_id"]]
        registration = expected_scores[score["attempt_id"]]
        proof = proofs[score["attempt_id"]]
        assert proof["source_row_sha256"] == row_sha(score)
        assert (
            score["candidate_sha256"]
            == registration["candidate_sha256"]
            == proof["candidate_sha256"]
        )
        assert (
            previous["oracle_result"] == "NOT_EXECUTED"
            and previous["stop_reason"] == "USER_CANCELLED"
        )
        assert score["scoring_model_requests"] == 0 and score["stop_reason"] == "USER_CANCELLED"
        previous["oracle_result"] = score["oracle_result"]
        previous["checkpoint_oracle"] = copy.deepcopy(score)
    assert set(proofs) == set(expected) | set(expected_scores)
    request_ids = [
        identity for proof in proofs.values() for identity in proof.get("request_ids", [])
    ]
    assert len(request_ids) == len(set(request_ids)) == verification["issued_requests"]
    paid_history = original["campaign_paid_history"] + reruns["attempts"]
    usage = totals(paid_history)
    assert (
        usage["issued_requests"]
        == verification["campaign_issued_requests"]
        <= protocol["parent_request_cap"]
    )
    assert (
        usage["issued_requests"]
        == original["campaign_usage"]["issued_requests"] + verification["issued_requests"]
    )
    paired = [row for row in rows if row["instance_id"] in original["paired_tasks"]]
    return {
        "schema": "repropatch.context-completion.v1",
        "status": "needs_revalidation"
        if any(row["oracle_result"] == "INFRASTRUCTURE_FAILED" for row in rows)
        else "completed",
        "new_model_requests": 0,
        "source_run_id": next(iter(source_runs)),
        "first_result_sha256": protocol["revalidation_snapshot"]["results"]["sha256"],
        "protocol_sha256": reruns["protocol_sha256"],
        "prior_oracle_results": original["oracle_results"],
        "oracle_results": dict(Counter(row["oracle_result"] for row in rows)),
        "registered_slots": len(rows),
        "tasks": original["tasks"],
        "attempts": rows,
        "revalidation_attempts": reruns["attempts"],
        "checkpoint_scores": cold_scores,
        "revalidation_usage": totals(reruns["attempts"]),
        "campaign_usage": usage,
        "campaign_paid_attempts": original["campaign_paid_attempts"] + len(reruns["attempts"]),
        "campaign_paid_history": paid_history,
        "paired_tasks": original["paired_tasks"],
        "paired_metrics": {
            arm: metrics([row for row in paired if row["arm"] == arm]) for arm in ARMS
        },
        "all_task_metrics": {
            arm: metrics([row for row in rows if row["arm"] == arm]) for arm in ARMS
        },
        "pairwise_full": {arm: comparison(paired, arm) for arm in ARMS if arm != "full"},
        "infrastructure_errors": [
            proof for proof in proofs.values() if proof.get("upstream_error")
        ],
    }


def report(result):
    labels = {
        "full": "Full",
        "no-checks": "关闭自检",
        "shell-only": "Shell-only",
        "mini": "mini",
        "codex": "Codex",
    }
    counts = Counter(row["oracle_result"] for row in result["revalidation_attempts"])
    usage = result["campaign_usage"]
    cold_pass = sum(row["oracle_result"] == "PASS" for row in result["checkpoint_scores"])
    current = result["oracle_results"]
    lines = [
        "# 上游故障复验与中断候选评分结果",
        "",
        f"{len(result['revalidation_attempts'])} 次独立复验有 **{counts['PASS']} 项通过、"
        f"{counts['INFRASTRUCTURE_FAILED']} 项上游错误**；"
        f"本轮中断候选冷评分通过 {cold_pass}/{len(result['checkpoint_scores'])}。",
        f"本轮已发 {result['revalidation_usage']['issued_requests']} 次请求，冷评分模型请求为 0；"
        "实际配置为 Luna `max`、180 秒模型总期限、原 O3 Docker 镜像。",
        "",
        "| 任务 | 实验臂 | 当前 Oracle | 停止原因 | 请求 |",
        "| --- | --- | --- | --- | ---: |",
    ]
    lines.extend(
        f"| {r['instance_id'].replace('fmtlib__', '')} | {labels[r['arm']]} | "
        f"{r['oracle_result']} | {r['stop_reason']} | {r['usage']['issued_requests']} |"
        for r in result["revalidation_attempts"]
    )
    lines += [
        "",
        "Full / fmt-3158 的 Checkpoint 20、Shell-only / fmt-1171 的 Checkpoint 24 "
        "取得独立冷评分，原始 `USER_CANCELLED` 停止状态继续保留。",
        "",
        "## 当前评分视图",
        "",
        "| 实验臂 | 21 题全部记录 | 19 题完整配对 | 剩余基础设施错误 |",
        "| --- | ---: | ---: | ---: |",
    ]
    for arm in ARMS:
        whole, paired = result["all_task_metrics"][arm], result["paired_metrics"][arm]
        lines.append(
            f"| {labels[arm]} | {whole['oracle_pass']}/21 | {paired['oracle_pass']}/19 | "
            f"{whole['oracle_results'].get('INFRASTRUCTURE_FAILED', 0)} |"
        )
    lines += [
        "",
        f"当前 105 个槽位有 **{current.get('PASS', 0)} 项通过、"
        f"{current.get('FAIL', 0)} 项候选失败、"
        f"{current.get('INFRASTRUCTURE_FAILED', 0)} 项基础设施错误**。"
        f"有效冷评分为 {current.get('PASS', 0) + current.get('FAIL', 0)}/105。"
        "三次人工中断状态持续保留，完整尝试配对集采用相同 19 题。",
        "",
        "剩余上游错误："
        + "；".join(
            f"{labels[row['arm']]} / {row['instance_id']} "
            f"HTTP {row['upstream_error']['upstream_http_status']}"
            for row in result["infrastructure_errors"]
        ),
        "",
        f"正式累计 **{usage['issued_requests']}/2520 请求**，"
        f"{usage['unknown_usage_requests']} 次用量未知，独立校准 11 次单列。"
        f"{result['campaign_paid_attempts']} 次收费尝试全部保留；"
        "首轮及两次计量故障复验的旧记录继续可查。",
        f"已知输入 {usage['known_input_tokens']:,} Token、"
        f"输出 {usage['known_output_tokens']:,} Token；"
        f"其中缓存输入 {usage['cached_input_tokens']:,}、"
        f"推理输出 {usage['reasoning_tokens']:,}，费用未知。",
        "",
        "[首轮报告](results.md)、[首轮 JSON](results.json)、"
        "[本轮 JSON](completion-results.json)和[当前逐题 CSV](completion-attempts.csv)"
        "分别提供原始事实与复验后的评分视图。",
        f"[Actions 原始批次](https://github.com/lilong555/ReproPatch/actions/runs/{result['source_run_id']})"
        "和[逐归档核验](../../docs/evidence/context-unified-2026-10-27/completion-verification.json)"
        "提供血缘、请求账本、候选 SHA-256 及冷评分证据。",
        "",
        "解开补充证据包，在 `source` 目录使用核心 Python 环境重算：",
        "",
        "```bash",
        "python scripts/summarize_context_completion.py \\",
        "  --protocol benchmarks/context-revalidation-protocol.json \\",
        "  --results ../evidence/results \\",
        "  --verification ../evidence/verification.json \\",
        "  --output ../replay",
        "```",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    p = json.loads(args.protocol.read_text())
    snapshot(p)
    original = json.loads((ROOT / p["revalidation_snapshot"]["results"]["path"]).read_text())
    reruns = json.loads((args.results / "results.json").read_text())
    cold = [
        row
        for path in (args.results / "checkpoint-oracles").rglob("summary.json")
        for row in json.loads(path.read_text())["attempts"]
    ]
    verification = json.loads(args.verification.read_text())
    result = combine(original, p, reruns, cold, verification, sha(args.protocol))
    result["verification_sha256"] = sha(args.verification)
    result["analysis_script_sha256"] = sha(Path(__file__))
    save(args.output / "completion-results.json", result)
    (args.output / "completion-results.md").write_text(report(result))
    with (args.output / "completion-attempts.csv").open("w", newline="") as stream:
        columns = (
            "instance_id",
            "arm",
            "attempt_id",
            "stop_reason",
            "oracle_result",
            "issued_requests",
            "scoring_id",
        )
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in result["attempts"]:
            writer.writerow(
                {
                    **{key: row.get(key, "") for key in columns[:5]},
                    "issued_requests": row.get("usage", {}).get("issued_requests", 0),
                    "scoring_id": row.get("checkpoint_oracle", {}).get("scoring_id", ""),
                }
            )
    print(
        json.dumps(
            {
                "oracle_results": result["oracle_results"],
                "campaign_usage": result["campaign_usage"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
