"""本 Run 独占目录、文件锁、资源身份与保留策略。"""

import fcntl
import json
import os
import shutil
from pathlib import Path

from .artifacts import MAX_AUDIT_BYTES, AuditBudget, read_regular
from .errors import InfrastructureError, SourceChanged


class RunLock:
    def __init__(self, directory):
        self.path = directory / ".run.lock"
        self.descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(self.descriptor)
            if (
                info.st_uid != os.getuid()
                or info.st_nlink != 1
                or info.st_mode & 0o777 != 0o600
                or not self.path.is_file()
            ):
                raise InfrastructureError("RUN_LOCK: 锁文件身份或权限不符")
            fcntl.flock(self.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(self.descriptor)
            raise

    def close(self):
        if self.descriptor is not None:
            os.close(self.descriptor)
            self.descriptor = None

    def assert_held(self, directory):
        """数据库写者必须持有本 Run 的活锁描述符及原始路径身份。"""
        if self.descriptor is None or self.path != Path(directory) / ".run.lock":
            raise InfrastructureError("RUN_LOCK: 未持有所属 Run 的排他锁")
        info = os.fstat(self.descriptor)
        observed = self.path.lstat()
        if (info.st_dev, info.st_ino) != (observed.st_dev, observed.st_ino) or any(
            parent.is_symlink() for parent in self.path.parents
        ):
            raise InfrastructureError("RUN_LOCK: 锁路径或目录发生变化")


class RunResources:
    @classmethod
    def open_existing(cls, directory, lock, snapshot):
        """仅接管原控制目录；资源删除只使用数据库已登记的容器身份。"""
        directory = Path(directory).absolute()
        data = json.loads(read_regular(directory / "resources.json", limit=MAX_AUDIT_BYTES)[0])
        origin = snapshot.events[0]["payload"]
        current = cls._identity(directory)
        if (
            data["schema_version"] != 1
            or data["run_id"] != snapshot.run_id
            or data["owner_uid"] != os.getuid()
            or current != tuple(origin["control_identity"])
            or current != tuple(data["control_identity"])
            or data["control_directory"] != str(directory)
        ):
            raise InfrastructureError("RUN_OWNERSHIP: 控制目录与原登记不符")
        obj = cls.__new__(cls)
        obj.run_id, obj.directory, obj.lock = snapshot.run_id, directory, lock
        obj.workspace = Path(data["workspace_directory"])
        obj._directory_identity = current
        obj._workspace_identity = None
        if obj.workspace.exists() or obj.workspace.is_symlink():
            observed = cls._identity(obj.workspace)
            if observed != tuple(data["workspace_identity"]):
                raise InfrastructureError("WORKSPACE_DIVERGED: 工作区根身份发生变化")
            obj._workspace_identity = observed
        obj.repository, obj.commit = data["repository"], data["commit"]
        obj.image_id = snapshot.run["image_id"]
        obj.budget = AuditBudget(directory)
        obj.worktrees = []
        obj.prior_worktrees = data["worktrees"]
        obj.snapshots = {entry["path"]: entry for entry in data["snapshots"]}
        obj.compiler_cache = data.get("compiler_cache")
        obj.containers = {}
        for event in snapshot.events:
            p = event["payload"]
            if event["type"] == "resource_registered" and p.get("resource_type") == "container":
                obj.containers[p["name"]] = {
                    key: value for key, value in p.items() if key != "resource_type"
                }
        obj.cleanup_errors = []
        obj.event_log = None
        obj.assert_owned()
        return obj

    def __init__(self, output_root, workspace_root, run_id, repository, commit):
        self.run_id = run_id
        self.directory = Path(output_root) / run_id
        self.workspace = Path(workspace_root) / run_id
        self.directory.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.directory.mkdir(mode=0o700)
        self._directory_identity = self._identity(self.directory)
        self.lock = RunLock(self.directory)
        self.budget = AuditBudget(self.directory)
        self.repository = str(repository.resolve())
        self.commit = commit
        self.worktrees = []
        self.snapshots = {}
        self.compiler_cache = None
        self.containers = {}
        self.cleanup_errors = []
        self.event_log = None
        self._workspace_identity = None
        try:
            self.workspace.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            self.workspace.mkdir(mode=0o700)
            self._workspace_identity = self._identity(self.workspace)
            self.save()
        except BaseException:
            self.lock.close()
            raise

    @staticmethod
    def _identity(path):
        info = path.lstat()
        if path.is_symlink() or not path.is_dir() or info.st_uid != os.getuid():
            raise SourceChanged("RUN_OWNERSHIP: 所属目录无效")
        return info.st_dev, info.st_ino

    def assert_owned(self):
        for path, identity in (
            (self.directory, self._directory_identity),
            (self.workspace, self._workspace_identity),
        ):
            if identity is None and path == self.workspace and not path.exists():
                continue
            if (
                self._identity(path) != identity
                or path.stat().st_mode & 0o777 != 0o700
                or any(parent.is_symlink() for parent in path.parents)
            ):
                raise SourceChanged("RUN_OWNERSHIP: 所属根目录或权限发生变化")
        lock_info = os.fstat(self.lock.descriptor)
        path_info = self.lock.path.lstat()
        if (lock_info.st_dev, lock_info.st_ino) != (path_info.st_dev, path_info.st_ino):
            raise SourceChanged("RUN_OWNERSHIP: 锁路径发生变化")

    def data(self):
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "owner_uid": os.getuid(),
            "control_identity": list(self._directory_identity),
            "workspace_identity": list(self._workspace_identity)
            if self._workspace_identity
            else None,
            "lock_path": str(self.lock.path),
            "repository": self.repository,
            "commit": self.commit,
            "control_directory": str(self.directory),
            "workspace_directory": str(self.workspace),
            "worktrees": list(
                {
                    entry["path"]: entry
                    for entry in [
                        *getattr(self, "prior_worktrees", []),
                        *(dict(work.ownership(), exists=work.created) for work in self.worktrees),
                    ]
                }.values()
            ),
            "snapshots": list(self.snapshots.values()),
            "compiler_cache": self.compiler_cache,
            "containers": list(self.containers.values()),
            "cleanup_errors": self.cleanup_errors,
        }

    def save(self, *, emergency=False):
        self.assert_owned()
        self.budget.write(
            "resources.json",
            json.dumps(self.data(), ensure_ascii=False, indent=2).encode() + b"\n",
            emergency=emergency,
        )

    def register_worktree(self, worktree):
        self.assert_owned()
        if worktree.path.parent != self.workspace:
            raise InfrastructureError("WORKTREE_OWNERSHIP: 工作树不在本 Run 工作区")
        self.worktrees.append(worktree)
        self.save()

    def prepare_compiler_cache(self):
        """只在本 Run 根内创建一个可丢弃的 ccache，绝不用于最终冷验收。"""
        self.assert_owned()
        path = self.workspace / "compiler-cache"
        if self.compiler_cache is None or not self.compiler_cache["exists"]:
            path.mkdir(mode=0o777)
            path.chmod(0o777)  # 容器内固定 nobody UID；宿主父目录始终为 0700。
            self.compiler_cache = {
                "path": str(path),
                "identity": list(self._identity(path)),
                "exists": True,
            }
            self.save()
        elif self._identity(path) != tuple(self.compiler_cache["identity"]):
            raise SourceChanged("CACHE_OWNERSHIP: 编译缓存目录身份发生变化")
        return path

    def remove_compiler_cache(self):
        if self.compiler_cache is None or not self.compiler_cache["exists"]:
            return
        path = self.workspace / "compiler-cache"
        if (
            str(path) != self.compiler_cache["path"]
            or self._identity(path) != tuple(self.compiler_cache["identity"])
            or not shutil.rmtree.avoids_symlink_attacks
        ):
            raise SourceChanged("CACHE_OWNERSHIP: 不删除身份不明的编译缓存")
        shutil.rmtree(path)
        self.compiler_cache["exists"] = False

    def record_container(self, record):
        if record["run_id"] != self.run_id:
            raise InfrastructureError("CONTAINER_OWNERSHIP: Run 不符")
        self.containers[record["name"]] = record
        self.save(emergency=bool(record["cleanup_confirmed"] or record["cleanup_error"]))
        if self.event_log is not None:
            self.event_log.emit(
                "resource_registered",
                {"resource_type": "container", **record},
                emergency=bool(record["cleanup_confirmed"] or record["cleanup_error"]),
            )

    def register_snapshot(self, path, manifest, *, identity=None):
        self.assert_owned()
        if path.parent != self.workspace / "snapshots":
            raise InfrastructureError("SNAPSHOT_OWNERSHIP: 快照不在本 Run 工作区")
        observed = self._identity(path)
        if identity is not None and identity != observed:
            raise SourceChanged("SNAPSHOT_OWNERSHIP: 快照创建后身份发生变化")
        identity = observed
        self.snapshots[str(path)] = {
            "path": str(path),
            "identity": list(identity),
            "source_tree_sha256": manifest.sha256,
            "exists": True,
        }
        self.save()

    def remove_snapshot(self, record):
        self.assert_owned()
        if not record["exists"]:
            return
        path = Path(record["path"])
        if (
            path.parent != self.workspace / "snapshots"
            or self._identity(path) != tuple(record["identity"])
            or any(parent.is_symlink() for parent in path.parents)
            or not shutil.rmtree.avoids_symlink_attacks
        ):
            raise SourceChanged("SNAPSHOT_OWNERSHIP: 不删除身份不明的快照")
        shutil.rmtree(path)
        record["exists"] = False

    def finish_evaluation(self, path, *, keep):
        # 未确认容器删除时不能移除仍可能被挂载的快照。
        if not self.containers_clean:
            return
        for record in self.snapshots.values():
            if record["exists"] and (
                (record["path"] == str(path) and not keep) or (record["path"] != str(path) and keep)
            ):
                self.remove_snapshot(record)
        self.save(emergency=True)

    @property
    def containers_clean(self):
        return all(
            record["cleanup_confirmed"] and not record["cleanup_error"]
            for record in self.containers.values()
        )

    def agent_containers_ready(self, repair_name=None):
        """仅允许指定的修复容器以冻结状态跨越模型请求边界。"""
        return all(
            not record["cleanup_error"]
            and (
                record["cleanup_confirmed"]
                or (
                    name == repair_name
                    and record.get("kind") == "repair"
                    and record["active"]
                    and record.get("paused") is True
                    and record["profile_verified"]
                )
            )
            for name, record in self.containers.items()
        )

    def cleanup(self, *, retain, passed, paused=False):
        keep = retain == "always" or (retain == "on_failure" and not passed)
        if not self.containers_clean:
            keep = True
            self.cleanup_errors.append("CLEANUP_UNCONFIRMED: 保留容器相关工作区供诊断")
        else:
            try:
                self.remove_compiler_cache()
            except Exception as exc:
                self.cleanup_errors.append(f"CACHE_CLEANUP: {exc}")
        for worktree in reversed(self.worktrees):
            if keep and (
                worktree.path.name == "repair" or worktree.path.name.startswith("repair-r")
            ):
                continue
            try:
                worktree.close()
            except Exception as exc:
                self.cleanup_errors.append(f"WORKTREE_CLEANUP: {exc}")
        latest = next(
            (r["path"] for r in reversed(list(self.snapshots.values())) if r["exists"]), None
        )
        for record in self.snapshots.values():
            if (
                record["exists"]
                and self.containers_clean
                and (paused or not keep or record["path"] != latest)
            ):
                try:
                    self.remove_snapshot(record)
                except Exception as exc:
                    self.cleanup_errors.append(f"SNAPSHOT_CLEANUP: {exc}")
        self.save(emergency=True)

    def close(self):
        self.lock.close()
