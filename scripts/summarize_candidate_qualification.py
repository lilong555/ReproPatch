"""核验原始资格证据，汇总候选实验准入状态。"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from check_native_cpp_candidate import restore_repository
from cpp_native_adapter import source_manifest
from qualify_cpp_batch import sha
from verify_qualification_evidence import required_task_artifacts


def qualification_gate_errors(result, contract, native, single_header=None):
    """逐项核对基线与冷验收用例结果。"""
    errors = []
    f2p, p2p = result.get("f2p", []), result.get("p2p", [])
    required = result.get("required_tests", [])
    native_required = contract.get("required_native_tests", [])
    phases = result.get("phases", {})
    baseline = phases.get("baseline", {})
    oracle = phases.get("native_oracle", {})
    declared = (
        sorted(name for name in contract["groups"] if name != "native-p2p")
        if contract.get("mode") != "ctest"
        else contract.get("declared_native_f2p", [])
    )
    if (
        result.get("adapter") != "native-cpp-v1"
        or result.get("qualification_policy") != "baseline-native-v1"
        or not f2p
        or not p2p
        or len(set(f2p + p2p)) != len(f2p + p2p)
        or sorted(f2p + p2p) != sorted(required)
        or sorted(required) != sorted(contract["groups"])
        or (declared and sorted(f2p) != sorted(declared))
        or baseline.get("status") != "TESTS_FAILED"
        or baseline.get("tests") != {**dict.fromkeys(f2p, "failed"), **dict.fromkeys(p2p, "passed")}
        or oracle.get("status") != "PASSED"
        or oracle.get("tests") != dict.fromkeys(required, "passed")
        or result.get("native_oracle", {}).get("passed") is not True
        or result.get("native_oracle", {}).get("cold_build") is not True
        or result.get("cleanup", {}).get("status") != "SUCCEEDED"
    ):
        errors.append("QUALIFICATION_GATE_INCOMPLETE")
    if (
        not native_required
        or len(set(native_required)) != len(native_required)
        or result.get("required_native_tests") != native_required
        or result.get("native_test_count") != len(native_required)
        or result.get("native_oracle", {}).get("native_test_count") != len(native_required)
        or native.get("tests") != dict.fromkeys(native_required, "passed")
        or native.get("missing") != []
        or native.get("additional_failures") != []
        or oracle.get("native_tests") != native.get("tests")
    ):
        errors.append("NATIVE_ORACLE_CASES_INCOMPLETE")
    if result.get("configuration", {}).get("repository") == "nlohmann/json":
        single = phases.get("single_header", {})
        expected = dict.fromkeys(f2p, "passed")
        if (
            single.get("status") != "PASSED"
            or single.get("tests") != expected
            or single_header is None
            or single_header.get("tests") != expected
        ):
            errors.append("SINGLE_HEADER_GATE_INCOMPLETE")
    return errors


def image_pull_row(pull, *, archive, archive_sha256=None):
    """保存资格开始前的基础设施状态。"""
    if (
        pull.get("schema") != "repropatch.image-pull.v1"
        or pull.get("model_requests") != 0
        or pull.get("qualification_executed") is not False
        or pull.get("status") not in {"IMAGE_PULL_FAILED", "IMAGE_PULLED"}
    ):
        raise ValueError("INVALID_IMAGE_PULL_EVIDENCE")
    attempts = pull.get("attempts", [])
    return {
        "instance_id": pull.get("instance_id"),
        "qualification_status": "IMAGE_PULL_FAILED"
        if pull["status"] == "IMAGE_PULL_FAILED"
        else "QUALIFICATION_NOT_STARTED",
        "eligible": False,
        "evidence_errors": ["QUALIFICATION_NOT_EXECUTED"],
        "archive": archive,
        "archive_sha256": archive_sha256,
        "image": pull.get("image"),
        "phases": {"image_pull": pull["status"]},
        "diagnostic": attempts[-1].get("diagnostic") if attempts else None,
        "image_pull": pull,
    }


def inspect_archive(path, image_id):
    sidecar = path.with_suffix(path.suffix + ".sha256")
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    checksum = sidecar.read_text().split() if sidecar.is_file() else []
    if not checksum or checksum[0] != actual:
        raise ValueError("ARCHIVE_CHECKSUM_MISMATCH")
    with tempfile.TemporaryDirectory(prefix="qualification-evidence-") as temporary:
        return inspect_verified_archive(path, image_id, actual, Path(temporary))


def inspect_verified_archive(path, image_id, actual, temporary):
    with tarfile.open(path) as archive:
        members = {member.name: member for member in archive.getmembers()}
        if len(members) != len(archive.getmembers()):
            raise ValueError("DUPLICATE_ARCHIVE_MEMBER")
        digests = {}
        for name, member in members.items():
            if not member.isfile():
                continue
            with archive.extractfile(member) as stream:
                digests[name] = {
                    "size": member.size,
                    "sha256": hashlib.file_digest(stream, "sha256").hexdigest(),
                }

        def read_json(name):
            return json.load(archive.extractfile(name))

        inventory = read_json("archive-manifest.json")
        if {item["path"] for item in inventory["files"]} != set(digests) - {
            "archive-manifest.json"
        }:
            raise ValueError("ARCHIVE_INVENTORY_INCOMPLETE")
        for item in inventory["files"]:
            if digests.get(item["path"]) != {
                "size": item["size_bytes"],
                "sha256": item["sha256"],
            }:
                raise ValueError("ARCHIVE_MEMBER_CHECKSUM_MISMATCH")
        result_names = [
            name
            for name in sorted(members)
            if name.count("/") == 1 and name.endswith("/result.json")
        ]
        pull = read_json("image-pull.json") if "image-pull.json" in members else None
        if not result_names and pull is not None:
            return [image_pull_row(pull, archive=path.parent.name, archive_sha256=actual)]
        sources = read_json("source-manifest.json")
        if not sources or any(
            digests.get("execution-source/" + name) != identity
            for name, identity in sources.items()
        ):
            raise ValueError("EXECUTION_SOURCE_CHECKSUM_MISMATCH")
        rows = []
        for name in result_names:
            result = read_json(name)
            instance = result["instance_id"]
            prefix = instance + "/"
            if name != prefix + "result.json":
                raise ValueError("RESULT_INSTANCE_PATH_MISMATCH")
            errors = []
            if pull is not None and pull.get("status") == "IMAGE_PULL_FAILED":
                errors.append("QUALIFICATION_AFTER_FAILED_IMAGE_PULL")
            manifest = read_json(prefix + "manifest.json")
            if not manifest:
                errors.append("EMPTY_TASK_MANIFEST")
            if result.get("status") == "QUALIFIED":
                # 从已核验的 bundle 离线恢复源码，校验打包时省略的可重建文件。
                directory = temporary / instance
                for member_name, member in members.items():
                    if member_name.startswith(prefix) and member.isfile():
                        archive.extract(member, temporary, filter="data")
                repository = directory / "repository"
                restore_repository(directory, result, repository)
                expected = read_json(prefix + "control/prepared-source-manifest.json")
                if source_manifest(repository) != expected:
                    errors.append("PREPARED_SOURCE_CHECKSUM_MISMATCH")
                contract = json.loads((repository / "repropatch-native/contract.json").read_text())
                errors.extend(
                    qualification_gate_errors(
                        result,
                        contract,
                        read_json(prefix + "native-oracle-native-results.json"),
                        read_json(prefix + "single-header-native-results.json")
                        if prefix + "single-header-native-results.json" in members
                        else None,
                    )
                )
                for relative in manifest:
                    if relative.startswith("repository/"):
                        restored = directory / relative
                        if restored.is_file() and not restored.is_symlink():
                            digests[prefix + relative] = {
                                "size": restored.stat().st_size,
                                "sha256": sha(restored),
                            }
                shutil.rmtree(directory)
            for relative, identity in manifest.items():
                if relative.startswith("repository/") and result.get("status") != "QUALIFIED":
                    continue
                if digests.get(prefix + relative) != identity:
                    errors.append("TASK_CHECKSUM_MISMATCH:" + relative)
            for relative in required_task_artifacts(result):
                if relative not in manifest:
                    errors.append("MISSING_REQUIRED_EVIDENCE:" + relative)
            if result.get("model_requests") != 0:
                errors.append("MODEL_REQUESTS_NOT_ZERO")
            if result.get("backend") != "docker" or result.get("image_id") != image_id:
                errors.append("DOCKER_IMAGE_MISMATCH")
            if result.get("status") == "QUALIFIED":
                for relative, key in (
                    ("task.yaml", "task_file_sha256"),
                    ("prepared.bundle", "prepared_bundle_sha256"),
                    ("repository/repropatch-native/contract.json", "native_contract_sha256"),
                ):
                    if digests.get(prefix + relative, {}).get("sha256") != result.get(key):
                        errors.append("QUALIFICATION_IDENTITY_MISMATCH:" + relative)
            rows.append(
                {
                    "instance_id": instance,
                    "qualification_status": result["status"],
                    "eligible": result["status"] == "QUALIFIED" and not errors,
                    "evidence_errors": errors,
                    "archive": path.parent.name,
                    "archive_sha256": actual,
                    "result_sha256": digests[name]["sha256"],
                    "native_test_count": result.get("native_test_count"),
                    "phases": {
                        phase: data.get("status")
                        for phase, data in result.get("phases", {}).items()
                    },
                    "diagnostic": result.get("diagnostic"),
                }
            )
    return rows


def summarize(plan, artifacts, *, download_status="success", environment_download_status="success"):
    if plan.get("model_requests") != 0 or plan.get("stage") != "qualify":
        raise ValueError("ZERO_MODEL_QUALIFICATION_PLAN_REQUIRED")
    selected = plan["instances"]
    if not selected or len(set(selected)) != len(selected):
        raise ValueError("UNIQUE_SELECTED_INSTANCES_REQUIRED")
    observed = {}
    archive_errors = []
    infrastructure = []
    for kind, status in (
        ("qualification", download_status),
        ("toolchain", environment_download_status),
    ):
        if status != "success":
            archive_errors.append({"archive": kind, "error": "ARTIFACT_DOWNLOAD_" + status.upper()})
    for archive in sorted(artifacts.glob("*/cross-evidence.tar.gz")):
        try:
            rows = inspect_archive(archive, plan["image_id"])
        except (
            ValueError,
            KeyError,
            TypeError,
            OSError,
            RuntimeError,
            subprocess.SubprocessError,
            tarfile.TarError,
        ) as error:
            archive_errors.append({"archive": archive.parent.name, "error": str(error)})
            continue
        for row in rows:
            instance = row["instance_id"]
            if row.get("image_pull"):
                infrastructure.append(row)
            if instance is None:
                continue
            if instance in observed:
                observed[instance]["eligible"] = False
                observed[instance]["evidence_errors"].append("DUPLICATE_QUALIFICATION_RESULT")
            else:
                observed[instance] = row
    for path in sorted(artifacts.glob("cross-inputs-*/cross-environment/image-pull.json")):
        try:
            row = image_pull_row(json.loads(path.read_text()), archive=path.parent.parent.name)
            row["diagnostic_sha256"] = sha(path)
            infrastructure.append(row)
            if row["qualification_status"] == "IMAGE_PULL_FAILED":
                archive_errors.append(
                    {"archive": path.parent.parent.name, "error": "TOOLCHAIN_IMAGE_PULL_FAILED"}
                )
                for instance in selected:
                    if instance not in observed:
                        observed[instance] = {**row, "instance_id": instance}
        except (ValueError, KeyError, TypeError, OSError) as error:
            archive_errors.append({"archive": path.parent.parent.name, "error": str(error)})
    rows = [
        observed.get(
            instance,
            {
                "instance_id": instance,
                "qualification_status": "MISSING_RESULT",
                "eligible": False,
                "evidence_errors": ["MISSING_QUALIFICATION_ARCHIVE"],
            },
        )
        for instance in selected
    ]
    for row in rows:
        entry = plan.get("reusable_qualifications", {}).get(row["instance_id"])
        if entry and any(row.get(key) != entry[key] for key in ("archive_sha256", "result_sha256")):
            row["eligible"] = False
            row["evidence_errors"].append("REUSED_QUALIFICATION_IDENTITY_MISMATCH")
        if entry and row.get("archive") != entry["artifact"]:
            row["eligible"] = False
            row["evidence_errors"].append("REUSED_QUALIFICATION_SOURCE_MISMATCH")
    qualified = [row["instance_id"] for row in rows if row["eligible"]]
    status = "QUALIFIED" if len(qualified) == len(selected) and not archive_errors else "BLOCKED"
    return {
        "schema": "repropatch.candidate-eligibility.v1",
        "status": status,
        "model_requests": 0,
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "execution_commit": os.environ.get("GITHUB_SHA"),
        "image": plan["image"],
        "image_id": plan["image_id"],
        "requested": len(selected),
        "qualified": len(qualified),
        "qualified_instances": qualified,
        "eligible_instances": qualified if status == "QUALIFIED" else [],
        "archive_errors": archive_errors,
        "infrastructure": infrastructure,
        "tasks": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--download-status", default="success")
    parser.add_argument("--environment-download-status", default="success")
    args = parser.parse_args()
    report = summarize(
        json.loads(args.plan.read_text()),
        args.artifacts,
        download_status=args.download_status,
        environment_download_status=args.environment_download_status,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "eligibility.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "eligible-instances.txt").write_text(
        ",".join(report["eligible_instances"]) + "\n"
    )
    lines = [
        "# 候选资格",
        "",
        f"状态：**{report['status']}**。"
        f"通过资格：**{report['qualified']}/{report['requested']}**。",
        "",
        "模型请求：**0**。准入依据为完整 Docker 基线与独立冷 Oracle 证据。",
        "",
        "| 题目 | 资格状态 | 准入 | 证据错误 | 诊断 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["tasks"]:
        errors = "; ".join(row["evidence_errors"]).replace("|", "\\|")
        diagnostic = " ".join((row.get("diagnostic") or "").split())[-400:].replace("|", "\\|")
        lines.append(
            f"| {row['instance_id']} | {row['qualification_status']} "
            f"| {row['eligible']} | {errors} | {diagnostic} |"
        )
    if report["archive_errors"]:
        lines.extend(["", "归档核验错误：", ""])
        lines.extend("- " + json.dumps(error) for error in report["archive_errors"])
    (args.output / "summary.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "requested", "qualified")}))
    return 0 if report["status"] == "QUALIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
