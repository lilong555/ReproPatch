"""原始证据、私有文件写入及 Run 审计磁盘预算。"""

import hashlib
import os
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .errors import AuditLimit, InfrastructureError, PolicyError, ReproPatchError, SourceChanged

MIB = 1024 * 1024
MAX_SOURCE_FILE = 16 * MIB
MAX_AUDIT_BYTES = 256 * MIB
FINAL_RESERVE = 8 * MIB


def _signature(info):
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_uid,
        info.st_gid,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def read_regular(path: Path, *, limit=MAX_SOURCE_FILE):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise PolicyError(
            f"SOURCE_CHANGED: 只支持普通文件，禁止 Symlink 和 hard links：{path.name}"
        )
    if before.st_size > limit:
        raise PolicyError(f"SOURCE_FILE_TOO_LARGE: {path.name}")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if _signature(opened) != _signature(before):
            raise SourceChanged("SOURCE_CHANGED: 文件在打开时发生变化")
        content = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if (
        len(content) != before.st_size
        or _signature(after) != _signature(before)
        or _signature(path.lstat()) != _signature(before)
    ):
        raise SourceChanged("SOURCE_CHANGED: 文件在读取期间发生变化")
    return content, before


def private_write(path: Path, content: bytes, *, budget=None, emergency=False):
    if budget is not None:
        budget.check(len(content), emergency=emergency)
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class EvidenceRef:
    path: str
    sha256: str
    size_bytes: int

    @classmethod
    def save(cls, root: Path, name: str, content: bytes, *, budget=None, emergency=False):
        from .task import relative_file

        relative_file(name)
        private_write(root / name, content, budget=budget, emergency=emergency)
        return cls(name, hashlib.sha256(content).hexdigest(), len(content))

    def read(self, root: Path, *, limit):
        try:
            from .task import relative_file

            name = relative_file(self.path)
            content, _ = read_regular(_evidence_path(root, name), limit=limit)
        except (OSError, ReproPatchError) as exc:
            raise InfrastructureError("ARTIFACT_CORRUPT: 证据路径或文件无效") from exc
        if (
            type(self.size_bytes) is not int
            or self.size_bytes != len(content)
            or self.sha256 != hashlib.sha256(content).hexdigest()
        ):
            raise InfrastructureError("ARTIFACT_CORRUPT: 证据大小或 hash 不符")
        return content


def _evidence_path(root, name):
    if root.is_symlink() or not root.is_dir():
        raise InfrastructureError("ARTIFACT_CORRUPT: 证据根必须是普通目录")
    path = root / name
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise InfrastructureError("ARTIFACT_CORRUPT: 证据目录不能是链接")
    return path


class AuditBudget:
    """控制目录只承载审计文件；源码工作树与快照位于独立工作区。"""

    def __init__(self, root, *, limit=None, reserve=None):
        self.root = root
        self.limit = MAX_AUDIT_BYTES if limit is None else limit
        self.reserve = min(FINAL_RESERVE if reserve is None else reserve, self.limit // 4)
        info = root.lstat()
        self.identity = (info.st_dev, info.st_ino)

    def usage(self):
        info = self.root.lstat()
        if self.root.is_symlink() or (info.st_dev, info.st_ino) != self.identity:
            raise InfrastructureError("RUN_OWNERSHIP: 控制目录身份发生变化")
        total = 0

        def read_error(error):
            raise error

        for directory, directories, names in os.walk(
            self.root, followlinks=False, onerror=read_error
        ):
            for name in directories:
                path = Path(directory) / name
                if (
                    path.is_symlink()
                    or path.stat().st_uid != os.getuid()
                    or path.stat().st_mode & 0o777 != 0o700
                ):
                    raise InfrastructureError("RUN_OWNERSHIP: 审计目录出现链接")
            for name in names:
                entry = (Path(directory) / name).lstat()
                if (
                    not stat.S_ISREG(entry.st_mode)
                    or entry.st_nlink != 1
                    or entry.st_uid != os.getuid()
                    or entry.st_mode & 0o777 != 0o600
                ):
                    raise InfrastructureError("RUN_OWNERSHIP: 审计文件不是独占普通文件")
                total += entry.st_size
        return total

    def check(self, additional=0, *, emergency=False):
        ceiling = self.limit if emergency else self.limit - self.reserve
        if self.usage() + additional > ceiling:
            raise AuditLimit("AUDIT_LIMIT: Run 非源码审计产物超过允许预算")
        if shutil.disk_usage(self.root).free < additional + self.reserve:
            raise AuditLimit("DISK_SPACE: 没有足够空间保存证据与最终诊断")

    def write(self, name, content, *, emergency=False):
        from .task import relative_file

        relative_file(name)
        self.check(0, emergency=emergency)
        path = self.root / name
        if path.exists() and read_regular(path, limit=self.limit)[0] == content:
            return
        private_write(path, content, budget=self, emergency=emergency)
