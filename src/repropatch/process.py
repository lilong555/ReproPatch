"""双流原始证据、有界输出、单调时限和进程组清理。"""

import hashlib
import os
import selectors
import signal
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .artifacts import EvidenceRef

RAW_OUTPUT_LIMIT = 4 * 1024 * 1024
PREVIEW_LIMIT = 64 * 1024


def host_env() -> dict[str, str]:
    return {
        "PATH": os.defpath + ":/usr/local/bin",
        "HOME": "/nonexistent",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_ATTR_NOSYSTEM": "1",
    }


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int | None
    output: str
    duration_seconds: float
    timed_out: bool = False
    output_truncated: bool = False
    status: str = "exited"
    command_id: str | None = None
    cwd: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    stdout: str = ""
    stderr: str = ""
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    stdout_log: EvidenceRef | None = None
    stderr_log: EvidenceRef | None = None
    container_id: str | None = None
    cleanup_confirmed: bool = False
    error_code: str | None = None
    error: str | None = None
    truncated: bool = False

    def __post_init__(self):
        if self.timed_out and self.status == "exited":
            object.__setattr__(self, "status", "timed_out")

    @property
    def ok(self) -> bool:
        return self.status == "exited" and self.returncode == 0

    def to_dict(self) -> dict:
        result = asdict(self)
        result["exit_code"] = self.returncode
        result["duration_ms"] = round(self.duration_seconds * 1000)
        return result

    def contains(self, marker, root):
        if self.status != "exited" or self.output_truncated:
            return False
        if self.stdout_log is None or self.stderr_log is None:
            # 仅供显式注入的受信任测试后端；生产 Docker 必须有两个引用。
            return marker in self.output
        needle = marker.encode("utf-8")
        return any(
            needle in ref.read(root, limit=RAW_OUTPUT_LIMIT)
            for ref in (self.stdout_log, self.stderr_log)
        )


@dataclass(frozen=True)
class RawResult:
    """共享宿主进程循环的二进制结果，不直接放入事件。"""

    argv: tuple[str, ...]
    returncode: int
    stdout: bytes
    stderr: bytes
    duration_seconds: float
    timed_out: bool = False
    output_truncated: bool = False
    stdout_bytes_seen: int = 0
    stderr_bytes_seen: int = 0
    status: str = "exited"
    error: str | None = None

    @property
    def ok(self):
        return self.returncode == 0 and self.status == "exited"


def run_process(
    argv, *, cwd=None, timeout=60, output_limit=64_000, env=None, decode_errors="replace"
) -> CommandResult:
    result = run_process_bytes(argv, cwd=cwd, timeout=timeout, output_limit=output_limit, env=env)
    return CommandResult(
        result.argv,
        result.returncode,
        (result.stdout + result.stderr).decode("utf-8", decode_errors),
        result.duration_seconds,
        result.timed_out,
        result.output_truncated,
        status=result.status,
        error=result.error,
        stdout=result.stdout.decode("utf-8", decode_errors),
        stderr=result.stderr.decode("utf-8", decode_errors),
    )


def run_process_bytes(
    argv,
    *,
    cwd: Path | None = None,
    timeout=60,
    output_limit=64_000,
    env=None,
    hard_limit=False,
    on_data=None,
    on_stop=None,
) -> RawResult:
    """持续读取两个管道；硬限额或取消时先清理执行容器，再回收宿主客户端。"""
    start = time.monotonic()
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    seen = {"stdout": 0, "stderr": 0}
    captured = 0
    status = "exited"
    truncated = False
    error = None
    with subprocess.Popen(
        list(argv),
        cwd=cwd,
        env=host_env() if env is None else env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    ) as proc:
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
            selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
            try:
                while selector.get_map():
                    left = timeout - (time.monotonic() - start)
                    if left <= 0:
                        status = "timed_out"
                        break
                    for key, _ in selector.select(min(left, 0.1)):
                        data = os.read(key.fileobj.fileno(), 8192)
                        if not data:
                            selector.unregister(key.fileobj)
                            continue
                        seen[key.data] += len(data)
                        room = max(0, output_limit - captured)
                        kept = data[:room]
                        streams[key.data].extend(kept)
                        captured += len(kept)
                        if on_data is not None:
                            on_data(key.data, kept)
                        truncated |= len(data) > room
                        if hard_limit and sum(seen.values()) >= output_limit:
                            truncated = True
                            status = "output_limit"
                            break
                    if status != "exited":
                        break
                if status == "exited":
                    try:
                        proc.wait(timeout=max(0.001, timeout - (time.monotonic() - start)))
                    except subprocess.TimeoutExpired:
                        status = "timed_out"
            except KeyboardInterrupt:
                status = "cancelled"
            except Exception as exc:
                status = "infra_error"
                error = f"COMMAND_IO: {exc}"
            finally:
                # 先关闭本地输出生产者，避免 Docker 删除等待仍被管道背压阻塞的 exec。
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                if status != "exited" and on_stop is not None:
                    try:
                        on_stop(status)
                    except Exception as exc:
                        error = f"{error or status}; CLEANUP_UNCONFIRMED: {exc}"
                proc.wait()
    return RawResult(
        tuple(argv),
        proc.returncode,
        bytes(streams["stdout"]),
        bytes(streams["stderr"]),
        time.monotonic() - start,
        status == "timed_out",
        truncated,
        seen["stdout"],
        seen["stderr"],
        status,
        error,
    )


def preview(data, limit):
    text = data.decode("utf-8", "replace")
    text = "".join(
        char
        if char in "\n\t" or (ord(char) >= 32 and not 127 <= ord(char) < 160)
        else f"\\x{ord(char):02x}"
        for char in text
    )
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    marker = b"\n[... omitted ...]\n"
    room = max(0, limit - len(marker))
    return (
        encoded[: room // 2].decode("utf-8", "ignore")
        + marker.decode()
        + encoded[-(room - room // 2) :].decode("utf-8", "ignore")
    ), True


def run_logged_process(
    argv, *, root, budget, timeout, container_id=None, on_stop=None, on_started=None
):
    """每条执行命令直接写两份原始文件；启动失败也保留已创建的零字节证据。"""
    command_id = uuid.uuid4().hex
    if on_started is not None:
        on_started(command_id)
    started = datetime.now(UTC).isoformat()
    start = time.monotonic()
    handles = {}
    refs = {"stdout": None, "stderr": None}
    result = None
    failure = None
    directory = root / "logs" / command_id
    try:
        if budget is not None:
            budget.check(RAW_OUTPUT_LIMIT + 8192)
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        directory.parent.mkdir(mode=0o700, exist_ok=True)
        directory.mkdir(mode=0o700)
        for name in refs:
            descriptor = os.open(
                directory / f"{name}.bin",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            handles[name] = os.fdopen(descriptor, "wb")
        result = run_process_bytes(
            argv,
            timeout=timeout,
            output_limit=RAW_OUTPUT_LIMIT,
            hard_limit=True,
            on_data=lambda name, data: handles[name].write(data),
            on_stop=on_stop,
        )
    except KeyboardInterrupt:
        failure = "cancelled"
        if on_stop is not None:
            on_stop("cancelled")
    except Exception as exc:
        failure = str(exc)
        if on_stop is not None:
            try:
                on_stop("infra_error")
            except Exception as cleanup:
                failure += f"; CLEANUP_UNCONFIRMED: {cleanup}"
    finally:
        for name, handle in handles.items():
            try:
                handle.flush()
                os.fsync(handle.fileno())
            except OSError as exc:
                failure = f"{failure + '; ' if failure else ''}LOG_IO: {exc}"
            finally:
                try:
                    handle.close()
                except OSError as exc:
                    failure = f"{failure + '; ' if failure else ''}LOG_CLOSE: {exc}"
            path = directory / f"{name}.bin"
            try:
                data = path.read_bytes()

                refs[name] = EvidenceRef(
                    str(path.relative_to(root)), hashlib.sha256(data).hexdigest(), len(data)
                )
            except OSError as exc:
                failure = f"{failure + '; ' if failure else ''}LOG_IO: {exc}"
    if failure and result is not None and result.status == "exited" and on_stop is not None:
        try:
            on_stop("infra_error")
        except Exception as cleanup:
            failure += f"; CLEANUP_UNCONFIRMED: {cleanup}"
    stdout_data = b"" if result is None else result.stdout
    stderr_data = b"" if result is None else result.stderr
    stdout, stdout_cut = preview(stdout_data, PREVIEW_LIMIT // 2)
    stderr, stderr_cut = preview(stderr_data, PREVIEW_LIMIT // 2)
    if result is not None and result.status in {"timed_out", "cancelled", "output_limit"}:
        status = result.status
    else:
        status = (
            ("cancelled" if failure == "cancelled" else "infra_error") if failure else result.status
        )
    return CommandResult(
        tuple(argv),
        None if result is None or status in {"infra_error", "cancelled"} else result.returncode,
        stdout + stderr,
        time.monotonic() - start,
        status == "timed_out",
        bool(failure) or (result is not None and result.output_truncated),
        status=status,
        command_id=command_id,
        cwd="/build",
        started_at=started,
        finished_at=datetime.now(UTC).isoformat(),
        stdout=stdout,
        stderr=stderr,
        stdout_bytes=len(stdout_data),
        stderr_bytes=len(stderr_data),
        stdout_log=refs["stdout"],
        stderr_log=refs["stderr"],
        container_id=container_id,
        error_code="COMMAND_IO" if failure else (status.upper() if status != "exited" else None),
        error=failure or result.error,
        truncated=stdout_cut or stderr_cut or status == "output_limit",
    )
