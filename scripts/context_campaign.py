"""统一上下文批次的源码身份、CI、校准及 Pilot 门禁。"""

import argparse
import ast
import hashlib
import json
import os
import subprocess
import time
from collections import Counter
from pathlib import Path

from benchmark_budget import LocalUsageLedger

from repropatch.context import ContextPolicy, TokenEstimator, admission_reason, encoded

ROOT = Path(__file__).resolve().parents[1]
EXECUTION_PATHS = (
    "src",
    "scripts",
    "tests",
    "requirements",
    "docker",
    ".github/workflows",
    "pyproject.toml",
)
ARMS = ("full", "no-checks", "shell-only", "mini", "codex")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execution_identity():
    """执行文件与测试一起冻结，协议和运行证据拥有独立身份。"""
    paths = subprocess.check_output(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            *EXECUTION_PATHS,
        ],
        cwd=ROOT,
    ).split(b"\0")
    manifest = {
        name.decode(): sha(ROOT / name.decode())
        for name in sorted(set(paths))
        if name and (ROOT / name.decode()).is_file()
    }
    return {"sha256": hashlib.sha256(encoded(manifest)).hexdigest(), "files": manifest}


def validate_protocol(p):
    policy = ContextPolicy.from_dict(p["context_policy"])
    assert policy.context_policy_version == "v1.0-unified-compaction"
    assert p["model"] == "gpt-6-luna" and p["reasoning_effort"] == "max"
    assert p["endpoint"] == "https://cpa.liyinlong.me/v1"
    assert p["retries"] == 0
    if "paid_calls_authorized" in p:
        assert p["paid_calls_authorized"] is True
    if p["phase"] == "calibration":
        assert p["calibration_request_cap"] == 12
        return
    assert p["arms"] == list(ARMS)
    assert p["request_cap_per_attempt"] == policy.request_cap == 24
    recovering = p["phase"] == "recovery"
    expected = (
        {(a["instance_id"], a["arm"]) for a in p["attempts"]}
        if recovering
        else {(task, arm) for task in p["tasks"] for arm in ARMS}
    )
    assert expected <= {(task, arm) for task in p["tasks"] for arm in ARMS}
    ordered = [(row["instance_id"], row["arm"]) for row in p["execution_order"]]
    assert len(ordered) == len(expected) and set(ordered) == expected
    assert p["formal_request_cap"] == len(expected) * 24
    assert set(p["task_contracts"]) == set(p["tasks"])
    if recovering:
        assert p["parent_request_cap"] == 2520
        assert p["prior_committed_request_upper_bound"] + p["formal_request_cap"] <= 2520
        assert len(expected) == len(p["attempts"])
    else:
        assert p["formal_request_cap"] == (480 if p["phase"] == "pilot" else 2520)


def gh_json(*arguments):
    return json.loads(subprocess.check_output(["gh", *arguments], cwd=ROOT))


def download(repo, run_id, artifact, destination):
    subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(run_id),
            "--repo",
            repo,
            "--name",
            artifact,
            "--dir",
            str(destination),
        ],
        check=True,
        cwd=ROOT,
    )


def calibration_gate(source, p):
    result = json.loads((source / "result.json").read_text())
    frozen = json.loads((source / "protocol.json").read_text())
    assert result["passed"] is True
    assert result["context_policy"] == p["context_policy"] == frozen["context_policy"]
    for key in ("model", "endpoint", "reasoning_effort"):
        assert p[key] == frozen[key]
    assert frozen["execution_sha256"] == p.get(
        "calibration_execution_sha256", p["execution_sha256"]
    )
    for name, digest in p.get("calibration_compatible_files", {}).items():
        assert sha(ROOT / name) == digest, "CALIBRATION_WIRE_SOURCE_CHANGED"
    if p.get("calibration_context_wire_sha256"):
        assert p["calibration_context_wire_source_commit"] == frozen["execution_source_commit"]
        assert context_wire_identity() == p["calibration_context_wire_sha256"], (
            "CALIBRATION_CONTEXT_WIRE_CHANGED"
        )
    usage = LocalUsageLedger(source / "usage.sqlite3").summary()
    assert usage == result["usage"]
    assert usage["issued_requests"] <= 12 and usage["unknown_usage_requests"] == 0
    assert {row["check"] for row in result["checks"]} == {
        "common_context_window",
        "transport_body",
        "repropatch_context_wire",
        "mini_context_wire",
        "codex_context_wire",
    }
    assert all(row["passed"] for row in result["checks"])
    return {"passed": True, "issued_requests": usage["issued_requests"]}


def context_wire_identity(source=None):
    """摘要、序列化和策略合同拥有独立身份，计量修正通过原始请求重放验收。"""
    tree = ast.parse(source or (ROOT / "src/repropatch/context.py").read_text())
    nodes = [
        ast.dump(node, include_attributes=False)
        for node in tree.body
        if getattr(node, "name", None) not in {"fingerprint", "TokenEstimator"}
    ]
    return hashlib.sha256(encoded(nodes)).hexdigest()


def replay_context_rejection(archive, policy, expected):
    """原始请求和Usage完整重放，复验额度只授予已确认的本地计量拒绝。"""
    from audit_context_history import load_archive, sql_rows

    files, digest = load_archive(archive)
    assert digest == expected["archive_sha256"]
    database = files["ledgers/" + expected["arm"] + ".sqlite3"]
    requests = sql_rows(
        database, "SELECT id,payload FROM pre_send WHERE issued=1 ORDER BY sequence"
    )
    assert len(requests) == expected["previous_issued_requests"]
    estimator = TokenEstimator()
    for row in requests:
        response = files[expected["arm"] + "/http-native/" + row["id"] + "-response.json"]
        estimator.observe(json.loads(row["payload"]), json.loads(response))
    rejected = sql_rows(
        database,
        "SELECT sequence,payload,telemetry FROM pre_send WHERE issued=0 ORDER BY sequence LIMIT 1",
    )[0]
    old = json.loads(rejected["telemetry"])
    assert old["stop_reason"] == "CONTEXT_BUDGET_EXHAUSTED"
    assert rejected["sequence"] == expected["request_sequence"]
    assert old["request_sha256"] == expected["request_sha256"]
    corrected = {**old, **estimator.estimate(json.loads(rejected["payload"]))}
    assert admission_reason(ContextPolicy.from_dict(policy), corrected) is None
    assert corrected["estimated_input_tokens"] < old["estimated_input_tokens"]
    return {
        "passed": True,
        "issued_requests": len(requests),
        "request_sha256": old["request_sha256"],
        "original_stop_reason": old["stop_reason"],
        "old_estimated_tokens": old["estimated_input_tokens"],
        "corrected_estimated_tokens": corrected["estimated_input_tokens"],
        "new_model_requests": 0,
    }


def recovery_gate(source, p, jobs, interrupted_usage_counts, correction_proofs=None):
    """零请求续跑与计量故障复验分别登记，历次已发请求和中断额度持续累计。"""
    result = json.loads((source / "results.json").read_text())
    assert result["protocol_sha256"] == p["parent_protocol_sha256"]
    rows = {row["attempt_id"]: row for row in result["attempts"]}
    jobs_by_name = {job["name"]: job for job in jobs}
    known_requests = sum(
        (row.get("usage") or {}).get("issued_requests", 0) for row in rows.values()
    )
    reserved = p["interrupted_attempt_requests"]
    carried = p.get("carried_issued_requests", 0)
    if carried:
        previous = json.loads((source / "protocol.json").read_text())
        assert carried == previous["prior_committed_request_upper_bound"]
        assert p["parent_request_cap"] == previous["parent_request_cap"]
    assert all(
        interrupted_usage_counts.get(identity) == count for identity, count in reserved.items()
    )
    for identity, count in interrupted_usage_counts.items():
        if rows.get(identity, {}).get("usage") is not None:
            assert rows[identity]["usage"]["issued_requests"] == count
    assert (
        known_requests + sum(reserved.values()) + carried
        == p["prior_committed_request_upper_bound"]
    )
    correction_proofs = correction_proofs or {}
    for attempt in p["attempts"]:
        original = attempt["original_attempt_id"]
        assert original not in reserved
        prior = rows[original]
        assert (prior["instance_id"], prior["arm"]) == (attempt["instance_id"], attempt["arm"])
        usage = prior.get("usage")
        if usage is not None:
            if usage["issued_requests"]:
                correction = p.get("estimator_corrections", {}).get(original)
                proof = correction_proofs.get(original)
                assert correction and proof and proof["passed"], "MODEL_ATTEMPT_ALREADY_ISSUED"
                assert (
                    prior["stop_reason"]
                    == proof["original_stop_reason"]
                    == "CONTEXT_BUDGET_EXHAUSTED"
                )
                assert (
                    usage["issued_requests"]
                    == proof["issued_requests"]
                    == correction["previous_issued_requests"]
                )
                assert proof["request_sha256"] == correction["request_sha256"]
                assert proof["new_model_requests"] == 0
        elif original in interrupted_usage_counts:
            assert interrupted_usage_counts[original] == 0, "INTERRUPTED_ATTEMPT_ALREADY_ISSUED"
        else:
            job = jobs_by_name[prior["instance_id"] + " / " + prior["arm"]]
            assert not job["steps"], "INTERRUPTED_ATTEMPT_USAGE_UNKNOWN"
    assert len({a["original_attempt_id"] for a in p["attempts"]}) == len(p["attempts"])
    assert (
        known_requests + sum(reserved.values()) + carried + p["formal_request_cap"]
        <= p["parent_request_cap"]
    )
    return {
        "passed": True,
        "prior_issued_requests": known_requests,
        "carried_issued_requests": carried,
        "interrupted_issued_requests": sum(reserved.values()),
        "remaining_attempts": len(p["attempts"]),
        "remaining_request_cap": p["formal_request_cap"],
        "estimator_correction_attempts": len(correction_proofs),
    }


def pilot_gate(result, pilot_protocol, expected_protocol_sha):
    """三类执行器各有真实压缩后工具执行，全部二十次首跑用量和冷评分闭合。"""
    assert pilot_protocol["phase"] == "pilot"
    validate_protocol(pilot_protocol)
    assert result["protocol_sha256"] == expected_protocol_sha
    assert result["context_policy"] == pilot_protocol["context_policy"]
    expected = {(task, arm) for task in pilot_protocol["tasks"] for arm in ARMS}
    rows = result["attempts"]
    assert len(rows) == 20 and {(r["instance_id"], r["arm"]) for r in rows} == expected
    failures = []
    engines = set()
    compact_by_arm = Counter()
    for row in rows:
        label = row["instance_id"] + "/" + row["arm"]
        score = row["score"]
        metrics = row.get("metrics", {})
        if (
            score.get("classification") not in {"resolved", "candidate"}
            or type(score.get("accepted")) is not bool
        ):
            failures.append({"attempt": label, "reason": "COLD_ORACLE_INCOMPLETE"})
        if not (
            1 <= metrics.get("issued_requests", 0) <= 24
            and metrics.get("unknown_usage_requests") == 0
        ):
            failures.append({"attempt": label, "reason": "USAGE_INCOMPLETE"})
        if row.get("stop_reason") in {
            "LOCAL_TRANSPORT_LIMIT",
            "CONTEXT_BUDGET_EXHAUSTED",
            "COMPACTION_FAILED",
            "MODEL_CONTEXT_EXCEEDED",
            "MODEL_TIMEOUT",
            "MODEL_SERVER_ERROR",
            "MODEL_ERROR",
        }:
            failures.append({"attempt": label, "reason": row["stop_reason"]})
        for compact in metrics.get("compactions", []):
            actual = compact.get("post_compact_actual_input_tokens") or compact.get(
                "post_compact_tokens"
            )
            passed = (
                compact.get("status", "completed") == "completed"
                and compact.get("continued_with_tools") is True
                and compact.get("post_transport_bytes", 0) < compact["pre_transport_bytes"]
                and type(actual) is int
                and actual <= pilot_protocol["context_policy"]["compact_target_tokens"]
            )
            if passed:
                compact_by_arm[row["arm"]] += 1
                engines.add(row["arm"] if row["arm"] in {"mini", "codex"} else "repropatch")
            else:
                failures.append({"attempt": label, "reason": "COMPACTION_CHAIN_INCOMPLETE"})
    for engine in sorted({"repropatch", "mini", "codex"} - engines):
        failures.append({"engine": engine, "reason": "REAL_COMPACTION_NOT_OBSERVED"})
    return {
        "passed": not failures,
        "attempts": len(rows),
        "issued_requests": sum(r.get("metrics", {}).get("issued_requests", 0) for r in rows),
        "verified_compactions_by_arm": dict(compact_by_arm),
        "failures": failures,
        "ranking": False,
    }


def preflight(protocol_file, output, wait_ci=0):
    p = json.loads(protocol_file.read_text())
    validate_protocol(p)
    output.mkdir(parents=True, exist_ok=False)
    identity = execution_identity()
    assert identity["sha256"] == p["execution_sha256"], "EXECUTION_SOURCE_CHANGED"
    repo = os.environ.get("GITHUB_REPOSITORY", "lilong555/ReproPatch")
    ci = gh_json("api", f"repos/{repo}/actions/runs/{p['ci_run_id']}")
    deadline = time.monotonic() + wait_ci
    while ci["status"] != "completed" and time.monotonic() < deadline:
        print(json.dumps({"waiting_for_ci": ci["id"], "status": ci["status"]}), flush=True)
        time.sleep(min(15, max(0, deadline - time.monotonic())))
        ci = gh_json("api", f"repos/{repo}/actions/runs/{p['ci_run_id']}")
    assert ci["status"] == "completed" and ci["conclusion"] == "success", "CI_GATE_FAILED"
    assert ci["head_sha"] == p["execution_source_commit"], "CI_SOURCE_MISMATCH"
    save(output / "ci.json", {k: ci[k] for k in ("id", "head_sha", "conclusion", "html_url")})
    native = output / "native"
    download(repo, p["ci_run_id"], "context-native-evidence", native)
    for engine in ("mini", "codex"):
        evidence = json.loads((native / engine / "result.json").read_text())
        assert evidence["passed"] is True and evidence["paid_model_requests"] == 0
    for requirement in p.get("requires", []):
        run = gh_json("api", f"repos/{repo}/actions/runs/{requirement['run_id']}")
        assert run["status"] == "completed", "PRIOR_STAGE_RUNNING"
        target = output / requirement["phase"]
        download(repo, requirement["run_id"], requirement["artifact"], target)
        for name, digest in requirement["files"].items():
            assert sha(target / name) == digest, "PRIOR_STAGE_EVIDENCE_CHANGED"
        if requirement["phase"] == "calibration":
            calibration_gate(target, p)
        elif requirement["phase"] == "registry":
            from audit_context_history import load_archive, sql_rows

            pages = gh_json(
                "api",
                f"repos/{repo}/actions/runs/{requirement['run_id']}/jobs?per_page=100",
                "--paginate",
                "--slurp",
            )
            jobs = [job for page in pages for job in page["jobs"]]
            proofs = {}
            for original_attempt_id, evidence in p.get("interrupted_usage_evidence", {}).items():
                directory = target / "interrupted-usage" / evidence["arm"]
                download(repo, requirement["run_id"], evidence["artifact"], directory)
                archive = next(directory.glob("*.tar.gz"))
                files, digest = load_archive(archive)
                assert digest == evidence["archive_sha256"]
                proofs[original_attempt_id] = sql_rows(
                    files["ledgers/" + evidence["arm"] + ".sqlite3"],
                    "SELECT COUNT(*) AS count FROM requests",
                )[0]["count"]
            corrections = {}
            for original_attempt_id, evidence in p.get("estimator_corrections", {}).items():
                directory = target / "estimator-corrections" / original_attempt_id.replace("/", "_")
                download(repo, requirement["run_id"], evidence["artifact"], directory)
                archive = next(directory.glob("*.tar.gz"))
                corrections[original_attempt_id] = replay_context_rejection(
                    archive, p["context_policy"], evidence
                )
            save(output / "estimator-correction-gate.json", corrections)
            save(output / "recovery-gate.json", recovery_gate(target, p, jobs, proofs, corrections))
        else:
            result = json.loads((target / "results.json").read_text())
            prior = json.loads((target / "protocol.json").read_text())
            for key in ("execution_sha256", "context_policy"):
                assert prior[key] == p[key], "PILOT_CONFIGURATION_CHANGED"
            gate = pilot_gate(result, prior, sha(target / "protocol.json"))
            save(output / "pilot-gate.json", gate)
            assert gate["passed"], "PILOT_CONTEXT_GATE_FAILED"
    if p.get("revalidation_snapshot"):
        from complete_context_campaign import preflight as revalidation_preflight

        revalidation_preflight(p, output)
    save(
        output / "gate.json",
        {
            "passed": True,
            "protocol_sha256": sha(protocol_file),
            "execution_sha256": identity["sha256"],
            "phase": p["phase"],
            "new_model_requests": 0,
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("identity", "preflight", "pilot-gate"))
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--wait-ci", type=int, default=0)
    args = parser.parse_args()
    if args.mode == "identity":
        print(json.dumps(execution_identity(), ensure_ascii=False))
    elif args.mode == "preflight":
        preflight(args.protocol, args.output, args.wait_ci)
    else:
        result = pilot_gate(
            json.loads((args.source / "results.json").read_text()),
            json.loads(args.protocol.read_text()),
            sha(args.protocol),
        )
        save(args.output, result)
        assert result["passed"], "PILOT_CONTEXT_GATE_FAILED"


if __name__ == "__main__":
    main()
