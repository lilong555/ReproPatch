"""只读领域轨迹与显式 JSONL 导出；不恢复控制器或执行历史动作。"""

import os
import uuid
from pathlib import Path

from .errors import InfrastructureError, StateReadError
from .events import encode_json, read_events
from .reports import _text, committed_state, evidence_errors, load_result

DETAILS = frozenset(
    {
        "from",
        "to",
        "outcome",
        "reason_code",
        "reason",
        "task_id",
        "status",
        "steps_used",
        "tool_calls_used",
        "tool_calls_admitted",
        "counters",
        "usage",
        "cumulative_usage",
        "success",
        "recovery_attempt",
        "source_state",
        "checkpoint_id",
        "evaluation_role",
        "evaluation_id",
        "verdict",
        "self_check_passed",
        "name",
        "provider_call_id",
        "argv",
        "cwd",
        "container_id",
        "active_code_stopped",
        "workspace_retained",
        "errors",
        "verification_eligible",
        "cleanup_confirmed",
        "cleanup_error",
        "resource_type",
        "purpose",
        "pause_after_step",
        "takeover",
    }
)
OPAQUE = frozenset(
    {
        "encrypted_content",
        "reasoning",
        "instructions",
        "input",
        "output",
        "content",
        "arguments",
        "text",
        "raw_usage",
    }
)


def _visible(value):
    if isinstance(value, dict):
        return {key: _visible(child) for key, child in value.items() if key not in OPAQUE}
    if isinstance(value, list):
        return [_visible(child) for child in value]
    return value


def _references(value):
    """只收集宿主引用，不打开或展开模型原生内容。"""
    result = []
    pending = [value]
    seen = set()
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            if set(current) == {"path", "sha256", "size_bytes"}:
                identity = encode_json(current)
                if identity not in seen:
                    result.append(current)
                    seen.add(identity)
            else:
                pending.extend(reversed(list(current.values())))
        elif isinstance(current, list):
            pending.extend(reversed(current))
    return result


def _read(directory):
    directory = Path(directory).absolute()
    snapshot = read_events(directory, directory.name)
    if not snapshot.events:
        raise StateReadError("STATE_CORRUPT: 缺少已提交的 Run 事件")
    state = committed_state(snapshot)
    body, problems = None, []
    if snapshot.version != 0 and state["state"] in {"FINISHED", "INTERRUPTED"}:
        try:
            body = load_result(directory, snapshot, state)
        except StateReadError as exc:
            problems.append(
                {
                    "path": "events.sqlite3",
                    "code": "EVIDENCE_UNVERIFIABLE",
                    "message": str(exc).split(":", 1)[0],
                }
            )
    problems.extend(evidence_errors(directory, snapshot, body))
    return snapshot, state, problems


def replay_trace(directory):
    """查看既有事件和引用；未完成、缺失附件或旧格式都不提升为执行成功。"""
    snapshot, state, problems = _read(directory)
    timeline = []
    for event in snapshot.events:
        payload = event["payload"]
        timeline.append(
            {
                **{
                    key: event.get(key)
                    for key in ("seq", "timestamp", "step_id", "tool_call_id", "operation_id")
                },
                "type": event.get("type", event.get("kind")),
                "details": {
                    key: _visible(value) for key, value in payload.items() if key in DETAILS
                },
                "references": _references(payload),
            }
        )
    return {
        "schema_version": 1,
        "mode": "trace",
        "run_id": snapshot.run_id,
        "task_id": state["task_id"],
        "state": state["state"],
        "outcome": state["outcome"],
        "reason_code": state["reason_code"],
        "database_version": snapshot.version,
        "event_format": 1 if snapshot.version else None,
        "events_last_seq": snapshot.last_seq,
        "evidence_complete": not problems if snapshot.version else None,
        "evidence_errors": problems,
        "timeline": timeline,
        "limitations": ["只读观察不构成恢复或重新验收；原生模型内容和外部 trace 不展开。"]
        + (
            ["历史 kind 审计按原格式展示，不升级为新事件或可恢复状态。"]
            if snapshot.version == 0
            else []
        ),
    }


def trace_markdown(trace):
    lines = [
        f"# ReproPatch 只读轨迹 {_text(trace['run_id'])}",
        "",
        f"阶段：{_text(trace['state'])}；结局：{_text(trace['outcome'])}",
        f"事件截止：{trace['events_last_seq']}；证据完整：{_text(trace['evidence_complete'])}",
        "",
        "| seq | 事件 | step / tool | 观察 | 引用 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in trace["timeline"]:
        details = "; ".join(f"{key}={value}" for key, value in item["details"].items())
        references = ", ".join(str(ref["path"]) for ref in item["references"])
        lines.append(
            f"| {item['seq']} | {_text(item['type'])} | "
            f"{_text(item['step_id'])} / {_text(item['tool_call_id'])} | "
            f"{_text(details)} | {_text(references)} |"
        )
    for problem in trace["evidence_errors"]:
        lines.append(f"证据不可核查：{_text(problem['path'])}（{_text(problem['message'])}）")
    lines.extend(["", *trace["limitations"], ""])
    return "\n".join(lines)


def _write_new_trace(directory, output, content):
    """新文件独占发布，既有产物及原 Run 目录均不覆盖。"""
    target = Path(output).absolute()
    if any(ord(char) < 32 or ord(char) == 127 for char in str(target)):
        raise InfrastructureError("TRACE_OUTPUT_INVALID: 导出路径不能包含控制字符")
    if any(path.is_symlink() for path in (target, *target.parents)):
        raise InfrastructureError("TRACE_OUTPUT_INVALID: 导出路径不能包含链接")
    target = Path(os.path.abspath(target))
    directory = Path(os.path.abspath(directory))
    if target == directory or directory in target.parents:
        raise InfrastructureError("TRACE_OUTPUT_INVALID: 导出位置必须在原 Run 目录之外")
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    descriptor = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = ".repropatch-trace-" + uuid.uuid4().hex
    created = False
    try:
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=descriptor,
        )
        created = True
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(
            temporary,
            target.name,
            src_dir_fd=descriptor,
            dst_dir_fd=descriptor,
            follow_symlinks=False,
        )
        os.fsync(descriptor)
    finally:
        if created:
            os.unlink(temporary, dir_fd=descriptor)
        os.close(descriptor)


def export_trace(directory, output=None):
    """输出一个已提交的一致性事件前缀；缺失附件仍可导出，并另报不可核查。"""
    directory = Path(directory).absolute()
    snapshot, _, problems = _read(directory)
    content = snapshot.jsonl()
    if output is not None:
        _write_new_trace(directory, output, content)
    return content, problems
