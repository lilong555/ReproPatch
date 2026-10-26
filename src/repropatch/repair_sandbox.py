"""Attempt 内持久的修复容器；命令间冻结进程，源码经宿主审计后同步。"""

from .errors import ExecutionError, PolicyError
from .sandbox import DockerSandbox
from .task import relative_file
from .workspace import _source_file


class PersistentRepairSandbox(DockerSandbox):
    def __init__(self, source, image, *, editable, **options):
        super().__init__(source, image, **options)
        self.editable = tuple(sorted(set(editable)))
        self.paused = False
        self.idle_pids = None
        for name in self.editable:
            relative_file(name)
            if "," in name or "\n" in name:
                raise PolicyError("SHELL_PATH: 可写挂载路径含不支持的字符")
            _source_file(self.source, name)

    def bind_mounts(self):
        return {
            **super().bind_mounts(),
            **{"/src/" + name: (str(self.source / name), True) for name in self.editable},
        }

    def ownership(self):
        return {
            **super().ownership(),
            "kind": "repair",
            "paused": self.paused,
            "idle_pids": sorted(self.idle_pids) if self.idle_pids is not None else None,
            "editable_files": list(self.editable),
        }

    def __enter__(self):
        for name in self.editable:
            _, _, info = _source_file(self.source, name)
            (self.source / name).chmod((info.st_mode & 0o777) | 0o002)
        try:
            super().__enter__()
            probe = super().run(
                (
                    "/bin/bash",
                    "--noprofile",
                    "--norc",
                    "-c",
                    "command -v bash && command -v python3 && command -v cmake "
                    "&& command -v ctest && command -v grep",
                )
            )
            if not probe.ok:
                raise ExecutionError(
                    "IMAGE_TOOLS: Shell 修复要求 Bash、Python、CMake、CTest 和 grep"
                )
            self._pause()
            self.idle_pids = self._live_pids()
            if not 1 <= len(self.idle_pids) <= 2:
                raise ExecutionError("SHELL_PROCESS_STATE: 初始容器进程集合无效")
            self.assert_idle()
            self._record()
            return self
        except BaseException as error:
            try:
                self.close()
            except Exception as cleanup:
                error.add_note(f"修复容器初始化后的清理失败：{cleanup}")
            raise

    def _live_pids(self):
        result = self._docker("top", self.container_id, "-eo", "pid,stat")
        lines = result.stdout.splitlines()
        if not lines or lines[0].split() != ["PID", "STAT"]:
            raise ExecutionError("SHELL_PROCESS_STATE: 容器进程清单格式无效")
        pids = set()
        for line in lines[1:]:
            fields = line.split()
            if len(fields) != 2 or not fields[0].isdigit() or not fields[1]:
                raise ExecutionError("SHELL_PROCESS_STATE: 容器进程清单格式无效")
            if not fields[1].startswith("Z"):
                pids.add(int(fields[0]))
        return frozenset(pids)

    def _pause(self):
        self._docker("pause", self.container_id)
        self.paused = True

    def assert_idle(self):
        info = self._inspect(self.container_id)
        if info is None:
            raise ExecutionError("CONTAINER_LOST: 修复容器已消失")
        self._verify_profile(info)
        state = info.get("State", {})
        if (
            not self.active
            or not self.paused
            or state.get("Running") is not True
            or state.get("Paused") is not True
            or state.get("OOMKilled")
        ):
            raise ExecutionError("SHELL_NOT_QUIESCENT: 修复容器须处于已冻结的空闲状态")
        if self.idle_pids is None or self._live_pids() != self.idle_pids:
            raise ExecutionError("SHELL_PROCESS_LEAK: 命令结束后仍有派生进程")

    def execute(self, command, *, cwd="/src"):
        self.assert_idle()
        self.paused = False
        self._record()
        try:
            self._docker("unpause", self.container_id)
            result = super().run(("/bin/bash", "--noprofile", "--norc", "-c", command), cwd=cwd)
            if self.active:
                self._pause()
                self.assert_idle()
                self._record()
            return result
        except BaseException as error:
            try:
                self.close()
            except Exception as cleanup:
                error.add_note(f"修复命令后的清理失败：{cleanup}")
            raise

    def exec_start_failed(self, argv, result):
        # Bash 已经预检，126/127 可表示命令权限或程序缺失，属于模型可见反馈。
        return argv[0] != "/bin/bash" and super().exec_start_failed(argv, result)

    def close(self):
        self.paused = False
        super().close()
