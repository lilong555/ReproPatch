"""Bounded output, monotonic deadlines, process-group cleanup, sanitized host env."""

import os
import selectors
import signal
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path


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
    }


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    output: str
    duration_seconds: float
    timed_out: bool = False
    output_truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def to_dict(self) -> dict:
        return asdict(self)


def run_process(
    argv,
    *,
    cwd: Path | None = None,
    timeout: float = 60,
    output_limit: int = 64_000,
    env: dict | None = None,
) -> CommandResult:
    start = time.monotonic()
    output = bytearray()
    timed_out = False
    truncated = False
    # No inherited stdin or environment. Kill the entire process group on timeout,
    # including a child retaining the stdout pipe after its parent exits.
    with subprocess.Popen(
        list(argv),
        cwd=cwd,
        env=host_env() if env is None else env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    ) as proc:
        assert proc.stdout is not None
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            try:
                while selector.get_map():
                    left = timeout - (time.monotonic() - start)
                    if left <= 0:
                        timed_out = True
                        break
                    for key, _ in selector.select(min(left, 0.1)):
                        data = os.read(key.fileobj.fileno(), 8192)
                        if not data:
                            selector.unregister(key.fileobj)
                        else:
                            room = max(0, output_limit - len(output))
                            output.extend(data[:room])
                            truncated |= len(data) > room
                if not timed_out:
                    try:
                        proc.wait(timeout=max(0.001, timeout - (time.monotonic() - start)))
                    except subprocess.TimeoutExpired:
                        timed_out = True
            finally:
                # Also reap background processes after a nominally successful command.
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
    return CommandResult(
        tuple(argv),
        proc.returncode,
        output.decode("utf-8", "replace"),
        time.monotonic() - start,
        timed_out,
        truncated,
    )
