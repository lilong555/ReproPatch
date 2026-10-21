"""公开完整输入边界的 Checkpoint；不执行恢复或历史工具。"""

import hashlib
import os
import re
from dataclasses import asdict
from pathlib import Path

from .artifacts import MAX_AUDIT_BYTES, EvidenceRef
from .errors import InfrastructureError, ReproPatchError
from .events import _json, read_events
from .task import canonical_json
from .workspace import SourceManifest, git_deadline

MANIFEST_KEYS = {
    "schema_version",
    "checkpoint_id",
    "boundary",
    "step_id",
    "input_fingerprints",
    "baseline",
    "native_next_input",
    "patch",
    "source_manifest",
    "source_tree_sha256",
    "counters",
    "deadline_at",
}


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def save_checkpoint(harness, workspace, native, tools_sha256):
    """先持久化不可变文件，再提交引用和关闭片段；失败留下的文件没有恢复效力。"""
    log = harness.log
    row = log.state
    if row["state"] != "REPAIRING" or not harness.resources.containers_clean:
        raise InfrastructureError("CHECKPOINT_UNSAFE: 输入边界仍有未确认资源")
    harness.resources.assert_owned()
    with git_deadline(harness.context.clock.deadline("agent_check")):
        source, patch = workspace.checkpoint_source(
            harness.resolved.editable_files, harness.resolved.protected_files
        )
    checkpoint_id = (row["last_checkpoint_id"] or 0) + 1
    parent = harness.directory / "checkpoints"
    parent.mkdir(mode=0o700, exist_ok=True)
    target = parent / str(checkpoint_id)
    target.mkdir(mode=0o700)
    _sync_directory(harness.directory)
    _sync_directory(parent)
    prefix = f"checkpoints/{checkpoint_id}"

    def save(name, content):
        return asdict(
            EvidenceRef.save(
                harness.directory, f"{prefix}/{name}", content, budget=harness.resources.budget
            )
        )

    frozen = _json(row["inputs_json"])
    config = _json(
        EvidenceRef(**frozen["configuration"]).read(harness.directory, limit=MAX_AUDIT_BYTES)
    )
    manifest = {
        "schema_version": 1,
        "checkpoint_id": checkpoint_id,
        "boundary": "model_input_ready",
        "step_id": row["steps_used"],
        "input_fingerprints": {
            **{key: row[key] for key in ("task_sha256", "base_commit", "image_id")},
            **{
                key: config[key]
                for key in ("harness_version", "implementation_sha256", "python", "sdk_versions")
            },
            "configuration": frozen["configuration"],
            "tools_sha256": tools_sha256,
            "instructions_sha256": hashlib.sha256(
                canonical_json(native["instructions"])
            ).hexdigest(),
        },
        "baseline": asdict(harness.baseline.evidence),
        "native_next_input": save("next-input.json", canonical_json(native) + b"\n"),
        "patch": save("patch.diff", patch),
        "source_manifest": save("source-manifest.json", canonical_json(source.to_dict()) + b"\n"),
        "source_tree_sha256": source.sha256,
        "counters": {key: row[key] for key in ("steps_used", "tool_calls_admitted")},
        "deadline_at": row["deadline_at"],
    }
    reference = save("manifest.json", canonical_json(manifest) + b"\n")
    _sync_directory(target)
    pause = harness.pause_after_step == row["steps_used"]
    with log.transaction():
        log.emit(
            "checkpoint_committed",
            {
                "checkpoint_id": checkpoint_id,
                "step_id": row["steps_used"],
                "manifest_ref": reference,
                "counters": manifest["counters"],
            },
            step_id=row["steps_used"] or None,
        )
        if pause:
            log.emit(
                "state_changed",
                {
                    "from": "REPAIRING",
                    "to": "INTERRUPTED",
                    "pause_after_step": harness.pause_after_step,
                },
            )
    return manifest, reference, pause


def read_checkpoint(directory, snapshot=None, checkpoint_id=None):
    """仅信任数据库引用，不扫描目录猜测 Checkpoint；不导入 SDK 或执行源码。"""
    directory = Path(directory).absolute()
    snapshot = snapshot or read_events(directory, directory.name)
    try:
        if snapshot.version != 2 or snapshot.run is None:
            raise ValueError("历史格式没有 Checkpoint")
        checkpoint_id = (
            snapshot.run["last_checkpoint_id"] if checkpoint_id is None else checkpoint_id
        )
        (record,) = (
            record for record in snapshot.checkpoints if record["checkpoint_id"] == checkpoint_id
        )
        reference = _json(record["manifest_ref_json"])
        prefix = f"checkpoints/{checkpoint_id}"
        if reference["path"] != prefix + "/manifest.json":
            raise ValueError("manifest 路径无效")
        manifest = _json(EvidenceRef(**reference).read(directory, limit=2 * 1024 * 1024))
        if (
            set(manifest) != MANIFEST_KEYS
            or type(manifest["schema_version"]) is not int
            or manifest["schema_version"] != 1
            or type(manifest["checkpoint_id"]) is not int
            or manifest["checkpoint_id"] != checkpoint_id
            or manifest["boundary"] != "model_input_ready"
            or type(manifest["step_id"]) is not int
            or manifest["step_id"] != record["step_id"]
        ):
            raise ValueError("Checkpoint 版本或身份不一致")
        data = {}
        for key, filename, limit in (
            ("native_next_input", "next-input.json", 256 * 1024 + 1),
            ("patch", "patch.diff", 8 * 1024 * 1024),
            ("source_manifest", "source-manifest.json", MAX_AUDIT_BYTES),
        ):
            ref = manifest[key]
            if ref["path"] != prefix + "/" + filename:
                raise ValueError("Checkpoint 附件路径不一致")
            data[key] = EvidenceRef(**ref).read(directory, limit=limit)
        native = _json(data["native_next_input"])
        if (
            not isinstance(native, dict)
            or set(native) != {"input", "instructions"}
            or not isinstance(native["input"], list)
            or not (native["instructions"] is None or isinstance(native["instructions"], str))
        ):
            raise ValueError("完整原生输入结构错误")
        source = SourceManifest.from_dict(_json(data["source_manifest"]))
        if source.sha256 != manifest["source_tree_sha256"]:
            raise ValueError("源码逻辑摘要不一致")
        event = snapshot.events[record["event_seq"] - 1]
        counters = manifest["counters"]
        if (
            not isinstance(counters, dict)
            or set(counters) != {"steps_used", "tool_calls_admitted"}
            or any(type(v) is not int or v < 0 for v in counters.values())
            or counters != event["payload"]["counters"]
            or counters["steps_used"] != manifest["step_id"]
        ):
            raise ValueError("累计预算快照不一致")
        row = snapshot.run
        if manifest["deadline_at"] != row["deadline_at"]:
            raise ValueError("原始期限不一致")
        if (
            row["segment_open"] == 0
            and checkpoint_id == row["last_checkpoint_id"]
            and counters != {key: row[key] for key in counters}
        ):
            raise ValueError("关闭片段的累计预算不一致")
        frozen = _json(row["inputs_json"])
        fingerprint = manifest["input_fingerprints"]
        config = _json(
            EvidenceRef(**frozen["configuration"]).read(directory, limit=MAX_AUDIT_BYTES)
        )
        for name in ("task_original", "task_resolved", "source_manifest"):
            EvidenceRef(**frozen[name]).read(directory, limit=MAX_AUDIT_BYTES)
        if config.get("script") is not None:
            EvidenceRef(**config["script"]).read(directory, limit=256000)
        expected = {
            **{key: row[key] for key in ("task_sha256", "base_commit", "image_id")},
            **{
                key: config[key]
                for key in ("harness_version", "implementation_sha256", "python", "sdk_versions")
            },
            "configuration": frozen["configuration"],
            "tools_sha256": fingerprint["tools_sha256"],
            "instructions_sha256": hashlib.sha256(
                canonical_json(native["instructions"])
            ).hexdigest(),
        }
        if (
            fingerprint != expected
            or not isinstance(fingerprint["tools_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", fingerprint["tools_sha256"]) is None
        ):
            raise ValueError("输入指纹不一致")
        baseline = _json(EvidenceRef(**manifest["baseline"]).read(directory, limit=MAX_AUDIT_BYTES))
        if not baseline["cleanup"]["confirmed"] or not any(
            e["type"] == "baseline_finished"
            and e["seq"] < record["event_seq"]
            and e["payload"]["outcome"] is None
            and e["payload"]["reason_code"] == "BASELINE_PASSED"
            and e["payload"]["evidence"] == manifest["baseline"]
            for e in snapshot.events
        ):
            raise ValueError("没有已确认的同 Run 基线")
        return manifest, reference
    except (OSError, ReproPatchError, ValueError, TypeError, KeyError) as exc:
        raise InfrastructureError("CHECKPOINT_CORRUPT: 无法核验已提交的完整输入边界") from exc
