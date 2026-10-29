"""在固定原生源码上应用授权候选，执行完整冷 Oracle 与分发头文件验证。"""

import json
import shutil
import subprocess
import time

from cpp_native_adapter import source_manifest
from cpp_sources import MULTISWE_REVISION, load_records
from qualify_cpp_batch import CANCELLED, archive, git, save, sha
from qualify_cross_repo import NativeExecutor, manifest

from repropatch.task import Task


def restore_repository(directory, qualification, destination):
    """从资格 bundle 恢复固定 prepared 与原始上游快照。"""
    bundle = directory / "prepared.bundle"
    if sha(bundle) != qualification["prepared_bundle_sha256"]:
        raise ValueError("PREPARED_BUNDLE_IDENTITY_MISMATCH")
    destination.mkdir(parents=True, exist_ok=False)
    git(destination, "init", "--template=", "-q", ".")
    git(destination, "fetch", str(bundle), "HEAD")
    git(destination, "checkout", "--detach", qualification["prepared_commit"])
    if (
        git(destination, "rev-parse", "HEAD^").decode().strip()
        != qualification["upstream_snapshot_commit"]
    ):
        raise ValueError("UPSTREAM_SNAPSHOT_IDENTITY_MISMATCH")
    expected = json.loads((directory / "control/upstream-source-manifest.json").read_text())
    snapshot = destination.parent / (destination.name + "-snapshot")
    try:
        archive(destination, qualification["upstream_snapshot_commit"], snapshot)
        if source_manifest(snapshot) != expected:
            raise ValueError("UPSTREAM_SOURCE_MANIFEST_MISMATCH")
    finally:
        if snapshot.exists():
            shutil.rmtree(snapshot)
    return destination


def check(args):
    from check_qualified_cpp_candidate import CandidateRejected, candidate_paths
    from verify_qualification_evidence import required_task_artifacts, verify_tree

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {
        "accepted": False,
        "status": "PREPARING",
        "adapter": "native-cpp-v1",
        "adapter_used": False,
        "cold_build": True,
        "compiler_cache": "disabled",
        "qualification_sha256": sha(args.qualification),
    }
    runner = None
    prepared, native = output / "prepared-source", output / "native-source"
    try:
        q = json.loads(args.qualification.read_text())
        directory = args.qualification.parent
        issues = verify_tree(
            directory,
            json.loads((directory / "manifest.json").read_text()),
            required_task_artifacts(q),
        )
        if issues:
            raise ValueError("QUALIFICATION_EVIDENCE_INCOMPLETE")
        if q["status"] not in {"QUALIFIED", "HOST_QUALIFIED"}:
            raise ValueError("TASK_NOT_QUALIFIED")
        record = next(
            row for row in load_records(args.dataset) if row["instance_id"] == q["instance_id"]
        )
        if (
            record["base"]["sha"] != q["upstream_commit"]
            or record.get("dataset_revision", MULTISWE_REVISION) != q["dataset_revision"]
        ):
            raise ValueError("QUALIFICATION_DATASET_MISMATCH")
        task = Task.load(directory / "task.yaml") if q["backend"] == "docker" else None
        if task and (
            sha(directory / "task.yaml") != q["task_file_sha256"]
            or task.revision != q["prepared_commit"]
            or task.environment.image != q["image_id"]
        ):
            raise ValueError("TASK_IDENTITY_MISMATCH")
        patch = args.candidate.read_bytes()
        result["candidate_sha256"] = sha(args.candidate)
        if len(patch) > 8 * 1024 * 1024:
            raise CandidateRejected("CANDIDATE_TOO_LARGE")
        (output / "candidate.patch").write_bytes(patch)
        if not patch.strip():
            result["status"] = "EMPTY_CANDIDATE"
            return result
        if q["backend"] == "native" and result["candidate_sha256"] != q["reference_patch_sha256"]:
            raise ValueError("NATIVE_CANDIDATE_REQUIRES_DOCKER")
        restore_repository(directory, q, prepared)
        editable = (
            task.editable_paths
            if task
            else json.loads((directory / "control/editable-files.json").read_text())
        )
        changed = candidate_paths(prepared, output / "candidate.patch", editable=editable)
        archive(prepared, q["upstream_snapshot_commit"], native)
        git(native, "init", "--template=", "-q", ".")
        if (
            sha(directory / "control/test.patch") != q["test_patch_sha256"]
            or (directory / "control/test.patch").read_text() != record["test_patch"]
        ):
            raise ValueError("TEST_PATCH_IDENTITY_MISMATCH")
        git(native, "apply", str(directory / "control/test.patch"))
        git(native, "add", "-f", ".")
        try:
            git(native, "apply", "--check", str(output / "candidate.patch"))
            git(native, "apply", str(output / "candidate.patch"))
        except subprocess.CalledProcessError as error:
            raise CandidateRejected("INVALID_CANDIDATE_PATCH") from error
        actual = git(native, "diff", "--name-only", "-z").split(b"\0")[:-1]
        if sorted(path.decode() for path in actual) != changed or git(native, "diff", "--summary"):
            raise CandidateRejected("CANDIDATE_SCOPE_REJECTED")
        shutil.copytree(prepared / "repropatch-native", native / "repropatch-native")
        contract_file = native / "repropatch-native/contract.json"
        if sha(contract_file) != q["native_contract_sha256"]:
            raise ValueError("NATIVE_CONTRACT_IDENTITY_MISMATCH")
        contract = json.loads(contract_file.read_text())
        runner = NativeExecutor(
            q["backend"], q["image_id"], output, started + args.timeout, q["configuration"]
        )
        oracle = runner.native_oracle(native, "native-oracle", contract)
        result.update(
            instance_id=q["instance_id"],
            image_id=q["image_id"],
            prepared_commit=q["prepared_commit"],
            changed_files=changed,
            oracle=oracle,
        )
        result["status"] = "ORACLE_" + oracle["status"]
        result["f2p"] = {name: oracle["tests"].get(name, "not_run") for name in q["f2p"]}
        result["p2p"] = {name: oracle["tests"].get(name, "not_run") for name in q["p2p"]}
        if oracle["status"] != "PASSED":
            return result
        if q["configuration"]["repository"] == "nlohmann/json":
            configuration = {
                **q["configuration"],
                "configure": [
                    arg.replace("-DJSON_MultipleHeaders=ON", "-DJSON_MultipleHeaders=OFF")
                    for arg in q["configuration"]["configure"]
                ],
            }
            single = runner.native_oracle(
                native, "single-header", contract, configuration=configuration, selected=q["f2p"]
            )
            result["single_header"] = single
            if single["status"] != "PASSED":
                result["status"] = "ORACLE_" + single["status"]
                return result
        result.update(accepted=True, status="ORACLE_PASSED")
        return result
    except CandidateRejected as error:
        result["status"] = str(error)
        return result
    except (InterruptedError, TimeoutError) as error:
        result.update(
            status="CANCELLED" if CANCELLED.is_set() else "TIMED_OUT", diagnostic=str(error)
        )
        return result
    except (
        ValueError,
        OSError,
        KeyError,
        RuntimeError,
        StopIteration,
        subprocess.SubprocessError,
    ) as error:
        result.update(status="INFRASTRUCTURE_FAILED", diagnostic=str(error)[-2000:])
        return result
    finally:
        result["commands"] = runner.commands if runner else []
        errors = []
        for path in [prepared, native, *([runner.build_root] if runner else [])]:
            if path.exists():
                try:
                    shutil.rmtree(path)
                except OSError as error:
                    errors.append(type(error).__name__)
        result["cleanup"] = {"status": "FAILED" if errors else "SUCCEEDED", "errors": errors}
        if errors:
            result.update(accepted=False, status="CLEANUP_FAILED")
        result["wall_seconds"] = time.monotonic() - started
        save(output / "oracle-verdict.json", result)
        manifest(output)
