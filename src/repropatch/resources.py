"""本 Run 独占目录、文件锁、资源身份与保留策略。"""

import fcntl
import json
import os
import shutil
from pathlib import Path

from .artifacts import AuditBudget
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
            "workspace_identity": list(self._workspace_identity),
            "lock_path": str(self.lock.path),
            "repository": self.repository,
            "commit": self.commit,
            "control_directory": str(self.directory),
            "workspace_directory": str(self.workspace),
            "worktrees": [dict(work.ownership(), exists=work.created) for work in self.worktrees],
            "snapshots": list(self.snapshots.values()),
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
            self._identity(path) != tuple(record["identity"])
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

    def cleanup(self, *, retain, passed, paused=False):
        keep = retain == "always" or (retain == "on_failure" and not passed)
        if not self.containers_clean:
            keep = True
            self.cleanup_errors.append("CLEANUP_UNCONFIRMED: 保留容器相关工作区供诊断")
        for worktree in reversed(self.worktrees):
            if keep and worktree.path.name == "repair":
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
