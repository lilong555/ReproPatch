"""两个原生 Agent 共用的人民币请求账本；只记录计量信息，不保存凭据。"""

import hashlib
import json
import os
import sqlite3
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from repropatch.context import (
    REQUEST_PURPOSE,
    ContextLimit,
    ContextPolicy,
    TokenEstimator,
    admission_reason,
    encoded,
)
from repropatch.cpa import cpa_route

NANO_PER_CNY = 1_000_000_000
POLICY = {
    "model": "deepseek-flash",
    "model_version": "DeepSeek-V4.1-Flash-1017",
    "currency": "CNY",
    "verified_date": "2026-10-22",
    "source": "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/",
    "input_ceiling_tokens": 1_048_576,
    "max_output_tokens": 8192,
    "peak_input_nano_per_token": 2000,
    "peak_cached_input_nano_per_token": 40,
    "peak_output_nano_per_token": 8000,
    "request_limit_per_attempt": 12,
}
POLICY_JSON = json.dumps(POLICY, sort_keys=True, separators=(",", ":"))


def request_reservation():
    """预留和结算共用 POLICY 中的单价。"""
    return (
        POLICY["input_ceiling_tokens"] * POLICY["peak_input_nano_per_token"]
        + POLICY["max_output_tokens"] * POLICY["peak_output_nano_per_token"]
    )


class BudgetLimit(ContextLimit):
    """发送前额度不足或请求不属于本次冻结实验。"""

    def __init__(self, code, *, layer=None):
        reason = {
            "BENCHMARK_REQUEST_LIMIT": "REQUEST_BUDGET_EXHAUSTED",
            "BENCHMARK_BUDGET_EXHAUSTED": "REQUEST_BUDGET_EXHAUSTED",
            "TOOL_BUDGET": "TOOL_BUDGET_EXHAUSTED",
            "CONTEXT_LIMIT": "LOCAL_TRANSPORT_LIMIT",
            "BENCHMARK_REQUEST_TOO_LARGE": "LOCAL_TRANSPORT_LIMIT",
        }.get(code, code)
        super().__init__(reason, layer=layer)
        self.args = (code,)


def validate_task_budget(task, *, request_cap=12):
    """按批次额度核对请求、工具和输出预算。"""
    if (
        task.budget.max_output_tokens != POLICY["max_output_tokens"]
        or task.budget.max_steps != request_cap
        or task.budget.model_timeout_seconds not in (90, 180)
        or task.budget.max_tool_calls != request_cap * 2
    ):
        raise BudgetLimit("BENCHMARK_TASK_BUDGET_MISMATCH")


def check_pricing_date():
    """跨 UTC 日必须复核价格，不以本地时区或运行目录恢复额度。"""
    if datetime.now(UTC).date().isoformat() != POLICY["verified_date"]:
        raise BudgetLimit("BENCHMARK_PRICING_REVIEW_REQUIRED")


class BudgetLedger:
    def __init__(self, path):
        self.path = Path(path).resolve()
        with self.connect() as db:
            policy, cap = db.execute("SELECT policy,cap FROM budget").fetchone()
            if policy != POLICY_JSON or cap != 20 * NANO_PER_CNY:
                raise BudgetLimit("BENCHMARK_BUDGET_POLICY_MISMATCH")

    @classmethod
    def create(cls, path):
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        with sqlite3.connect(path) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.executescript(
                "CREATE TABLE budget(policy TEXT NOT NULL,cap INTEGER NOT NULL);"
                "CREATE TABLE requests(id TEXT PRIMARY KEY,attempt TEXT NOT NULL,"
                "sent_at TEXT NOT NULL,request_sha256 TEXT NOT NULL,reserved INTEGER NOT NULL,"
                "charged INTEGER,usage TEXT,status_code INTEGER,response_sha256 TEXT);"
            )
            db.execute("INSERT INTO budget VALUES (?,?)", (POLICY_JSON, 20 * NANO_PER_CNY))
        return cls(path)

    def connect(self):
        # mode=rw 禁止在账本丢失后自动重新创建额度。
        db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=10)
        db.execute("PRAGMA synchronous=FULL")
        return db

    def reserve(self, attempt, payload):
        identity = uuid.uuid4().hex
        reservation = request_reservation()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            cap = db.execute("SELECT cap FROM budget").fetchone()[0]
            spent = db.execute(
                "SELECT COALESCE(SUM(COALESCE(charged,reserved)),0) FROM requests"
            ).fetchone()[0]
            count = db.execute(
                "SELECT COUNT(*) FROM requests WHERE attempt=?", (attempt,)
            ).fetchone()[0]
            if count >= POLICY["request_limit_per_attempt"] or spent + reservation > cap:
                raise BudgetLimit("BENCHMARK_BUDGET_EXHAUSTED")
            db.execute(
                "INSERT INTO requests(id,attempt,sent_at,request_sha256,reserved) "
                "VALUES (?,?,?,?,?)",
                (
                    identity,
                    attempt,
                    datetime.now(UTC).isoformat(),
                    hashlib.sha256(payload).hexdigest(),
                    reservation,
                ),
            )
        return identity

    def settle(self, identity, content, status_code):
        # 未知或矛盾用量继续占用完整预留；不得从 SDK 缺省零推断免费。
        charged = None
        usage = None
        try:
            body = json.loads(content)
            value = body.get("usage")
            if status_code == 200 and isinstance(value, dict):
                incoming, outgoing = value.get("input_tokens"), value.get("output_tokens")
                if all(type(n) is int and n >= 0 for n in (incoming, outgoing)):
                    total = value.get("total_tokens")
                    if total is not None and (
                        type(total) is not int or total != incoming + outgoing
                    ):
                        raise ValueError("矛盾用量继续保留预留")
                    if (
                        incoming > POLICY["input_ceiling_tokens"]
                        or outgoing > POLICY["max_output_tokens"]
                    ):
                        raise BudgetLimit("PROVIDER_TOKEN_BOUND_VIOLATION")
                    details = value.get("input_tokens_details")
                    cached = details.get("cached_tokens") if isinstance(details, dict) else None
                    if type(cached) is not int or not 0 <= cached <= incoming:
                        cached = 0
                    charged = (
                        (incoming - cached) * POLICY["peak_input_nano_per_token"]
                        + cached * POLICY["peak_cached_input_nano_per_token"]
                        + outgoing * POLICY["peak_output_nano_per_token"]
                    )
                    usage = json.dumps(value, sort_keys=True)
        except (ValueError, TypeError, AttributeError):
            pass
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE requests SET charged=?,usage=?,status_code=?,response_sha256=? "
                "WHERE id=? AND status_code IS NULL",
                (charged, usage, status_code, hashlib.sha256(content).hexdigest(), identity),
            )
            if cursor.rowcount != 1:
                raise BudgetLimit("BENCHMARK_BUDGET_SETTLEMENT_CONFLICT")

    def summary(self, attempt=None):
        with self.connect() as db:
            rows = db.execute(
                "SELECT attempt,reserved,charged,usage,status_code FROM requests"
                + (" WHERE attempt=?" if attempt is not None else ""),
                (attempt,) if attempt is not None else (),
            ).fetchall()
        return {
            "currency": "CNY",
            "cap_cny": 20,
            "requests": len(rows),
            "unknown_usage_requests": sum(r[2] is None for r in rows),
            "committed_upper_bound_cny": sum(r[2] if r[2] is not None else r[1] for r in rows)
            / NANO_PER_CNY,
            "known_usage_cost_upper_bound_cny": sum(r[2] or 0 for r in rows) / NANO_PER_CNY,
            "cost_basis": "冻结高峰单价上界；不冒充账单实际扣款",
        }


class BudgetHooks:
    def __init__(self, ledger, attempt, trace_root, *, local_luna=False, route="public"):
        self.ledger = ledger
        self.attempt = attempt
        self.trace_root = Path(trace_root)
        self.trace_root.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.local_luna = local_luna
        self.route = cpa_route(route)
        self.transport_times = {}
        self.last_request_body = None
        self.last_response = None

    def request(self, request):
        payload = request.content
        identity = None
        if isinstance(self.ledger, LocalUsageLedger):
            identity = self.ledger.record_pre_send_telemetry(
                self.attempt, payload, request_purpose=REQUEST_PURPOSE.get()
            )
            self._save(identity + "-request.json", payload)
        try:
            self._request(request, identity)
        except BudgetLimit as error:
            if identity is not None:
                self.ledger.reject(identity, error.reason, error.layer or "BudgetHooks")
            raise
        except (ValueError, TypeError, AttributeError) as error:
            if identity is not None:
                self.ledger.reject(identity, "BENCHMARK_REQUEST_INVALID", "BudgetHooks")
            raise BudgetLimit("BENCHMARK_REQUEST_INVALID") from error

    def _save(self, name, content):
        path = self.trace_root / name
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(content)

    def _request(self, request, identity):
        if not self.local_luna:
            check_pricing_date()
        url = request.url
        endpoint_matches = (
            self.route.accepts(url)
            if self.local_luna
            else url.scheme == "https"
            and url.host == "api.deepseek.com"
            and url.port in (None, 443)
        )
        if (
            request.method != "POST"
            or not endpoint_matches
            or url.query
            or url.fragment
            or url.username
            or url.password
            or url.path not in {"/responses", "/v1/responses"}
        ):
            raise BudgetLimit("BENCHMARK_ENDPOINT_REJECTED")
        payload = request.content
        if not self.local_luna and len(payload) > ContextPolicy().transport_max_bytes:
            raise BudgetLimit("BENCHMARK_REQUEST_TOO_LARGE")
        body = json.loads(payload)
        purpose = REQUEST_PURPOSE.get()
        if (
            body.get("model") != ("gpt-6-luna" if self.local_luna else POLICY["model"])
            or (
                body.get("max_output_tokens") != POLICY["max_output_tokens"]
                if purpose == "repair"
                else not 1 <= body.get("max_output_tokens", 0) <= POLICY["max_output_tokens"]
            )
            or body.get("stream", False) is not False
        ):
            raise BudgetLimit("BENCHMARK_MODEL_SETTINGS_MISMATCH")
        if any(tool.get("type") != "function" for tool in body.get("tools", [])):
            raise BudgetLimit("BENCHMARK_EXTRA_PAID_TOOL_REJECTED")

        def text_only(value):
            if isinstance(value, dict):
                if value.get("type") in {"input_image", "input_audio", "input_file", "image_url"}:
                    raise BudgetLimit("BENCHMARK_MEDIA_REJECTED")
                for item in value.values():
                    text_only(item)
            elif isinstance(value, list):
                for item in value:
                    text_only(item)

        text_only(body)
        identity = (
            self.ledger.reserve(self.attempt, payload, identity=identity)
            if isinstance(self.ledger, LocalUsageLedger)
            else self.ledger.reserve(self.attempt, payload)
        )
        request.extensions["benchmark_request_id"] = identity
        if not hasattr(request, "headers"):
            request.headers = {}
        request.headers["X-Request-ID"] = identity
        self.transport_times[identity] = {
            "request_id": identity,
            "attempt_id": self.attempt,
            "started_at": datetime.now(UTC).isoformat(),
            "started_monotonic": time.monotonic(),
            "route": self.route.to_dict() if self.local_luna else None,
        }
        self.last_request_body = body
        if not isinstance(self.ledger, LocalUsageLedger):
            self._save(identity + "-request.json", payload)

    def response(self, response):
        identity = response.request.extensions["benchmark_request_id"]
        self.record_headers(identity, response)
        content = response.read()
        self.finish(identity, content, response.status_code)

    def finish(self, identity, content, status_code):
        self._save(identity + "-response.json", content)
        self.ledger.settle(identity, content, status_code)
        try:
            self.last_response = json.loads(content)
        except ValueError:
            self.last_response = None
        timing = self.transport_times.pop(identity, {})
        started = timing.pop("started_monotonic", time.monotonic())
        timing.update(
            completed_at=datetime.now(UTC).isoformat(),
            wall_seconds=time.monotonic() - started,
            http_status=status_code,
            received_bytes=len(content),
            supplier_started_at=None,
            supplier_started_at_evidence="CPA 供应商阶段日志单独关联",
        )
        self._save(identity + "-transport.json", encoded(timing))

    def record_headers(self, identity, response):
        timing = self.transport_times[identity]
        timing.update(
            response_headers_at=datetime.now(UTC).isoformat(),
            response_headers_seconds=time.monotonic() - timing["started_monotonic"],
            cpa_request_id=response.headers.get("X-Request-ID"),
        )

    def abort(self, request, error):
        """HTTP 连接失败也关闭已发请求；真实用量保持未知。"""
        identity = request.extensions.get("benchmark_request_id")
        if identity is not None and not (self.trace_root / (identity + "-response.json")).exists():
            self.finish(identity, encoded({"transport_error": type(error).__name__}), 0)

    async def async_request(self, request):
        self.request(request)

    async def async_response(self, response):
        identity = response.request.extensions["benchmark_request_id"]
        self.record_headers(identity, response)
        content = await response.aread()
        self.finish(identity, content, response.status_code)


class LocalUsageLedger:
    """CPA 自备额度记录请求和供应商用量，费用保持未知，独立于人民币账本。"""

    def __init__(self, path):
        self.path = Path(path).resolve()
        with self.connect() as db:
            if db.execute("SELECT value FROM metadata").fetchone() != ("local-luna-v1",):
                raise BudgetLimit("LOCAL_USAGE_LEDGER_MISMATCH")

    def connect(self):
        db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=10)
        db.execute("PRAGMA synchronous=FULL")
        return db

    @classmethod
    def create(cls, path, *, context_policy=None):
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        with sqlite3.connect(path) as db:
            db.executescript(
                "CREATE TABLE metadata(value TEXT NOT NULL);"
                "INSERT INTO metadata VALUES ('local-luna-v1');"
                "CREATE TABLE requests(id TEXT PRIMARY KEY,attempt TEXT NOT NULL,"
                "sent_at TEXT NOT NULL,request_sha256 TEXT NOT NULL,"
                "usage TEXT,status_code INTEGER,response_sha256 TEXT,"
                "purpose TEXT NOT NULL DEFAULT 'repair');"
                "CREATE TABLE context_policy(value TEXT NOT NULL);"
                "CREATE TABLE context_anchors(attempt TEXT PRIMARY KEY,state TEXT NOT NULL);"
                "CREATE TABLE pre_send(id TEXT PRIMARY KEY,attempt TEXT NOT NULL,"
                "sequence INTEGER NOT NULL,purpose TEXT NOT NULL,payload BLOB NOT NULL,"
                "telemetry TEXT NOT NULL,issued INTEGER NOT NULL DEFAULT 0);"
            )
            db.execute(
                "INSERT INTO context_policy VALUES (?)",
                (encoded((context_policy or ContextPolicy.legacy()).to_dict()).decode(),),
            )
        return cls(path)

    @classmethod
    def create_scoped(cls, path, attempts, *, context_policy=None):
        """正式批次固定每个 Attempt 的独占额度，分片额度相加构成总上限。"""
        if not attempts or any(
            type(cap) is not int or not 1 <= cap <= 24 for cap in attempts.values()
        ):
            raise BudgetLimit("INVALID_SCOPED_ALLOCATION")
        if context_policy and any(cap > context_policy.request_cap for cap in attempts.values()):
            raise BudgetLimit("INVALID_SCOPED_ALLOCATION")
        ledger = cls.create(path, context_policy=context_policy)
        with ledger.connect() as db:
            db.execute("CREATE TABLE allocations(attempt TEXT PRIMARY KEY, request_cap INTEGER)")
            db.executemany("INSERT INTO allocations VALUES (?,?)", attempts.items())
        return ledger

    @property
    def policy(self):
        with self.connect() as db:
            if not db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='context_policy'"
            ).fetchone():
                return ContextPolicy.legacy()
            return ContextPolicy.from_dict(
                json.loads(db.execute("SELECT value FROM context_policy").fetchone()[0])
            )

    def estimator(self, attempt):
        with self.connect() as db:
            row = db.execute(
                "SELECT state FROM context_anchors WHERE attempt=?", (attempt,)
            ).fetchone()
        return TokenEstimator(**json.loads(row[0])) if row else TokenEstimator()

    def record_pre_send_telemetry(
        self, attempt, payload, *, request_purpose="repair", declared_transport_bytes=None
    ):
        """完整正文和测量先提交到 SQLite，所有准入判断随后执行。"""
        identity = uuid.uuid4().hex
        try:
            body = json.loads(payload)
            measurement = self.estimator(attempt).estimate(body)
        except (ValueError, TypeError, AttributeError):
            measurement = {"estimated_input_tokens": None, "opaque_state_bytes": None}
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            sequence = db.execute(
                "SELECT COUNT(*) + 1 FROM pre_send WHERE attempt=?", (attempt,)
            ).fetchone()[0]
            telemetry = {
                "attempt_id": attempt,
                "request_sequence": sequence,
                "request_purpose": request_purpose,
                "transport_bytes": len(payload)
                if declared_transport_bytes is None
                else declared_transport_bytes,
                "captured_transport_bytes": len(payload),
                "body_complete": declared_transport_bytes in (None, len(payload)),
                "request_sha256": hashlib.sha256(payload).hexdigest(),
                "context_policy_version": self.policy.context_policy_version,
                "rejection_layer": None,
                "stop_reason": None,
                "issued": False,
                **measurement,
            }
            db.execute(
                "INSERT INTO pre_send(id,attempt,sequence,purpose,payload,telemetry) "
                "VALUES (?,?,?,?,?,?)",
                (
                    identity,
                    attempt,
                    sequence,
                    request_purpose,
                    payload,
                    encoded(telemetry).decode(),
                ),
            )
        return identity

    def reject(self, identity, reason, layer):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT telemetry,issued FROM pre_send WHERE id=?", (identity,)
            ).fetchone()
            if row and not row[1]:
                prior = json.loads(row[0])
                value = {
                    **prior,
                    "stop_reason": prior.get("stop_reason") or reason,
                    "rejection_layer": prior.get("rejection_layer") or layer,
                }
                db.execute(
                    "UPDATE pre_send SET telemetry=? WHERE id=?",
                    (encoded(value).decode(), identity),
                )

    def request_cap(self, attempt):
        """读取当前 Attempt 的静态额度，未分片账本使用其冻结策略。"""
        with self.connect() as db:
            scoped = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='allocations'"
            ).fetchone()
            if not scoped:
                return self.policy.request_cap
            allocation = db.execute(
                "SELECT request_cap FROM allocations WHERE attempt=?", (attempt,)
            ).fetchone()
            if allocation is None:
                raise BudgetLimit("UNREGISTERED_FORMAL_ATTEMPT")
            return allocation[0]

    def reserve(self, attempt, payload, *, identity=None, request_purpose=None):
        identity = identity or self.record_pre_send_telemetry(
            attempt, payload, request_purpose=request_purpose or REQUEST_PURPOSE.get()
        )
        try:
            return self._reserve(attempt, payload, identity)
        except BudgetLimit as error:
            self.reject(identity, error.reason, error.layer or "LocalUsageLedger.reserve")
            raise

    def _reserve(self, attempt, payload, identity):
        policy = self.policy
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            entry = db.execute(
                "SELECT attempt,payload,telemetry,purpose,issued FROM pre_send WHERE id=?",
                (identity,),
            ).fetchone()
            if not entry or entry[0] != attempt or entry[1] != payload or entry[4]:
                raise BudgetLimit("PRE_SEND_IDENTITY_MISMATCH")
            telemetry, purpose = json.loads(entry[2]), entry[3]
            reason = admission_reason(policy, telemetry)
            if reason:
                raise BudgetLimit(reason)
            if purpose not in {"repair", "compact", "retry"}:
                raise BudgetLimit("REQUEST_PURPOSE_INVALID")
            scoped = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='allocations'"
            ).fetchone()
            cap = policy.request_cap
            if scoped:
                allocation = db.execute(
                    "SELECT request_cap FROM allocations WHERE attempt=?", (attempt,)
                ).fetchone()
                if allocation is None:
                    raise BudgetLimit("UNREGISTERED_FORMAL_ATTEMPT")
                cap = allocation[0]
                body = json.loads(payload)
                if (
                    body.get("model") != "gpt-6-luna"
                    or body.get("reasoning", {}).get("effort") != "max"
                    or type(body.get("max_output_tokens")) is not int
                    or not 1 <= body["max_output_tokens"] <= 8192
                ):
                    raise BudgetLimit("FORMAL_REQUEST_PARAMETERS")
                if db.execute("SELECT 1 FROM requests WHERE usage IS NULL LIMIT 1").fetchone():
                    raise BudgetLimit("FORMAL_USAGE_UNSETTLED")
            count = db.execute(
                "SELECT COUNT(*) FROM requests WHERE attempt=?", (attempt,)
            ).fetchone()[0]
            if count >= cap:
                raise BudgetLimit("BENCHMARK_REQUEST_LIMIT")
            db.execute(
                "INSERT INTO requests(id,attempt,sent_at,request_sha256,purpose) "
                "VALUES (?,?,?,?,?)",
                (
                    identity,
                    attempt,
                    datetime.now(UTC).isoformat(),
                    hashlib.sha256(payload).hexdigest(),
                    purpose,
                ),
            )
            telemetry["issued"] = True
            db.execute(
                "UPDATE pre_send SET issued=1,telemetry=? WHERE id=?",
                (encoded(telemetry).decode(), identity),
            )
        return identity

    def settle(self, identity, content, status_code):
        usage = None
        response = {}
        try:
            response = json.loads(content)
            value = response.get("usage")
            if status_code == 200 and isinstance(value, dict):
                if all(
                    type(value.get(k)) is int and value[k] >= 0
                    for k in ("input_tokens", "output_tokens")
                ):
                    incoming, outgoing = value["input_tokens"], value["output_tokens"]
                    total = value.get("total_tokens", incoming + outgoing)
                    cached = (value.get("input_tokens_details") or {}).get("cached_tokens", 0)
                    reasoning = (value.get("output_tokens_details") or {}).get(
                        "reasoning_tokens", 0
                    )
                    if (
                        type(total) is int
                        and total == incoming + outgoing
                        and type(cached) is int
                        and 0 <= cached <= incoming
                        and type(reasoning) is int
                        and 0 <= reasoning <= outgoing
                    ):
                        usage = json.dumps(value, sort_keys=True)
        except (ValueError, TypeError, AttributeError):
            pass
        with self.connect() as db:
            updated = db.execute(
                "UPDATE requests SET usage=?,status_code=?,response_sha256=? "
                "WHERE id=? AND status_code IS NULL",
                (usage, status_code, hashlib.sha256(content).hexdigest(), identity),
            )
            if updated.rowcount != 1:
                raise BudgetLimit("BENCHMARK_BUDGET_SETTLEMENT_CONFLICT")
            if usage is not None:
                row = db.execute(
                    "SELECT attempt,payload,telemetry FROM pre_send WHERE id=?", (identity,)
                ).fetchone()
                if row:
                    prior = db.execute(
                        "SELECT state FROM context_anchors WHERE attempt=?", (row[0],)
                    ).fetchone()
                    estimator = (
                        TokenEstimator(**json.loads(prior[0])) if prior else TokenEstimator()
                    )
                    try:
                        body = json.loads(row[1])
                    except ValueError:
                        body = {"input": []}
                    estimator.observe(body, response)
                    db.execute(
                        "INSERT OR REPLACE INTO context_anchors VALUES (?,?)",
                        (row[0], encoded(estimator.to_dict()).decode()),
                    )
                    measurement = {
                        **json.loads(row[2]),
                        "measured_input_tokens": response["usage"]["input_tokens"],
                        "measured_output_tokens": response["usage"]["output_tokens"],
                    }
                    db.execute(
                        "UPDATE pre_send SET telemetry=? WHERE id=?",
                        (encoded(measurement).decode(), identity),
                    )

    def summary(self, attempt=None):
        with self.connect() as db:
            rows = db.execute(
                "SELECT usage FROM requests" + (" WHERE attempt=?" if attempt else ""),
                (attempt,) if attempt else (),
            ).fetchall()
            modern = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pre_send'"
            ).fetchone()
            observations = (
                db.execute(
                    "SELECT telemetry,purpose,issued FROM pre_send"
                    + (" WHERE attempt=?" if attempt else "")
                    + " ORDER BY rowid",
                    (attempt,) if attempt else (),
                ).fetchall()
                if modern
                else []
            )
        values = [json.loads(r[0]) for r in rows if r[0]]
        telemetry = [json.loads(r[0]) for r in observations]
        purposes = {
            name + "_requests": sum(r[1] == name and r[2] for r in observations)
            for name in ("repair", "compact", "retry")
        }
        unknown_usage = sum(row[0] is None for row in rows)
        known_input = sum(v["input_tokens"] for v in values)
        known_output = sum(v["output_tokens"] for v in values)
        return {
            "requests": len(rows),
            "issued_requests": len(rows),
            "attempted_model_steps": sum(r[1] != "retry" for r in observations),
            "local_rejections": sum(not r[2] for r in observations),
            **purposes,
            "unknown_usage_requests": unknown_usage,
            "input_tokens": known_input if not unknown_usage else None,
            "output_tokens": known_output if not unknown_usage else None,
            "known_input_tokens": known_input,
            "known_output_tokens": known_output,
            "cached_input_tokens": sum(
                (v.get("input_tokens_details") or {}).get("cached_tokens", 0) for v in values
            ),
            "reasoning_tokens": sum(
                (v.get("output_tokens_details") or {}).get("reasoning_tokens", 0) for v in values
            ),
            "peak_single_input_tokens": max((v["input_tokens"] for v in values), default=0),
            "peak_transport_bytes": max((v["transport_bytes"] for v in telemetry), default=0),
            "opaque_state_peak_bytes": max(
                (v.get("opaque_state_bytes") or 0 for v in telemetry), default=0
            ),
            "opaque_state_peak_fraction": max(
                (
                    (v.get("opaque_state_bytes") or 0) / max(1, v["transport_bytes"])
                    for v in telemetry
                ),
                default=0,
            ),
            "last_local_stop_reason": next(
                (v["stop_reason"] for v in reversed(telemetry) if v.get("stop_reason")), None
            ),
            "cost_cny": None,
            "cost_basis": "用户提供的本机模型额度；供应商账单未知，单独记录用量",
        }
