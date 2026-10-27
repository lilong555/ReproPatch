"""完整输入 Checkpoint 与有限恢复；未知模型请求和历史工具绝不重做。"""

import hashlib
import os
import re
from dataclasses import asdict
from pathlib import Path

from .artifacts import MAX_AUDIT_BYTES, EvidenceRef
from .context import ContextPolicy, ContextState
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
    if row["state"] != "REPAIRING" or not harness.agent_resources_ready():
        raise InfrastructureError("CHECKPOINT_UNSAFE: 输入边界仍有未确认资源")
    harness.assert_repair_idle(workspace)
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
    if harness.context_policy.compaction_enabled:
        manifest["schema_version"] = 2
        manifest["context_state"] = save(
            "context-state.json", canonical_json(harness.context_state.to_dict()) + b"\n"
        )
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
            set(manifest)
            != (
                MANIFEST_KEYS | {"context_state"}
                if manifest.get("schema_version") == 2
                else MANIFEST_KEYS
            )
            or type(manifest["schema_version"]) is not int
            or manifest["schema_version"] not in {1, 2}
            or type(manifest["checkpoint_id"]) is not int
            or manifest["checkpoint_id"] != checkpoint_id
            or manifest["boundary"] != "model_input_ready"
            or type(manifest["step_id"]) is not int
            or manifest["step_id"] != record["step_id"]
        ):
            raise ValueError("Checkpoint 版本或身份不一致")
        data = {}
        frozen = _json(snapshot.run["inputs_json"])
        config = _json(
            EvidenceRef(**frozen["configuration"]).read(directory, limit=MAX_AUDIT_BYTES)
        )
        context_policy = ContextPolicy.from_dict(
            config.get("context_policy", ContextPolicy.legacy().to_dict())
        )
        if manifest["schema_version"] == 2:
            if manifest["context_state"]["path"] != prefix + "/context-state.json":
                raise ValueError("上下文状态路径不一致")
            state = _json(
                EvidenceRef(**manifest["context_state"]).read(directory, limit=MAX_AUDIT_BYTES)
            )
            ContextState.restore(context_policy, state)
        for key, filename, limit in (
            ("native_next_input", "next-input.json", context_policy.transport_max_bytes + 1),
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


def _cleanup_owned(resources):
    """按数据库登记的名称、ID、Run 标签核对并删除，禁止查询陌生对象推导成功。"""
    from .sandbox import DockerSandbox

    failures = []
    for record in list(resources.containers.values()):
        try:
            if (
                record["run_id"] != resources.run_id
                or re.fullmatch(r"repropatch-[0-9a-f]{32}", record["name"]) is None
                or record["labels"]
                != {
                    "repropatch.run": resources.run_id,
                    "repropatch.operation": record["name"],
                    "repropatch.purpose": record["purpose"],
                }
            ):
                raise InfrastructureError("OWNED_RESOURCE_UNCONFIRMED: 容器登记归属无效")

            def record_cleanup(value, original=record):
                value = {**original, **value}
                if original.get("kind") == "repair":
                    value["paused"] = False
                resources.record_container(value)

            sandbox = DockerSandbox(
                Path(record["snapshot"]),
                record["image_id"] or resources.commit,
                run_id=resources.run_id,
                purpose=record["purpose"],
                record=record_cleanup,
            )
            sandbox.name, sandbox.labels = record["name"], record["labels"]
            sandbox.container_id, sandbox.image_id = record["container_id"], record["image_id"]
            sandbox.created = True
            sandbox.profile, sandbox.tools = record["profile"], record["tools"]
            sandbox.profile_verified = record["profile_verified"]
            actual = sandbox._inspect(sandbox.container_id or sandbox.name, timeout=5)
            if actual is not None:
                sandbox._verify_owner(actual)
                if actual.get("Image") != (record["image_id"] or resources.image_id):
                    raise InfrastructureError("OWNED_RESOURCE_UNCONFIRMED: 容器镜像与登记不符")
            sandbox.close()

        except (ReproPatchError, OSError, KeyError, ValueError, TypeError) as exc:
            failures.append(str(exc).split(":", 1)[0])
    if failures:
        resources.cleanup_errors.extend(failures)
        raise InfrastructureError("OWNED_RESOURCE_UNCONFIRMED: 所属容器清理有未确认项")


def _registered_resources(log, snapshot):
    """只按权威事件核对容器，工作区损坏也不能跳过已登记对象的必要清理。"""
    from types import SimpleNamespace

    observed = SimpleNamespace(
        run_id=snapshot.run_id,
        directory=log.directory,
        budget=log.budget,
        image_id=snapshot.run["image_id"],
        commit=snapshot.run["base_commit"],
        containers={},
        cleanup_errors=[],
        data=lambda: {"worktrees": []},
    )
    for event in snapshot.events:
        p = event["payload"]
        if event["type"] == "resource_registered" and p.get("resource_type") == "container":
            observed.containers[p["name"]] = {
                key: value for key, value in p.items() if key != "resource_type"
            }

    def record(value):
        log.emit("resource_registered", {"resource_type": "container", **value}, emergency=True)
        observed.containers[value["name"]] = value
        observed.containers_clean = all(
            r["cleanup_confirmed"] and not r["cleanup_error"] for r in observed.containers.values()
        )

    observed.record_container = record
    observed.containers_clean = all(
        r["cleanup_confirmed"] and not r["cleanup_error"] for r in observed.containers.values()
    )
    return observed


def _recovery_directory(directory, attempt):
    parent = Path(directory) / "recovery"
    parent.mkdir(mode=0o700, exist_ok=True)
    target = parent / str(attempt)
    target.mkdir(mode=0o700, exist_ok=True)
    for path in (parent, target):
        if (
            path.is_symlink()
            or path.stat().st_uid != os.getuid()
            or path.stat().st_mode & 0o777 != 0o700
        ):
            raise InfrastructureError("RUN_OWNERSHIP: 恢复诊断目录归属无效")
    return target


def _diagnostic_candidate(resources, snapshot, attempt):
    """尽力保存原树的未验候选；不 reset、不改写或运行旧源码。"""
    from .workspace import Worktree

    references, errors = [], []
    try:
        frozen = _json(snapshot.run["inputs_json"])
        initial = SourceManifest.from_dict(
            _json(
                EvidenceRef(**frozen["source_manifest"]).read(
                    resources.directory, limit=MAX_AUDIT_BYTES
                )
            )
        )
        records = resources.data()["worktrees"]
        record = next(
            (
                r
                for r in reversed(records)
                if r["exists"] and Path(r["path"]).name.startswith("repair")
            ),
            None,
        )
        if record is not None and Path(record["path"]).exists():
            if Path(record["path"]).parent != resources.workspace:
                raise ValueError("候选目录不属于 Run")
            work = Worktree.open_existing(record, initial)
            prefix = f"recovery/{attempt}"
            _recovery_directory(resources.directory, attempt)
            for name, data in (
                ("unverified.patch", work.diff_bytes()),
                ("source-manifest.json", canonical_json(work.manifest().to_dict()) + b"\n"),
            ):
                references.append(
                    asdict(
                        EvidenceRef.save(
                            resources.directory,
                            f"{prefix}/{name}",
                            data,
                            budget=resources.budget,
                            emergency=True,
                        )
                    )
                )
    except (ReproPatchError, OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc).split(":", 1)[0])
    return references, errors


def _fail_recovery(log, resources, snapshot, reason, error, *, outcome="RECOVERY_FAILED"):
    """可写库提交明确恢复失败；候选仅为诊断，不具备验收资格。"""
    from datetime import UTC, datetime

    from .events import encode_json
    from .harness import __version__, implementation_sha256
    from .reports import export_report

    row = log.state
    attempt = row["recovery_attempt"]
    _recovery_directory(log.directory, attempt)
    diagnostics, diagnostic_errors = (
        _diagnostic_candidate(resources, snapshot, attempt) if resources else ([], [])
    )
    cleanup = {
        "active_code_stopped": resources is not None
        and resources.containers_clean
        and not resources.cleanup_errors,
        "workspace_retained": True,
        "errors": list(resources.cleanup_errors) if resources else ["OWNERSHIP_UNCONFIRMED"],
    }
    with log.transaction():
        log.emit(
            "recovery_finished",
            {
                "recovery_attempt": attempt,
                "success": False,
                "reason_code": reason,
                "verification_eligible": False,
                "diagnostics": diagnostics,
                "diagnostic_errors": diagnostic_errors,
            },
            emergency=True,
        )
        log.emit("cleanup_finished", cleanup, emergency=True)
    origin = snapshot.events[0]["payload"]
    frozen = _json(row["inputs_json"]) if row["inputs_json"] else {}
    baseline = None
    for event in snapshot.events:
        if event["type"] == "baseline_finished":
            try:
                baseline = _json(
                    EvidenceRef(**event["payload"]["evidence"]).read(
                        log.directory, limit=MAX_AUDIT_BYTES
                    )
                )
            except (ReproPatchError, OSError, ValueError, KeyError, TypeError):
                diagnostic_errors.append("BASELINE_UNVERIFIABLE")
    task_source_sha256 = None
    if frozen.get("task_original"):
        try:
            ref = EvidenceRef(**frozen["task_original"])
            ref.read(log.directory, limit=128 * 1024)
            task_source_sha256 = ref.sha256
        except (ReproPatchError, OSError, ValueError, KeyError, TypeError):
            diagnostic_errors.append("TASK_SOURCE_UNVERIFIABLE")
    engines = [
        event["payload"]["engine"] for event in snapshot.events if event["type"] == "model_started"
    ]
    now = datetime.now(UTC)
    body = {
        "schema_version": 1,
        "run_id": snapshot.run_id,
        "task_id": origin["task_id"],
        "input_mode": row["input_mode"],
        "state": "FINISHED",
        "outcome": outcome,
        "reason_code": reason,
        "status": "interrupted" if outcome == "CANCELLED" else "recovery_failed",
        "paused": False,
        "engine": engines[-1] if engines else origin["engine"],
        "usage": _json(row["usage_json"]),
        "agent": {
            "agent_stop_reason": row["agent_stop_reason"],
            "steps_used": row["steps_used"],
            "tool_calls_used": row["tool_calls_admitted"],
            "http_attempts": 0 if row["engine_kind"] in {"fake", "none"} else None,
        },
        "provenance": {
            **{key: row[key] for key in ("base_commit", "image_id", "task_sha256")},
            "task_source_sha256": task_source_sha256,
            "image_repo_digests": [],
            "platform": None,
            "software_version": __version__,
            "implementation_sha256": implementation_sha256(),
            "tool_versions": {},
        },
        "task_original": frozen.get("task_original"),
        "task_resolved": frozen.get("task_resolved"),
        "cost": None,
        "candidate": None,
        "baseline": baseline,
        "independent": None,
        "isolated": baseline.get("isolated") if baseline else None,
        "evaluations": [baseline] if baseline else [],
        "producer": frozen.get(
            "producer",
            {
                "name": None,
                "patch": None,
                "trace": None,
                "trace_trust": None,
            },
        ),
        "cleanup": cleanup,
        "diagnostics": diagnostics,
        "diagnostic_errors": diagnostic_errors,
        "verification_eligible": False,
        "error": str(error)[:4000],
        "artifact_directory": str(log.directory),
        "workspace_directory": str(resources.workspace)
        if hasattr(resources, "workspace")
        else None,
        "timing": {
            "created_at": row["created_at"],
            "deadline_at": row["deadline_at"],
            "finished_at": now.isoformat(),
            "elapsed_ms": round(
                (now - datetime.fromisoformat(row["created_at"])).total_seconds() * 1000
            ),
        },
        "events_last_seq": log.sequence + 1,
        "limitations": [
            "仅验收固定 Task 的测试 oracle，不证明所有输入正确。",
            "Docker 与宿主共享内核；模型生成不保证正确。",
            "未知副作用不重做；诊断补丁需以新的 verify-patch Run 独立验收。",
        ],
    }
    reference = EvidenceRef.save(
        log.directory,
        f"recovery/{attempt}/result.json",
        encode_json(body) + b"\n",
        budget=log.budget,
        emergency=True,
    )
    log.emit(
        "state_changed",
        {
            "from": "RECOVERING",
            "to": "FINISHED",
            "outcome": outcome,
            "reason_code": reason,
            "result_ref": asdict(reference),
            "agent_stop_reason": row["agent_stop_reason"],
        },
        emergency=True,
    )
    try:
        return export_report(log.directory)
    except (ReproPatchError, OSError):
        return {**body, "command_error": "ARTIFACT_EXPORT_FAILED", "artifacts_complete": False}


def _resume_harness(log, resources, snapshot, pause_after_step, sandbox_factory):
    """核对冻结配置，在新自有工作树重建安全源码后交回同一 Harness。"""
    import platform
    import time
    from importlib.metadata import PackageNotFoundError, version

    from . import __version__
    from .harness import Harness, implementation_sha256, instructions_for
    from .models import ResponsesConfig, prepare_sdk, sdk_script_bytes
    from .task import ImageIdentity, Task, resolve_task
    from .tools import sdk_tools_sha256, shell_only_tools
    from .verification import EvaluationEvidence, RunClock, RunContext, baseline_result
    from .workspace import Worktree

    directory, row = log.directory, log.state
    manifest, _ = read_checkpoint(directory, read_events(directory, snapshot.run_id))
    frozen = _json(row["inputs_json"])
    config = _json(EvidenceRef(**frozen["configuration"]).read(directory, limit=MAX_AUDIT_BYTES))
    raw = _json(EvidenceRef(**frozen["task_resolved"]).read(directory, limit=MAX_AUDIT_BYTES))
    context_policy = ContextPolicy.from_dict(
        config.get("context_policy", ContextPolicy.legacy().to_dict())
    )
    native = _json(
        EvidenceRef(**manifest["native_next_input"]).read(
            directory, limit=context_policy.transport_max_bytes + 1
        )
    )
    tool_mode = config.get("benchmark", {}).get("tool_mode", "legacy")
    intermediate_checks = config.get("benchmark", {}).get("intermediate_checks", True)
    # 禁用自检的提示和工具子集由已校验的冻结配置确定。
    expected_instructions = (
        instructions_for(tool_mode) if intermediate_checks else config["instructions"]
    )
    try:
        versions = {name: version(name) for name in ("openai-agents", "openai")}
    except PackageNotFoundError:
        versions = None
    if (
        config["harness_version"] != __version__
        or config["implementation_sha256"] != implementation_sha256()
        or config["python"] != platform.python_version()
        or config["sdk_versions"] != versions
        or config["instructions"] != expected_instructions
        or native["instructions"] != config["instructions"]
    ):
        raise InfrastructureError(
            "INPUT_CHANGED: Harness、Python、SDK 或 instructions 身份发生变化"
        )
    prepare_sdk()
    from .tools import sdk_tools

    restored_tools = (
        shell_only_tools(None, None) if tool_mode == "shell-only" else sdk_tools(None, None, None)
    )
    if not intermediate_checks:
        restored_tools = [
            tool for tool in restored_tools if tool.name not in {"run_command", "run_shell"}
        ]
    tools_hash = (
        sdk_tools_sha256()
        if tool_mode == "legacy" and intermediate_checks
        else sdk_tools_sha256(restored_tools)
    )
    if manifest["input_fingerprints"]["tools_sha256"] != tools_hash:
        raise InfrastructureError("INPUT_CHANGED: 工具 schema 发生变化")
    original = EvidenceRef(**frozen["task_original"]).read(directory, limit=128 * 1024)
    task = Task.from_dict(raw["task"], directory, source_bytes=original)
    if config["budget"] != asdict(task.budget):
        raise InfrastructureError("INPUT_CHANGED: 冻结预算不一致")
    resolved = resolve_task(
        task,
        output_root=directory.parent,
        image_identity=ImageIdentity(row["image_id"]) if sandbox_factory else None,
    )
    if (
        resolved.task_sha256 != row["task_sha256"]
        or resolved.execution_contract() != raw["execution_contract"]
        or resources.workspace != resolved.workspace_root / snapshot.run_id
        or resources.repository != str(resolved.repository_path)
        or resources.commit != resolved.base_commit
    ):
        raise InfrastructureError("INPUT_CHANGED: Task、base、image 或路径身份发生变化")
    if row["engine_kind"] == "fake":
        if config.get("script") is None:
            raise InfrastructureError("INPUT_CHANGED: fake 恢复缺少冻结原生脚本")
        reference = EvidenceRef(**config["script"])
        script = reference.read(directory, limit=256000)
        model = sdk_script_bytes(script, steps_used=row["steps_used"])
    else:
        engine = config["engine"]
        model = ResponsesConfig(
            engine["model_name"],
            engine["api_base"],
            config["key_env"],
            True,
            engine["use_env_proxy"],
        )
    harness = Harness(
        task,
        model,
        directory.parent,
        sandbox_factory=sandbox_factory,
        pause_after_step=pause_after_step,
        candidate_only=config.get("benchmark", {}).get("candidate_only", False),
        compiler_cache=config.get("benchmark", {}).get("compiler_cache", False),
        tool_mode=tool_mode,
        context_policy=context_policy,
        intermediate_checks=intermediate_checks,
    )
    if "context_state" in manifest:
        harness.context_state = ContextState.restore(
            context_policy,
            _json(EvidenceRef(**manifest["context_state"]).read(directory, limit=MAX_AUDIT_BYTES)),
        )
    harness.resources, harness.log, harness.directory = resources, log, directory
    clock = RunClock.restore(
        row["created_at"], row["deadline_at"], task.budget.verification_reserve_seconds
    )
    harness._initial_report(clock, snapshot.run_id)
    harness.resolved, harness.resuming, harness.resume_native = resolved, True, native
    if tool_mode == "shell-only":
        native["input"].append(
            {
                "role": "user",
                "content": (
                    "修复环境已从已提交的 Checkpoint 恢复。/src 包含已审计的源码修改；"
                    "/build 和 /tmp 已清空，编译缓存重新开始。请按需重新配置、构建和创建临时文件。"
                    "累计请求、工具预算和原始期限继续生效。"
                ),
            }
        )
    harness.instructions = native["instructions"]
    harness.independent = None
    baseline_ref = EvidenceRef(**manifest["baseline"])
    baseline = _json(baseline_ref.read(directory, limit=MAX_AUDIT_BYTES))
    harness.baseline = EvaluationEvidence.from_dict(baseline, baseline_ref)
    if baseline_result(resolved, harness.baseline)[0] is not None:
        raise InfrastructureError("CHECKPOINT_CORRUPT: 已存基线不合格")
    harness.context = RunContext(
        resolved,
        resources,
        log,
        clock,
        harness.factory,
        harness.test_backend,
        [harness.baseline],
        image_id=harness.baseline.image_id,
        isolated=harness.baseline.isolated,
        use_compiler_cache=harness.compiler_cache,
    )
    prior_ids = {harness.baseline.evaluation_id}
    for event in snapshot.events:
        payload = event["payload"]
        if (
            event["type"] == "verification_finished"
            and payload.get("evaluation_role") == "agent_check"
        ):
            reference = EvidenceRef(**payload["evidence"])
            observed = EvaluationEvidence.from_dict(
                _json(reference.read(directory, limit=MAX_AUDIT_BYTES)), reference
            )
            if observed.evaluation_id not in prior_ids:
                harness.context.evaluations.append(observed)
                prior_ids.add(observed.evaluation_id)
    for key in ("task_original", "task_resolved"):
        harness.report[key] = frozen[key]
    harness.report.update(
        state="RECOVERING",
        reproduced=True,
        task_sha256=row["task_sha256"],
        base_commit=row["base_commit"],
        engine={**config["engine"], "versions": versions},
    )
    harness.report["provenance"].update(
        {key: row[key] for key in ("task_sha256", "base_commit", "image_id")}
    )
    harness.report["provenance"].update(
        platform=task.environment.platform, image_repo_digests=list(resolved.image_repo_digests)
    )
    harness._sync_agent_state()
    initial = SourceManifest.from_dict(
        _json(EvidenceRef(**frozen["source_manifest"]).read(directory, limit=MAX_AUDIT_BYTES))
    )
    expected = SourceManifest.from_dict(
        _json(EvidenceRef(**manifest["source_manifest"]).read(directory, limit=MAX_AUDIT_BYTES))
    )
    patch = EvidenceRef(**manifest["patch"]).read(directory, limit=8 * 1024 * 1024)
    with git_deadline(time.monotonic() + 30):
        for record in resources.prior_worktrees:
            path = Path(record["path"])
            if not record["exists"] or not path.exists():
                continue
            if path.parent != resources.workspace:
                raise InfrastructureError("WORKSPACE_DIVERGED: 原工作树不属于 Run")
            work = Worktree.open_existing(record, initial)
            if path.name.startswith("repair") and work.manifest() != expected:
                raise InfrastructureError("WORKSPACE_DIVERGED: 原修复源码与 Checkpoint 不同")
            resources.worktrees.append(work)
        if resources._workspace_identity is None:
            if any(parent.is_symlink() for parent in resources.workspace.parents):
                raise InfrastructureError("WORKSPACE_DIVERGED: 工作区父目录是链接")
            resources.workspace.mkdir(mode=0o700, parents=True)
            resources._workspace_identity = resources._identity(resources.workspace)
        resources.save(emergency=True)
        repair = harness.context.new_worktree(f"repair-r{row['recovery_attempt']:04d}")
        if repair.initial_manifest != initial:
            raise InfrastructureError("INPUT_CHANGED: 固定 base 的完整字节清单发生变化")
        if patch:
            repair.apply_patch(patch, resolved.editable_files, resolved.protected_files)
        if repair.manifest() != expected:
            raise InfrastructureError("CHECKPOINT_CORRUPT: base 与 patch 不能重建完整源码")
        for old in resources.worktrees:
            if old is not repair:
                old.assert_current()
                old.close()
        resources.save(emergency=True)
        harness.resume_repair = repair
    orphan = directory / "checkpoints" / str(row["last_checkpoint_id"] + 1)
    if orphan.exists() or orphan.is_symlink():
        if orphan.is_symlink() or not orphan.is_dir() or orphan.stat().st_uid != os.getuid():
            raise InfrastructureError("CHECKPOINT_CORRUPT: 未提交目录归属无效")
        target = _recovery_directory(directory, row["recovery_attempt"])
        orphan.rename(target / "orphan-checkpoint")
        _sync_directory(orphan.parent)
        _sync_directory(target)
    with log.transaction():
        log.emit(
            "recovery_finished",
            {
                "recovery_attempt": row["recovery_attempt"],
                "success": True,
                "checkpoint_id": row["last_checkpoint_id"],
                "source_tree_sha256": expected.sha256,
            },
        )
        log.emit("state_changed", {"from": "RECOVERING", "to": "REPAIRING"})
    harness.report["state"] = "REPAIRING"
    return harness


def resume_run(directory, *, pause_after_step=None, sandbox_factory=None):
    """只接管已有 Run；锁和库有效前不产生恢复事实或外部执行。"""
    from .artifacts import AuditBudget
    from .events import EventLog, validate_run_id
    from .resources import RunLock, RunResources

    directory = Path(directory).absolute()
    validate_run_id(directory.name)
    control_identity = RunResources._identity(directory)
    if directory.stat().st_mode & 0o777 != 0o700 or any(
        parent.is_symlink() for parent in directory.parents
    ):
        raise InfrastructureError("RUN_OWNERSHIP: 控制目录权限或父路径不符")
    lock, log, resources = RunLock(directory), None, None
    try:
        log = EventLog.open_existing(
            directory, directory.name, lock=lock, budget=AuditBudget(directory)
        )
        snapshot = read_events(directory, directory.name)
        row = snapshot.run
        if control_identity != tuple(snapshot.events[0]["payload"]["control_identity"]):
            raise InfrastructureError("RUN_OWNERSHIP: 控制目录与原身份不同")
        if row["state"] == "FINISHED":
            raise ReproPatchError("RUN_FINISHED: 终态 Run 不能恢复")
        if pause_after_step is not None:
            if type(pause_after_step) is not int or pause_after_step <= row["steps_used"]:
                raise ReproPatchError("PAUSE_STEP_INVALID: 必须 steps_used < N < max_steps")
            frozen = _json(row["inputs_json"])
            raw = _json(
                EvidenceRef(**frozen["task_resolved"]).read(directory, limit=MAX_AUDIT_BYTES)
            )
            maximum = raw["execution_contract"]["budget"]["max_steps"]
            if (
                type(pause_after_step) is not int
                or not row["steps_used"] < pause_after_step < maximum
            ):
                raise ReproPatchError("PAUSE_STEP_INVALID: 必须 steps_used < N < max_steps")
        source = row["state"]
        with log.transaction():
            log.emit("state_changed", {"from": source, "to": "INTERRUPTED", "takeover": True})
            log.emit("state_changed", {"from": "INTERRUPTED", "to": "RECOVERING"})
            log.emit(
                "recovery_started",
                {
                    "recovery_attempt": row["recovery_attempt"] + 1,
                    "source_state": source,
                    "checkpoint_id": row["last_checkpoint_id"],
                },
            )
        try:
            resources = _registered_resources(log, snapshot)
            cleanup_failure = None
            try:
                _cleanup_owned(resources)
            except InfrastructureError as exc:
                cleanup_failure = exc
            cleanup_errors = list(resources.cleanup_errors)
            try:
                attached = RunResources.open_existing(
                    directory, lock, read_events(directory, directory.name)
                )
                attached.event_log = log
                attached.cleanup_errors.extend(cleanup_errors)
                resources = attached
            except (ReproPatchError, OSError, KeyError, ValueError, TypeError):
                if source in {"REPAIRING", "INTERRUPTED"} and not row["segment_open"]:
                    raise
            if source not in {"REPAIRING", "INTERRUPTED"} or row["input_mode"] != "run":
                raise InfrastructureError("UNSUPPORTED_RECOVERY_PHASE: 不重执行中断的阶段")
            if row["segment_open"]:
                started = [e for e in snapshot.events if e["type"] == "model_started"]
                ended = [e for e in snapshot.events if e["type"] == "model_finished"]
                reason = (
                    "MODEL_RESULT_UNKNOWN"
                    if started and (not ended or started[-1]["seq"] > ended[-1]["seq"])
                    else "OPEN_AGENT_SEGMENT"
                )
                raise InfrastructureError(reason + ": 不重发请求或重做工具")
            if row["last_checkpoint_id"] is None:
                raise InfrastructureError("NO_CHECKPOINT: 没有已提交的安全输入边界")
            if cleanup_failure is not None:
                raise cleanup_failure
            harness = _resume_harness(log, resources, snapshot, pause_after_step, sandbox_factory)
        except KeyboardInterrupt as exc:
            if resources is not None:
                try:
                    _cleanup_owned(resources)
                except (ReproPatchError, OSError):
                    pass
            return _fail_recovery(
                log, resources, snapshot, "USER_CANCELLED", exc, outcome="CANCELLED"
            )
        except (ReproPatchError, OSError, ValueError, TypeError, KeyError) as exc:
            reason = str(exc).split(":", 1)[0]
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", reason) is None:
                reason = "CHECKPOINT_CORRUPT"
            return _fail_recovery(log, resources, snapshot, reason, exc)
        return harness.run()
    except (ReproPatchError, OSError) as exc:
        if not str(exc).startswith(("RUN_FINISHED:", "PAUSE_STEP_INVALID:", "RESUME_UNSUPPORTED:")):
            try:
                from .events import encode_json

                EvidenceRef.save(
                    directory,
                    "recovery-error.json",
                    encode_json(
                        {
                            "database_updated": False,
                            "error": str(exc).split(":", 1)[0],
                            "message": "无法提交可靠恢复结论；停止执行。",
                        }
                    )
                    + b"\n",
                    emergency=True,
                )
            except (ReproPatchError, OSError):
                pass
        raise
    finally:
        if log is not None:
            log.close()
        lock.close()
