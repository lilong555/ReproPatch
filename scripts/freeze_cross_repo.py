"""从完整 Docker 资格证据生成独立阶段协议与预登记执行顺序。"""

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

from cpp_sources import build_index, encoded, history_index
from cross_repo_campaign import (
    development_selection,
    execution_fingerprint,
    execution_order,
    selection_review,
    validate_protocol,
)
from qualify_cpp_batch import save, sha
from verify_qualification_evidence import required_task_artifacts, verify_tree

ROOT = Path(__file__).resolve().parents[1]


def freeze(args):
    campaign = json.loads((ROOT / "benchmarks/cross-repo/campaign.json").read_text())
    calibration = json.loads(args.calibration.read_text())
    if (
        calibration.get("schema") != "repropatch.cross-network-calibration.v1"
        or calibration.get("status") != "PASSED"
        or calibration.get("usage", {}).get("issued_requests") != 12
        or calibration.get("reasoning_effort") != "max"
    ):
        raise ValueError("CROSS_NETWORK_CALIBRATION_REQUIRED")
    identities = {}
    selected = args.instances.split(",")
    gate = None
    history = history_index() if args.phase == "formal" else None
    existing = [
        "catchorg/Catch2",
        "fmtlib/fmt",
        "nlohmann/json",
        "simdjson/simdjson",
        "zeux/pugixml",
        "leethomason/tinyxml2",
    ]
    if args.phase == "formal":
        if not args.development_results or not args.development_run or not args.selection_review:
            raise ValueError("CROSS_DEVELOPMENT_SELECTION_GATE_REQUIRED")
        development = development_selection(
            json.loads(args.development_results.read_text()), campaign["development_queue"]
        )
        development.update(
            results_sha256=sha(args.development_results),
            run_id=args.development_run,
            artifact=f"cross-results-{args.development_run}",
        )
        review = json.loads(args.selection_review.read_text())
        quota = selection_review(review, selected, development, existing)
        gate = {"development": development, "review": review, **quota}
    for instance in selected:
        directory = args.qualification / instance
        q = json.loads((directory / "result.json").read_text())
        if q["status"] != "QUALIFIED" or q["backend"] != "docker" or q["image_id"] != args.image_id:
            raise ValueError("CROSS_QUALIFICATION_IMAGE_MISMATCH")
        issues = verify_tree(
            directory,
            json.loads((directory / "manifest.json").read_text()),
            required_task_artifacts(q),
        )
        if issues:
            raise ValueError("CROSS_QUALIFICATION_EVIDENCE_INCOMPLETE")
        if gate:
            record = json.loads((directory / "control/record.json").read_text())
            exposure = build_index([record], history)["candidates"][0]
            if exposure["historical_model_evidence"]:
                raise ValueError("CROSS_FORMAL_HISTORICAL_EXPOSURE")
            reviewed = gate["review"][instance]
            if reviewed.get("record_sha256") != hashlib.sha256(encoded(record)).hexdigest():
                raise ValueError("CROSS_FORMAL_REVIEW_RECORD_MISMATCH")
        identities[instance] = {
            "qualification_sha256": sha(directory / "result.json"),
            "task_sha256": sha(directory / "task.yaml"),
            "manifest_sha256": sha(directory / "manifest.json"),
            "bundle_sha256": sha(directory / "prepared.bundle"),
            "prepared_commit": q["prepared_commit"],
            "dataset_revision": q["dataset_revision"],
            "native_tests": q["native_test_count"],
        }
    batch = campaign["batch_id"] + "-" + args.phase
    attempts = execution_order(
        selected, batch=batch, replicate="repeat" if args.phase == "repeat" else "first"
    )
    prior_attempts = json.loads(args.prior_attempts.read_text()) if args.prior_attempts else []
    prior_ids = {a["attempt_id"] for a in prior_attempts}
    if prior_ids - {a["attempt_id"] for a in attempts}:
        raise ValueError("CROSS_PRIOR_ATTEMPT_REGISTRY_INVALID")
    attempts = [a for a in attempts if a["attempt_id"] not in prior_ids]
    preparation_failures = (
        json.loads(args.preparation_failures.read_text()) if args.preparation_failures else {}
    )
    if preparation_failures:
        if args.phase != "development" or set(preparation_failures) - {
            a["attempt_id"] for a in attempts
        }:
            raise ValueError("CROSS_PREPARATION_REVALIDATION_REGISTRY_INVALID")
        for attempt in attempts:
            original_id = attempt["attempt_id"]
            if original_id in preparation_failures:
                suffix = (
                    "/preparation-revalidation"
                    if preparation_failures[original_id]["issued_requests"] == 0
                    else "/infrastructure-revalidation"
                )
                attempt.update(
                    original_attempt_id=original_id,
                    attempt_id=original_id + suffix,
                    allocation_phase="infrastructure-revalidation",
                )
    pinned = json.loads((ROOT / "benchmarks/context-formal-protocol.json").read_text())
    archives = []
    for path in args.archives.rglob("cross-evidence.tar.gz"):
        with tarfile.open(path) as data:
            instances = []
            for name in data.getnames():
                if not name.endswith("/result.json"):
                    continue
                content = data.extractfile(name).read()
                instance = json.loads(content)["instance_id"]
                if (
                    instance in identities
                    and hashlib.sha256(content).hexdigest()
                    == identities[instance]["qualification_sha256"]
                ):
                    instances.append(instance)
        if not set(instances) & set(selected):
            continue
        artifact = path.parent.name
        run = int(artifact.removeprefix("cross-evidence-").split("-", 1)[0])
        if run not in args.qualification_run:
            raise ValueError("CROSS_QUALIFICATION_RUN_MISMATCH")
        archives.append(
            {"run_id": run, "artifact": artifact, "sha256": sha(path), "instances": instances}
        )
    if set(selected) - {i for a in archives for i in a["instances"]}:
        raise ValueError("CROSS_QUALIFICATION_ARCHIVE_MISSING")
    value = {
        **{
            key: campaign[key]
            for key in (
                "model",
                "reasoning_effort",
                "model_timeout_seconds",
                "request_cap_per_attempt",
                "max_tool_calls",
                "max_tools_per_response",
                "max_parallel",
                "arms",
                "context_policy",
            )
        },
        **{
            key: pinned[key]
            for key in (
                "mini_commit",
                "codex_binary",
                "codex_version",
                "codex_sha256",
                "codex_tarball",
                "codex_tarball_integrity",
                "code_host_sha256",
            )
        },
        "campaign_schema": campaign["schema"],
        "batch_id": batch,
        "phase": args.phase,
        "tasks": selected,
        "attempts": attempts,
        "prior_attempts": prior_attempts,
        "preparation_failures": preparation_failures,
        "formal_request_cap": len(attempts) * 24,
        "qualification_contracts": identities,
        "image": args.image,
        "image_id": args.image_id,
        "qualification_run_ids": args.qualification_run,
        "qualification_archives": archives,
        "network_calibration": {
            "run_id": args.calibration_run,
            "artifact": f"cross-network-calibration-{args.calibration_run}",
            "sha256": sha(args.calibration),
        },
        "ci_run_id": args.ci_run,
        "execution_source_commit": args.source_commit,
        "execution_sha256": execution_fingerprint(),
        "paid_calls_authorized": True,
        "cpa_route": "azure-ssh",
        "retries": 0,
        "oracle_timeout_seconds": 3600,
        "matrix_per_arm": True,
        "execution_order": attempts,
        "selection_seed": 20261028,
        "max_output_tokens": 8192,
        "protocol_identity": "冻结文件的 SHA256 随运行 provenance 保存",
    }
    if args.max_parallel:
        value["max_parallel"] = args.max_parallel
    if gate:
        value.update(
            selection_gate=gate,
            existing_repositories=existing,
            repeat_tasks=(args.repeat_instances or "").split(","),
        )
    if args.phase == "repeat":
        if not args.formal_protocol:
            raise ValueError("CROSS_FORMAL_PROTOCOL_REQUIRED")
        formal = json.loads(args.formal_protocol.read_text())
        validate_protocol(formal)
        if set(selected) != set(formal["repeat_tasks"]) or args.image_id != formal["image_id"]:
            raise ValueError("CROSS_REPEAT_PREREGISTRATION_MISMATCH")
        value["formal_protocol_sha256"] = sha(args.formal_protocol)
        value["formal_repeat_tasks"] = formal["repeat_tasks"]
    validate_protocol(value)
    if args.output.exists():
        raise ValueError("CROSS_FROZEN_PROTOCOL_ALREADY_EXISTS")
    save(args.output, value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("development", "formal", "repeat"), required=True)
    parser.add_argument("--instances", required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--archives", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--calibration-run", type=int, required=True)
    parser.add_argument("--qualification-run", type=int, action="append", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--ci-run", type=int, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--development-results", type=Path)
    parser.add_argument("--development-run", type=int)
    parser.add_argument("--selection-review", type=Path)
    parser.add_argument("--repeat-instances")
    parser.add_argument("--formal-protocol", type=Path)
    parser.add_argument("--preparation-failures", type=Path)
    parser.add_argument("--prior-attempts", type=Path)
    parser.add_argument("--max-parallel", type=int, choices=(2, 3))
    value = freeze(parser.parse_args())
    print(
        json.dumps(
            {
                "phase": value["phase"],
                "tasks": len(value["tasks"]),
                "attempts": len(value["attempts"]),
                "request_cap": value["formal_request_cap"],
            }
        )
    )


if __name__ == "__main__":
    main()
