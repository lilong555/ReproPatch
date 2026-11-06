"""Freeze non-answer eligibility metadata from hash-verified qualification archives."""

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path

import yaml

from repropatch.artifacts import MAX_AUDIT_BYTES, private_write, read_regular
from repropatch.events import _json
from repropatch.localization_scoring import ELIGIBILITY_SCHEMA, structural_eligibility
from repropatch.task import UniqueLoader, canonical_json, relative_file

ROOT = Path(__file__).resolve().parents[1]


def require(condition, code):
    if not condition:
        raise ValueError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verified_archive(path, expected):
    raw, _ = read_regular(path, limit=MAX_AUDIT_BYTES)
    archive_sha = sha(raw)
    require(archive_sha in expected, "QUALIFICATION_ARCHIVE_SHA256_MISMATCH")
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        members = archive.getmembers()
        require(len({m.name for m in members}) == len(members), "ARCHIVE_DUPLICATE_MEMBER")
        require(
            all(m.isfile() and 0 <= m.size <= MAX_AUDIT_BYTES for m in members),
            "ARCHIVE_MEMBER_TYPE_OR_SIZE",
        )
        require(sum(m.size for m in members) <= MAX_AUDIT_BYTES, "ARCHIVE_CONTENT_TOO_LARGE")
        for member in members:
            relative_file(member.name)
        contents = {m.name: archive.extractfile(m).read(m.size + 1) for m in members}
    manifest = _json(contents["archive-manifest.json"])
    require(manifest.get("schema_version") == 1, "ARCHIVE_MANIFEST_SCHEMA")
    entries = manifest["files"]
    require(len({r["path"] for r in entries}) == len(entries), "ARCHIVE_MANIFEST_DUPLICATE")
    require(
        {r["path"] for r in entries} == set(contents) - {"archive-manifest.json"},
        "ARCHIVE_MANIFEST_COVERAGE",
    )
    for row in entries:
        content = contents[row["path"]]
        require(
            type(row["size_bytes"]) is int
            and len(content) == row["size_bytes"]
            and sha(content) == row["sha256"],
            "ARCHIVE_MEMBER_HASH_MISMATCH",
        )
    return archive_sha, len(raw), contents


def freeze_registry(protocol_path, archive_paths):
    protocol_raw, _ = read_regular(Path(protocol_path), limit=MAX_AUDIT_BYTES)
    protocol = _json(protocol_raw)
    tasks = protocol["tasks"]
    require(len(tasks) == len(set(tasks)), "DUPLICATE_PROTOCOL_TASK")
    expected_archives = protocol["qualification_archive_sha256"]
    found_archives, metadata, selected = [], [], {}
    for path in sorted(archive_paths):
        digest, size, contents = verified_archive(Path(path), expected_archives)
        found_archives.append(digest)
        metadata.append({"name": Path(path).name, "sha256": digest, "size_bytes": size})
        for instance in tasks:
            prefix = f"qualification/{instance}/"
            if prefix + "result.json" not in contents:
                continue
            require(instance not in selected, "DUPLICATE_QUALIFIED_TASK")
            result_raw = contents[prefix + "result.json"]
            result = _json(result_raw)
            patch = contents[prefix + "control/reference.patch"]
            task_raw = contents[prefix + "task.yaml"]
            task = yaml.load(task_raw, Loader=UniqueLoader)
            normalized = instance.replace("__", "-").lower()
            prepared = protocol["task_contracts"][instance]["prepared_commit"]
            require(
                result.get("schema_version") == 1
                and result["instance_id"] == instance
                and result["status"] == "QUALIFIED"
                and result["backend"] == "docker"
                and result["phases"]["reference"]["status"] == "PASSED"
                and result["native_oracle"]["passed"] is True
                and result["prepared_commit"] == prepared
                and result["dataset_revision"] == protocol["dataset_revision"]
                and result["reference_patch_sha256"] == sha(patch)
                and result["task_file_sha256"] == sha(task_raw)
                and task["id"] == normalized
                and task["repository"]["commit"] == prepared,
                "QUALIFICATION_REFERENCE_CONTRACT_MISMATCH",
            )
            eligible, kind = structural_eligibility(patch)
            selected[instance] = {
                "task_id": normalized,
                "instance_id": instance,
                "eligible": eligible,
                "label_type": kind,
                "reference_patch_sha256": sha(patch),
                "prepared_commit": prepared,
                "qualification_archive_sha256": digest,
                "qualification_result_sha256": sha(result_raw),
                "qualification_task_sha256": sha(task_raw),
            }
    require(
        sorted(found_archives) == sorted(expected_archives), "QUALIFICATION_ARCHIVE_SET_MISMATCH"
    )
    require(set(selected) == set(tasks), "QUALIFIED_TASK_SET_INCOMPLETE")
    rows = [selected[task] for task in tasks]
    result = {
        "schema": ELIGIBILITY_SCHEMA,
        "eligibility_basis": "qualified_reference_structure",
        "primary_label_type": "changed_existing_old_lines",
        "source_protocol_sha256": sha(protocol_raw),
        "dataset_revision": protocol["dataset_revision"],
        "qualification_archives": metadata,
        "total_tasks": len(rows),
        "eligible_tasks": sum(row["eligible"] for row in rows),
        "pure_insertion_tasks": sum(row["label_type"] == "pure_insertion" for row in rows),
        "tasks": rows,
    }
    result["registry_sha256"] = sha(canonical_json(result))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol", type=Path, default=ROOT / "benchmarks/context-ablation/protocol.json"
    )
    parser.add_argument("--archive", action="append", type=Path)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "benchmarks/localization-ablation/eligibility.json"
    )
    args = parser.parse_args(argv)
    archives = args.archive or list((ROOT / "benchmarks/context-ablation/inputs").glob("*.tar.gz"))
    for path in [args.protocol, *archives]:
        require(
            args.output.resolve() != path.resolve()
            and not (args.output.exists() and args.output.samefile(path)),
            "OUTPUT_OVERWRITES_INPUT",
        )
    result = freeze_registry(args.protocol, archives)
    raw = (json.dumps(result, ensure_ascii=True, indent=2) + "\n").encode()
    private_write(args.output, raw)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": sha(raw),
                "total_tasks": result["total_tasks"],
                "eligible_tasks": result["eligible_tasks"],
                "pure_insertion_tasks": result["pure_insertion_tasks"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
