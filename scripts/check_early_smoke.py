"""Read-only GitHub smoke evidence gate for the frozen early-context experiment."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import context_ablation as shared
from context_early_campaign import CAMPAIGN

SHA256 = re.compile(r"[a-f0-9]{64}\Z")
SHA1 = re.compile(r"[a-f0-9]{40}\Z")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_MEMBER_BYTES = 16 * 1024 * 1024
COLD_FAILURES = {
    "ORACLE_CONFIGURE_FAILED",
    "ORACLE_BUILD_FAILED",
    "ORACLE_TESTS_FAILED",
    "INVALID_CANDIDATE_PATCH",
    "CANDIDATE_SCOPE_REJECTED",
    "CANDIDATE_TOO_LARGE",
}


def require(condition, reason):
    if not condition:
        raise ValueError("EARLY_SMOKE_" + reason)


def mapping(value, reason):
    require(isinstance(value, dict), reason)
    return value


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def hash_value(value):
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def validate_run(run, *, run_id, repository, source_commit):
    mapping(run, "RUN_FORMAT")
    require(integer(run.get("id"), 1) and str(run["id"]) == run_id, "RUN_ID")
    origin = mapping(run.get("repository"), "RUN_REPOSITORY")
    require(str(origin.get("full_name", "")).casefold() == repository.casefold(), "RUN_REPOSITORY")
    require(run.get("head_sha") == source_commit, "RUN_SOURCE")
    require(run.get("status") == "completed", "RUN_INCOMPLETE")
    require(type(run.get("run_attempt")) is int and run["run_attempt"] == 1, "RUN_ATTEMPT")


def validate_empty_candidate(row, score):
    """Accept the scorer's verified empty-patch outcome with its original identities."""
    require(
        score.get("accepted") is False
        and score.get("model_failure") is True
        and score.get("oracle_executed") is False
        and hash_value(score.get("worker_result_sha256"))
        and hash_value(score.get("qualification_manifest_sha256"))
        and all(
            score.get(key) is None
            for key in ("oracle_status", "oracle_verdict_sha256", "oracle_manifest_sha256")
        ),
        "EMPTY_CANDIDATE_SCORE",
    )
    require("candidate_sha256" in row, "EMPTY_CANDIDATE_IDENTITY")
    fields = {"candidate_available", "candidate_bytes", "candidate_sha256"}
    present = fields & score.keys()
    if not present:
        # The scorer returns before adding patch metadata for an absent candidate.
        require(row["candidate_sha256"] is None, "EMPTY_CANDIDATE_IDENTITY")
    else:
        require(
            present == fields
            and score["candidate_available"] is False
            and type(score["candidate_bytes"]) is int
            and score["candidate_bytes"] == 0
            and score["candidate_sha256"] is None
            and row["candidate_sha256"] in {None, hashlib.sha256(b"").hexdigest()},
            "EMPTY_CANDIDATE_IDENTITY",
        )


def validate_smoke(
    run, manifest, result, *, run_id, repository, source_commit, protocol, protocol_sha256, sources
):
    """Validate complete evidence without selecting for success or lower token use."""
    validate_run(run, run_id=run_id, repository=repository, source_commit=source_commit)
    m, result = mapping(manifest, "MANIFEST_FORMAT"), mapping(result, "RESULT_FORMAT")
    require(protocol.get("campaign") == CAMPAIGN, "CAMPAIGN")
    require(m.get("schema") == "repropatch.context-ablation.manifest.v1", "MANIFEST_SCHEMA")
    require(
        m.get("manifest_sha256")
        == shared.digest({k: v for k, v in m.items() if k != "manifest_sha256"}),
        "MANIFEST_HASH",
    )
    require(m.get("scope") == "smoke", "SCOPE")
    require(m.get("github_run_id") == run_id and m.get("github_run_attempt") == 1, "MANIFEST_RUN")
    require(m.get("source_commit") == source_commit, "MANIFEST_SOURCE")
    require(m.get("source_sha256") == sources and bool(sources), "SOURCE_HASHES")
    require(m.get("protocol_sha256") == protocol_sha256, "PROTOCOL_HASH")
    require(shared.digest(m.get("protocol")) == shared.digest(protocol), "PROTOCOL")
    expected = shared.trials(protocol, "smoke")
    require(
        len(expected) == 3 and {r["arm"] for r in expected} == {"baseline", "early", "early_state"},
        "EXPECTED_ARMS",
    )
    require(m.get("attempts") == expected and m.get("matrix") == {"include": expected}, "MATRIX")
    require(m.get("trial_count") == 3 and m.get("request_cap") == 72, "ALLOCATION")
    require(result.get("schema") == "repropatch.context-ablation.aggregate.v1", "RESULT_SCHEMA")
    require(result.get("scope") == "smoke" and result.get("registered_trials") == 3, "RESULT_SCOPE")
    require(result.get("manifest_sha256") == m["manifest_sha256"], "RESULT_MANIFEST")
    require(result.get("source_sha256") == sources, "RESULT_SOURCE")
    require(
        result.get("automatic_reruns") == 0 and not result.get("rejected_artifacts"),
        "RESULT_REJECTED",
    )
    rows = result.get("attempts")
    require(
        isinstance(rows, list) and len(rows) == 3 and all(isinstance(r, dict) for r in rows),
        "INCOMPLETE_ATTEMPTS",
    )
    by_id = {r.get("attempt_id"): r for r in rows}
    require(set(by_id) == {r["attempt_id"] for r in expected}, "ATTEMPT_IDENTITIES")
    arms = mapping(result.get("arms"), "ARM_SUMMARIES")
    require(
        set(arms) == {r["arm"] for r in expected}
        and all(isinstance(v, dict) and v.get("N") == 1 for v in arms.values()),
        "ARM_DENOMINATORS",
    )
    checked, first_requests = [], []
    for frozen in expected:
        row = by_id[frozen["attempt_id"]]
        require(all(row.get(k) == v for k, v in frozen.items()), "TRIAL_IDENTITY")
        require(
            row.get("manifest_sha256") == m["manifest_sha256"]
            and row.get("protocol_sha256") == protocol_sha256
            and row.get("source_sha256") == sources,
            "TRIAL_SOURCE",
        )
        accepted = row.get("accepted")
        classification = "resolved" if accepted is True else "candidate"
        require(
            type(accepted) is bool
            and row.get("failure") is None
            and row.get("classification") == classification,
            "TRIAL_OUTCOME",
        )
        usage = mapping(row.get("usage"), "USAGE_MISSING")
        require(
            integer(usage.get("requests"), 1)
            and usage["requests"] <= 24
            and usage.get("request_cap") == 24
            and integer(usage.get("unknown_usage_requests"))
            and usage["unknown_usage_requests"] == 0
            and all(integer(usage.get(k)) for k in ("input_tokens", "output_tokens")),
            "USAGE_UNKNOWN_OR_BUDGET",
        )
        require(
            all(
                integer(usage.get(k))
                for k in ("repair_requests", "compact_requests", "retry_requests")
            )
            and usage["repair_requests"] >= 1
            and usage["retry_requests"] == 0
            and usage["repair_requests"] + usage["compact_requests"] == usage["requests"],
            "USAGE_PURPOSES",
        )
        score = mapping(row.get("score"), "COLD_SCORE_MISSING")
        require(
            score.get("schema") == "repropatch.benchmark-score.v1"
            and score.get("attempt_id") == frozen["attempt_id"]
            and score.get("qualification_evidence_status") == "VERIFIED"
            and type(score.get("scoring_model_requests")) is int
            and score["scoring_model_requests"] == 0
            and score.get("accepted") is accepted
            and score.get("classification") == classification,
            "COLD_SCORE_INCOMPLETE",
        )
        contract = protocol["task_contracts"][frozen["instance_id"]]
        require(
            score.get("task_sha256") == contract["execution_task_sha256"]
            and score.get("prepared_commit") == contract["prepared_commit"]
            and score.get("image_id") == protocol["image_id"],
            "COLD_TASK_IDENTITY",
        )
        empty = score.get("status") == "EMPTY_CANDIDATE"
        if empty:
            validate_empty_candidate(row, score)
        else:
            statuses = {"ORACLE_PASSED"} if accepted else COLD_FAILURES
            require(
                score.get("oracle_executed") is True
                and score.get("status") in statuses
                and score.get("oracle_status") == score["status"]
                and hash_value(score.get("oracle_verdict_sha256"))
                and hash_value(score.get("oracle_manifest_sha256")),
                "COLD_VERDICT",
            )
        mechanism = mapping(
            row.get("mechanisms", {}).get("early_observation_reduction"), "AUXILIARY_METRICS"
        )
        auxiliary = mapping(mechanism.get("metrics"), "AUXILIARY_METRICS")
        enabled = frozen["arm"] != "baseline"
        require(mechanism.get("enabled") is enabled, "AUXILIARY_POLICY")
        count = auxiliary.get("auxiliary_requests")
        require(
            integer(count)
            and (1 <= count <= 4 if enabled else count == 0)
            and count <= usage["compact_requests"]
            and integer(auxiliary.get("auxiliary_unknown_usage"))
            and auxiliary["auxiliary_unknown_usage"] == 0
            and all(
                integer(auxiliary.get(k))
                for k in ("auxiliary_input_tokens", "auxiliary_output_tokens")
            )
            and auxiliary["auxiliary_input_tokens"] <= usage["input_tokens"]
            and auxiliary["auxiliary_output_tokens"] <= usage["output_tokens"],
            "AUXILIARY_INCOMPLETE",
        )
        first = mapping(row.get("first_request"), "FIRST_REQUEST_MISSING")
        require(
            all(
                hash_value(first.get(k))
                for k in ("input_sha256", "instructions_sha256", "tools_sha256")
            )
            and first.get("model") == protocol["model"]
            and first.get("reasoning", {}).get("effort") == protocol["reasoning_effort"],
            "FIRST_REQUEST_IDENTITY",
        )
        first_requests.append(first)
        checked.append(
            {
                "attempt_id": frozen["attempt_id"],
                "arm": frozen["arm"],
                "accepted": accepted,
                "cold_status": score["status"],
                "oracle_executed": score["oracle_executed"],
                "scorer_rejected_empty": empty,
                "requests": usage["requests"],
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "auxiliary_requests": count,
                "selection_triggers": mechanism.get("trigger_count"),
            }
        )
    instructions = sorted({r["instructions_sha256"] for r in first_requests})
    tools = sorted({r["tools_sha256"] for r in first_requests})
    inputs = sorted({r["input_sha256"] for r in first_requests})
    require(len(instructions) == len(tools) == 1, "FIRST_INSTRUCTIONS_OR_TOOLS_DIFFER")
    return {
        "passed": True,
        "attempts": checked,
        "scorer_rejected_empty": sum(row["scorer_rejected_empty"] for row in checked),
        "manifest_sha256": m["manifest_sha256"],
        "input_identity": {
            "instructions_sha256": instructions,
            "tools_sha256": tools,
            "input_sha256": inputs,
            "byte_identical_input": len(inputs) == 1,
            "input_difference_is_diagnostic": True,
        },
        "success_or_token_improvement_required": False,
    }


def select_artifact(artifacts, name, *, run_id, source_commit):
    selected = [a for a in artifacts if isinstance(a, dict) and a.get("name") == name]
    require(len(selected) == 1, "ARTIFACT_MISSING_OR_DUPLICATE:" + name)
    artifact = selected[0]
    workflow = mapping(artifact.get("workflow_run"), "ARTIFACT_RUN")
    require(
        integer(artifact.get("id"), 1)
        and artifact.get("expired") is False
        and str(workflow.get("id")) == run_id
        and workflow.get("head_sha") == source_commit,
        "ARTIFACT_IDENTITY:" + name,
    )
    digest = artifact.get("digest")
    require(
        isinstance(digest, str)
        and digest.startswith("sha256:")
        and hash_value(digest.removeprefix("sha256:")),
        "ARTIFACT_DIGEST_MISSING:" + name,
    )
    return artifact


def read_verified_json(data, artifact, member):
    """Check the GitHub ZIP digest and read one regular JSON member without extraction."""
    require(len(data) <= MAX_ARCHIVE_BYTES, "ARTIFACT_TOO_LARGE")
    observed = "sha256:" + hashlib.sha256(data).hexdigest()
    require(observed == artifact.get("digest"), "ARTIFACT_DIGEST_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = [i for i in archive.infolist() if i.filename == member]
        require(len(entries) == 1, "ARTIFACT_MEMBER_MISSING_OR_DUPLICATE")
        entry = entries[0]
        mode = stat.S_IFMT(entry.external_attr >> 16)
        require(
            not entry.is_dir()
            and mode in {0, stat.S_IFREG}
            and entry.file_size <= MAX_MEMBER_BYTES,
            "ARTIFACT_MEMBER_TYPE_OR_SIZE",
        )
        value = json.loads(archive.read(entry))
        mapping(value, "ARTIFACT_MEMBER_JSON")
    return value


def gh_json(endpoint, *, paginate=False):
    command = ["gh", "api", "--hostname", "github.com", "--method", "GET"]
    if paginate:
        command.extend(["--paginate", "--slurp"])
    response = subprocess.run([*command, endpoint], check=True, capture_output=True, timeout=120)
    return json.loads(response.stdout)


def download_artifact(repository, artifact_id, path):
    with path.open("xb") as stream:
        subprocess.run(
            [
                "gh",
                "api",
                "--hostname",
                "github.com",
                "--method",
                "GET",
                f"repos/{repository}/actions/artifacts/{artifact_id}/zip",
            ],
            stdout=stream,
            stderr=subprocess.PIPE,
            check=True,
            timeout=120,
        )
    with path.open("rb") as stream:
        return stream.read(MAX_ARCHIVE_BYTES + 1)


def check(args, receipt):
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    source_commit = os.environ.get("GITHUB_SHA", "")
    require(REPOSITORY.fullmatch(repository) is not None, "REPOSITORY_ENV")
    require(SHA1.fullmatch(source_commit) is not None, "SOURCE_ENV")
    require(re.fullmatch(r"[1-9][0-9]*", args.run_id) is not None, "RUN_ID_ARGUMENT")
    protocol = shared.read_protocol(args.protocol)
    protocol_sha256 = shared.sha(args.protocol)
    run = gh_json(f"repos/{repository}/actions/runs/{args.run_id}")
    validate_run(run, run_id=args.run_id, repository=repository, source_commit=source_commit)
    receipt.update(
        repository=repository,
        source_commit=source_commit,
        protocol_sha256=protocol_sha256,
        run_id=args.run_id,
        run_url=f"https://github.com/{repository}/actions/runs/{args.run_id}",
        run_conclusion=run.get("conclusion"),
    )
    pages = gh_json(
        f"repos/{repository}/actions/runs/{args.run_id}/artifacts?per_page=100", paginate=True
    )
    require(
        isinstance(pages, list)
        and all(isinstance(p, dict) and isinstance(p.get("artifacts"), list) for p in pages),
        "ARTIFACT_LIST",
    )
    artifacts = [artifact for page in pages for artifact in page["artifacts"]]
    inputs = args.output.with_name(args.output.stem + "-artifacts")
    inputs.mkdir(mode=0o700, exist_ok=False)
    documents, evidence = {}, []
    receipt["verified_artifacts"] = evidence
    for kind, member in (("plan", "context-plan.json"), ("results", "results.json")):
        name = f"context-{kind}-{args.run_id}"
        artifact = select_artifact(artifacts, name, run_id=args.run_id, source_commit=source_commit)
        path = inputs / f"{kind}.zip"
        data = download_artifact(repository, artifact["id"], path)
        documents[kind] = read_verified_json(data, artifact, member)
        evidence.append(
            {
                "name": name,
                "id": artifact["id"],
                "digest": artifact["digest"],
                "bytes": len(data),
                "member": member,
                "digest_verified": True,
                "local_path": str(path),
                "url": f"https://github.com/{repository}/actions/runs/{args.run_id}/artifacts/{artifact['id']}",
            }
        )
    validated = validate_smoke(
        run,
        documents["plan"],
        documents["results"],
        run_id=args.run_id,
        repository=repository,
        source_commit=source_commit,
        protocol=protocol,
        protocol_sha256=protocol_sha256,
        sources=shared.source_hashes(),
    )
    raw_entries = []
    for row in documents["plan"]["attempts"]:
        name = f"context-raw-{args.run_id}-{row['job_key']}"
        artifact = select_artifact(artifacts, name, run_id=args.run_id, source_commit=source_commit)
        raw_entries.append(
            {
                "attempt_id": row["attempt_id"],
                "name": name,
                "id": artifact["id"],
                "digest": artifact["digest"],
                "digest_verified": False,
                "url": f"https://github.com/{repository}/actions/runs/{args.run_id}/artifacts/{artifact['id']}",
            }
        )
    receipt.update(validated, raw_artifacts=raw_entries)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "repropatch.context-early.smoke-gate.v1",
        "passed": False,
        "campaign": CAMPAIGN,
        "new_model_requests": 0,
        "github_access": "read_only",
        "started_at": datetime.now(UTC).isoformat(),
    }
    with args.output.open("x") as stream:
        try:
            check(args, receipt)
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            OSError,
            subprocess.SubprocessError,
            zipfile.BadZipFile,
            RuntimeError,
        ) as error:
            receipt["error"] = (
                str(error)[:1000] if isinstance(error, ValueError) else type(error).__name__
            )
        receipt["finished_at"] = datetime.now(UTC).isoformat()
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {"passed": receipt["passed"], "output": str(args.output), "error": receipt.get("error")}
        )
    )
    return 0 if receipt["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
