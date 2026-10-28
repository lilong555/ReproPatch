"""Azure CPA 的重试租约：Job 心跳失联二十分钟后恢复共享配置。"""

import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

CONFIG = Path("/home/18577171104/services/cpa/config.yaml")
STATE = Path("/var/lib/repropatch-cpa")
NAME = re.compile(r"[a-zA-Z0-9_.:-]{1,100}\Z")
RETRY = re.compile(r"(?m)^request-retry\s*:\s*(\d+)\s*(?:#.*)?$")
TTL = 1200


def watched_reload(expected):
    """核验绑定文件和 CPA 文件监听器的配置加载事件。"""
    started = datetime.now(UTC).isoformat()
    return {"expected_retry": expected, "watch_started_at": started}


def confirm_reload(probe):
    """读取管理进程日志的固定事件标签，输出仅含配置加载计数。"""
    if probe is None:
        return None
    for _ in range(20):
        result = subprocess.run(
            [
                "docker",
                "logs",
                "--since",
                probe["watch_started_at"],
                "--tail",
                "300",
                "cli-proxy-api",
            ],
            capture_output=True,
            timeout=10,
        )
        lines = (result.stdout + result.stderr).decode(errors="replace").lower()
        markers = (
            "server config updated",
            "config file changed",
            "configuration reloaded",
            "config updated successfully",
        )
        found = [marker for marker in markers if marker in lines]
        if found:
            probe["reload_events"] = found
            probe["verified_at"] = datetime.now(UTC).isoformat()
            return probe
        time.sleep(0.5)
    raise RuntimeError("CPA_CONFIG_RELOAD_UNCONFIRMED")


class LeaseManager:
    def __init__(
        self, config=CONFIG, directory=STATE, clock=time.time, reload_probe=watched_reload
    ):
        self.config, self.directory, self.clock = config, directory, clock
        self.reload_probe = reload_probe
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextmanager
    def locked(self):
        with (self.directory / "lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def state(self):
        path = self.directory / "lease.json"
        return json.loads(path.read_text()) if path.exists() else None

    def save(self, value):
        path = self.directory / "lease.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        temporary.chmod(0o600)
        temporary.replace(path)

    def event(self, value):
        value = {"at": datetime.now(UTC).isoformat(), **value}
        with (self.directory / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(value, ensure_ascii=False) + "\n")

    def claim(self, request):
        """跨 Run 独立认领 Attempt，重复提交保持已分配额度。"""
        campaign = request.get("campaign")
        attempt = request.get("attempt_id")
        run = request.get("run_id")
        phase = request.get("phase")
        cap = request.get("request_cap")
        limits = {
            "calibration": 12,
            "development": 480,
            "formal": 3600,
            "repeat": 720,
            "infrastructure-revalidation": 480,
        }
        if campaign != "cross-repository-20261028" or phase not in limits:
            raise ValueError("CPA_CAMPAIGN_ALLOCATION_REJECTED")
        if (
            not isinstance(attempt, str)
            or not re.fullmatch(r"[A-Za-z0-9_./:-]{1,220}", attempt)
            or not isinstance(run, str)
            or not run.isdigit()
            or type(cap) is not int
            or cap != (1 if phase == "calibration" else 24)
        ):
            raise ValueError("CPA_ATTEMPT_CLAIM_INVALID")
        path = self.directory / "claims.json"
        claims = json.loads(path.read_text()) if path.exists() else {}
        if attempt in claims:
            raise ValueError("CPA_ATTEMPT_ALREADY_CLAIMED")
        allocated = sum(row["request_cap"] for row in claims.values() if row["phase"] == phase)
        if (
            allocated + cap > limits[phase]
            or sum(row["request_cap"] for row in claims.values()) + cap > 5292
        ):
            raise ValueError("CPA_CAMPAIGN_BUDGET_EXHAUSTED")
        row = {
            "campaign": campaign,
            "attempt_id": attempt,
            "run_id": run,
            "phase": phase,
            "request_cap": cap,
        }
        claims[attempt] = row
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(claims, ensure_ascii=False, indent=2) + "\n")
        temporary.chmod(0o600)
        temporary.replace(path)
        self.event({"event": "claim", **row})
        return {**row, "allocated_phase_requests": allocated + cap, "status": "CLAIMED"}

    def retry(self):
        matches = list(RETRY.finditer(self.config.read_text()))
        if len(matches) != 1:
            raise ValueError("CPA_RETRY_CONFIG_LAYOUT")
        return int(matches[0][1])

    def set_retry(self, value):
        original = self.config.read_text()
        matches = list(RETRY.finditer(original))
        if len(matches) != 1:
            raise ValueError("CPA_RETRY_CONFIG_LAYOUT")
        if int(matches[0][1]) == value:
            return None
        probe = self.reload_probe(value)
        changed = RETRY.sub(f"request-retry: {value}", original)
        # 保持绑定文件 inode，Docker 内的文件监听器随后读取新内容。
        with self.config.open("r+") as stream:
            stream.write(changed)
            stream.truncate()
            stream.flush()
            os.fsync(stream.fileno())
        if self.retry() != value:
            raise RuntimeError("CPA_RETRY_WRITE_FAILED")
        return probe

    def expire(self):
        state = self.state()
        if state and state["active"] and self.clock() - state["last_heartbeat"] >= TTL:
            self.set_retry(state["restore_retry"])
            state.update(active=False, restored_reason="HEARTBEAT_EXPIRED")
            self.save(state)
            self.event(
                {"event": "restored", "owner": state["owner"], "reason": "HEARTBEAT_EXPIRED"}
            )
        return state

    def rpc(self, request):
        action = request.get("action")
        with self.locked():
            state = self.expire()
            if action == "status":
                return {
                    "active": bool(state and state["active"]),
                    "owner": state["owner"] if state else None,
                    "request_retry": self.retry(),
                    "ttl_seconds": TTL,
                    "members": sorted(state.get("members", {}))
                    if state and state["active"]
                    else [],
                }
            if action == "claim":
                return self.claim(request)
            owner, member, token = (request.get(k, "") for k in ("owner", "member", "token"))
            if (
                not NAME.fullmatch(owner)
                or not NAME.fullmatch(member)
                or not re.fullmatch(r"[a-f0-9]{64}", token)
            ):
                raise ValueError("CPA_LEASE_IDENTITY_INVALID")
            digest = hashlib.sha256(token.encode()).hexdigest()
            if (
                state
                and state["active"]
                and (state["owner"] != owner or state["token_sha256"] != digest)
            ):
                raise ValueError("CPA_LEASE_BUSY")
            if action == "enter":
                if not state or not state["active"]:
                    if self.retry() != 2:
                        raise ValueError("CPA_RESTORE_BASELINE_MISMATCH")
                    state = {
                        "owner": owner,
                        "token_sha256": digest,
                        "restore_retry": 2,
                        "active": True,
                        "members": {},
                        "last_heartbeat": self.clock(),
                    }
                    # 先持久化恢复责任，进程中断后守护仍可恢复共享配置。
                    self.save(state)
                    probe = self.set_retry(0)
                    try:
                        state["configuration_reload"] = confirm_reload(probe) if probe else None
                    except Exception:
                        self.set_retry(2)
                        state.update(active=False, restored_reason="RELOAD_FAILED")
                        self.save(state)
                        raise
                state["members"][member] = self.clock()
                state["last_heartbeat"] = self.clock()
                self.save(state)
                self.event({"event": "enter", "owner": owner, "member": member, "request_retry": 0})
                return {
                    "active": True,
                    "request_retry": 0,
                    "configuration_reload": state.get("configuration_reload"),
                }
            if not state or not state["active"] or member not in state["members"]:
                raise ValueError("CPA_LEASE_MEMBER_MISSING")
            if action == "heartbeat":
                if self.retry() != 0:
                    raise ValueError("CPA_RETRY_CHANGED_DURING_EXPERIMENT")
                state["last_heartbeat"] = state["members"][member] = self.clock()
            elif action == "leave":
                del state["members"][member]
            elif action == "release":
                others = {
                    key: stamp
                    for key, stamp in state["members"].items()
                    if key != member and self.clock() - stamp < TTL
                }
                if others:
                    raise ValueError("CPA_LEASE_ACTIVE_MEMBERS")
                self.set_retry(state["restore_retry"])
                state.update(active=False, members={}, restored_reason="BATCH_COMPLETED")
                self.event({"event": "restored", "owner": owner, "reason": "BATCH_COMPLETED"})
            else:
                raise ValueError("CPA_LEASE_ACTION_INVALID")
            self.save(state)
            return {"active": state["active"], "request_retry": self.retry()}


def main():
    manager = LeaseManager()
    if sys.argv[1:] == ["monitor"]:
        while True:
            try:
                with manager.locked():
                    manager.expire()
            except Exception as error:
                manager.event({"event": "monitor_error", "error_type": type(error).__name__})
            time.sleep(5)
    elif sys.argv[1:] == ["rpc"]:
        try:
            raw = sys.stdin.buffer.read(8193)
            if len(raw) > 8192:
                raise ValueError("CPA_LEASE_RPC_TOO_LARGE")
            print(json.dumps(manager.rpc(json.loads(raw)), ensure_ascii=False))
        except Exception as error:
            print(
                json.dumps(
                    {
                        "error": str(error)
                        if isinstance(error, (ValueError, RuntimeError))
                        else type(error).__name__
                    }
                )
            )
            return 2
    else:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
