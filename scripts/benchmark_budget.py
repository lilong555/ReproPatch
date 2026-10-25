"""两个原生 Agent 共用的人民币请求账本；只记录计量信息，不保存凭据。"""

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

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


class BudgetLimit(RuntimeError):
    """发送前额度不足或请求不属于本次冻结实验。"""


def validate_task_budget(task):
    """模型调用前核对各框架共用的任务额度。"""
    if (
        task.budget.max_output_tokens != POLICY["max_output_tokens"]
        or task.budget.max_steps != POLICY["request_limit_per_attempt"]
        or task.budget.model_timeout_seconds != 90
        or task.budget.max_tool_calls != 24
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
    def __init__(self, ledger, attempt, trace_root, *, local_luna=False):
        self.ledger = ledger
        self.attempt = attempt
        self.trace_root = Path(trace_root)
        self.trace_root.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.local_luna = local_luna

    def request(self, request):
        if not self.local_luna:
            check_pricing_date()
        url = request.url
        endpoint_matches = (
            url.scheme == "https" and url.host == "cpa.liyinlong.me" and url.port in (None, 443)
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
        if len(payload) > 1024 * 1024:
            raise BudgetLimit("BENCHMARK_REQUEST_TOO_LARGE")
        body = json.loads(payload)
        if (
            body.get("model") != ("gpt-6-luna" if self.local_luna else POLICY["model"])
            or body.get("max_output_tokens") != POLICY["max_output_tokens"]
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
        identity = self.ledger.reserve(self.attempt, payload)
        request.extensions["benchmark_request_id"] = identity
        path = self.trace_root / (identity + "-request.json")
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(payload)

    def response(self, response):
        identity = response.request.extensions["benchmark_request_id"]
        content = response.read()
        self.finish(identity, content, response.status_code)

    def finish(self, identity, content, status_code):
        path = self.trace_root / (identity + "-response.json")
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(content)
        self.ledger.settle(identity, content, status_code)

    async def async_request(self, request):
        self.request(request)

    async def async_response(self, response):
        identity = response.request.extensions["benchmark_request_id"]
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
        return sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=10)

    @classmethod
    def create(cls, path):
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        with sqlite3.connect(path) as db:
            db.executescript(
                "CREATE TABLE metadata(value TEXT NOT NULL);"
                "INSERT INTO metadata VALUES ('local-luna-v1');"
                "CREATE TABLE requests(id TEXT PRIMARY KEY,attempt TEXT NOT NULL,"
                "sent_at TEXT NOT NULL,request_sha256 TEXT NOT NULL,"
                "usage TEXT,status_code INTEGER,response_sha256 TEXT);"
            )
        return cls(path)

    @classmethod
    def create_scoped(cls, path, attempts):
        """正式批次固定每个 Attempt 的独占额度，分片额度相加构成总上限。"""
        if not attempts or any(
            type(cap) is not int or not 1 <= cap <= 12 for cap in attempts.values()
        ):
            raise BudgetLimit("INVALID_SCOPED_ALLOCATION")
        ledger = cls.create(path)
        with ledger.connect() as db:
            db.execute("CREATE TABLE allocations(attempt TEXT PRIMARY KEY, request_cap INTEGER)")
            db.executemany("INSERT INTO allocations VALUES (?,?)", attempts.items())
        return ledger

    def reserve(self, attempt, payload):
        identity = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            scoped = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='allocations'"
            ).fetchone()
            cap = POLICY["request_limit_per_attempt"]
            if scoped:
                allocation = db.execute(
                    "SELECT request_cap FROM allocations WHERE attempt=?", (attempt,)
                ).fetchone()
                if allocation is None:
                    raise BudgetLimit("UNREGISTERED_FORMAL_ATTEMPT")
                cap = allocation[0]
                body = json.loads(payload)
                if (
                    len(payload) > 262144
                    or body.get("model") != "gpt-6-luna"
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
                "INSERT INTO requests(id,attempt,sent_at,request_sha256) VALUES (?,?,?,?)",
                (
                    identity,
                    attempt,
                    datetime.now(UTC).isoformat(),
                    hashlib.sha256(payload).hexdigest(),
                ),
            )
        return identity

    def settle(self, identity, content, status_code):
        usage = None
        try:
            value = json.loads(content).get("usage")
            if status_code == 200 and isinstance(value, dict):
                if all(
                    type(value.get(k)) is int and value[k] >= 0
                    for k in ("input_tokens", "output_tokens")
                ):
                    usage = json.dumps(value, sort_keys=True)
        except (ValueError, AttributeError):
            pass
        with self.connect() as db:
            updated = db.execute(
                "UPDATE requests SET usage=?,status_code=?,response_sha256=? "
                "WHERE id=? AND status_code IS NULL",
                (usage, status_code, hashlib.sha256(content).hexdigest(), identity),
            )
            if updated.rowcount != 1:
                raise BudgetLimit("BENCHMARK_BUDGET_SETTLEMENT_CONFLICT")

    def summary(self, attempt=None):
        with self.connect() as db:
            rows = db.execute(
                "SELECT usage FROM requests" + (" WHERE attempt=?" if attempt else ""),
                (attempt,) if attempt else (),
            ).fetchall()
        return {
            "requests": len(rows),
            "unknown_usage_requests": sum(row[0] is None for row in rows),
            "cost_cny": None,
            "cost_basis": "用户提供的本机模型额度；供应商账单未知，单独记录用量",
        }
