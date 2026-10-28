"""Verify task evidence before publication; preserve every original byte.

The only optional recovery uses the redundant result.commands representation.
Recovered bytes must match the originally recorded checksum and are written
to a separate directory, never over the original evidence.
"""

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def required_task_artifacts(result):
    required = {"result.json"}
    if result.get("adapter") == "native-cpp-v1" and result.get("status") in {
        "QUALIFIED",
        "HOST_QUALIFIED",
    }:
        required.update(
            {
                "commands.json",
                "prepared.bundle",
                "control/record.json",
                "control/reference.patch",
                "control/reference-full.patch",
                "control/test.patch",
                "control/upstream-source-manifest.json",
                "control/prepared-source-manifest.json",
                "control/editable-files.json",
                "repository/repropatch-native/contract.json",
                "repository/repropatch-native/runner.py",
                "native-oracle-native-results.json",
            }
        )
        for phase in ("baseline", "reference"):
            required.update({f"{phase}-inventory.json", f"{phase}-results.xml"})
            required.update(
                f"logs/{phase}-{stage}.log"
                for stage in ("configure", "inventory", "build", "ctest")
            )
        required.update(
            f"logs/native-oracle-{stage}.log" for stage in ("configure", "build", "ctest")
        )
        if result["backend"] == "docker":
            required.add("task.yaml")
        if result.get("configuration", {}).get("repository") == "nlohmann/json":
            required.add("single-header-native-results.json")
        return required
    if result.get("status") in {"QUALIFIED", "HOST_QUALIFIED"}:
        required.update(
            {
                "commands.json",
                "control/record.json",
                "control/reference.patch",
                "control/test.patch",
            }
        )
        for phase in ("baseline", "reference", "native-oracle"):
            required.update({f"{phase}-inventory.json", f"{phase}-results.xml"})
            required.update(
                f"logs/{phase}-{stage}.log"
                for stage in ("configure", "inventory", "build", "ctest")
            )
        if result.get("backend") == "docker" or result["status"] == "QUALIFIED":
            required.add("task.yaml")
    return required


def verify_tree(directory, manifest, required=()):
    if not isinstance(manifest, dict) or not manifest:
        return [{"file": "manifest.json", "reason": "EMPTY_OR_INVALID_MANIFEST"}]
    issues = []
    for relative in sorted(set(required) - manifest.keys()):
        issues.append({"file": relative, "reason": "REQUIRED_ARTIFACT_NOT_IN_MANIFEST"})
    for relative, expected in manifest.items():
        path = directory / relative
        issue = {"file": relative, "expected": expected}
        if not path.resolve().is_relative_to(directory.resolve()):
            issues.append(issue | {"reason": "PATH_OUTSIDE_EVIDENCE"})
        elif not path.is_file():
            issues.append(issue | {"reason": "MISSING_FILE"})
        else:
            actual = {"size": path.stat().st_size, "sha256": digest(path)}
            if actual != expected:
                issues.append(issue | {"reason": "CHECKSUM_MISMATCH", "actual": actual})
    return issues


def audit(
    batches, output, recover_commands=False, summary_output=None, legacy_source_snapshot=False
):
    if summary_output is not None:
        if len(batches) != 1 or summary_output.exists():
            raise ValueError("--summary-output requires one batch and a new output file")
        if not (batches[0] / "batch-summary.json").is_file():
            raise FileNotFoundError(batches[0] / "batch-summary.json")
        if summary_output.resolve() == (batches[0] / "batch-summary.json").resolve():
            raise ValueError("The original summary must remain unchanged")
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "schema_version": 1,
        "started_at": datetime.now(UTC).isoformat(),
        "validator_sha256": digest(Path(__file__)),
        "original_files_modified": False,
        "cause_of_any_mismatch": "UNKNOWN",
        "batches": [],
        "tasks": [],
    }
    for batch in batches:
        batch_record = {
            "directory": str(batch),
            "source_snapshot": (
                "LEGACY_SOURCE_SNAPSHOT_MISSING" if legacy_source_snapshot else "MISSING"
            ),
        }
        source_manifest = batch / "source-manifest.json"
        if source_manifest.exists():
            source_issues = verify_tree(
                batch / "execution-source",
                json.loads(source_manifest.read_text()),
                required={
                    "scripts/qualify_cpp_batch.py",
                    "scripts/prepare_multiswe_task.py",
                    "scripts/screen_multiswe.py",
                    "src/repropatch/task.py",
                },
            )
            batch_record.update(
                source_snapshot="EVIDENCE_INCOMPLETE" if source_issues else "VERIFIED",
                source_snapshot_issues=source_issues,
                source_manifest_sha256=digest(source_manifest),
            )
        report["batches"].append(batch_record)
        summary = batch / "batch-summary.json"
        batch_record["summary_status"] = "PRESENT" if summary.is_file() else "MISSING"
        summary_states = (
            {
                r["instance_id"]: r["status"]
                for r in json.loads(summary.read_text()).get(
                    "results", json.loads(summary.read_text()).get("tasks", [])
                )
            }
            if summary.exists()
            else {}
        )
        for result_file in sorted(batch.glob("*/result.json")):
            directory = result_file.parent
            result = json.loads(result_file.read_text())
            manifest_file = directory / "manifest.json"
            item = {
                "directory": str(directory),
                "instance_id": result["instance_id"],
                "qualification_status": result["status"],
                "batch_summary_status": summary_states.get(result["instance_id"]),
                "result_sha256": digest(result_file),
                "status": "EVIDENCE_INCOMPLETE",
                "recoveries": [],
            }
            if not manifest_file.exists():
                item["issues"] = [{"file": "manifest.json", "reason": "MISSING_MANIFEST"}]
            else:
                manifest = json.loads(manifest_file.read_text())
                item["manifest_sha256"] = digest(manifest_file)
                item["checked_files"] = len(manifest)
                item["issues"] = verify_tree(directory, manifest, required_task_artifacts(result))
                if recover_commands and isinstance(result.get("commands"), list):
                    for issue in item["issues"]:
                        if issue["file"] != "commands.json":
                            continue
                        encoded = (
                            json.dumps(result["commands"], ensure_ascii=False, indent=2) + "\n"
                        ).encode()
                        expected = issue.get("expected")
                        if not isinstance(expected, dict):
                            continue
                        if len(encoded) != expected["size"] or (
                            hashlib.sha256(encoded).hexdigest() != expected["sha256"]
                        ):
                            continue
                        target = (
                            output
                            / "recovered-files"
                            / batch.name
                            / directory.name
                            / "commands.json"
                        )
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(encoded)
                        item["recoveries"].append(
                            {
                                "file": "commands.json",
                                "source": "result.json:commands",
                                "recovered_file": str(target.relative_to(output)),
                                **expected,
                            }
                        )
                recovered = {record["file"] for record in item["recoveries"]}
                if all(issue["file"] in recovered for issue in item["issues"]):
                    item["status"] = "VERIFIED_WITH_BYTE_RECOVERY" if recovered else "VERIFIED"
                if batch_record["source_snapshot"] != "VERIFIED":
                    item["status"] = "EVIDENCE_INCOMPLETE"
            item["source_snapshot_status"] = batch_record["source_snapshot"]
            report["tasks"].append(item)
    report["finished_at"] = datetime.now(UTC).isoformat()
    audit_file = output / "audit.json"
    audit_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if summary_output is not None:
        source_summary = batches[0] / "batch-summary.json"
        summary = json.loads(source_summary.read_text())
        indexed = {r["instance_id"]: r for r in report["tasks"]}
        audit_reference = {
            "path": os.path.relpath(audit_file, summary_output.parent),
            "sha256": digest(audit_file),
        }
        for result in summary["results"]:
            result["execution_status"] = result["status"]
            task_audit = indexed.get(result["instance_id"], {})
            state = task_audit.get("status", "EVIDENCE_INCOMPLETE")
            evidence_status = {
                "VERIFIED": "VERIFIED",
                "VERIFIED_WITH_BYTE_RECOVERY": "RECOVERED_EXACT",
            }.get(state, "INCOMPLETE")
            if not task_audit or any(
                issue["reason"] == "MISSING_MANIFEST" for issue in task_audit.get("issues", [])
            ):
                evidence_status = "MISSING"
            status_matches = not task_audit or (
                result["status"] == task_audit.get("qualification_status")
            )
            if not status_matches:
                evidence_status = "INCOMPLETE"
            result["evidence_status"] = evidence_status
            result["evidence_audit"] = audit_reference | {
                "task_directory": task_audit.get("directory")
            }
            result["evidence_integrity"] = {
                "status": state,
                "recoveries": task_audit.get("recoveries", []),
                "audit_task_directory": task_audit.get("directory"),
                "summary_matches_task_status": status_matches,
            }
            if result["status"] in {"QUALIFIED", "HOST_QUALIFIED"} and (
                evidence_status not in {"VERIFIED", "RECOVERED_EXACT"}
                or result["status"] != task_audit.get("qualification_status")
            ):
                result["status"] = "EVIDENCE_INCOMPLETE"
        summary["qualified_tasks"] = [r for r in summary["results"] if r["status"] == "QUALIFIED"]
        summary["host_qualified_tasks"] = [
            r for r in summary["results"] if r["status"] == "HOST_QUALIFIED"
        ]
        summary["evidence_audit"] = {
            **audit_reference,
            "original_summary_sha256": digest(source_summary) if source_summary.exists() else None,
        }
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True, help="New audit directory")
    parser.add_argument("--recover-commands", action="store_true")
    parser.add_argument("--summary-output", type=Path, help="New audited summary; one batch only")
    parser.add_argument(
        "--legacy-source-snapshot",
        action="store_true",
        help="Label missing old snapshots; never waive checks",
    )
    args = parser.parse_args()
    report = audit(
        args.batch,
        args.output,
        args.recover_commands,
        args.summary_output,
        args.legacy_source_snapshot,
    )
    incomplete = [r for r in report["tasks"] if r["status"] == "EVIDENCE_INCOMPLETE"]
    incomplete_batches = [
        r
        for r in report["batches"]
        if r["summary_status"] != "PRESENT" or r["source_snapshot"] != "VERIFIED"
    ]
    print(
        json.dumps(
            {
                "checked_tasks": len(report["tasks"]),
                "incomplete_tasks": len(incomplete),
                "incomplete_batches": len(incomplete_batches),
            }
        )
    )
    return 1 if incomplete or incomplete_batches else 0


if __name__ == "__main__":
    raise SystemExit(main())
