"""Verify a completed context batch and export per-attempt failure evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from audit_context_triggers import digest, load_events
from audit_false_positives import VerificationArchive
from context_ablation import arm_statistics, paired_statistics


def require(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def excerpt(text, pattern, limit=4):
    lines, excerpts, end = text.splitlines(), [], -1
    for index, line in enumerate(lines):
        if index <= end or not re.search(pattern, line):
            continue
        start, end = max(0, index - 1), min(len(lines) - 1, index + 8)
        excerpts.append({"line": start + 1, "text": "\n".join(lines[start : end + 1])})
        if len(excerpts) == limit:
            break
    return excerpts


def inspect_attempt(row, artifact, raw_root, output):
    record = {
        key: row[key]
        for key in ("job_key", "attempt_id", "instance_id", "arm", "repeat", "accepted")
    }
    record.update(
        artifact_id=artifact["id"],
        artifact_url=artifact["url"],
        archive_verified=False,
        evidence_status="missing",
        score_status=row["score"]["status"],
        stop_reason=row["stop_reason"],
        input_tokens=row["usage"]["input_tokens"],
        output_tokens=row["usage"]["output_tokens"],
        requests=row["usage"]["requests"],
        f2p=row["score"].get("f2p", {}),
        p2p=row["score"].get("p2p", {}),
        logs=[],
        compact_requests=[],
    )
    folder = raw_root / artifact["name"]
    try:
        receipt = load(folder / "download.json")
        expected = artifact["digest"].removeprefix("sha256:")
        require(receipt["artifact_id"] == artifact["id"], "artifact_id_mismatch")
        require(digest((folder / "artifact.zip").read_bytes()) == expected, "zip_sha_mismatch")
        for member in receipt["members"]:
            require(
                digest((folder / member["path"]).read_bytes()) == member["sha256"],
                "zip_member_sha_mismatch",
            )
        archive = VerificationArchive(folder / "context-attempt.tar.gz")
        metadata = load(folder / "context-attempt.tar.metadata.json")
        require(archive.sha256 == metadata["sha256"], "tar_sha_mismatch")
        require(archive.json("summary.json") == row, "raw_summary_mismatch")
        score = archive.json("score/score.json")
        require(score == row["score"], "raw_score_mismatch")
        require(
            digest(archive.read("worker/result.json")) == score["worker_result_sha256"],
            "worker_result_sha_mismatch",
        )
        if score.get("oracle_executed"):
            verdict = archive.json("score/oracle/oracle-verdict.json")
            require(
                digest(archive.read("score/oracle/oracle-verdict.json"))
                == score["oracle_verdict_sha256"],
                "cold_verdict_sha_mismatch",
            )
            require(verdict["status"] == score["status"], "cold_status_mismatch")
            require(verdict["accepted"] == row["accepted"], "cold_outcome_mismatch")
            require(
                digest(archive.read("score/candidate.patch")) == row["candidate_sha256"],
                "candidate_sha_mismatch",
            )
        roots = [
            name.removesuffix("events.jsonl")
            for name in archive.files
            if name.startswith("worker/runs/") and name.endswith("/events.jsonl")
        ]
        require(len(roots) == 1, "run_root_ambiguous")
        root = roots[0]
        events = load_events(archive, root, root.split("/")[2])
        record.update(
            archive_verified=True,
            evidence_status="verified",
            archive_sha256=archive.sha256,
            archive_file_count=len(archive.identities),
            event_count=len(events),
        )
        for event in events:
            if "compact" in event["type"]:
                record["compact_requests"].append(
                    {key: event.get(key) for key in ("seq", "type", "step_id", "payload")}
                )
        if row["accepted"]:
            return record
        for name in sorted(archive.files):
            if not name.startswith("score/oracle/logs/") or not name.endswith(".log"):
                continue
            raw = archive.read(name)
            target = output / "evidence" / row["job_key"] / Path(name).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            text = raw.decode("utf-8", errors="replace")
            record["logs"].append(
                {
                    "archive_path": name,
                    "report_path": target.relative_to(output).as_posix(),
                    "sha256": digest(raw),
                    "bytes": len(raw),
                    "excerpts": excerpt(
                        text,
                        r"(?:fatal )?error:|undefined reference|: Failure|SEGFAULT|"
                        r"\[  FAILED  \]|CMake Error|TIMEOUT|Aborted|Assertion .*failed",
                    ),
                }
            )
        patch_name = "score/candidate.patch"
        if patch_name in archive.files:
            target = output / "evidence" / row["job_key"] / "candidate.patch"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(patch_name))
            record["candidate_path"] = target.relative_to(output).as_posix()
    except (OSError, ValueError, KeyError) as error:
        record.update(evidence_status="verification_failed", error=str(error))
    return record


def statistics(results):
    rows, baseline = results["attempts"], results["arms"]["baseline"]
    base_input = baseline["input_tokens"]["all_trial_mean"]
    base_total = base_input + baseline["output_tokens"]["all_trial_mean"]
    analysis = {"arms": {}, "paired_outcomes": {}, "task_results": {}}
    for arm, official in results["arms"].items():
        selected = [row for row in rows if row["arm"] == arm]
        require(arm_statistics(selected) == official, "arm_recompute_mismatch:" + arm)
        inp, out = (official[key]["all_trial_mean"] for key in ("input_tokens", "output_tokens"))
        mechanisms = {}
        for name, counts in official["mechanisms"].items():
            metrics = [row["mechanisms"][name].get("metrics", {}) for row in selected]
            mechanisms[name] = {
                **counts,
                "bytes": {
                    key: sum(value.get(key, 0) or 0 for value in metrics)
                    for key in ("input_bytes", "output_bytes", "saved_bytes", "added_bytes")
                },
            }
        analysis["arms"][arm] = {
            "n": len(selected),
            "accepted": official["pass"],
            "success_rate": official["pass"] / len(selected),
            "input_mean": inp,
            "output_mean": out,
            "total_mean": inp + out,
            "input_change_percent": 100 * (inp / base_input - 1),
            "total_change_percent": 100 * ((inp + out) / base_total - 1),
            "requests": sum(row["usage"]["requests"] for row in selected),
            "cached_input_tokens": sum(row["usage"]["cached_input_tokens"] for row in selected),
            "score_statuses": dict(Counter(row["score"]["status"] for row in selected)),
            "mechanisms": mechanisms,
        }
    by_key = {(row["instance_id"], row["repeat"], row["arm"]): row for row in rows}
    for pair in results["paired_differences"]:
        require(
            paired_statistics(rows, pair["left"], pair["right"]) == pair,
            "paired_recompute_mismatch",
        )
        if pair["left"] != "baseline":
            continue
        counts = Counter()
        for task, repeat in {(row["instance_id"], row["repeat"]) for row in rows}:
            left = by_key[task, repeat, "baseline"]["accepted"]
            right = by_key[task, repeat, pair["right"]]["accepted"]
            counts[
                "both_pass"
                if left and right
                else "both_fail"
                if not (left or right)
                else "treatment_only_pass"
                if right
                else "baseline_only_pass"
            ] += 1
        analysis["paired_outcomes"][pair["right"]] = dict(counts)
    for task in sorted({row["instance_id"] for row in rows}):
        analysis["task_results"][task] = {
            arm: sum(
                row["accepted"] for row in rows if row["instance_id"] == task and row["arm"] == arm
            )
            for arm in results["arms"]
        }
    analysis["usage"] = {
        key: sum(row["usage"].get(key, 0) or 0 for row in rows)
        for key in (
            "requests",
            "repair_requests",
            "compact_requests",
            "input_tokens",
            "output_tokens",
            "cached_input_tokens",
            "unknown_usage_requests",
        )
    }
    return analysis


def failure_report(records, analysis):
    failed = [row for row in records if not row["accepted"]]
    lines = [
        "# 回执上下文策略逐题结果与失败证据",
        "",
        f"全部 {len(records)} 条轨迹中，{len(records) - len(failed)} 条冷验收通过，"
        f"{len(failed)} 条失败。评分状态、执行停止原因与具体日志分别保存。",
        "",
        "## 19 题逐组通过数",
        "",
        "| 任务 | baseline | diagnostics | dedup | state | combined |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for task, arms in analysis["task_results"].items():
        lines.append(f"| `{task}` | " + " | ".join(f"{v}/2" for v in arms.values()) + " |")
    lines += [
        "",
        "## 逐条失败与原始轨迹",
        "",
        "日志链接保存冷构建、测试输出与候选补丁全文。原始轨迹包含完整模型请求、"
        "工具回执、SQLite 事件及源码身份。",
        "",
    ]
    for row in sorted(failed, key=lambda r: (r["instance_id"], r["arm"], r["repeat"])):
        lines += [
            f"### {row['job_key']} · {row['instance_id']} · {row['arm']} · r{row['repeat']}",
            "",
            f"冷评分：`{row['score_status']}`；停止：`{row['stop_reason']}`；"
            f"请求：{row['requests']}/24；原件核验：`{row['evidence_status']}`。",
            "",
            f"[完整原始轨迹]({row['artifact_url']})。",
            "",
        ]
        if row["score_status"] == "EMPTY_CANDIDATE":
            lines += ["执行结束时未形成非空候选补丁，冷构建与测试保持未执行状态。", ""]
        else:
            for group in ("f2p", "p2p"):
                groups = row[group]
                failed_names = [name for name, state in groups.items() if state != "passed"]
                lines.append(
                    f"{group.upper()}：{sum(v == 'passed' for v in groups.values())}/{len(groups)}"
                    " 通过；其余状态："
                    + (", ".join(f"`{name}`={groups[name]}" for name in failed_names) or "全部通过")
                    + "。"
                )
            lines.append("")
        if row.get("candidate_path"):
            lines += [f"[候选补丁]({row['candidate_path']})。", ""]
        for log in row["logs"]:
            lines += [f"[{Path(log['archive_path']).name}]({log['report_path']})", ""]
            for part in log["excerpts"]:
                lines += [f"从第 {part['line']} 行起：", "", "```text", part["text"], "```", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 9))
    args = parser.parse_args()
    results, index = load(args.results), load(args.artifacts)
    rows = results["attempts"]
    require(len(rows) == results["registered_trials"], "registered_count_mismatch")
    require(len({row["attempt_id"] for row in rows}) == len(rows), "duplicate_attempt")
    require(all(type(row["accepted"]) is bool for row in rows), "unknown_outcome")
    require(all(row["usage"]["unknown_usage_requests"] == 0 for row in rows), "unknown_usage")
    artifacts = {artifact["name"]: artifact for artifact in index["raw_artifacts"]}
    run_id = index["run_id"]
    expected = {f"context-raw-{run_id}-{row['job_key']}" for row in rows}
    require(set(artifacts) == expected, "artifact_population_mismatch")
    args.output.mkdir(parents=True, exist_ok=False)
    analysis = statistics(results)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        records = list(
            pool.map(
                lambda row: inspect_attempt(
                    row,
                    artifacts[f"context-raw-{run_id}-{row['job_key']}"],
                    args.raw_dir,
                    args.output,
                ),
                rows,
            )
        )
    analysis.update(
        schema="repropatch.context-result-evidence.v1",
        run_id=run_id,
        source_commit=index["source_commit"],
        registered_trials=len(rows),
        verified_raw=sum(row["evidence_status"] == "verified" for row in records),
        failure_count=sum(not row["accepted"] for row in rows),
        failure_tasks=dict(Counter(row["instance_id"] for row in rows if not row["accepted"])),
        input_refs={
            "results_sha256": digest(args.results.read_bytes()),
            "artifacts_sha256": digest(args.artifacts.read_bytes()),
            "analysis_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
    )
    save(args.output / "analysis.json", analysis)
    for name, selected in (
        ("evidence.jsonl", records),
        ("failures.jsonl", [row for row in records if not row["accepted"]]),
    ):
        (args.output / name).write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in selected)
        )
    (args.output / "failures.md").write_text(failure_report(records, analysis))
    print(
        json.dumps(
            {
                key: analysis[key]
                for key in ("run_id", "registered_trials", "verified_raw", "failure_count")
            }
        )
    )
    raise SystemExit(analysis["verified_raw"] != len(rows))


if __name__ == "__main__":
    main()
