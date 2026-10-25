"""Bind a frozen worker attempt to a qualified task and run the common cold Oracle.

No model is loaded or called. Only Docker QUALIFIED tasks accept agent candidates.
Use --check-only to validate identities and leave a valid candidate PENDING_ORACLE.
"""

import argparse
import hashlib
import json
import os
import signal
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

from run_benchmark_agent import attempt_identity, candidate_metadata, save

from repropatch.errors import ReproPatchError
from repropatch.task import IMAGE_ID, Task


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def producer_blocker(worker):
    """Preparation and infrastructure states take precedence over an empty patch."""
    state, reason = worker.get("native_status"), worker.get("native_reason") or ""
    if state == "CANCELLED" or reason == "USER_CANCELLED":
        return "CANCELLED", "cancelled"
    if (
        worker.get("baseline_eligible") is False
        or state == "NOT_REPRODUCED"
        or reason.startswith("BASELINE_")
        or reason in {"F2P_PASSED", "FAILURE_SIGNATURE_MISMATCH", "UNSUPPORTED_TEST_LAYOUT"}
    ):
        return "PREPARATION_FAILED", "preparation"
    if (
        worker.get("container_deleted")
        and worker.get("candidate_available")
        and (
            state in {"CLI_ERROR", "MODEL_REQUEST_ERROR"}
            or worker.get("recovered_from_unverified_patch")
            or worker.get("candidate_source") == "native_frozen"
        )
    ):
        return None
    if worker.get("error_type") or state in {
        "ERROR",
        "ENVIRONMENT_ERROR",
        "MODEL_REQUEST_ERROR",
        "CLI_ERROR",
    }:
        return "INFRASTRUCTURE_FAILED", "infrastructure"
    if worker.get("check_only") or state in {None, "NOT_STARTED", "INTERRUPTED"}:
        return "PENDING_ATTEMPT", "pending"
    if worker.get("container_deleted") is not True:
        return "CLEANUP_UNCONFIRMED", "infrastructure"
    return None


def oracle_execution_failure(verdict, directory):
    """Only fixed configure/build commands: a test's segfault can be a repair bug."""
    for command in verdict.get("commands", []):
        code = command.get("exit_code")
        if command.get("stage") not in {"configure", "build"} or not code:
            continue
        details = {key: command.get(key) for key in ("stage", "exit_code", "log", "log_sha256")}
        if code in {-9, 137}:
            return "RESOURCE_TERMINATED", {**details, "reason": "SIGKILL_EXIT_STATUS"}
        if code in {125, 126, 127}:
            return "ENVIRONMENT_FAILED", {**details, "reason": "DOCKER_OR_COMMAND_START_FAILED"}
        if code < 0 or 128 < code < 193:
            return "EXECUTION_TERMINATED", {**details, "reason": "PROCESS_SIGNAL_EXIT_STATUS"}
        if command.get("log"):
            logfile = (directory / command["log"]).resolve()
            if directory.resolve() not in logfile.parents or digest(logfile) != command.get(
                "log_sha256"
            ):
                raise ValueError("ORACLE_LOG_IDENTITY_MISMATCH")
            with logfile.open("rb") as stream:
                for line in stream:
                    if any(
                        marker in line
                        for marker in (
                            b"Killed signal terminated program cc1",
                            b"No space left on device",
                        )
                    ):
                        return "RESOURCE_TERMINATED", {
                            **details,
                            "reason": "COMPILER_OR_STORAGE_TERMINATION_LOG",
                        }
    return None


def score(args):
    from qualify_cpp_batch import CANCELLED
    from verify_qualification_evidence import required_task_artifacts, verify_tree

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    started = time.monotonic()
    result = {
        "schema": "repropatch.benchmark-score.v1",
        "attempt_id": args.attempt_id,
        "status": "PENDING_ORACLE",
        "classification": "pending",
        "accepted": None,
        "model_failure": None,
        "oracle_executed": False,
        "scoring_model_requests": 0,
    }
    try:
        worker_bytes = args.worker_result.read_bytes()
        qualification_bytes = args.qualification.read_bytes()
        worker = json.loads(worker_bytes)
        qualification = json.loads(qualification_bytes)
        (output / "worker-result.json").write_bytes(worker_bytes)
        (output / "qualification.json").write_bytes(qualification_bytes)
        result.update(
            worker_result_sha256=hashlib.sha256(worker_bytes).hexdigest(),
            qualification_sha256=hashlib.sha256(qualification_bytes).hexdigest(),
            agent=worker.get("agent"),
            native_status=worker.get("native_status"),
            native_reason=worker.get("native_reason"),
            internal_verification_status=worker.get("internal_verification_status"),
            worker_usage=worker.get("usage", worker.get("money")),
        )
        if (
            worker.get("schema") != "repropatch.benchmark-attempt.v1"
            or worker.get("attempt_id") != args.attempt_id
            or worker.get("attempt") != args.attempt_id
            or worker.get("agent") not in {"repropatch", "mini", "codex"}
        ):
            raise ValueError("ATTEMPT_IDENTITY_MISMATCH")
        if qualification.get("status") != "QUALIFIED" or qualification.get("backend") != "docker":
            result.update(
                status="PREPARATION_FAILED",
                classification="preparation",
                reason="TASK_NOT_DOCKER_QUALIFIED",
                qualification_status=qualification.get("status"),
            )
            return result
        if not IMAGE_ID.fullmatch(str(qualification.get("image_id", ""))):
            raise ValueError("IMMUTABLE_DOCKER_IMAGE_REQUIRED")
        manifest_path = args.qualification.parent / "manifest.json"
        if not manifest_path.is_file():
            result.update(
                status="QUALIFICATION_EVIDENCE_INCOMPLETE",
                classification="infrastructure",
                qualification_evidence_status="MISSING",
                reason="MISSING_QUALIFICATION_MANIFEST",
            )
            return result
        manifest_bytes = manifest_path.read_bytes()
        (output / "qualification-manifest.json").write_bytes(manifest_bytes)
        issues = verify_tree(
            args.qualification.parent,
            json.loads(manifest_bytes),
            required=required_task_artifacts(qualification)
            | {args.qualification.name, "task.yaml"},
        )
        result.update(
            qualification_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
            qualification_evidence_status="INCOMPLETE" if issues else "VERIFIED",
        )
        if issues:
            result.update(
                status="QUALIFICATION_EVIDENCE_INCOMPLETE",
                classification="infrastructure",
                qualification_evidence_issues=issues,
            )
            return result
        task = Task.load(args.qualification.parent / "task.yaml")
        identity = attempt_identity(task, args.attempt_id)
        if (
            any(worker.get(key) != value for key, value in identity.items())
            or identity["task_sha256"] != qualification["task_file_sha256"]
            or identity["prepared_commit"] != qualification["prepared_commit"]
            or identity["image_id"] != qualification["image_id"]
            or identity["task_id"] != qualification["instance_id"].replace("__", "-")
            or worker.get("native_image_id") not in {None, qualification["image_id"]}
            or digest(args.worker_result.parent / "task.original.yaml") != identity["task_sha256"]
        ):
            raise ValueError("TASK_IDENTITY_MISMATCH")
        result.update(identity)
        (output / "task.original.yaml").write_bytes(task.source_bytes)
        if CANCELLED.is_set():
            result.update(status="CANCELLED", classification="cancelled")
            return result
        blocker = producer_blocker(worker)
        if blocker:
            result.update(status=blocker[0], classification=blocker[1])
            return result
        candidate = args.candidate or args.worker_result.parent / "candidate.patch"
        if not candidate.is_file():
            if worker.get("candidate_available") is False and worker.get("candidate_bytes") == 0:
                if worker.get("candidate_sha256") is not None:
                    raise ValueError("CANDIDATE_IDENTITY_MISMATCH")
                result.update(
                    status="EMPTY_CANDIDATE",
                    classification="candidate",
                    accepted=False,
                    model_failure=True,
                )
            else:
                result.update(status="MISSING_CANDIDATE", classification="infrastructure")
            return result
        with candidate.open("rb") as stream:
            patch = stream.read(8 * 1024 * 1024 + 1)
        if len(patch) > 8 * 1024 * 1024:
            raise ValueError("CANDIDATE_ARTIFACT_TOO_LARGE")
        metadata = candidate_metadata(patch)
        if any(worker.get(key) != value for key, value in metadata.items()):
            raise ValueError("CANDIDATE_IDENTITY_MISMATCH")
        frozen_candidate = output / "candidate.patch"
        frozen_candidate.write_bytes(patch)
        result.update(metadata)
        if not patch.strip():
            result.update(
                status="EMPTY_CANDIDATE",
                classification="candidate",
                accepted=False,
                model_failure=True,
            )
            return result
        if args.check_only:
            return result
        import check_qualified_cpp_candidate as oracle

        result["oracle_executed"] = True
        verdict = oracle.check(
            SimpleNamespace(
                qualification=args.qualification,
                dataset=args.dataset,
                repository=args.repository,
                candidate=frozen_candidate,
                output=output / "oracle",
                timeout=args.timeout,
                build_jobs=args.build_jobs,
            )
        )
        if (
            verdict.get("qualification_sha256") != result["qualification_sha256"]
            or verdict.get("candidate_sha256") != metadata["candidate_sha256"]
            or verdict.get("cold_build") is not True
            or verdict.get("compiler_cache") != "disabled"
        ):
            raise ValueError("ORACLE_IDENTITY_MISMATCH")
        result.update(
            status=verdict["status"],
            oracle_status=verdict["status"],
            oracle_verdict_sha256=digest(output / "oracle/oracle-verdict.json"),
            oracle_manifest_sha256=digest(output / "oracle/manifest.json"),
            f2p=verdict.get("f2p"),
            p2p=verdict.get("p2p"),
        )
        execution_failure = oracle_execution_failure(verdict, output / "oracle")
        if execution_failure:
            result.update(
                status=execution_failure[0],
                classification="infrastructure",
                execution_failure=execution_failure[1],
            )
        elif verdict.get("accepted") is True and verdict["status"] == "ORACLE_PASSED":
            result.update(accepted=True, model_failure=False, classification="resolved")
        elif verdict["status"] in {
            "ORACLE_CONFIGURE_FAILED",
            "ORACLE_BUILD_FAILED",
            "ORACLE_TESTS_FAILED",
            "INVALID_CANDIDATE_PATCH",
            "CANDIDATE_SCOPE_REJECTED",
            "CANDIDATE_TOO_LARGE",
        }:
            result.update(accepted=False, model_failure=True, classification="candidate")
        else:
            result["classification"] = (
                "cancelled" if verdict["status"] == "CANCELLED" else "infrastructure"
            )
        return result
    except KeyboardInterrupt:
        result.update(status="CANCELLED", classification="cancelled", accepted=None)
        return result
    except (OSError, ValueError, KeyError, TypeError, ReproPatchError) as error:
        result.update(
            status="IDENTITY_OR_INFRASTRUCTURE_FAILED",
            classification="infrastructure",
            accepted=None,
            model_failure=None,
            reason=str(error)[:1000],
        )
        return result
    finally:
        result["wall_seconds"] = time.monotonic() - started
        save(output / "score.json", result)
        try:
            save(
                output / "manifest.json",
                {
                    p.name: {"sha256": digest(p), "bytes": p.stat().st_size}
                    for p in output.iterdir()
                    if p.is_file() and p.name != "manifest.json"
                },
            )
        except OSError as error:
            result.update(
                status="ARCHIVE_FAILED",
                classification="infrastructure",
                accepted=None,
                model_failure=None,
                reason=str(error)[:1000],
            )
            save(output / "score.json", result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-result", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--build-jobs", type=int, choices=range(1, 5), default=2)
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    from qualify_cpp_batch import CANCELLED

    os.environ.setdefault("REPROPATCH_BATCH_ID", "score-" + uuid.uuid4().hex)
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: CANCELLED.set())
    result = score(args)
    print(json.dumps(result))
    return 0 if result["accepted"] is True or result["status"] == "PENDING_ORACLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
