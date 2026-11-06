"""从已提交事实和核验附件生成只读运行诊断。"""

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .artifacts import MAX_AUDIT_BYTES, EvidenceRef
from .errors import ReproPatchError, StateReadError
from .events import _json, read_events
from .recovery import read_checkpoint
from .reports import _text, committed_state, evidence_errors, load_result
from .trace import _references
from .verification import RunClock

TOKEN_FIELDS = ("input_tokens", "output_tokens", "total_tokens")
RESUME_CHECKS = (
    (
        "RunLock / RunResources.open_existing / assert_owned",
        "排他锁、控制目录及 resources.json 的身份、权限和工作区归属。",
    ),
    ("_cleanup_owned", "按已登记容器名称、ID、Run 标签及镜像检查归属并确认清理。"),
    (
        "read_checkpoint / baseline_result",
        "完整输入边界、附件摘要、累计计数、原始期限及同 Run 基线资格。",
    ),
    (
        "_resume_harness",
        "Harness 源码、Python、SDK、instructions、工具 schema、冻结预算及"
        " Task/base/image/路径身份。",
    ),
    (
        "Worktree.open_existing / manifest / apply_patch",
        "原修复树与 Checkpoint 源码指纹一致，固定 base 加 patch 在新工作树重建相同完整清单。",
    ),
    (
        "RunClock.restore / Harness._agent / 工具批次准入",
        "累计步骤和工具限额、原始绝对期限、独立验收预留及清理时间继续生效。",
    ),
)


def _problem(problems, path, error):
    problems.append(
        {"path": path, "code": "EVIDENCE_UNVERIFIABLE", "message": str(error).split(":", 1)[0]}
    )


def _document(directory, reference, problems):
    try:
        value = _json(EvidenceRef(**reference).read(directory, limit=MAX_AUDIT_BYTES))
        if not isinstance(value, dict):
            raise ValueError("结构化附件须为对象")
        return value
    except (ReproPatchError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        path = reference.get("path") if isinstance(reference, dict) else None
        _problem(problems, path, exc)
        return None


def _milliseconds(start, end):
    try:
        seconds = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
        return round(seconds * 1000) if seconds >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _timing(snapshot, body):
    first, last = snapshot.events[0], snapshot.events[-1]
    phases, timeline = [], []
    stage, beginning = "CREATED", first
    for event in snapshot.events:
        kind, payload = event.get("type", event.get("kind")), event["payload"]
        timeline.append(
            {
                "seq": event["seq"],
                "timestamp": event["timestamp"],
                "type": kind,
                "step_id": event.get("step_id"),
                "tool_call_id": event.get("tool_call_id"),
                "stage": payload.get("to") if kind == "state_changed" else None,
            }
        )
        if kind == "state_changed":
            phases.append(
                {
                    "stage": stage,
                    "started_at": beginning["timestamp"],
                    "finished_at": event["timestamp"],
                    "first_seq": beginning["seq"],
                    "last_seq": event["seq"],
                    "elapsed_ms": _milliseconds(beginning["timestamp"], event["timestamp"]),
                    "closed": True,
                }
            )
            stage, beginning = payload["to"], event
    if snapshot.version and stage != "FINISHED":
        phases.append(
            {
                "stage": stage,
                "started_at": beginning["timestamp"],
                "finished_at": None,
                "observed_through": last["timestamp"],
                "first_seq": beginning["seq"],
                "last_seq": last["seq"],
                "elapsed_ms": _milliseconds(beginning["timestamp"], last["timestamp"]),
                "closed": False,
            }
        )
    return {
        **(body or {}).get("timing", {}),
        "basis": "committed_event_timestamps",
        "observed_span_ms": _milliseconds(first["timestamp"], last["timestamp"]),
        "phases": phases,
        "timeline": timeline,
    }


def _budget(snapshot, resolved, problems, reference):
    row, limits = snapshot.run or {}, None
    if resolved is not None:
        try:
            limits = resolved["execution_contract"]["budget"]
            if not isinstance(limits, dict):
                raise ValueError("冻结预算须为对象")
            for name in ("wall_seconds", "max_steps", "max_tool_calls"):
                value = limits[name]
                if value is not None and (type(value) is not int or value <= 0):
                    raise ValueError("冻结预算字段无效")
            reserve = limits.get("verification_reserve_seconds")
            if reserve is not None and (type(reserve) is not int or reserve < 0):
                raise ValueError("验收预留无效")
        except (KeyError, TypeError, ValueError) as exc:
            _problem(problems, reference["path"], exc)
            limits = None
    result = {
        "limits": limits,
        "created_at": row.get("created_at"),
        "deadline_at": row.get("deadline_at"),
        "observed_at": datetime.now(UTC).isoformat(),
        "remaining_steps": None,
        "remaining_tool_calls": None,
        "wall_remaining_seconds": None,
        "agent_remaining_seconds": None,
        "verification_remaining_seconds": None,
    }
    if row:
        result["wall_remaining_seconds"] = round(
            (datetime.fromisoformat(row["deadline_at"]) - datetime.now(UTC)).total_seconds(), 3
        )
        # 时限沿用执行侧时钟，包含原始停机时间和清理预留。
        reserve = limits.get("verification_reserve_seconds") if limits else None
        clock = RunClock.restore(row["created_at"], row["deadline_at"], reserve or 0)
        result["verification_remaining_seconds"] = round(clock.remaining("independent"), 3)
        if reserve is not None:
            result["agent_remaining_seconds"] = round(clock.remaining("agent_check"), 3)
        if limits:
            for name, counter, target in (
                ("max_steps", "steps_used", "remaining_steps"),
                ("max_tool_calls", "tool_calls_admitted", "remaining_tool_calls"),
            ):
                if limits[name] is not None:
                    result[target] = max(0, limits[name] - row[counter])
    return result


def _recovery(directory, snapshot, state, problems):
    row, manifest, reference = snapshot.run or {}, None, None
    checkpoint_id = row.get("last_checkpoint_id")
    if checkpoint_id is not None:
        try:
            manifest, reference = read_checkpoint(directory, snapshot)
        except (ReproPatchError, OSError, ValueError, TypeError, KeyError) as exc:
            _problem(problems, f"checkpoints/{checkpoint_id}/manifest.json", exc)
    starts = [e["seq"] for e in snapshot.events if e.get("type") == "model_started"]
    finishes = [e["seq"] for e in snapshot.events if e.get("type") == "model_finished"]
    reason = None
    if snapshot.version != 2:
        reason = "RESUME_UNSUPPORTED"
    elif state["state"] == "FINISHED":
        reason = "RUN_FINISHED"
    elif state["state"] not in {"REPAIRING", "INTERRUPTED"} or state["input_mode"] != "run":
        reason = "UNSUPPORTED_RECOVERY_PHASE"
    elif row["segment_open"]:
        reason = (
            "MODEL_RESULT_UNKNOWN"
            if starts and (not finishes or starts[-1] > finishes[-1])
            else "OPEN_AGENT_SEGMENT"
        )
    elif checkpoint_id is None:
        reason = "NO_CHECKPOINT"
    elif manifest is None:
        reason = "CHECKPOINT_CORRUPT"
    containers, cleanup = {}, None
    for event in snapshot.events:
        payload = event["payload"]
        if (
            event.get("type") == "resource_registered"
            and payload.get("resource_type") == "container"
        ):
            containers[payload.get("name")] = {
                key: payload.get(key)
                for key in (
                    "name",
                    "container_id",
                    "run_id",
                    "image_id",
                    "purpose",
                    "cleanup_confirmed",
                    "cleanup_error",
                    "paused",
                )
            }
        elif event.get("type") == "cleanup_finished":
            cleanup = {
                key: payload.get(key)
                for key in ("active_code_stopped", "workspace_retained", "errors")
            }
    registry = directory / "resources.json"
    return {
        "status": "blocked" if reason else "checks_required",
        "reason_code": reason,
        "recovery_attempt": row.get("recovery_attempt"),
        "checkpoint": {
            "checkpoint_id": checkpoint_id,
            "verified": manifest is not None,
            "closed": bool(checkpoint_id is not None and row.get("segment_open") == 0),
            "manifest": reference,
            "source_tree_sha256": manifest["source_tree_sha256"] if manifest else None,
            "input_fingerprints": manifest["input_fingerprints"] if manifest else None,
        },
        "resources": {
            "registry_path": "resources.json",
            "registry_present": registry.is_file() and not registry.is_symlink(),
            "containers": list(containers.values()),
            "cleanup": cleanup,
        },
        "resume_checks": [{"api": api, "check": check} for api, check in RESUME_CHECKS],
        "source_status": "resume_check_required",
    }


def _commands(directory, snapshot, problems):
    observations = []
    for event in snapshot.events:
        if event.get("type") != "command_finished":
            continue
        payload = event["payload"]
        reference = payload.get("result_ref")
        command = _document(directory, reference, problems)
        if command is None:
            continue
        if command.get("command_id") != event.get("operation_id"):
            _problem(problems, reference["path"], "COMMAND_ID_MISMATCH")
            continue
        if command.get("status") == "exited" and command.get("returncode") == 0:
            continue
        observations.append(
            {
                "seq": event["seq"],
                "evaluation_role": payload.get("evaluation_role"),
                **{key: command.get(key) for key in ("command_id", "status", "returncode")},
                "references": [
                    reference,
                    *_references({key: command.get(key) for key in ("stdout_log", "stderr_log")}),
                ],
            }
        )
    return observations


def _recommendations(result):
    actions = []

    def add(action, message):
        actions.append({"action": action, "message": message})

    if not result["evidence_complete"]:
        add(
            "restore_evidence",
            "按证据问题列表从可信备份补全附件并重新核验摘要，保留数据库已提交结局。",
        )
    outcome, reason = result["outcome"], result["reason_code"] or ""
    if outcome == "ACCEPTED":
        add("inspect_acceptance", "查看固定 Task 的独立验收证据、基线和候选补丁。")
    elif outcome == "REJECTED":
        add(
            "inspect_candidate",
            "按已提交 reason code 查看候选编译或测试观察及原始日志，"
            "修正后以新的 verify-patch Run 独立验收。",
        )
    elif outcome in {"ERROR", "RECOVERY_FAILED"}:
        detail = (
            "核对模型配置、鉴权和网络"
            if reason.startswith("MODEL_")
            else "核对故障阶段的环境、输入身份和资源登记"
        )
        add(
            "inspect_failure",
            f"查看故障阶段的宿主命令和诊断附件，{detail}；"
            "保存已有候选，使用新的 Run 验证后续修复。",
        )
    elif outcome == "NOT_REPRODUCED":
        add(
            "review_baseline",
            "核对固定 base、F2P 失败签名和测试选择，按已提交基线观察调整 Task 后建立新的 Run。",
        )
    elif outcome in {"BUDGET_EXHAUSTED", "CANCELLED"}:
        add("new_run", "保存已有候选和证据；后续工作使用新的 Run 及显式预算。")
    elif outcome == "INCONCLUSIVE":
        add(
            "verify_candidate",
            "查看已提交验收原因、命令状态及证据；保留候选，"
            "使用完整 oracle 和显式预算建立新的 verify-patch Run。",
        )
    elif result["recovery"]["status"] == "checks_required":
        resources = result["recovery"]["resources"]
        if not resources["registry_present"]:
            add(
                "restore_resources",
                "恢复前从可信备份补全原 resources.json，实际 resume 将核对登记与目录归属。",
            )
        budget = result["budget"]
        exhausted = [
            name
            for name in (
                "remaining_steps",
                "remaining_tool_calls",
                "agent_remaining_seconds",
                "verification_remaining_seconds",
            )
            if budget[name] is not None and budget[name] <= 0
        ]
        if exhausted:
            add(
                "review_remaining_budget",
                "累计预算或时限已用尽；resume 按原限额停止模型或工具准入，"
                "并按剩余验收时间处理已有候选。",
            )
        else:
            add(
                "review_resume_checks",
                "已核验关闭的完整输入边界；恢复前查看下列检查，"
                "实际 resume 会核对源码、SDK、容器及累计预算。",
            )
    else:
        add(
            "preserve_run",
            "保存当前事实、原始证据和未验候选；查看恢复条件代码，后续执行使用新的 Run。",
        )
    return actions


def diagnose_run(directory: Path) -> dict:
    """返回一致性只读诊断；数据库读取失败沿用 StateReadError。"""
    directory = Path(directory).absolute()
    snapshot = read_events(directory, directory.name)
    if not snapshot.events:
        raise StateReadError("STATE_CORRUPT: 缺少已提交的 Run 事件")
    state, body, problems = committed_state(snapshot), None, []
    if snapshot.version and state["state"] in {"FINISHED", "INTERRUPTED"}:
        try:
            body = load_result(directory, snapshot, state)
        except StateReadError as exc:
            ref = state.get("result_ref") or {}
            _problem(problems, ref.get("path", "events.sqlite3"), exc)
    problems.extend(evidence_errors(directory, snapshot, body))
    row, resolved, resolved_ref = snapshot.run or {}, None, None
    if row.get("inputs_json"):
        frozen = _json(row["inputs_json"])
        resolved_ref = frozen["task_resolved"]
        resolved = _document(directory, resolved_ref, problems)
    budget = _budget(snapshot, resolved, problems, resolved_ref)
    recovery = _recovery(directory, snapshot, state, problems)
    commands = _commands(directory, snapshot, problems)
    counts = Counter(event.get("type", event.get("kind")) for event in snapshot.events)
    engine = state["engine"]
    for event in snapshot.events:
        if event.get("type") == "model_started" and event["payload"].get("engine"):
            engine = event["payload"]["engine"]
    engine = {key: (engine or {}).get(key) for key in ("kind", "model_name", "versions")}
    usage = _json(row["usage_json"]) if row else (body or {}).get("usage", {})
    agent = {
        "steps_used": row.get("steps_used", (body or {}).get("agent", {}).get("steps_used")),
        "tool_calls_used": row.get(
            "tool_calls_admitted", (body or {}).get("agent", {}).get("tool_calls_used")
        ),
        "agent_stop_reason": row.get(
            "agent_stop_reason", (body or {}).get("agent", {}).get("agent_stop_reason")
        ),
        "http_attempts": 0
        if engine["kind"] in {"none", "fake"}
        else (body or {}).get("agent", {}).get("http_attempts"),
        **{
            name: counts[name]
            for name in (
                "model_started",
                "model_finished",
                "tool_started",
                "tool_finished",
                "command_started",
                "command_finished",
            )
        },
    }
    unique = {(p["path"], p["code"], p["message"]): p for p in problems}
    if snapshot.version == 0:
        unique[("events.sqlite3", "LEGACY_AUDIT", "LEGACY_AUDIT")] = {
            "path": "events.sqlite3",
            "code": "LEGACY_AUDIT",
            "message": "历史审计按原格式展示",
        }
    result = {
        "schema": "repropatch.diagnosis.v1",
        **{
            key: state[key]
            for key in ("run_id", "task_id", "input_mode", "state", "outcome", "reason_code")
        },
        "failure_stage": snapshot.events[-1]["payload"].get("from")
        if state["state"] == "FINISHED" and state["outcome"] != "ACCEPTED"
        else None,
        "database_version": snapshot.version,
        "events_last_seq": snapshot.last_seq,
        "evidence_complete": not unique,
        "evidence_errors": list(unique.values()),
        "engine": engine,
        "agent": agent,
        "usage": usage,
        "unknown_token_fields": [key for key in TOKEN_FIELDS if usage.get(key) is None],
        "unknown_usage_turns": usage.get("unknown_turns"),
        "timing": _timing(snapshot, body),
        "budget": budget,
        "recovery": recovery,
        "command_observations": commands,
        "diagnostic_references": _references((body or {}).get("diagnostics", [])),
    }
    result["recommendations"] = _recommendations(result)
    return result


def diagnostics_markdown(result: dict) -> str:
    """呈现终态、观察和恢复前置条件，原生模型内容保持封装。"""
    agent, usage = result["agent"], result["usage"]
    recovery, budget = result["recovery"], result["budget"]
    checkpoint, resources = recovery["checkpoint"], recovery["resources"]
    lines = [
        f"# ReproPatch 运行诊断 {_text(result['run_id'])}",
        "",
        f"阶段：{_text(result['state'])}；结局：{_text(result['outcome'])}；原因：{_text(result['reason_code'])}",
        f"失败阶段：{_text(result['failure_stage'])}；事件截止：{result['events_last_seq']}",
        f"证据完整：{_text(result['evidence_complete'])}",
        "",
        "## 用量与时序",
        "",
        f"引擎：{_text(result['engine']['kind'])}；模型：{_text(result['engine']['model_name'])}",
        f"模型步骤：{_text(agent['steps_used'])}；"
        f"开始 / 完成：{agent['model_started']} / {agent['model_finished']}",
        f"准入工具：{_text(agent['tool_calls_used'])}；"
        f"开始 / 完成：{agent['tool_started']} / {agent['tool_finished']}",
        f"宿主命令开始 / 完成：{agent['command_started']} / {agent['command_finished']}；"
        f"HTTP 次数：{_text(agent['http_attempts'])}",
        "Token 输入 / 输出 / 合计：" + " / ".join(_text(usage.get(key)) for key in TOKEN_FIELDS),
        f"未知 Token 项：{_text(', '.join(result['unknown_token_fields']) or '无')}；"
        f"未知用量轮数：{_text(result['unknown_usage_turns'])}；"
        f"合成用量：{_text(usage.get('synthetic'))}",
        f"已知 Token 小计：{_text(usage.get('known_tokens'))}",
        "",
        "阶段耗时依据已提交事件时间；开放阶段展示截至最后事件的观察跨度。",
        "",
        "| 阶段 | seq 起止 | 毫秒 | 已关闭 |",
        "| --- | --- | ---: | --- |",
    ]
    for phase in result["timing"]["phases"]:
        lines.append(
            f"| {_text(phase['stage'])} | {phase['first_seq']} / {phase['last_seq']} | "
            f"{_text(phase['elapsed_ms'])} | {_text(phase['closed'])} |"
        )
    for problem in result["evidence_errors"]:
        lines.append(
            f"证据问题：{_text(problem['path'])}（{_text(problem['code'])}；{_text(problem['message'])}）"
        )
    if result["command_observations"]:
        lines.extend(
            [
                "",
                "## 命令观察",
                "",
                "| 评估 | 命令 ID | 状态 / 退出码 | 证据 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for command in result["command_observations"]:
            refs = ", ".join(str(ref["path"]) for ref in command["references"])
            lines.append(
                f"| {_text(command['evaluation_role'])} | {_text(command['command_id'])} | "
                f"{_text(command['status'])} / {_text(command['returncode'])} | {_text(refs)} |"
            )
    for reference in result["diagnostic_references"]:
        lines.append(f"诊断附件：{_text(reference['path'])}")
    lines.extend(
        [
            "",
            "## Checkpoint 与恢复",
            "",
            f"恢复条件：{_text(recovery['status'])}；条件代码：{_text(recovery['reason_code'])}",
            f"Checkpoint：{_text(checkpoint['checkpoint_id'])}；已核验：{_text(checkpoint['verified'])}；片段关闭：{_text(checkpoint['closed'])}",
            f"源码指纹：{_text(checkpoint['source_tree_sha256'])}；当前源码：待 resume 检查",
            f"资源登记文件存在：{_text(resources['registry_present'])}；已登记容器：{len(resources['containers'])}",
            f"已提交清理观察：{_text(resources['cleanup'])}",
            f"原始期限：{_text(budget['deadline_at'])}；预算观察时间：{_text(budget['observed_at'])}",
            f"剩余步骤 / 工具：{_text(budget['remaining_steps'])} / "
            f"{_text(budget['remaining_tool_calls'])}",
            "剩余 wall / 模型阶段 / 独立验收秒数："
            f"{_text(budget['wall_remaining_seconds'])} / "
            f"{_text(budget['agent_remaining_seconds'])} / "
            f"{_text(budget['verification_remaining_seconds'])}",
            "",
            "实际 resume 执行的检查：",
            "",
        ]
    )
    for check in recovery["resume_checks"]:
        lines.append(f"- {_text(check['api'])}：{_text(check['check'])}")
    lines.extend(["", "## 操作建议", ""])
    lines.extend(f"- {_text(action['message'])}" for action in result["recommendations"])
    return "\n".join(lines) + "\n"
