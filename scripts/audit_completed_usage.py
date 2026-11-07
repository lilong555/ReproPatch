"""Audit completed context/recovery artifacts offline and account for every request."""

from __future__ import annotations

import argparse
import json
import statistics
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from audit_context_triggers import Archive, digest, load_events
from benchmark_recovery_costs import open_database, usage_sum
from report_context_results import excerpt, load, require, save
from run_recovery_pair import pair_metrics, remaining_budget, summarize

FIELDS = ("requests", "input_tokens", "output_tokens", "cached_input_tokens")


def retain(archive, predicate):
    selected = {
        name for name in archive.identities if predicate(name) and name not in archive.files
    }
    with tarfile.open(archive.path, "r|gz") as stream:
        for member in stream:
            if member.name not in selected:
                continue
            raw = stream.extractfile(member).read()
            require((len(raw), digest(raw)) == archive.identities[member.name], "member_changed")
            archive.files[member.name] = raw
            selected.remove(member.name)
    require(not selected, "missing_members")


def verified_archive(folder, artifact, stem):
    receipt = load(folder / "download.json")
    require(receipt["artifact_id"] == artifact["id"], "artifact_id_mismatch")
    require(
        digest((folder / "artifact.zip").read_bytes())
        == artifact["digest"].removeprefix("sha256:"),
        "artifact_zip_hash_mismatch",
    )
    for member in receipt["members"]:
        require(digest((folder / member["path"]).read_bytes()) == member["sha256"], "member_sha")
    archive = Archive(folder / (stem + ".tar.gz"))
    metadata = load(folder / (stem + ".tar.metadata.json"))
    require(archive.inventory_verified, "inventory_missing")
    require(archive.sha256 == metadata["sha256"], "archive_hash_mismatch")
    require(len(archive.identities) - 1 == metadata["files"], "archive_file_count")
    return archive


def ledger_evidence(archive, ledger_name, attempt, http_prefix):
    with open_database(archive.read(ledger_name)) as db:
        rows = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM requests WHERE attempt=? ORDER BY sent_at,id", (attempt,)
            )
        ]
        presend = {
            r["id"]: dict(r)
            for r in db.execute("SELECT * FROM pre_send WHERE attempt=? AND issued=1", (attempt,))
        }
    require(rows and {r["id"] for r in rows} == set(presend), "issued_request_population")
    names = {Path(n).name: n for n in archive.files if n.startswith(http_prefix)}
    require(
        len(names) == len([n for n in archive.files if n.startswith(http_prefix)]),
        "ambiguous_http_member",
    )
    compact = []
    bodies = []
    for row in rows:
        pre = presend[row["id"]]
        request_name = names[row["id"] + "-request.json"]
        response_name = names[row["id"] + "-response.json"]
        request, response = archive.read(request_name), archive.read(response_name)
        require(pre["purpose"] == row["purpose"], "purpose_mismatch")
        require(digest(request) == row["request_sha256"] == digest(pre["payload"]), "request_hash")
        require(digest(response) == row["response_sha256"], "response_hash")
        require(row["status_code"] == 200 and row["usage"] is not None, "unknown_usage")
        usage = json.loads(row["usage"])
        require(json.loads(response)["usage"] == usage, "provider_usage_mismatch")
        body = json.loads(request)
        role = row["purpose"]
        if role == "compact":
            role = (
                "early_selection"
                if body.get("instructions", "").startswith(
                    "Select source lines to retain from an older file observation."
                )
                else "history_compaction"
            )
        compact.append(
            {
                "id": row["id"],
                "role": role,
                "requests": 1,
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "cached_input_tokens": (usage.get("input_tokens_details") or {}).get(
                    "cached_tokens", 0
                ),
                "request_sha256": row["request_sha256"],
                "response_sha256": row["response_sha256"],
            }
        )
        bodies.append(body)
    by_role = {}
    for role in sorted({r["role"] for r in compact}):
        by_role[role] = {k: sum(r[k] for r in compact if r["role"] == role) for k in FIELDS}
    return {"usage": usage_sum(rows), "by_role": by_role, "requests": compact}, rows, bodies


def match_usage(accounted, expected):
    for field in (*FIELDS, "unknown_usage_requests", "known_input_tokens", "known_output_tokens"):
        require(accounted[field] == expected[field], "usage_mismatch:" + field)
    for role in ("repair", "compact"):
        require(
            accounted["request_purposes"].get(role, 0) == expected[role + "_requests"],
            "request_purpose_count:" + role,
        )


def context_row(row, artifact, root):
    archive = verified_archive(root / artifact["name"], artifact, "context-attempt")
    retain(
        archive,
        lambda n: (
            n in {"summary.json", "usage.sqlite3", "raw-usage.json"}
            or n.startswith("worker/http-native/")
        ),
    )
    require(archive.json("summary.json") == row, "raw_summary_mismatch")
    account, requests, bodies = ledger_evidence(
        archive, "usage.sqlite3", row["attempt_id"], "worker/http-native/"
    )
    require(
        sorted(archive.json("raw-usage.json"), key=lambda r: r["id"])
        == sorted(requests, key=lambda r: r["id"]),
        "raw_usage_mismatch",
    )
    match_usage(account["usage"], row["usage"])
    early = account["by_role"].get("early_selection", dict.fromkeys(FIELDS, 0))
    metrics = row["mechanisms"]["early_observation_reduction"]["metrics"]
    for key in FIELDS:
        require(early[key] == metrics["auxiliary_" + key], "early_auxiliary_mismatch:" + key)
    record = {
        key: row[key]
        for key in ("job_key", "attempt_id", "instance_id", "arm", "repeat", "accepted")
    }
    record.update(
        account,
        verified=True,
        artifact_url=artifact["url"],
        archive_sha256=archive.sha256,
        archive_files=len(archive.identities),
    )
    return record, bodies[0]


def expanded_input(body):
    values = []
    for item in body["input"]:
        value = dict(item)
        if isinstance(value.get("content"), str):
            try:
                value["content"] = json.loads(value["content"])
            except ValueError:
                pass
        values.append(value)
    return values


def differing_paths(left, right, path="input"):
    if left == right:
        return set()
    if isinstance(left, dict) and isinstance(right, dict):
        result = set()
        for key in left.keys() | right.keys():
            result |= differing_paths(left.get(key), right.get(key), path + "." + key)
        return result
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        result = set()
        for i, (a, b) in enumerate(zip(left, right, strict=True)):
            result |= differing_paths(a, b, f"{path}[{i}]")
        return result
    return {path}


def context_summary(results, audited):
    records = [r for r, _ in audited]
    by_arm, by_task, identities = {}, {}, []
    for arm in results["arms"]:
        selected = [r for r in records if r["arm"] == arm]
        totals = {k: sum(r["usage"][k] for r in selected) for k in FIELDS}
        roles = sorted({role for r in selected for role in r["by_role"]})
        by_arm[arm] = {
            "n": len(selected),
            "accepted": sum(r["accepted"] for r in selected),
            **totals,
            "total_tokens": totals["input_tokens"] + totals["output_tokens"],
            "uncached_input_tokens": totals["input_tokens"] - totals["cached_input_tokens"],
            "by_role": {
                role: {
                    k: sum(r["by_role"].get(role, {}).get(k, 0) for r in selected) for k in FIELDS
                }
                for role in roles
            },
        }
    for task in sorted({r["instance_id"] for r in records}):
        by_task[task] = {}
        for arm in by_arm:
            group = [r for r in records if r["instance_id"] == task and r["arm"] == arm]
            by_task[task][arm] = {
                "n": len(group),
                "accepted": sum(r["accepted"] for r in group),
                "input_mean": statistics.mean(r["usage"]["input_tokens"] for r in group),
                "output_mean": statistics.mean(r["usage"]["output_tokens"] for r in group),
            }
        inputs = [expanded_input(body) for r, body in audited if r["instance_id"] == task]
        paths = set()
        for body in inputs[1:]:
            paths |= differing_paths(inputs[0], body)
        identities.append({"instance_id": task, "differing_first_input_paths": sorted(paths)})
    comparisons = {}
    for arm in by_arm:
        if arm == "baseline":
            continue
        baseline, treatment = by_arm["baseline"], by_arm[arm]
        by_repeat = {}
        for repeat in sorted({r["repeat"] for r in records}):
            sums = {
                a: sum(
                    r["usage"]["input_tokens"]
                    for r in records
                    if r["arm"] == a and r["repeat"] == repeat
                )
                for a in ("baseline", arm)
            }
            by_repeat[str(repeat)] = {
                "baseline_input": sums["baseline"],
                "treatment_input": sums[arm],
                "input_change_percent": 100 * (sums[arm] / sums["baseline"] - 1),
            }
        comparisons[arm] = {
            "input_change_percent": 100
            * (treatment["input_tokens"] / baseline["input_tokens"] - 1),
            "total_change_percent": 100
            * (treatment["total_tokens"] / baseline["total_tokens"] - 1),
            "task_means_lower": sum(
                v[arm]["input_mean"] < v["baseline"]["input_mean"] for v in by_task.values()
            ),
            "task_count": len(by_task),
            "by_repeat": by_repeat,
        }
    return {
        "arms": by_arm,
        "tasks": by_task,
        "first_input_differences": identities,
        "comparisons": comparisons,
        "verified_attempts": len(records),
        "verified_provider_responses": sum(r["usage"]["requests"] for r in records),
    }


def event_projection(archive, root, run_id):
    events = load_events(archive, root, run_id)
    with open_database(archive.read(root + "events.sqlite3")) as db:
        stored = [
            json.loads(r[0]) for r in db.execute("SELECT envelope_json FROM events ORDER BY seq")
        ]
        runs = [dict(r) for r in db.execute("SELECT * FROM runs")]
        checkpoints = [
            dict(r) for r in db.execute("SELECT * FROM checkpoints ORDER BY checkpoint_id")
        ]
    require(
        events == stored and len(runs) == 1 and runs[0]["run_id"] == run_id,
        "sqlite_event_projection_mismatch",
    )
    return events, runs[0], checkpoints


def recovery_pair(row, artifact, root, output):
    archive = verified_archive(root / artifact["name"], artifact, "recovery")
    retain(archive, lambda n: n.startswith("execution/"))
    prefix_path = "execution/" + row["pair_id"] + "/"
    require(
        archive.json(prefix_path + "pair.json")
        == {k: v for k, v in row.items() if k != "workflow"},
        "raw_pair_mismatch",
    )
    require(row["workflow"]["raw_artifact"] == artifact["name"], "workflow_artifact_mismatch")
    prefix = archive.json(prefix_path + "resume/prefix.json")
    resumed = archive.json(prefix_path + "resume/result.json")
    restarted = archive.json(prefix_path + "restart/result.json")
    require(pair_metrics(prefix, resumed, restarted) == row["metrics"], "pair_metrics_mismatch")
    require(
        remaining_budget(prefix["run_state"], prefix["checkpoint"], prefix["original_budget"])
        == row["remaining_budget"],
        "remaining_budget_mismatch",
    )
    evidence = {
        k: row[k] for k in ("pair_id", "instance_id", "repeat", "recovery_checks", "metrics")
    }
    evidence.update(
        artifact_url=artifact["url"],
        archive_sha256=archive.sha256,
        archive_files=len(archive.identities),
        verified=False,
        arms={},
        failures=[],
    )
    for arm, result in (("resume", resumed), ("restart", restarted)):
        account, requests, _ = ledger_evidence(
            archive,
            prefix_path + arm + "-usage.sqlite3",
            row[arm + "_attempt"],
            prefix_path + arm + "/http-native/",
        )
        match_usage(account["usage"], result["usage"])
        require(result["usage"] == row["attempt_usage"][arm], "attempt_usage_mismatch")
        run_id = result["native_run_id"]
        run_root = prefix_path + arm + "/runs/" + run_id + "/"
        events, run, checkpoints = event_projection(archive, run_root, run_id)
        require(run["steps_used"] == result["model_steps"], "model_counter_mismatch")
        if arm == "resume":
            require(run_id == prefix["native_run_id"], "same_run_mismatch")
            require(run["deadline_at"] == prefix["run_state"]["deadline_at"], "deadline_mismatch")
            require(all(row["recovery_checks"].values()), "recovery_check_failed")
            require(
                resumed["recovery_checks"] == row["recovery_checks"], "recovery_checks_mismatch"
            )
            cp = next(
                c
                for c in checkpoints
                if c["checkpoint_id"] == prefix["checkpoint"]["checkpoint_id"]
            )
            ref = json.loads(cp["manifest_ref_json"])
            archive.verify(ref, run_root)
            manifest = archive.json(run_root + ref["path"])
            require(
                {**manifest, "committed_at": cp["created_at"]} == prefix["checkpoint"],
                "checkpoint_mismatch",
            )
            archive.verify_nested(manifest, run_root)
            require(
                manifest["step_id"] == 3 and manifest["boundary"] == "model_input_ready",
                "prefix_boundary",
            )
            match_usage(usage_sum(requests[:3]), prefix["usage"])
            columns = ("id", "request_sha256", "response_sha256", "usage", "status_code")
            require(
                [{k: r[k] for k in columns} for r in requests[:3]] == prefix["ledger"]["requests"],
                "prefix_ledger_rows_changed",
            )
        score_root = prefix_path + arm + "-score/"
        score = archive.json(score_root + "score.json")
        require(score == row[arm + "_score"]["score"], "score_mismatch")
        require(
            digest(archive.read(prefix_path + arm + "/result.json"))
            == score["worker_result_sha256"],
            "worker_hash",
        )
        require(
            digest(archive.read(score_root + "candidate.patch")) == score["candidate_sha256"],
            "candidate_hash",
        )
        verdict = archive.json(score_root + "oracle/oracle-verdict.json")
        require(
            digest(archive.read(score_root + "oracle/oracle-verdict.json"))
            == score["oracle_verdict_sha256"],
            "verdict_hash",
        )
        require(
            verdict["status"] == score["status"] and verdict["accepted"] == score["accepted"],
            "verdict_mismatch",
        )
        evidence["arms"][arm] = {
            **account,
            "accepted": score["accepted"],
            "score_status": score["status"],
            "stop_reason": result["agent_stop_reason"],
            "event_count": len(events),
        }
        if not score["accepted"]:
            failure = {
                "pair_id": row["pair_id"],
                "instance_id": row["instance_id"],
                "arm": arm,
                "score_status": score["status"],
                "stop_reason": result["agent_stop_reason"],
                "artifact_url": artifact["url"],
                "logs": [],
            }
            for name in sorted(archive.files):
                if (
                    name.startswith(score_root + "oracle/logs/") and name.endswith(".log")
                ) or name == score_root + "candidate.patch":
                    data = archive.read(name)
                    target = output / "evidence" / row["pair_id"] / arm / Path(name).name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    failure["logs"].append(
                        {
                            "path": target.relative_to(output).as_posix(),
                            "sha256": digest(data),
                            "excerpts": excerpt(
                                data.decode(errors="replace"),
                                r"(?:fatal )?error:|undefined reference|\[  FAILED  \]",
                            ),
                        }
                    )
            evidence["failures"].append(failure)
    evidence["verified"] = True
    return evidence


def failure_markdown(records):
    count = sum(len(r["failures"]) for r in records)
    lines = [
        "# 恢复配对实验逐条失败",
        "",
        f"全部 {len(records)} 对、{2 * len(records)} 条最终轨迹中有 {count} 条冷验收失败。",
        "",
    ]
    for record in records:
        for row in record["failures"]:
            lines += [
                f"## {row['pair_id']} · {row['instance_id']} · {row['arm']}",
                "",
                f"冷评分 `{row['score_status']}`；停止原因 `{row['stop_reason']}`。",
                "",
                f"[完整原始轨迹]({row['artifact_url']})。",
                "",
            ]
            for log in row["logs"]:
                lines += [f"[{Path(log['path']).name}]({log['path']})", ""]
                for part in log["excerpts"]:
                    lines += [f"第 {part['line']} 行起：", "", "```text", part["text"], "```", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("context", "recovery"))
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 9))
    args = parser.parse_args()
    results, index = load(args.results), load(args.artifacts)
    artifacts = {a["name"]: a for a in index["raw_artifacts"]}
    rows = results["attempts" if args.kind == "context" else "pairs"]
    key = "job_key" if args.kind == "context" else "pair_id"
    require(len({r[key] for r in rows}) == len(rows), "duplicate_population")
    names = [f"{args.kind}-raw-{index['run_id']}-{r[key]}" for r in rows]
    require(set(names) == set(artifacts), "artifact_population_mismatch")
    args.output.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        if args.kind == "context":
            require(len(rows) == results["registered_trials"], "registered_count")
            audited = list(
                pool.map(
                    lambda pair: context_row(pair[0], artifacts[pair[1]], args.raw_dir),
                    zip(rows, names, strict=True),
                )
            )
            summary = context_summary(results, audited)
            records = [r for r, _ in audited]
        else:
            require(args.protocol is not None, "protocol_required")
            require(summarize(load(args.protocol), rows) == results, "recovery_summary_mismatch")
            records = list(
                pool.map(
                    lambda pair: recovery_pair(
                        pair[0], artifacts[pair[1]], args.raw_dir, args.output
                    ),
                    zip(rows, names, strict=True),
                )
            )
            timings = [r["resume_measurement"]["restore_ready_seconds"] for r in rows]
            summary = {
                "verified_pairs": len(records),
                "verified_provider_responses": sum(
                    a["usage"]["requests"] for r in records for a in r["arms"].values()
                ),
                "cold_successes": results["cold_successes"],
                "paired_input_cost": results["paired_input_cost"],
                "restore_ready_seconds": {
                    "median": statistics.median(timings),
                    "min": min(timings),
                    "max": max(timings),
                },
                "resume_wall_seconds": sum(r["metrics"]["resume_wall_seconds"] for r in rows),
                "restart_wall_seconds": sum(r["metrics"]["restart_wall_seconds"] for r in rows),
                "restart_minus_resume_wall_seconds": sum(
                    r["metrics"]["restart_minus_resume_wall_seconds"] for r in rows
                ),
                "checks": {
                    k: sum(r["recovery_checks"][k] for r in rows)
                    for k in rows[0]["recovery_checks"]
                },
            }
            (args.output / "failures.md").write_text(failure_markdown(records))
    summary.update(
        schema="repropatch.completed-usage-audit.v1",
        kind=args.kind,
        run_id=index["run_id"],
        source_commit=index["source_commit"],
        results_sha256=digest(args.results.read_bytes()),
        artifact_index_sha256=digest(args.artifacts.read_bytes()),
        audit_source_sha256=digest(Path(__file__).read_bytes()),
    )
    save(args.output / "summary.json", summary)
    (args.output / "attempts.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    )
    print(
        json.dumps({k: v for k, v in summary.items() if k.startswith("verified_") or k == "run_id"})
    )


if __name__ == "__main__":
    main()
