"""从已提交事件和有界证据生成报告；查询不运行模型、Git 或仓库代码。"""

import hashlib
import html
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .artifacts import MAX_AUDIT_BYTES, AuditBudget, EvidenceRef, read_regular
from .errors import ArtifactExportError, ReproPatchError, StateReadError
from .events import OUTCOMES, TRANSITIONS, _json, encode_json, read_events


def committed_state(snapshot):
    state = {
        "run_id": snapshot.run_id,
        "task_id": None,
        "input_mode": None,
        "state": "CREATED",
        "outcome": None,
        "reason_code": None,
        "engine": None,
        "result_ref": None,
    }
    if snapshot.version == 0:
        state["state"] = "LEGACY"
        for event in snapshot.events:
            payload = event["payload"]
            if event["kind"] == "run_started":
                state.update(task_id=payload.get("task_id"), input_mode=payload.get("input_mode"))
            elif event["kind"] == "run_finished":
                state.update(
                    outcome=payload.get("outcome"),
                    reason_code=payload.get("reason_code"),
                    legacy_status=payload.get("status"),
                )
        return state
    try:
        for event in snapshot.events:
            kind, payload = event["type"], event["payload"]
            if state["state"] == "FINISHED":
                raise ValueError("终态之后仍有事件")
            if event["seq"] == 1 and kind != "run_created":
                raise ValueError("缺少创建事件")
            if kind == "run_created":
                if event["seq"] != 1:
                    raise ValueError("重复创建事件")
                state.update(
                    task_id=payload["task_id"],
                    input_mode=payload["input_mode"],
                    engine=payload["engine"],
                )
            elif kind == "state_changed":
                source, target = payload["from"], payload["to"]
                if source != state["state"] or target not in TRANSITIONS[source]:
                    raise ValueError("非法阶段转移")
                if target == "REPAIRING" and state["input_mode"] != "run":
                    raise ValueError("纯验证进入模型阶段")
                state["state"] = target
                if target == "FINISHED":
                    if payload["outcome"] not in OUTCOMES or not payload["reason_code"]:
                        raise ValueError("终态结局无效")
                    state.update(
                        outcome=payload["outcome"],
                        reason_code=payload["reason_code"],
                        result_ref=payload["result_ref"],
                    )
        if snapshot.version == 2:
            row = snapshot.run
            state.update(
                {
                    key: row[key]
                    for key in (
                        "state",
                        "outcome",
                        "reason_code",
                        "steps_used",
                        "tool_calls_admitted",
                        "segment_open",
                        "last_checkpoint_id",
                        "recovery_attempt",
                        "created_at",
                        "deadline_at",
                        "task_sha256",
                        "base_commit",
                        "image_id",
                        "agent_stop_reason",
                    )
                }
            )
            state["usage"] = _json(row["usage_json"])
        return state
    except (KeyError, TypeError, ValueError) as exc:
        raise StateReadError("STATE_CORRUPT: 事件不能构成一致的 Run 阶段") from exc


def compact_result(report):
    """最终事实保留完整观察与引用，过长命令预览由原始日志承载。"""
    body = json.loads(encode_json(report))
    for key in ("trace", "artifacts_complete", "command_error", "evidence_errors"):
        body.pop(key, None)
    if len(encode_json(body)) > 1024 * 1024:

        def omit(value):
            if isinstance(value, dict):
                if "argv" in value and "command_id" in value:
                    for key in ("output", "stdout", "stderr"):
                        value[key] = ""
                    value["truncated"] = True
                for child in value.values():
                    omit(child)
            elif isinstance(value, list):
                for child in value:
                    omit(child)

        omit(body)
        body["report_previews_omitted"] = True
    return body


def _reference(name, content):
    return EvidenceRef(name, hashlib.sha256(content).hexdigest(), len(content))


def load_result(directory, snapshot, state):
    if state["state"] == "INTERRUPTED":
        try:
            return paused_result(directory, snapshot, state)
        except (ReproPatchError, OSError, ValueError, TypeError, KeyError) as exc:
            raise StateReadError("CHECKPOINT_CORRUPT: 暂停报告的输入边界无法核验") from exc
    if state["state"] != "FINISHED":
        raise StateReadError("RUN_INCOMPLETE: Run 尚未提交最终事实")
    try:
        reference = EvidenceRef(**state["result_ref"])
        body = _json(reference.read(directory, limit=MAX_AUDIT_BYTES))
        if not isinstance(body, dict) or any(
            body[key] != state[key]
            for key in ("run_id", "task_id", "input_mode", "state", "outcome", "reason_code")
        ):
            raise ValueError("报告事实与终态事件不符")
        if body["events_last_seq"] != snapshot.last_seq:
            raise ValueError("报告事件截止序号不符")
        if snapshot.version == 2:
            row = snapshot.run
            if (
                body["agent"]["steps_used"] != row["steps_used"]
                or body["agent"]["tool_calls_used"] != row["tool_calls_admitted"]
                or body["agent"]["agent_stop_reason"] != row["agent_stop_reason"]
                or body["usage"] != _json(row["usage_json"])
                or body["timing"]["deadline_at"] != row["deadline_at"]
            ):
                raise ValueError("报告预算或期限与权威状态不符")
        return body
    except (ReproPatchError, ValueError, TypeError, KeyError) as exc:
        raise StateReadError("EVIDENCE_UNVERIFIABLE: 最终事实附件无法核验") from exc


def paused_result(directory, snapshot, state):
    """暂停报告仅由已提交 Checkpoint、累计状态与清理观察派生，不伪造终态。"""
    from .recovery import read_checkpoint

    if snapshot.run["segment_open"] or snapshot.run["last_checkpoint_id"] is None:
        raise StateReadError("CHECKPOINT_CORRUPT: 暂停没有关闭的输入边界")
    manifest, reference = read_checkpoint(directory, snapshot)
    frozen = _json(snapshot.run["inputs_json"])
    resolved = _json(EvidenceRef(**frozen["task_resolved"]).read(directory, limit=MAX_AUDIT_BYTES))
    baseline = _json(EvidenceRef(**manifest["baseline"]).read(directory, limit=MAX_AUDIT_BYTES))
    engines = [
        event["payload"]["engine"] for event in snapshot.events if event["type"] == "model_started"
    ]
    cleanups = [event for event in snapshot.events if event["type"] == "cleanup_finished"]
    cleanup = (
        cleanups[-1]["payload"]
        if cleanups
        else {
            "active_code_stopped": False,
            "workspace_retained": True,
            "errors": ["PAUSE_CLEANUP_UNCONFIRMED"],
        }
    )
    return {
        "schema_version": 1,
        "run_id": snapshot.run_id,
        "task_id": state["task_id"],
        "input_mode": state["input_mode"],
        "state": "INTERRUPTED",
        "outcome": None,
        "reason_code": None,
        "status": "interrupted",
        "paused": True,
        "checkpoint": {"checkpoint_id": manifest["checkpoint_id"], "manifest": reference},
        "artifact_directory": str(directory),
        "engine": engines[-1] if engines else state["engine"],
        "workspace_directory": str(Path(resolved["workspace_root"]) / snapshot.run_id),
        "isolated": baseline["isolated"],
        "provenance": manifest["input_fingerprints"],
        "agent": {
            "agent_stop_reason": None,
            "steps_used": snapshot.run["steps_used"],
            "tool_calls_used": snapshot.run["tool_calls_admitted"],
            "http_attempts": 0 if snapshot.run["engine_kind"] == "fake" else None,
        },
        "usage": _json(snapshot.run["usage_json"]),
        "cleanup": cleanup,
        "deadline_at": snapshot.run["deadline_at"],
    }


def evidence_errors(directory, snapshot, body=None):
    errors = []
    seen = set()
    pending = [event["payload"] for event in snapshot.events]
    if body is not None:
        pending.append(body)
    while pending:
        value = pending.pop()
        if isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, dict):
            if set(value) == {"path", "sha256", "size_bytes"}:
                identity = encode_json(value)
                if identity in seen:
                    continue
                seen.add(identity)
                try:
                    reference = EvidenceRef(**value)
                    content = reference.read(directory, limit=MAX_AUDIT_BYTES)
                    # 只展开宿主结构化结果；原生模型和外部 trace 始终是不透明附件。
                    if (
                        reference.path.startswith("evidence/")
                        and reference.path.endswith((".result.json", "/evaluation.json"))
                    ) or reference.path.startswith("agent/tool-results/"):
                        pending.append(_json(content))
                    elif (
                        reference.path.startswith("checkpoints/")
                        and reference.path.endswith("/manifest.json")
                    ) or reference.path == "execution-config.json":
                        pending.append(_json(content))
                except (ReproPatchError, OSError, ValueError, TypeError, RecursionError) as exc:
                    errors.append(
                        {
                            "path": value.get("path"),
                            "code": "EVIDENCE_UNVERIFIABLE",
                            "message": str(exc).split(":", 1)[0],
                        }
                    )
            else:
                pending.extend(value.values())
    return errors


def _presentation(body, snapshot, trace, errors, *, complete):
    return {
        **body,
        "events_last_seq": snapshot.last_seq,
        "trace": asdict(trace) if trace is not None else None,
        "artifacts_complete": complete and not errors,
        "evidence_errors": errors,
    }


def _text(value):
    if value is None:
        return "未知"
    if isinstance(value, bool):
        return "是" if value else "否"
    value = "".join(
        char if ord(char) >= 32 and not 127 <= ord(char) < 160 else f"\\x{ord(char):02x}"
        for char in str(value)
    )
    value = html.escape(value).replace("|", "&#124;").replace("`", "&#96;")
    for char in "\\*_[]()!#{}":
        value = value.replace(char, "\\" + char)
    return value


def markdown(report):
    if report.get("paused"):
        return (
            f"# ReproPatch {_text(report['run_id'])}\n\n"
            f"状态：INTERRUPTED；paused=true；结局：未知\n\n"
            f"Checkpoint：{report['checkpoint']['checkpoint_id']}\n"
            f"累计模型步骤：{report['agent']['steps_used']}；工具：{report['agent']['tool_calls_used']}\n"
            f"执行清理确认：{_text(report['cleanup']['active_code_stopped'])}\n"
            f"原始期限：{_text(report['deadline_at'])}\n\n暂停不表示补丁通过。\n"
        )
    engine = report["engine"]
    agent = report["agent"]
    usage = report["usage"]
    lines = [
        f"# ReproPatch {_text(report['run_id'])}",
        "",
        f"任务：{_text(report['task_id'])}",
        f"入口：{_text(report['input_mode'])}",
        f"结局：**{_text(report['outcome'])}**",
        f"原因：{_text(report['reason_code'])}",
        f"执行引擎：{_text(engine['kind'])}",
        f"模型：{_text(engine['model_name'])}",
        f"Docker 隔离：{_text(report.get('isolated'))}",
        f"基线 commit：{_text(report['provenance']['base_commit'])}",
        f"镜像：{_text(report['provenance']['image_id'])}",
        f"耗时：{report['timing']['elapsed_ms'] / 1000:.3f} 秒",
        f"模型步骤：{agent['steps_used']}；准入工具：{agent['tool_calls_used']}",
        f"模型停止原因：{_text(agent['agent_stop_reason'])}",
        f"HTTP 请求次数：{_text(agent['http_attempts'])}",
        f"Token 输入 / 输出 / 合计：{_text(usage['input_tokens'])} / "
        f"{_text(usage['output_tokens'])} / {_text(usage['total_tokens'])}",
        f"合成用量：{_text(usage['synthetic'])}；费用：未知",
        f"执行清理确认：{_text(report['cleanup']['active_code_stopped'])}",
        f"产物完整：{_text(report['artifacts_complete'])}",
        f"事件截止序号：{report['events_last_seq']}",
        "",
    ]
    if report["producer"]["name"] is not None:
        lines.append(f"外部来源标签（未认证）：{_text(report['producer']['name'])}")
    if report["producer"]["trace"] is not None:
        lines.append("外部轨迹：未验证的 opaque 附件，不作为测试或用量证据。")
    lines.extend(["", "| 评估 | 测试 | 观察 | 证据 |", "| --- | --- | --- | --- |"])
    statuses = {
        "passed": "通过",
        "failed": "失败",
        "not_run": "未运行",
        "skipped": "跳过",
        "timed_out": "超时",
        "invalid": "证据无效",
        "crashed": "崩溃",
    }
    for evaluation in report.get("evaluations", []):
        for test in evaluation.get("tests", []):
            result = test.get("result")
            lines.append(
                f"| {_text(evaluation['evaluation_role'])} | {_text(test['name'])} | "
                f"{_text(statuses.get(test['observed_status'], test['observed_status']))} | "
                f"{_text(result['path'] if result else None)} |"
            )
    lines.extend(
        ["", "| 评估 | 命令 | 状态 | 退出码 | stderr |", "| --- | --- | --- | ---: | --- |"]
    )
    for evaluation in report.get("evaluations", []):
        for command in evaluation.get("commands", []):
            stderr = command.get("stderr_log")
            lines.append(
                f"| {_text(evaluation['evaluation_role'])} | {_text(' '.join(command['argv']))} | "
                f"{_text(command['status'])} | {_text(command['returncode'])} | "
                f"{_text(stderr['path'] if stderr else None)} |"
            )
    if report.get("error"):
        lines.extend(["", f"错误：{_text(report['error'])}"])
    for error in report["cleanup"]["errors"]:
        lines.append(f"清理诊断：{_text(error)}")
    for error in report.get("evidence_errors", []):
        lines.append(f"证据不可核查：{_text(error['path'])}")
    for ref in report["diagnostics"]:
        lines.append(f"诊断附件：{_text(ref['path'])}")
    trace = report["trace"]
    lines.extend(["", f"领域轨迹：{_text(trace['path'] if trace else None)}", ""])
    lines.extend(_text(item) for item in report["limitations"])
    return "\n".join(lines) + "\n"


def export_report(directory, snapshot=None, *, budget=None):
    """逐个原子导出；失败只属于本次导出，不能更改已提交的结局。"""
    directory = Path(directory)
    snapshot = snapshot or read_events(directory, directory.name)
    state = committed_state(snapshot)
    body = load_result(directory, snapshot, state)
    errors = evidence_errors(directory, snapshot, body)
    budget = budget or AuditBudget(directory)
    failed = []
    written = {}

    def write(name, content):
        try:
            budget.write(name, content, emergency=True)
            written[name] = asdict(_reference(name, content))
            return True
        except (OSError, ReproPatchError):
            failed.append(name)
            return False

    trace_bytes = snapshot.jsonl()
    trace = _reference("events.jsonl", trace_bytes) if write("events.jsonl", trace_bytes) else None
    report = _presentation(body, snapshot, trace, errors, complete=not failed)
    write("report.json", encode_json(report) + b"\n")
    write("report.md", markdown(report).encode("utf-8"))
    index = {
        "schema_version": 1,
        "run_id": snapshot.run_id,
        "source": {
            "event_format": 1,
            "database_version": snapshot.version,
            "database": "events.sqlite3",
        },
        "origin": snapshot.events[0]["payload"],
        "export_metadata": {
            "exported_through_seq": snapshot.last_seq if trace is not None else None,
            "exported_at": datetime.now(UTC).isoformat(),
            "artifacts": dict(written),
            "failed": list(failed),
        },
    }
    write("run.json", encode_json(index) + b"\n")
    if failed:
        report["artifacts_complete"] = False
        # Markdown 或索引失败时，仍尽力让可写的 JSON 显示真实导出状态。
        write("report.json", encode_json(report) + b"\n")
    report["command_error"] = (
        "ARTIFACT_EXPORT_FAILED" if failed else "EVIDENCE_UNVERIFIABLE" if errors else None
    )
    return report


def inspect_run(directory):
    directory = Path(directory)
    snapshot = read_events(directory, directory.name)
    state = committed_state(snapshot)
    result = {
        **{key: value for key, value in state.items() if key != "result_ref"},
        "event_format": 0 if snapshot.version == 0 else 1,
        "database_version": snapshot.version,
        "events_last_seq": snapshot.last_seq,
        "artifact_dir": str(directory),
        "artifacts_complete": False,
        "evidence_complete": False,
        "last_event": (
            {
                key: snapshot.events[-1][key]
                for key in ("seq", "timestamp", "type" if snapshot.version in (1, 2) else "kind")
            }
            if snapshot.events
            else None
        ),
        "errors": [],
    }
    if snapshot.version == 0:
        result["errors"].append("LEGACY_AUDIT: 历史 kind 记录按原格式查询，不升级为新事件")
        return result
    body = None
    if state["state"] in {"FINISHED", "INTERRUPTED"}:
        try:
            body = load_result(directory, snapshot, state)
        except StateReadError as exc:
            result["errors"].append(str(exc))
    errors = evidence_errors(directory, snapshot, body)
    result["evidence_errors"] = errors
    result["evidence_complete"] = not errors and (
        body is not None or state["state"] not in {"FINISHED", "INTERRUPTED"}
    )
    if body is None:
        return result
    trace = _reference("events.jsonl", snapshot.jsonl())
    expected = _presentation(body, snapshot, trace, errors, complete=True)
    try:
        index = _json(read_regular(directory / "run.json", limit=MAX_AUDIT_BYTES)[0])
        metadata = index["export_metadata"]
        if (
            index["schema_version"] != 1
            or index["run_id"] != snapshot.run_id
            or metadata["exported_through_seq"] != snapshot.last_seq
            or metadata["failed"]
        ):
            raise ValueError("导出索引滞后或不完整")
        required = {
            "events.jsonl": snapshot.jsonl(),
            "report.json": encode_json(expected) + b"\n",
            "report.md": markdown(expected).encode("utf-8"),
        }
        for name, content in required.items():
            ref = EvidenceRef(**metadata["artifacts"][name])
            if ref.path != name or ref.read(directory, limit=MAX_AUDIT_BYTES) != content:
                raise ValueError(f"派生产物不一致：{name}")
        result["artifacts_complete"] = result["evidence_complete"]
    except (OSError, ReproPatchError, ValueError, KeyError, TypeError) as exc:
        result["errors"].append(f"ARTIFACTS_INCOMPLETE: {str(exc).split(':', 1)[0]}")
    result["agent"] = body["agent"]
    result["usage"] = body["usage"]
    result["cleanup"] = body["cleanup"]
    if body.get("paused"):
        result["paused"] = True
        result["checkpoint"] = body["checkpoint"]
        result["artifacts_complete"] &= body["cleanup"]["active_code_stopped"]
    return result


def historical_report(directory, snapshot):
    """展示原格式历史报告，明确不提供重建或恢复承诺。"""
    state = committed_state(snapshot)
    try:
        body = _json(read_regular(Path(directory) / "report.json", limit=MAX_AUDIT_BYTES)[0])
        if body["run_id"] != snapshot.run_id:
            raise ValueError("历史报告身份不符")
        if state["outcome"] is not None and body.get("outcome") != state["outcome"]:
            raise ValueError("历史报告与已记录结局不符")
        return {"event_format": 0, "authority": state, "historical_report": body}
    except (OSError, ReproPatchError, ValueError, KeyError, TypeError) as exc:
        raise ArtifactExportError("LEGACY_REPORT_UNAVAILABLE: 无法核验历史报告") from exc
