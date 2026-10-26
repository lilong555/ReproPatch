"""统一上下文批次的源码身份、CI、校准及 Pilot 门禁。"""

import argparse
import hashlib
import json
import os
import subprocess
import time
from collections import Counter
from pathlib import Path

from benchmark_budget import LocalUsageLedger

from repropatch.context import ContextPolicy, encoded

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
    expected = {(task, arm) for task in p["tasks"] for arm in ARMS}
    ordered = [(row["instance_id"], row["arm"]) for row in p["execution_order"]]
    assert len(ordered) == len(expected) and set(ordered) == expected
    assert p["formal_request_cap"] == len(expected) * 24
    assert set(p["task_contracts"]) == set(p["tasks"])
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
    for key in ("model", "endpoint", "reasoning_effort", "execution_sha256"):
        assert p[key] == frozen[key]
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
        else:
            result = json.loads((target / "results.json").read_text())
            prior = json.loads((target / "protocol.json").read_text())
            for key in ("execution_sha256", "context_policy"):
                assert prior[key] == p[key], "PILOT_CONFIGURATION_CHANGED"
            gate = pilot_gate(result, prior, sha(target / "protocol.json"))
            save(output / "pilot-gate.json", gate)
            assert gate["passed"], "PILOT_CONTEXT_GATE_FAILED"
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
