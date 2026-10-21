"""SQLite 领域审计；JSONL 仅从已提交的一致性快照导出。"""

import json
import os
import re
import sqlite3
import stat
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .artifacts import MAX_AUDIT_BYTES, EvidenceRef
from .errors import StateReadError, StateWriteError
from .resources import RunLock

TRANSITIONS = {
    "CREATED": {"PREPARING", "FINISHED"},
    "PREPARING": {"REPRODUCING", "FINISHED"},
    "REPRODUCING": {"REPAIRING", "VERIFYING", "FINISHED"},
    "REPAIRING": {"VERIFYING", "INTERRUPTED", "FINISHED"},
    "VERIFYING": {"FINISHED"},
    "INTERRUPTED": {"RECOVERING", "FINISHED"},
    "RECOVERING": {"REPAIRING", "FINISHED"},
    "FINISHED": set(),
}
OUTCOMES = {
    "ACCEPTED",
    "REJECTED",
    "NOT_REPRODUCED",
    "INCONCLUSIVE",
    "BUDGET_EXHAUSTED",
    "ERROR",
    "CANCELLED",
    "RECOVERY_FAILED",
}
SCHEMA = """
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    input_mode TEXT NOT NULL CHECK (input_mode IN ('run', 'verify-patch')),
    engine_kind TEXT NOT NULL CHECK (engine_kind IN ('agents-sdk', 'fake', 'none')),
    state TEXT NOT NULL CHECK (state IN (
        'CREATED', 'PREPARING', 'REPRODUCING', 'REPAIRING',
        'VERIFYING', 'INTERRUPTED', 'RECOVERING', 'FINISHED')),
    outcome TEXT CHECK (outcome IN (
        'ACCEPTED', 'REJECTED', 'NOT_REPRODUCED', 'INCONCLUSIVE',
        'BUDGET_EXHAUSTED', 'ERROR', 'CANCELLED', 'RECOVERY_FAILED')),
    reason_code TEXT,
    agent_stop_reason TEXT,
    created_at TEXT NOT NULL,
    deadline_at TEXT NOT NULL,
    task_sha256 TEXT,
    base_commit TEXT,
    image_id TEXT,
    inputs_json TEXT,
    steps_used INTEGER NOT NULL DEFAULT 0 CHECK (steps_used >= 0),
    tool_calls_admitted INTEGER NOT NULL DEFAULT 0 CHECK (tool_calls_admitted >= 0),
    usage_json TEXT,
    segment_open INTEGER NOT NULL DEFAULT 0 CHECK (segment_open IN (0, 1)),
    last_checkpoint_id INTEGER REFERENCES checkpoints(checkpoint_id),
    recovery_attempt INTEGER NOT NULL DEFAULT 0 CHECK (recovery_attempt >= 0),
    updated_at TEXT NOT NULL,
    CHECK ((state = 'FINISHED' AND outcome IS NOT NULL AND reason_code IS NOT NULL)
        OR (state <> 'FINISHED' AND outcome IS NULL)),
    CHECK ((input_mode = 'run' AND engine_kind IN ('agents-sdk', 'fake'))
        OR (input_mode = 'verify-patch' AND engine_kind = 'none')),
    CHECK (state <> 'REPAIRING' OR input_mode = 'run'),
    CHECK (state NOT IN ('REPRODUCING', 'REPAIRING', 'VERIFYING')
        OR (task_sha256 IS NOT NULL AND base_commit IS NOT NULL
            AND image_id IS NOT NULL AND inputs_json IS NOT NULL))
);
CREATE TABLE events (
    seq INTEGER PRIMARY KEY, timestamp TEXT NOT NULL,
    type TEXT NOT NULL, envelope_json TEXT NOT NULL
);
CREATE TABLE checkpoints (
    checkpoint_id INTEGER PRIMARY KEY,
    event_seq INTEGER NOT NULL UNIQUE REFERENCES events(seq),
    step_id INTEGER NOT NULL CHECK (step_id >= 0),
    manifest_ref_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
RUN_COLUMNS = (
    "run_id",
    "input_mode",
    "engine_kind",
    "state",
    "outcome",
    "reason_code",
    "agent_stop_reason",
    "created_at",
    "deadline_at",
    "task_sha256",
    "base_commit",
    "image_id",
    "inputs_json",
    "steps_used",
    "tool_calls_admitted",
    "usage_json",
    "segment_open",
    "last_checkpoint_id",
    "recovery_attempt",
    "updated_at",
)

RUN_ID = re.compile(r"[0-9a-f]{32}")
EVENT_TYPES = {
    "run_created",
    "state_changed",
    "inputs_frozen",
    "resource_registered",
    "baseline_finished",
    "model_started",
    "model_finished",
    "tool_batch_admitted",
    "tool_started",
    "tool_finished",
    "command_started",
    "command_finished",
    "agent_stopped",
    "verification_finished",
    "cleanup_finished",
    "checkpoint_committed",
    "recovery_started",
    "recovery_finished",
}
ENVELOPE_KEYS = {
    "schema_version",
    "seq",
    "run_id",
    "timestamp",
    "type",
    "step_id",
    "tool_call_id",
    "operation_id",
    "payload",
}


def encode_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True).encode("utf-8")


def _json(value):
    def unique(items):
        result = {}
        for key, child in items:
            if key in result:
                raise ValueError("JSON 含重复键")
            result[key] = child
        return result

    def invalid(_):
        raise ValueError("JSON 含非有限数值")

    return json.loads(value, object_pairs_hook=unique, parse_constant=invalid)


def validate_run_id(run_id):
    if not isinstance(run_id, str) or RUN_ID.fullmatch(run_id) is None:
        raise ValueError("RUN_ID_INVALID: Run ID 必须是 32 位小写十六进制")
    return run_id


def run_directory(root, run_id):
    validate_run_id(run_id)
    path = Path(root).absolute() / run_id
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise StateReadError("RUN_PATH_INVALID: Run 路径不能包含链接")
    if not path.is_dir():
        raise StateReadError("RUN_NOT_FOUND: 指定根目录中没有该 Run")
    return path


def _validate_envelope(event, run_id, seq):
    if (
        not isinstance(event, dict)
        or set(event) != ENVELOPE_KEYS
        or type(event["schema_version"]) is not int
        or event["schema_version"] != 1
        or type(event["seq"]) is not int
        or event["seq"] != seq
        or event["run_id"] != run_id
        or event["type"] not in EVENT_TYPES
        or not isinstance(event["payload"], dict)
    ):
        raise ValueError("事件信封或顺序无效")
    timestamp = datetime.fromisoformat(event["timestamp"])
    if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
        raise ValueError("事件时间不是 UTC")
    step, tool, operation = (event[name] for name in ("step_id", "tool_call_id", "operation_id"))
    if step is not None and (type(step) is not int or step < 1):
        raise ValueError("模型步骤无效")
    if tool is not None and (step is None or re.fullmatch(rf"s{step:06d}\.t0[1-8]", tool) is None):
        raise ValueError("工具调用身份无效")
    if operation is not None:
        validate_run_id(operation)


@dataclass(frozen=True)
class EventSnapshot:
    run_id: str
    version: int
    events: tuple
    run: dict | None = None
    checkpoints: tuple = ()

    @property
    def last_seq(self):
        return self.events[-1]["seq"] if self.events else 0

    def jsonl(self):
        if self.version not in (1, 2):
            raise StateReadError("EVENT_FORMAT_UNSUPPORTED: 历史 kind 审计不能导出为新信封")
        return b"".join(encode_json(event) + b"\n" for event in self.events)


def _usage(value):
    if (
        not isinstance(value, dict)
        or not {"input_tokens", "output_tokens", "total_tokens", "synthetic"} <= value.keys()
    ):
        raise ValueError("用量不是原始字段聚合")
    for name in ("input_tokens", "output_tokens", "total_tokens"):
        if value[name] is not None and (type(value[name]) is not int or value[name] < 0):
            raise ValueError("用量字段无效")
    if type(value["synthetic"]) is not bool:
        raise ValueError("合成用量标志无效")
    if "unknown_turns" in value and (
        type(value["unknown_turns"]) is not int or value["unknown_turns"] < 0
    ):
        raise ValueError("未知用量计数无效")
    if "known_tokens" in value:
        known = value["known_tokens"]
        if (
            not isinstance(known, dict)
            or set(known) != {"input_tokens", "output_tokens", "total_tokens"}
            or any(type(v) is not int or v < 0 for v in known.values())
        ):
            raise ValueError("已知用量无效")
    return encode_json(value).decode()


def _reduce_run(previous, event):
    """固定领域事件与外层行的同一约束，同时用于写入与只读一致性核对。"""
    kind, p, now = event["type"], event["payload"], event["timestamp"]
    if previous is None:
        if kind != "run_created" or event["seq"] != 1:
            raise ValueError("缺少 Run 创建事务")
        created, deadline = (
            datetime.fromisoformat(p[key]) for key in ("created_at", "deadline_at")
        )
        if (
            any(
                t.utcoffset() is None or t.utcoffset().total_seconds() != 0
                for t in (created, deadline)
            )
            or deadline <= created
        ):
            raise ValueError("Run 绝对期限无效")
        mode, engine = p["input_mode"], p["engine"]["kind"]
        if (mode, engine) not in {("run", "fake"), ("run", "agents-sdk"), ("verify-patch", "none")}:
            raise ValueError("入口与引擎不一致")
        return dict(
            zip(
                RUN_COLUMNS,
                (
                    event["run_id"],
                    mode,
                    engine,
                    "CREATED",
                    None,
                    None,
                    None,
                    p["created_at"],
                    p["deadline_at"],
                    None,
                    None,
                    None,
                    None,
                    0,
                    0,
                    _usage(p["usage"]),
                    0,
                    None,
                    0,
                    now,
                ),
                strict=True,
            )
        )
    row = dict(previous)
    if row["state"] == "FINISHED" or kind == "run_created":
        raise ValueError("终态写入或重复创建")
    if kind == "state_changed":
        source, target = p["from"], p["to"]
        takeover = p.get("takeover") is True and target == "INTERRUPTED"
        if source != row["state"] or (target not in TRANSITIONS[source] and not takeover):
            raise ValueError("非法阶段转移")
        if target == "REPAIRING" and row["input_mode"] != "run":
            raise ValueError("纯验证不能进入修复阶段")
        if (
            target == "INTERRUPTED"
            and not takeover
            and (
                row["segment_open"]
                or row["last_checkpoint_id"] is None
                or p.get("pause_after_step") != row["steps_used"]
                or row["steps_used"] < 1
            )
        ):
            raise ValueError("暂停必须引用刚提交的完整输入边界")
        if (
            source == "RECOVERING"
            and target == "REPAIRING"
            and (row["segment_open"] or row["last_checkpoint_id"] is None)
        ):
            raise ValueError("没有关闭的 Checkpoint，不能继续修复")
        if target in {"REPRODUCING", "REPAIRING", "VERIFYING"} and not row["inputs_json"]:
            raise ValueError("执行阶段缺少冻结输入")
        if target == "FINISHED":
            if (
                p["outcome"] not in OUTCOMES
                or not isinstance(p["reason_code"], str)
                or not re.fullmatch(r"[A-Z][A-Z0-9_]*", p["reason_code"])
            ):
                raise ValueError("终态结局无效")
            EvidenceRef(**p["result_ref"])
            row.update(
                outcome=p["outcome"],
                reason_code=p["reason_code"],
                agent_stop_reason=p.get("agent_stop_reason", row["agent_stop_reason"]),
            )
        row["state"] = target
    elif kind == "recovery_started":
        if (
            row["state"] != "RECOVERING"
            or type(p["recovery_attempt"]) is not int
            or p["recovery_attempt"] != row["recovery_attempt"] + 1
            or p["source_state"] not in TRANSITIONS
            or p["source_state"] == "FINISHED"
            or p["checkpoint_id"] != row["last_checkpoint_id"]
        ):
            raise ValueError("恢复编号或接管来源不一致")
        row["recovery_attempt"] = p["recovery_attempt"]
    elif kind == "recovery_finished":
        if (
            row["state"] != "RECOVERING"
            or p["recovery_attempt"] != row["recovery_attempt"]
            or type(p["success"]) is not bool
            or (p["success"] and (row["segment_open"] or row["last_checkpoint_id"] is None))
        ):
            raise ValueError("恢复结论没有匹配的安全边界")
    elif kind == "inputs_frozen":
        if row["state"] != "PREPARING" or row["inputs_json"] is not None:
            raise ValueError("只能在准备阶段冻结一次输入")
        for name in ("task_original", "task_resolved", "source_manifest", "configuration"):
            EvidenceRef(**p[name])
        for name, pattern in (
            ("task_sha256", r"[0-9a-f]{64}"),
            ("base_commit", r"(?:[0-9a-f]{40}|[0-9a-f]{64})"),
            ("image_id", r"sha256:[0-9a-f]{64}"),
        ):
            if not isinstance(p[name], str) or re.fullmatch(pattern, p[name]) is None:
                raise ValueError("冻结身份无效")
            row[name] = p[name]
        row["inputs_json"] = encode_json(p).decode()
    elif kind == "model_started":
        if (
            row["state"] != "REPAIRING"
            or type(p["steps_used"]) is not int
            or p["steps_used"] != row["steps_used"] + 1
            or event["step_id"] != p["steps_used"]
        ):
            raise ValueError("请求开始步骤与累计预算不一致")
        EvidenceRef(**p["native_input"])
        row.update(steps_used=p["steps_used"], segment_open=1, usage_json=_usage(p["usage"]))
    elif kind == "model_finished":
        if (
            row["state"] != "REPAIRING"
            or not row["segment_open"]
            or event["step_id"] != row["steps_used"]
        ):
            raise ValueError("模型结果没有对应执行片段")
        row["usage_json"] = _usage(p["cumulative_usage"])
    elif kind == "tool_batch_admitted":
        calls, total = p["calls"], p["tool_calls_used"]
        if (
            row["state"] != "REPAIRING"
            or not row["segment_open"]
            or event["step_id"] != row["steps_used"]
            or not isinstance(calls, list)
            or len(calls) > 8
            or type(total) is not int
            or total != row["tool_calls_admitted"] + len(calls)
        ):
            raise ValueError("整批工具准入与累计预算不一致")
        row["tool_calls_admitted"] = total
    elif kind == "checkpoint_committed":
        counters = p["counters"]
        if (
            row["state"] != "REPAIRING"
            or type(p["checkpoint_id"]) is not int
            or p["checkpoint_id"] != (row["last_checkpoint_id"] or 0) + 1
            or type(p["step_id"]) is not int
            or p["step_id"] != row["steps_used"]
            or counters
            != {"steps_used": row["steps_used"], "tool_calls_admitted": row["tool_calls_admitted"]}
        ):
            raise ValueError("Checkpoint 与累计状态不一致")
        EvidenceRef(**p["manifest_ref"])
        row.update(last_checkpoint_id=p["checkpoint_id"], segment_open=0)
    elif kind == "agent_stopped":
        if (
            row["state"] != "REPAIRING"
            or p["steps_used"] != row["steps_used"]
            or p["tool_calls_admitted"] != row["tool_calls_admitted"]
            or _usage(p["usage"]) != row["usage_json"]
        ):
            raise ValueError("模型停止观察与累计状态不一致")
        row["agent_stop_reason"] = p["reason"]
    row["updated_at"] = now
    return row


class EventLog:
    def __init__(self, directory: Path, run_id: str, *, budget=None, lock=None, existing=False):
        self.directory = Path(directory).absolute()
        self.run_id = validate_run_id(run_id)
        self.budget = budget
        self.sequence = 0
        self._depth = 0
        self._failed = False
        self._context = ContextVar(f"event-context-{run_id}", default=None)
        self._owned_lock = lock is None
        self.lock = lock or RunLock(self.directory)
        self.db = None
        self._database_identity = None
        try:
            self._open(existing)
        except sqlite3.Error as exc:
            self.close()
            if existing:
                raise StateReadError("STATE_CORRUPT: 无法打开已有状态数据库") from exc
            raise StateWriteError("STATE_WRITE_FAILED: 无法初始化状态数据库") from exc
        except OSError as exc:
            self.close()
            if existing:
                raise StateReadError("STATE_CORRUPT: 无法读取已有状态数据库") from exc
            raise
        except BaseException:
            self.close()
            raise

    @classmethod
    def open_existing(cls, directory, run_id, *, budget=None, lock=None):
        """只打开已有 P2 数据库；不迁移历史审计、不创建缺失数据库。"""
        return cls(directory, run_id, budget=budget, lock=lock, existing=True)

    def _open(self, existing):
        self._assert_lock()
        path = self.directory / "events.sqlite3"
        if not existing:
            if self.budget is not None:
                self.budget.check(32768)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            os.close(fd)
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size > MAX_AUDIT_BYTES
            or info.st_uid != os.getuid()
        ):
            raise StateReadError("STATE_CORRUPT: 数据库权限或归属无效")
        self._database_identity = info.st_dev, info.st_ino
        self.db = sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=1)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("PRAGMA trusted_schema = OFF")
        if existing:
            # 持锁的 SQLite 写连接先处理原生回滚日志，再核对完整只读快照；不改建 schema。
            observed_version = self.db.execute("PRAGMA user_version").fetchone()[0]
            snapshot = read_events(self.directory, self.run_id)
            if observed_version in (0, 1):
                raise StateReadError("RESUME_UNSUPPORTED: 历史审计仅可查询")
            if observed_version != 2:
                raise StateReadError("STATE_CORRUPT: 不支持的状态版本")
            self.sequence = snapshot.last_seq
        if info.st_mode & 0o777 != 0o600:
            raise StateReadError("STATE_CORRUPT: 状态数据库必须为 0600")
        self.db.execute("PRAGMA journal_mode = DELETE")
        self.db.execute("PRAGMA synchronous = FULL")
        if not existing:
            try:
                self.db.executescript(
                    "BEGIN IMMEDIATE;" + SCHEMA + "PRAGMA user_version = 2; COMMIT;"
                )
            except sqlite3.Error as exc:
                raise StateWriteError("STATE_WRITE_FAILED: 无法创建状态数据库") from exc

    def _assert_lock(self):
        self.lock.assert_held(self.directory)
        if self._database_identity is not None:
            info = (self.directory / "events.sqlite3").lstat()
            if (info.st_dev, info.st_ino) != self._database_identity or info.st_nlink != 1:
                raise StateWriteError("STATE_WRITE_FAILED: 数据库身份发生变化")

    @property
    def state(self):
        self._assert_lock()
        try:
            rows = self.db.execute("SELECT * FROM runs").fetchall()
            if not rows:
                return None
            if len(rows) != 1 or rows[0]["run_id"] != self.run_id:
                raise StateWriteError("STATE_INVARIANT_BROKEN: Run 归属无效")
            return dict(rows[0])
        except sqlite3.Error as exc:
            raise StateWriteError("STATE_WRITE_FAILED: 无法读取所属 Run") from exc

    @contextmanager
    def transaction(self):
        """只包围本地状态和事件；不把模型、工具或文件操作放入数据库事务。"""
        self._assert_lock()
        outer = self._depth == 0
        try:
            if outer:
                self._failed = False
                self.db.execute("BEGIN IMMEDIATE")
            self._depth += 1
            try:
                yield
            except BaseException:
                self._failed = True
                raise
            finally:
                self._depth -= 1
            if outer:
                if self._failed:
                    raise StateWriteError("STATE_WRITE_FAILED: 事务内操作失败")
                row = self.state
                if row and row["state"] == "PREPARING" and row["inputs_json"] is not None:
                    raise StateWriteError("STATE_INVARIANT_BROKEN: 冻结输入必须同时进入复现阶段")
                self.db.commit()
                self.sequence = self.db.execute(
                    "SELECT COALESCE(MAX(seq), 0) FROM events"
                ).fetchone()[0]
        except BaseException as exc:
            if outer and self.db.in_transaction:
                self.db.rollback()
            if isinstance(exc, sqlite3.Error):
                raise StateWriteError("STATE_WRITE_FAILED: 状态与事件事务未提交") from exc
            raise

    @contextmanager
    def bind(self, **identity):
        token = self._context.set({**(self._context.get() or {}), **identity})
        try:
            yield
        finally:
            self._context.reset(token)

    def _check_inputs(self, row, event_type, payload):
        needs_inputs = event_type in {"model_started", "tool_batch_admitted"} or (
            event_type == "state_changed"
            and payload["to"] in {"REPRODUCING", "REPAIRING", "VERIFYING"}
        )
        if not needs_inputs:
            return
        try:
            frozen = _json(row["inputs_json"])
            contents = {
                name: EvidenceRef(**frozen[name]).read(self.directory, limit=MAX_AUDIT_BYTES)
                for name in ("task_original", "task_resolved", "source_manifest", "configuration")
            }
            resolved = _json(contents["task_resolved"])
            if any(
                resolved[name] != row[name] for name in ("task_sha256", "base_commit", "image_id")
            ):
                raise ValueError("冻结输入与状态身份不符")
            budget = resolved["execution_contract"]["budget"]
            if any(
                type(budget[name]) is not int or budget[name] <= 0
                for name in ("wall_seconds", "max_steps", "max_tool_calls")
            ):
                raise ValueError("冻结预算无效")
            elapsed = datetime.fromisoformat(row["deadline_at"]) - datetime.fromisoformat(
                row["created_at"]
            )
            if (
                elapsed.total_seconds() != budget["wall_seconds"]
                or row["steps_used"] > budget["max_steps"]
                or row["tool_calls_admitted"] > budget["max_tool_calls"]
            ):
                raise ValueError("状态预算超过冻结上限")
            if _json(contents["configuration"])["engine"]["kind"] != row["engine_kind"]:
                raise ValueError("模型配置与状态不一致")
        except (ValueError, TypeError, KeyError) as exc:
            raise StateWriteError("STATE_INVARIANT_BROKEN: 冻结执行输入无效") from exc

    def emit(self, event_type, payload, *, emergency=False, **identity):
        context = {
            "step_id": None,
            "tool_call_id": None,
            "operation_id": None,
            **(self._context.get() or {}),
            **identity,
        }
        now = datetime.now(UTC).isoformat()
        try:
            with self.transaction():
                seq = self.db.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM events").fetchone()[0]
                event = {
                    "schema_version": 1,
                    "seq": seq,
                    "run_id": self.run_id,
                    "timestamp": now,
                    "type": event_type,
                    **context,
                    "payload": payload,
                }
                _validate_envelope(event, self.run_id, seq)
                encoded = encode_json(event)
                if self.budget is not None:
                    self.budget.check(len(encoded) * 4 + 32768, emergency=emergency)
                self.db.execute(
                    "INSERT INTO events VALUES (?, ?, ?, ?)",
                    (seq, now, event_type, encoded.decode("utf-8")),
                )
                previous = self.state
                try:
                    row = _reduce_run(previous, event)
                except (ValueError, KeyError, TypeError) as exc:
                    raise StateWriteError("STATE_INVARIANT_BROKEN: 拒绝不一致的状态事务") from exc
                self._check_inputs(row, event_type, payload)
                if event_type == "checkpoint_committed":
                    self.db.execute(
                        "INSERT INTO checkpoints VALUES (?,?,?,?,?)",
                        (
                            payload["checkpoint_id"],
                            seq,
                            payload["step_id"],
                            encode_json(payload["manifest_ref"]).decode(),
                            now,
                        ),
                    )
                if previous is None:
                    placeholders = ",".join("?" for _ in RUN_COLUMNS)
                    self.db.execute(
                        f"INSERT INTO runs VALUES ({placeholders})",
                        tuple(row[name] for name in RUN_COLUMNS),
                    )
                else:
                    assignments = ",".join(f"{name}=?" for name in RUN_COLUMNS[1:])
                    self.db.execute(
                        f"UPDATE runs SET {assignments} WHERE run_id=?",
                        (*[row[name] for name in RUN_COLUMNS[1:]], self.run_id),
                    )
            return event
        except sqlite3.Error as exc:
            raise StateWriteError("STATE_WRITE_FAILED: 事件事务未提交") from exc

    def command_started(self, command_id, argv, cwd, container_id, payload):
        self.emit(
            "command_started",
            {**payload, "argv": list(argv), "cwd": cwd, "container_id": container_id},
            operation_id=command_id,
        )

    def command_finished(self, result, payload):
        reference = EvidenceRef.save(
            self.directory,
            f"evidence/{result.command_id}.result.json",
            encode_json(result.to_dict()) + b"\n",
            budget=self.budget,
        )
        self.emit(
            "command_finished",
            {**payload, "result_ref": asdict(reference)},
            operation_id=result.command_id,
        )

    def close(self):
        if self.db is not None:
            self.db.close()
            self.db = None
        if self._owned_lock:
            self.lock.close()


def read_events(directory, run_id):
    """只读打开已存在的数据库；历史审计明确保留原始版本。"""
    validate_run_id(run_id)
    path = Path(directory).absolute() / "events.sqlite3"
    try:
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("数据库路径包含链接")
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_AUDIT_BYTES:
            raise ValueError("数据库不是有界普通文件")
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
        try:
            db.execute("PRAGMA query_only = ON")
            db.execute("PRAGMA trusted_schema = OFF")
            db.execute("BEGIN")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
            columns = [item[1] for item in db.execute("PRAGMA table_info(events)")]
            expected_tables = (
                [("checkpoints",), ("events",), ("runs",)] if version == 2 else [("events",)]
            )
            if tables != expected_tables:
                raise ValueError("不支持的审计表结构")
            if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise ValueError("数据库完整性校验失败")
            events = []
            run = None
            checkpoints = ()
            if version in (1, 2) and columns == ["seq", "timestamp", "type", "envelope_json"]:
                for seq, timestamp, event_type, encoded in db.execute(
                    "SELECT seq, timestamp, type, envelope_json FROM events ORDER BY seq"
                ):
                    event = _json(encoded)
                    _validate_envelope(event, run_id, len(events) + 1)
                    if (event["seq"], event["timestamp"], event["type"]) != (
                        seq,
                        timestamp,
                        event_type,
                    ):
                        raise ValueError("事件索引与信封不一致")
                    events.append(event)
                if version == 2:
                    if [item[1] for item in db.execute("PRAGMA table_info(runs)")] != list(
                        RUN_COLUMNS
                    ) or [item[1] for item in db.execute("PRAGMA table_info(checkpoints)")] != [
                        "checkpoint_id",
                        "event_seq",
                        "step_id",
                        "manifest_ref_json",
                        "created_at",
                    ]:
                        raise ValueError("不支持的外层状态结构")
                    if db.execute("PRAGMA foreign_key_check").fetchall():
                        raise ValueError("Checkpoint 结构或引用不符合当前支持范围")
                    for event in events:
                        run = _reduce_run(run, event)
                    expected_checkpoints = [
                        (
                            e["payload"]["checkpoint_id"],
                            e["seq"],
                            e["payload"]["step_id"],
                            encode_json(e["payload"]["manifest_ref"]).decode(),
                            e["timestamp"],
                        )
                        for e in events
                        if e["type"] == "checkpoint_committed"
                    ]
                    observed_checkpoints = db.execute(
                        "SELECT * FROM checkpoints ORDER BY checkpoint_id"
                    ).fetchall()
                    if observed_checkpoints != expected_checkpoints:
                        raise ValueError("Checkpoint 行与提交事件不一致")
                    checkpoints = tuple(
                        dict(
                            zip(
                                (
                                    "checkpoint_id",
                                    "event_seq",
                                    "step_id",
                                    "manifest_ref_json",
                                    "created_at",
                                ),
                                row,
                                strict=True,
                            )
                        )
                        for row in observed_checkpoints
                    )
                    rows = db.execute("SELECT * FROM runs").fetchall()
                    if (
                        run is None
                        or len(rows) != 1
                        or dict(zip(RUN_COLUMNS, rows[0], strict=True)) != run
                    ):
                        raise ValueError("外层状态与事务事件不一致")
                    if run["state"] == "PREPARING" and run["inputs_json"] is not None:
                        raise ValueError("冻结输入与复现阶段未原子提交")
            elif version == 0 and columns == ["seq", "timestamp", "run_id", "kind", "payload"]:
                for seq, timestamp, owner, kind, encoded in db.execute(
                    "SELECT seq, timestamp, run_id, kind, payload FROM events ORDER BY seq"
                ):
                    if owner != run_id or seq != len(events) + 1:
                        raise ValueError("历史事件身份或顺序无效")
                    payload = _json(encoded)
                    if not isinstance(payload, dict):
                        raise ValueError("历史事件 payload 无效")
                    events.append(
                        {
                            "seq": seq,
                            "timestamp": timestamp,
                            "run_id": owner,
                            "kind": kind,
                            "payload": payload,
                        }
                    )
            else:
                raise ValueError("不支持的审计格式")
            observed = path.lstat()
            if (info.st_dev, info.st_ino) != (observed.st_dev, observed.st_ino):
                raise ValueError("读取期间数据库被替换")
            return EventSnapshot(run_id, version, tuple(events), run, checkpoints)
        finally:
            db.close()
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise StateReadError("STATE_CORRUPT: 无法读取或核验事件数据库") from exc
