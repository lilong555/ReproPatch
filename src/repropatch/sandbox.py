"""固定 Docker 执行 profile、所属资源记录与删除确认；无宿主执行回退。"""

import json
import re
import shutil
import tempfile
import time
import uuid
from dataclasses import replace
from pathlib import Path

from .artifacts import AuditBudget
from .errors import CleanupUnconfirmed, ExecutionError, InfrastructureError, PolicyError
from .process import run_logged_process, run_process


class DockerSandbox:
    isolated = True

    def __init__(
        self,
        source: Path,
        image: str,
        *,
        timeout=60,
        resources=None,
        run_id=None,
        purpose=None,
        log_root=None,
        audit_budget=None,
        record=None,
    ):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_./:@-]{0,255}", image):
            raise ExecutionError("Invalid Docker image reference")
        if "," in str(source) or "\n" in str(source) or source.is_symlink():
            raise ExecutionError("SNAPSHOT_PATH: 快照路径不受支持")
        self.source = source.resolve()
        self.image = image
        self.timeout = timeout
        self.resources = resources
        self.name = "repropatch-" + uuid.uuid4().hex
        self.run_id = run_id or uuid.uuid4().hex
        self.purpose = purpose or source.name
        self.labels = {
            "repropatch.run": self.run_id,
            "repropatch.operation": self.name,
            "repropatch.purpose": self.purpose,
        }
        self.executable = shutil.which("docker") or "docker"
        self.image_id = ""
        self.container_id = None
        self.active = False
        self.created = False
        self.cleanup_confirmed = False
        self.cleanup_error = None
        self.record = record
        self.log_root = log_root
        self.audit_budget = audit_budget
        self._temporary = None
        self.profile_verified = False
        self.profile = None
        self.tools = None
        self.operation_deadline = None
        self._cleaning = False
        self.host_versions = {}

    def ownership(self):
        return {
            "name": self.name,
            "container_id": self.container_id,
            "run_id": self.run_id,
            "purpose": self.purpose,
            "labels": self.labels,
            "image_id": self.image_id,
            "snapshot": str(self.source),
            "active": self.active,
            "cleanup_confirmed": self.cleanup_confirmed,
            "cleanup_error": self.cleanup_error,
            "profile_verified": self.profile_verified,
            "profile": self.profile,
            "tools": self.tools,
        }

    def _record(self):
        if self.record is not None:
            self.record(self.ownership())

    def _docker(self, *args, timeout=15, allow_missing=False):
        if self.operation_deadline is not None and not self._cleaning:
            left = self.operation_deadline - time.monotonic()
            if left <= 0:
                raise ExecutionError("EXECUTION_DEADLINE: 阶段执行预算耗尽")
            timeout = min(timeout, left)
        try:
            result = run_process([self.executable, *args], timeout=timeout, output_limit=512 * 1024)
        except OSError as exc:
            raise ExecutionError("Docker is unavailable; no host fallback is permitted") from exc
        if allow_missing and not result.ok and not result.timed_out and not result.output_truncated:
            identifier = args[-1]
            message = result.stderr.strip()
            if result.stdout.strip() in {"", "[]"} and re.fullmatch(
                r"(?:Error response from daemon: |Error: )?No such (?:container|object): "
                + re.escape(identifier),
                message,
            ):
                return None
        if not result.ok or result.output_truncated:
            raise ExecutionError(f"DOCKER_FAILED: {args[0]}: {result.output[:2000]}")
        return result

    def _inspect(self, identifier, *, timeout=15):
        result = self._docker(
            "container", "inspect", identifier, timeout=timeout, allow_missing=True
        )
        if result is None:
            return None
        try:
            entries = json.loads(result.output)
            if (
                not isinstance(entries, list)
                or len(entries) != 1
                or not isinstance(entries[0], dict)
            ):
                raise ValueError("容器数量不符")
            return entries[0]
        except (ValueError, TypeError) as exc:
            raise ExecutionError("DOCKER_INSPECT: 容器状态无效") from exc

    def _verify_owner(self, info):
        identifier = info.get("Id", "")
        if (
            not re.fullmatch(r"[a-f0-9]{64}", identifier)
            or (self.container_id is not None and identifier != self.container_id)
            or info.get("Name") != "/" + self.name
            or info.get("Config", {}).get("Labels", {}) != self.actual_labels(info)
        ):
            raise CleanupUnconfirmed("CONTAINER_OWNERSHIP: 容器 ID、名称或 Run 标签不符")
        self.container_id = identifier

    def actual_labels(self, info):
        actual = info.get("Config", {}).get("Labels", {}) or {}
        return {**actual, **self.labels}

    def create_argv(self):
        memory = self.resources.memory_mib if self.resources else 768
        pids = self.resources.pids_limit if self.resources else 64
        cpus = self.resources.cpu_limit if self.resources else 1
        build_tmpfs = self.resources.build_tmpfs_mib if self.resources else 256
        args = [
            "create",
            "--name",
            self.name,
            "--pull=never",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            f"--pids-limit={pids}",
            f"--memory={memory}m",
            f"--memory-swap={memory}m",
            f"--cpus={cpus}",
            "--user=65534:65534",
            "--init",
            "--no-healthcheck",
            "--restart=no",
            "--ulimit=nofile=256:256",
            "--ulimit=core=0:0",
            "--ipc=none",
            "--log-driver=none",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
            f"--tmpfs=/build:rw,exec,nosuid,nodev,size={build_tmpfs}m,uid=65534,gid=65534,mode=0700",
            "--mount",
            f"type=bind,source={self.source},target=/src,readonly",
            "--workdir=/build",
            "--env=HOME=/tmp",
            "--env=TMPDIR=/tmp",
            "--env=LANG=C.UTF-8",
            "--env=LC_ALL=C.UTF-8",
            "--env=CMAKE_BUILD_PARALLEL_LEVEL=2",
            "--env=CTEST_PARALLEL_LEVEL=1",
        ]
        for name, value in self.labels.items():
            args += ["--label", f"{name}={value}"]
        return args + ["--entrypoint=/usr/bin/sleep", self.image_id or self.image, "infinity"]

    def _verify_profile(self, info):
        self._verify_owner(info)
        host = info["HostConfig"]
        config = info["Config"]
        memory = (self.resources.memory_mib if self.resources else 768) * 1024 * 1024
        pids = self.resources.pids_limit if self.resources else 64
        cpus = self.resources.cpu_limit if self.resources else 1
        required = {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Privileged": False,
            "Memory": memory,
            "MemorySwap": memory,
            "PidsLimit": pids,
            "NanoCpus": round(cpus * 1_000_000_000),
            "Init": True,
            "IpcMode": "none",
        }
        binds = [m for m in info.get("Mounts", []) if m.get("Type") == "bind"]
        if (
            any(host.get(k) != v for k, v in required.items())
            or host.get("CapDrop") != ["ALL"]
            or host.get("SecurityOpt") != ["no-new-privileges:true"]
            or host.get("RestartPolicy", {}).get("Name") != "no"
            or host.get("LogConfig", {}).get("Type") != "none"
            or host.get("PidMode")
            or host.get("Devices")
            or host.get("DeviceRequests")
            or config.get("User") != "65534:65534"
            or config.get("Tty")
            or config.get("Entrypoint") != ["/usr/bin/sleep"]
            or config.get("Cmd") != ["infinity"]
            or config.get("Healthcheck", {}).get("Test") != ["NONE"]
            or info.get("Image") != self.image_id
            or len(binds) != 1
            or binds[0].get("Source") != str(self.source)
            or binds[0].get("Destination") != "/src"
            or binds[0].get("RW")
            or any(
                m.get("Destination") not in {"/src", "/tmp", "/build"}
                for m in info.get("Mounts", [])
            )
        ):
            raise ExecutionError("DOCKER_PROFILE: 实际容器权限或挂载不符合固定配置")
        expected_tmpfs = {}
        for arg in self.create_argv():
            if arg.startswith("--tmpfs="):
                target, options = arg.removeprefix("--tmpfs=").split(":", 1)
                expected_tmpfs[target] = options
        if host.get("Tmpfs") != expected_tmpfs:
            raise ExecutionError("DOCKER_PROFILE: tmpfs 限额或权限不符")
        self.profile_verified = True
        self.profile = {
            "host_config": {
                key: host.get(key)
                for key in (
                    *required,
                    "Tmpfs",
                    "SecurityOpt",
                    "CapDrop",
                    "RestartPolicy",
                    "LogConfig",
                    "Devices",
                    "DeviceRequests",
                    "PidMode",
                )
            },
            "config": {
                key: config.get(key) for key in ("User", "Tty", "Entrypoint", "Cmd", "Healthcheck")
            },
            "mounts": info.get("Mounts"),
        }

    def __enter__(self):
        try:
            info = json.loads(self._docker("info", "--format", "{{json .}}").output)
            if any(
                info.get(key) is not True
                for key in ("MemoryLimit", "SwapLimit", "CpuCfsQuota", "PidsLimit")
            ):
                raise ExecutionError("DOCKER_RESOURCES: daemon 不支持要求的 cgroup 限额")
            self.host_versions = {"docker_server": str(info.get("ServerVersion", "unknown"))}
            image = json.loads(self._docker("image", "inspect", self.image).output)[0]
            self.image_id = image["Id"]
            if not re.fullmatch(r"sha256:[a-f0-9]{64}", self.image_id) or image.get(
                "Config", {}
            ).get("Volumes"):
                raise ExecutionError("DOCKER_IMAGE: 镜像身份无效或包含额外 VOLUME")
            self.host_versions["docker_client"] = self._docker(
                "version", "--format", "{{.Client.Version}}"
            ).output.strip()
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            raise ExecutionError("DOCKER_PREFLIGHT: 镜像或 daemon 返回无效状态") from exc
        try:
            self._record()
            self.created = True
            created = self._docker(*self.create_argv()).output.strip()
            if not re.fullmatch(r"[a-f0-9]{64}", created):
                raise ExecutionError("DOCKER_CREATE: 未返回完整容器 ID")
            self.container_id = created
            actual = self._inspect(created)
            if actual is None:
                raise ExecutionError("DOCKER_CREATE: 容器创建后不存在")
            self._verify_profile(actual)
            self._record()
            self._docker("start", self.container_id)
            self.active = True
            self._record()
            return self
        except BaseException as error:
            try:
                self.close()
            except Exception as cleanup:
                error.add_note(f"容器清理失败：{cleanup}")
            raise

    def preflight(self):
        result = self.run(
            (
                "/bin/sh",
                "-ec",
                "command -v cmake; command -v ctest; command -v c++; "
                "command -v cat; command -v timeout; /usr/bin/sleep --version; "
                "cmake --version; ctest --version; "
                "printf '\\nREPROPATCH_CXX_VERSION\\n'; c++ --version",
            )
        )
        if not result.ok:
            return result
        versions = dict(
            re.findall(r"(cmake|ctest) version ([0-9]+\.[0-9]+(?:\.[0-9]+)?)", result.output)
        )
        if len(versions) != 2 or any(
            tuple(map(int, v.split(".")[:2])) < (3, 26) for v in versions.values()
        ):
            return replace(
                result,
                status="infra_error",
                error_code="IMAGE_TOOLS",
                error="IMAGE_TOOLS: 要求 CMake/CTest >= 3.26",
            )
        self.tools = {
            **self.host_versions,
            "cxx": result.stdout.split("REPROPATCH_CXX_VERSION\n", 1)[-1].splitlines()[0],
            "versions": versions,
            "paths": dict(
                zip(
                    ("cmake", "ctest", "c++", "cat", "timeout"),
                    result.stdout.splitlines()[:5],
                    strict=True,
                )
            ),
        }
        self._record()
        return result

    def run(self, argv, *, cwd="/build"):
        if cwd not in {"/src", "/build"}:
            raise PolicyError("INVALID_ARGUMENT: 容器工作目录不受支持")
        if not self.active:
            raise ExecutionError("SANDBOX_INACTIVE: 容器已停止或清理未确认")
        if self.log_root is None:
            self._temporary = tempfile.TemporaryDirectory(prefix="repropatch-logs-")
            self.log_root = Path(self._temporary.name)
            self.audit_budget = AuditBudget(self.log_root)
        result = run_logged_process(
            [self.executable, "exec", f"--workdir={cwd}", self.container_id, *argv],
            root=self.log_root,
            budget=self.audit_budget,
            timeout=self.timeout,
            container_id=self.container_id,
            on_stop=lambda reason: self.close(),
            on_started=(
                lambda cid: self.audit_log.command_started(
                    cid, argv, cwd, self.container_id, self.audit_payload
                )
            )
            if getattr(self, "audit_log", None) is not None
            else None,
        )
        status = result.status
        error = result.error
        if status == "exited":
            try:
                state = self._inspect(self.container_id)
                if state is None:
                    raise ExecutionError("CONTAINER_LOST: 命令后容器不存在")
                self._verify_owner(state)
                if state.get("State", {}).get("OOMKilled") is True:
                    status = "oom_killed"
                    self.close()
                elif state.get("State", {}).get("Running") is not True or result.returncode in {
                    125,
                    126,
                    127,
                }:
                    status = "infra_error"
                    error = "CONTAINER_EXEC: 命令启动失败或容器状态矛盾"
                    self.close()
            except InfrastructureError as exc:
                status = "infra_error"
                error = str(exc)
        if status != "exited" and self.created:
            try:
                self.close()
            except InfrastructureError as cleanup:
                error = f"{error or status}; {cleanup}"
        result = replace(
            result,
            argv=tuple(argv),
            cwd=cwd,
            status=status,
            error=error,
            error_code=result.error_code or (status.upper() if status != "exited" else None),
            cleanup_confirmed=self.cleanup_confirmed,
        )
        if getattr(self, "audit_log", None) is not None:
            self.audit_log.command_finished(result, self.audit_payload)
        return result

    def close(self):
        self.active = False
        if not self.created:
            if not self.cleanup_confirmed:
                self.cleanup_confirmed = True
                self._record()
            return
        self._cleaning = True
        deadline = time.monotonic() + 10

        def remaining():
            value = deadline - time.monotonic()
            if value <= 0:
                raise CleanupUnconfirmed("CLEANUP_DEADLINE: 容器清理预算耗尽")
            return value

        try:
            identifier = self.container_id or self.name
            actual = self._inspect(identifier, timeout=remaining())
            if actual is not None:
                self._verify_owner(actual)
                self._docker("rm", "--force", self.container_id, timeout=remaining())
            if self._inspect(self.container_id or self.name, timeout=remaining()) is not None:
                raise CleanupUnconfirmed("CLEANUP_UNCONFIRMED: 删除后容器仍存在")
            self.cleanup_confirmed = True
            self.created = False
            self._record()
        except Exception as exc:
            self.cleanup_error = str(exc)
            try:
                self._record()
            except Exception as record_error:
                exc.add_note(f"资源清理记录失败：{record_error}")
            raise CleanupUnconfirmed(f"CLEANUP_UNCONFIRMED: {exc}") from exc
        finally:
            self._cleaning = False

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.close()
        except InfrastructureError as cleanup:
            if exc is None:
                raise
            exc.add_note(f"容器清理失败：{cleanup}")
