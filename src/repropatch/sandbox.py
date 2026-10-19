"""Docker is the only production execution backend. No host execution fallback."""

import re
import shutil
import uuid
from pathlib import Path

from .errors import InfrastructureError
from .process import CommandResult, run_process


class DockerSandbox:
    isolated = True

    def __init__(self, source: Path, image: str, *, timeout: float = 60):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_./:@-]{0,255}", image):
            raise InfrastructureError("Invalid Docker image reference")
        if "," in str(source) or "\n" in str(source):
            raise InfrastructureError("Snapshot paths containing commas/newlines are unsupported")
        self.source = source.resolve()
        self.image = image
        self.timeout = timeout
        self.name = "repropatch-" + uuid.uuid4().hex
        self.executable = shutil.which("docker") or "docker"
        self.image_id = ""
        self.active = False
        self.created = False

    def _docker(self, *args, timeout=15):
        try:
            result = run_process([self.executable, *args], timeout=timeout)
        except OSError as exc:
            raise InfrastructureError(
                "Docker is unavailable; no host fallback is permitted"
            ) from exc
        if not result.ok:
            raise InfrastructureError(f"Docker {args[0]} failed: {result.output[:2000]}")
        return result

    def create_argv(self) -> list[str]:
        return [
            "create",
            "--name",
            self.name,
            "--pull=never",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--pids-limit=64",
            "--memory=768m",
            "--memory-swap=768m",
            "--cpus=1",
            "--user=65534:65534",
            "--init",
            "--ulimit=nofile=256:256",
            "--ulimit=core=0:0",
            "--ipc=none",
            "--log-driver=none",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
            "--tmpfs=/build:rw,exec,nosuid,nodev,size=256m,mode=1777",
            "--mount",
            f"type=bind,source={self.source},target=/src,readonly",
            "--workdir=/build",
            "--env=HOME=/tmp",
            "--env=LANG=C.UTF-8",
            "--env=LC_ALL=C.UTF-8",
            "--env=CMAKE_BUILD_PARALLEL_LEVEL=2",
            "--entrypoint=/usr/bin/python3",
            self.image_id or self.image,
            "-I",
            "-c",
            "import time; time.sleep(86400)",
        ]

    def __enter__(self):
        self._docker("info", "--format", "{{.ServerVersion}}")
        self.image_id = self._docker(
            "image", "inspect", "--format", "{{.Id}}", self.image
        ).output.strip()
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", self.image_id):
            raise InfrastructureError("Docker did not return a content-addressed image ID")
        try:
            self.created = True
            self._docker(*self.create_argv())
            self._docker("start", self.name)
            self.active = True
        except BaseException as error:
            try:
                self.close()
            except InfrastructureError as cleanup_error:
                error.add_note(f"Cleanup of {self.name} also failed: {cleanup_error}")
            raise
        return self

    def run(self, argv: tuple[str, ...]) -> CommandResult:
        if not self.active:
            raise InfrastructureError("Sandbox is not active")
        result = run_process(
            [self.executable, "exec", "--workdir=/build", self.name, *argv], timeout=self.timeout
        )
        # A timeout invalidates the whole container, killing all build subprocesses.
        if result.timed_out:
            self.close()
        elif result.returncode in {125, 126, 127}:
            raise InfrastructureError(
                f"Container command could not execute: {result.output[:2000]}"
            )
        return CommandResult(
            tuple(argv),
            result.returncode,
            result.output,
            result.duration_seconds,
            result.timed_out,
            result.output_truncated,
        )

    def close(self):
        self.active = False
        if self.created:
            self._docker("rm", "--force", self.name)
            self.created = False

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.close()
        except InfrastructureError as cleanup_error:
            if exc is None:
                raise
            exc.add_note(f"Cleanup of {self.name} also failed: {cleanup_error}")
