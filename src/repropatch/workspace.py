"""受控 Git、完整源码清单、原子文本编辑及可往返的候选补丁。"""

import hashlib
import json
import os
import re
import stat
import tempfile
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from pathlib import Path

from .artifacts import EvidenceRef, read_regular
from .artifacts import private_write as private_write
from .errors import (
    InfrastructureError,
    OperationDeadline,
    PatchRejected,
    PolicyError,
    ReproPatchError,
    SourceChanged,
)
from .process import host_env, run_process_bytes
from .task import canonical_json, relative_file

MIB = 1024 * 1024
MAX_SOURCE_FILE = 16 * MIB
MAX_SOURCE_TREE = 256 * MIB
MAX_EDIT_FILE = MIB
MAX_PATCH = 8 * MIB
CPP_SUFFIXES = {".cpp", ".cc", ".cxx", ".c", ".h", ".hh", ".hpp", ".hxx"}
_GIT_DEADLINE = ContextVar("repropatch_git_deadline", default=None)


@contextmanager
def git_deadline(deadline):
    """工具内 Git 共享阶段时限；退出作用域后恢复独立验证与清理预算。"""
    token = _GIT_DEADLINE.set(deadline)
    try:
        yield
    finally:
        _GIT_DEADLINE.reset(token)


def git_argv(repo: Path, *args: str) -> list[str]:
    return [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.autocrlf=false",
        "-c",
        "color.ui=false",
        "-c",
        "core.quotePath=false",
        "-c",
        "apply.whitespace=warn",
        "-c",
        "apply.ignoreWhitespace=no",
        "-C",
        str(repo),
        *args,
    ]


def git_result(
    repo: Path, *args: str, limit=MAX_SOURCE_TREE, index_file=None, allow_truncated=False
):
    environment = host_env()
    if index_file is not None:
        environment["GIT_INDEX_FILE"] = str(index_file)
    deadline = _GIT_DEADLINE.get()
    timeout = 60 if deadline is None else min(60, deadline - time.monotonic())
    if timeout <= 0:
        raise OperationDeadline("AGENT_DEADLINE: Git 操作未开始")
    try:
        result = run_process_bytes(
            git_argv(repo, *args), env=environment, output_limit=limit, timeout=timeout
        )
    except OSError as exc:
        raise InfrastructureError(f"GIT_UNAVAILABLE: {args[0]}") from exc
    if result.timed_out and deadline is not None and time.monotonic() >= deadline:
        raise OperationDeadline("AGENT_DEADLINE: Git 操作达到阶段时限")
    if result.timed_out or (result.output_truncated and not allow_truncated):
        raise InfrastructureError(f"GIT_INCOMPLETE: {args[0]} 超时或输出超限")
    return result


def git(repo: Path, *args: str, strict=False, index_file=None) -> str:
    result = git_result(repo, *args, index_file=index_file)
    if not result.ok:
        detail = result.stderr[:2000].decode("utf-8", "replace")
        raise InfrastructureError(f"Git {args[0]} failed: {detail}")
    try:
        return result.stdout.decode("utf-8", "strict" if strict else "replace")
    except UnicodeError as exc:
        raise PolicyError("UNSUPPORTED_PATH_ENCODING: Git 路径必须使用 UTF-8") from exc


def git_blob(repo: Path, oid: str, *, max_bytes=MAX_SOURCE_FILE) -> bytes:
    size = int(git(repo, "cat-file", "-s", oid).strip())
    if not 0 <= size <= max_bytes:
        raise PolicyError("SOURCE_FILE_TOO_LARGE: 单个源文件超过允许大小")
    result = git_result(repo, "cat-file", "blob", oid, limit=max_bytes + 65536)
    if not result.ok or len(result.stdout) != size:
        raise InfrastructureError("GIT_BLOB_CHANGED: 对象读取失败或大小变化")
    return result.stdout


def audit_git(repo: Path):
    """只读取本地配置，不展开 include，不执行被检查的外部程序。"""
    raw = git(repo, "config", "--local", "--no-includes", "--null", "--list", strict=True)
    for entry in filter(None, raw.split("\0")):
        key, _, value = entry.partition("\n")
        key = key.lower()
        active = value.lower() not in {"", "false", "0", "no", "off"}
        forbidden = (
            key == "include.path"
            or key.startswith("includeif.")
            or (
                key.startswith("filter.")
                and key.endswith((".clean", ".smudge", ".process"))
                and bool(value)
            )
            or (key == "core.fsmonitor" and active)
            or (key == "core.hookspath" and value not in {"", "/dev/null"})
            or (key == "extensions.worktreeconfig" and active)
            or (key == "diff.external" and bool(value))
            or (key.startswith("diff.") and key.endswith((".command", ".textconv")) and bool(value))
            or (key == "extensions.partialclone" and bool(value))
            or (key.startswith("remote.") and key.endswith(".promisor") and active)
        )
        if forbidden:
            raise PolicyError(f"UNSAFE_GIT_CONFIG: 不支持本地配置项 {key}")
    manager = Path(git(repo, "rev-parse", "--absolute-git-dir").removesuffix("\n")).resolve()
    common = Path(
        git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").removesuffix("\n")
    ).resolve()
    if (manager / "config.worktree").exists() or (common / "config.worktree").exists():
        raise PolicyError("UNSAFE_GIT_CONFIG: 不支持额外 worktree 配置")


@dataclass(frozen=True)
class TreeFile:
    path: str
    oid: str
    git_mode: str
    size_bytes: int


def git_tree(repo: Path, revision: str) -> tuple[TreeFile, ...]:
    raw = git(repo, "ls-tree", "-rlz", "--full-tree", revision, strict=True)
    entries = []
    total = 0
    for item in filter(None, raw.split("\0")):
        metadata, path = item.split("\t", 1)
        mode, kind, oid, size = metadata.split()
        if mode not in {"100644", "100755"} or kind != "blob":
            raise PolicyError("UNSUPPORTED_SOURCE_LAYOUT: 不支持 symlink、gitlink 或特殊文件")
        size = int(size)
        if size > MAX_SOURCE_FILE:
            raise PolicyError("SOURCE_FILE_TOO_LARGE: 单个源文件超过 16 MiB")
        total += size
        if total > MAX_SOURCE_TREE:
            raise PolicyError("SOURCE_TREE_TOO_LARGE: 源码超过 256 MiB")
        entries.append(TreeFile(relative_file(path), oid, mode, size))
    return tuple(sorted(entries, key=lambda entry: entry.path))


def audit_attributes(repo: Path, revision: str, files: tuple[TreeFile, ...]):
    """Git 在私有索引上解释提交属性，原工作区和 index 均不改变。"""
    with tempfile.TemporaryDirectory(prefix="repropatch-attributes-") as directory:
        index = Path(directory) / "index"
        git(repo, "read-tree", "--no-sparse-checkout", revision, index_file=index)
        names = [entry.path for entry in files]
        for start in range(0, len(names), 128):
            output = git(
                repo,
                "check-attr",
                "--cached",
                "-z",
                "filter",
                "--",
                *names[start : start + 128],
                index_file=index,
                strict=True,
            )
            fields = output.split("\0")
            if fields.pop() != "" or len(fields) % 3:
                raise InfrastructureError("GIT_ATTRIBUTE_INVALID: 属性输出不完整")
            for offset in range(0, len(fields), 3):
                path, attribute, value = fields[offset : offset + 3]
                if attribute != "filter" or path not in names[start : start + 128]:
                    raise InfrastructureError("GIT_ATTRIBUTE_INVALID: 属性身份不符")
                if value not in {"unspecified", "unset"}:
                    raise PolicyError(f"UNSUPPORTED_GIT_FILTER: {path}")


@dataclass(frozen=True)
class SourceFile:
    path: str
    sha256: str
    size_bytes: int
    git_mode: str


@dataclass(frozen=True)
class SourceManifest:
    files: tuple[SourceFile, ...]

    def to_dict(self):
        return {"schema_version": 1, "files": [asdict(entry) for entry in self.files]}

    @property
    def sha256(self):
        return hashlib.sha256(canonical_json(self.to_dict())).hexdigest()

    @property
    def by_path(self):
        return {entry.path: entry for entry in self.files}

    def updated(self, entry: SourceFile):
        return SourceManifest(
            tuple(entry if item.path == entry.path else item for item in self.files)
        )

    @classmethod
    def from_dict(cls, raw):
        try:
            if (
                not isinstance(raw, dict)
                or set(raw) != {"schema_version", "files"}
                or type(raw["schema_version"]) is not int
                or raw["schema_version"] != 1
                or not isinstance(raw["files"], list)
            ):
                raise ValueError("结构错误")
            entries = []
            for item in raw["files"]:
                if not isinstance(item, dict) or set(item) != {
                    "path",
                    "sha256",
                    "size_bytes",
                    "git_mode",
                }:
                    raise ValueError("文件结构错误")
                relative_file(item["path"])
                if (
                    not isinstance(item["sha256"], str)
                    or re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) is None
                    or type(item["size_bytes"]) is not int
                    or not 0 <= item["size_bytes"] <= MAX_SOURCE_FILE
                    or item["git_mode"] not in {"100644", "100755"}
                ):
                    raise ValueError("文件身份错误")
                entries.append(SourceFile(**item))
            paths = [entry.path for entry in entries]
            if (
                paths != sorted(set(paths))
                or sum(entry.size_bytes for entry in entries) > MAX_SOURCE_TREE
            ):
                raise ValueError("排序、唯一性或总大小错误")
            return cls(tuple(entries))
        except (KeyError, TypeError, ValueError, ReproPatchError) as exc:
            raise InfrastructureError("ARTIFACT_CORRUPT: 源码清单不符合契约") from exc


def _source_file(root: Path, name: str):
    try:
        path = root / relative_file(name)
    except ReproPatchError as exc:
        raise PolicyError("UNSUPPORTED_SOURCE_LAYOUT: 非法路径") from exc
    for parent in path.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise PolicyError("UNSUPPORTED_SOURCE_LAYOUT: Symlink 目录不可访问")
    content, info = read_regular(path)
    mode = "100755" if info.st_mode & stat.S_IXUSR else "100644"
    return SourceFile(name, hashlib.sha256(content).hexdigest(), len(content), mode), content, info


def source_manifest(root: Path, *, worktree=False) -> SourceManifest:
    if root.is_symlink() or not root.is_dir():
        raise SourceChanged("SOURCE_CHANGED: 源码根必须是普通目录")
    files = []
    actual_directories = set()
    total = 0

    def read_error(error):
        raise error

    for directory, directories, names in os.walk(root, followlinks=False, onerror=read_error):
        for name in directories:
            actual_directories.add((Path(directory) / name).relative_to(root).as_posix())
            if (Path(directory) / name).is_symlink():
                raise PolicyError("UNSUPPORTED_SOURCE_LAYOUT: Symlink 目录不可导出")
        for name in names:
            path = Path(directory) / name
            if worktree and path == root / ".git":
                continue
            entry, _, _ = _source_file(root, path.relative_to(root).as_posix())
            total += entry.size_bytes
            if total > MAX_SOURCE_TREE:
                raise PolicyError("SOURCE_TREE_TOO_LARGE: 源码超过 256 MiB")
            files.append(entry)
    required_directories = {
        parent.as_posix()
        for entry in files
        for parent in Path(entry.path).parents
        if parent != Path(".")
    }
    if actual_directories != required_directories:
        raise PolicyError("UNSUPPORTED_SOURCE_LAYOUT: 不允许补丁无法表达的额外空目录")
    return SourceManifest(tuple(sorted(files, key=lambda entry: entry.path)))


@dataclass(frozen=True)
class CandidatePatch:
    base_commit: str
    patch: EvidenceRef
    manifest: EvidenceRef
    source_tree_sha256: str
    changed_files: tuple[str, ...]

    def to_dict(self):
        result = asdict(self)
        result["changed_files"] = list(self.changed_files)
        return result

    def load(self, root):
        patch = self.patch.read(root, limit=MAX_PATCH)
        try:
            manifest = SourceManifest.from_dict(
                json.loads(self.manifest.read(root, limit=MAX_SOURCE_TREE))
            )
        except (ValueError, UnicodeError) as exc:
            raise InfrastructureError("ARTIFACT_CORRUPT: 候选清单损坏") from exc
        if manifest.sha256 != self.source_tree_sha256:
            raise InfrastructureError("ARTIFACT_CORRUPT: 候选逻辑摘要不符")
        return patch, manifest


class Worktree:
    def __init__(self, repository: Path, path: Path, revision: str, *, retain=False):
        self.retain = retain
        self.repository = repository
        self.path = path.parent.resolve() / path.name
        self.revision = revision
        self.created = False
        self._owned = False

    def __enter__(self):
        audit_git(self.repository)
        self.revision = git(
            self.repository,
            "rev-parse",
            "--verify",
            "--end-of-options",
            self.revision + "^{commit}",
        ).strip()
        self.tree = git_tree(self.repository, self.revision)
        audit_attributes(self.repository, self.revision, self.tree)
        if self.path.exists() or self.path.is_symlink():
            raise InfrastructureError("WORKTREE_EXISTS: 不覆盖已有目录")
        self.path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        try:
            git(self.repository, "worktree", "add", "--detach", str(self.path), self.revision)
            self.created = True
            self.manager = Path(
                git(self.path, "rev-parse", "--absolute-git-dir").removesuffix("\n")
            ).resolve()
            self.common = Path(
                git(
                    self.path, "rev-parse", "--path-format=absolute", "--git-common-dir"
                ).removesuffix("\n")
            ).resolve()
            root_stat = self.path.lstat()
            manager_stat = self.manager.lstat()
            self._root_identity = (root_stat.st_dev, root_stat.st_ino)
            self._manager_identity = (manager_stat.st_dev, manager_stat.st_ino)
            common_stat = self.common.stat()
            self._common_identity = (common_stat.st_dev, common_stat.st_ino, common_stat.st_uid)
            self._git_pointer, _ = read_regular(self.path / ".git", limit=4096)
            self._manager_pointer, _ = read_regular(self.manager / "gitdir", limit=4096)
            self._owned = True
            self.initial_manifest = self.manifest()
            expected_modes = {entry.path: entry.git_mode for entry in self.tree}
            if {
                entry.path: entry.git_mode for entry in self.initial_manifest.files
            } != expected_modes:
                raise SourceChanged("SOURCE_CHANGED: checkout 文件集合或 mode 不符合固定提交")
            self.expected_manifest = self.initial_manifest
            self._permissions = {
                name: self._file_metadata((self.path / name).stat()) for name in self.files()
            }
            return self
        except BaseException as error:
            if self._owned:
                try:
                    self.close()
                except Exception as cleanup:
                    error.add_note(f"Worktree 清理失败：{cleanup}")
            raise

    def ownership(self):
        return {
            "repository": str(self.repository.resolve()),
            "path": str(self.path),
            "commit": self.revision,
            "git_dir": str(self.manager),
            "common_dir": str(self.common),
            "owner_uid": os.getuid(),
            "root_identity": list(self._root_identity),
            "git_dir_identity": list(self._manager_identity),
            "common_dir_identity": list(self._common_identity),
            "git_pointer_sha256": hashlib.sha256(self._git_pointer).hexdigest(),
            "manager_pointer_sha256": hashlib.sha256(self._manager_pointer).hexdigest(),
        }

    @classmethod
    def open_existing(cls, record, initial_manifest):
        """按原登记身份接管工作树；不 checkout、不覆盖或修改现有源码。"""
        work = cls(Path(record["repository"]), Path(record["path"]), record["commit"], retain=True)
        audit_git(work.repository)
        work.manager = Path(record["git_dir"])
        work.common = Path(record["common_dir"])
        work._root_identity = tuple(record["root_identity"])
        work._manager_identity = tuple(record["git_dir_identity"])
        work._common_identity = tuple(record["common_dir_identity"])
        work._git_pointer, _ = read_regular(work.path / ".git", limit=4096)
        work._manager_pointer, _ = read_regular(work.manager / "gitdir", limit=4096)
        if (
            hashlib.sha256(work._git_pointer).hexdigest() != record["git_pointer_sha256"]
            or hashlib.sha256(work._manager_pointer).hexdigest() != record["manager_pointer_sha256"]
            or record["owner_uid"] != os.getuid()
        ):
            raise SourceChanged("WORKSPACE_DIVERGED: 工作树登记身份不符")
        work._owned = work.created = True
        work._ensure_owned()
        if work.ownership() != {key: value for key, value in record.items() if key != "exists"}:
            raise SourceChanged("WORKSPACE_DIVERGED: 工作树路径或登记身份不符")
        if git(work.path, "rev-parse", "HEAD").strip() != work.revision:
            raise SourceChanged("WORKSPACE_DIVERGED: 工作树基线发生变化")
        work.tree = git_tree(work.repository, work.revision)
        audit_attributes(work.repository, work.revision, work.tree)
        work.initial_manifest = initial_manifest
        work.expected_manifest = work.manifest()
        work._permissions = {
            item.path: work._file_metadata((work.path / item.path).stat())
            for item in work.expected_manifest.files
        }
        return work

    def _ensure_owned(self):
        if (
            not self._owned
            or self.path.is_symlink()
            or self.manager.is_symlink()
            or self.common.is_symlink()
            or any(parent.is_symlink() for parent in (*self.path.parents, *self.manager.parents))
        ):
            raise SourceChanged("SOURCE_CHANGED: Worktree 所有权不可确认")
        info = self.path.lstat()
        manager = self.manager.lstat()
        common = self.common.lstat()
        pointer, _ = read_regular(self.path / ".git", limit=4096)
        manager_pointer, _ = read_regular(self.manager / "gitdir", limit=4096)
        if (
            info.st_uid != os.getuid()
            or (info.st_dev, info.st_ino) != self._root_identity
            or (manager.st_dev, manager.st_ino) != self._manager_identity
            or (common.st_dev, common.st_ino, common.st_uid) != self._common_identity
            or pointer != self._git_pointer
            or manager_pointer != self._manager_pointer
        ):
            raise SourceChanged("SOURCE_CHANGED: Worktree 身份发生变化")

    def close(self):
        if self.created:
            self._ensure_owned()
            common = Path(
                git(
                    self.path, "rev-parse", "--path-format=absolute", "--git-common-dir"
                ).removesuffix("\n")
            ).resolve()
            manager = Path(
                git(self.path, "rev-parse", "--absolute-git-dir").removesuffix("\n")
            ).resolve()
            if common != self.common or manager != self.manager:
                raise SourceChanged("SOURCE_CHANGED: Worktree 不再属于原仓库")
            git(self.repository, "worktree", "remove", "--force", str(self.path))
            self.created = False

    def __exit__(self, exc_type, error, traceback):
        if self.retain:
            return
        try:
            self.close()
        except Exception as cleanup:
            if error is None:
                raise
            error.add_note(f"Worktree 清理失败：{cleanup}")

    def files(self):
        return [entry.path for entry in self.tree]

    def safe_path(self, name):
        self._ensure_owned()
        relative_file(name)
        if name not in self.files():
            raise PolicyError("Only tracked files are accessible")
        path = self.path / name
        for parent in (path, *path.parents):
            if parent == self.path:
                break
            if parent.is_symlink():
                raise SourceChanged("SOURCE_CHANGED: Symlink access is forbidden")
        if not path.is_file():
            raise SourceChanged("SOURCE_CHANGED: 跟踪文件不再是普通文件")
        return path

    def manifest(self):
        self._ensure_owned()
        return source_manifest(self.path, worktree=True)

    @staticmethod
    def _file_metadata(info):
        return info.st_mode & 0o7777, info.st_uid, info.st_gid

    def assert_current(self):
        try:
            current = self.manifest()
        except (PolicyError, OSError) as exc:
            raise SourceChanged("SOURCE_CHANGED: 源码布局或读取不再符合受控状态") from exc
        if current != self.expected_manifest or git(
            self.path, "diff", "--cached", "--name-only", "-z", self.revision, "--"
        ):
            raise SourceChanged("SOURCE_CHANGED: 源码或 index 不符合受控编辑记录")
        for name, metadata in self._permissions.items():
            if self._file_metadata(self.safe_path(name).stat()) != metadata:
                raise SourceChanged("SOURCE_CHANGED: 文件权限发生变化")
        return current

    def read_file(self, name):
        self.safe_path(name)
        try:
            entry, content, info = _source_file(self.path, name)
        except PolicyError as exc:
            raise SourceChanged("SOURCE_CHANGED: 跟踪文件不再符合受控状态") from exc
        if (
            entry != self.expected_manifest.by_path[name]
            or self._file_metadata(info) != self._permissions[name]
        ):
            raise SourceChanged("SOURCE_CHANGED: 文件不符合受控编辑记录")
        return content, info

    def edit_text(self, name, old, new):
        self.assert_current()
        content, info = self.read_file(name)
        if len(content) > MAX_EDIT_FILE:
            raise PolicyError("EDIT_FILE_TOO_LARGE: 被编辑文件超过 1 MiB")
        try:
            text = content.decode("utf-8")
        except UnicodeError as exc:
            raise PolicyError("EDIT_NOT_TEXT: 仅支持 UTF-8") from exc
        if b"\0" in content:
            raise PolicyError("EDIT_NOT_TEXT: 二进制文件不可编辑")
        if not old or text.count(old) != 1:
            raise PolicyError("old must match exactly once; re-read the file")
        updated = text.replace(old, new, 1).encode("utf-8")
        if len(updated) > MAX_EDIT_FILE or b"\0" in updated:
            raise PolicyError("EDIT_FILE_TOO_LARGE: 内容不符合编辑边界")
        directory = self._parent_descriptor(name)
        temporary = ".repropatch-edit-" + uuid.uuid4().hex
        primary_error = None
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(updated)
                stream.flush()
                os.fchown(stream.fileno(), info.st_uid, info.st_gid)
                os.fchmod(stream.fileno(), info.st_mode & 0o777)
                os.fsync(stream.fileno())
            self.read_file(name)
            os.replace(temporary, Path(name).name, src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
            entry = SourceFile(
                name,
                hashlib.sha256(updated).hexdigest(),
                len(updated),
                self.expected_manifest.by_path[name].git_mode,
            )
            self.expected_manifest = self.expected_manifest.updated(entry)
            self.assert_current()
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass
            except OSError as cleanup:
                if primary_error is None:
                    raise
                primary_error.add_note(f"临时编辑文件清理失败：{cleanup}")
            finally:
                os.close(directory)
        return updated != content

    def _parent_descriptor(self, name):
        """逐段禁止链接并固定目录 fd，替换不再重新跟随宿主路径。"""
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptor = os.open(self.path, flags)
        try:
            info = os.fstat(descriptor)
            if (info.st_dev, info.st_ino) != self._root_identity:
                raise SourceChanged("SOURCE_CHANGED: 源码根在编辑时变化")
            for component in Path(name).parts[:-1]:
                child = os.open(component, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def export(self, destination: Path, *, on_created=None) -> str:
        current = self.manifest()
        destination.mkdir(parents=True)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        root_descriptor = os.open(destination, flags)
        root_info = os.fstat(root_descriptor)
        directories = {"": (root_info.st_dev, root_info.st_ino)}
        try:
            os.fchmod(root_descriptor, 0o755)
            if on_created is not None:
                on_created((root_info.st_dev, root_info.st_ino))
            for entry in current.files:
                actual, content, _ = _source_file(self.path, entry.path)
                if actual != entry:
                    raise SourceChanged("SOURCE_CHANGED: 导出期间源码发生变化")
                descriptor = os.dup(root_descriptor)
                try:
                    prefix = []
                    for component in Path(entry.path).parts[:-1]:
                        prefix.append(component)
                        name = "/".join(prefix)
                        created = name not in directories
                        if created:
                            os.mkdir(component, mode=0o755, dir_fd=descriptor)
                        child = os.open(component, flags, dir_fd=descriptor)
                        os.close(descriptor)
                        descriptor = child
                        info = os.fstat(descriptor)
                        identity = (info.st_dev, info.st_ino)
                        if not created and identity != directories[name]:
                            raise SourceChanged("SOURCE_CHANGED: 快照目录身份发生变化")
                        directories[name] = identity
                        if created:
                            os.fchmod(descriptor, 0o755)
                    file_descriptor = os.open(
                        Path(entry.path).name,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=descriptor,
                    )
                    with os.fdopen(file_descriptor, "wb") as stream:
                        stream.write(content)
                        stream.flush()
                        os.fchmod(stream.fileno(), 0o755 if entry.git_mode == "100755" else 0o644)
                finally:
                    os.close(descriptor)
        except OSError as exc:
            raise SourceChanged("SOURCE_CHANGED: 快照目标路径或写入失败") from exc
        finally:
            os.close(root_descriptor)
        try:
            observed = source_manifest(destination)
        except (PolicyError, OSError) as exc:
            raise SourceChanged("SOURCE_CHANGED: 快照导出目标布局发生变化") from exc
        if self.manifest() != current or observed != current:
            raise SourceChanged("SOURCE_CHANGED: 快照与源码清单不一致")
        return current.sha256

    def changes(self):
        before = self.initial_manifest.by_path
        after = self.manifest().by_path
        return sorted(
            name for name in before.keys() | after.keys() if before.get(name) != after.get(name)
        )

    def diff_bytes(self):
        result = git_result(
            self.path,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-renames",
            "--no-color",
            "--full-index",
            "--binary",
            "--src-prefix=a/",
            "--dst-prefix=b/",
            "--no-relative",
            "--unified=3",
            "--diff-algorithm=myers",
            "--no-indent-heuristic",
            self.revision,
            "--",
            limit=MAX_PATCH + 65536,
            allow_truncated=True,
        )
        if not result.ok:
            raise InfrastructureError("GIT_DIFF_FAILED: 无法导出补丁")
        if result.stdout_bytes_seen > MAX_PATCH:
            raise PatchRejected("PATCH_TOO_LARGE: 补丁超过 8 MiB")
        if result.output_truncated:
            raise InfrastructureError("GIT_DIFF_INCOMPLETE: 补丁输出不完整")
        return result.stdout

    def diff(self):
        return self.diff_bytes().decode("utf-8")

    def validate_changes(self, allowed, protected=()):
        try:
            current = self.manifest()
        except PolicyError as exc:
            raise PatchRejected(f"FORBIDDEN_PATCH: {exc}") from exc
        before = self.initial_manifest.by_path
        after = current.by_path
        if before.keys() != after.keys():
            raise PatchRejected("FORBIDDEN_PATCH: 新增、删除或重命名文件不受支持")
        changed = []
        for name, entry in after.items():
            if entry.git_mode != before[name].git_mode:
                raise PatchRejected("FORBIDDEN_PATCH: Git mode 变化")
            if entry.sha256 != before[name].sha256:
                if not _editable(name, allowed, protected):
                    raise PatchRejected(f"FORBIDDEN_PATCH: protected 文件变化 {name}")
                _, content, _ = _source_file(self.path, name)
                if len(content) > MAX_EDIT_FILE or b"\0" in content:
                    raise PatchRejected("FORBIDDEN_PATCH: 修改文件不是允许大小内的文本")
                try:
                    content.decode("utf-8")
                except UnicodeError as exc:
                    raise PatchRejected("FORBIDDEN_PATCH: 修改文件不是 UTF-8") from exc
                changed.append(name)
        status = git(
            self.path,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignored=matching",
            strict=True,
        )
        if any(item[:2] != " M" for item in filter(None, status.split("\0"))):
            raise PatchRejected("FORBIDDEN_PATCH: 仅支持已有文件的未暂存 M 变更")
        return current, tuple(sorted(changed))

    def freeze_candidate(self, root, allowed, protected=(), *, budget=None):
        current, changed = self.validate_changes(allowed, protected)
        if not changed:
            raise PatchRejected("NO_PATCH: 没有源码变化")
        patch = self.diff_bytes()
        if not patch:
            raise PatchRejected("PATCH_ROUNDTRIP_MISMATCH: Git diff 隐藏了源码变化")
        _preflight_patch(self, patch, allowed, protected)
        patch_ref = EvidenceRef.save(root, "patch.diff", patch, budget=budget)
        manifest_ref = EvidenceRef.save(
            root,
            "candidate.manifest.json",
            json.dumps(current.to_dict(), ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
            budget=budget,
        )
        return CandidatePatch(self.revision, patch_ref, manifest_ref, current.sha256, changed)

    def checkpoint_source(self, allowed, protected=()):
        """允许原始零字节补丁，同时核对受控源码、Git 导出与编辑策略。"""
        self.assert_current()
        current, changed = self.validate_changes(allowed, protected)
        patch = self.diff_bytes()
        if bool(patch) != bool(changed):
            raise PatchRejected("PATCH_ROUNDTRIP_MISMATCH: Checkpoint 补丁与源码变化不一致")
        if patch:
            _preflight_patch(self, patch, allowed, protected)
        if self.assert_current() != current:
            raise SourceChanged("SOURCE_CHANGED: Checkpoint 源码读取期间变化")
        return current, patch

    def apply_patch(self, patch: bytes, allowed, protected=()):
        self.assert_current()
        if self.manifest() != self.initial_manifest or self.diff_bytes():
            raise InfrastructureError("VERIFIER_NOT_CLEAN: 补丁必须应用到干净原始源码")
        _preflight_patch(self, patch, allowed, protected, apply=True)
        self.expected_manifest = self.manifest()
        self.validate_changes(allowed, protected)


def _editable(name, allowed, protected):
    return (
        name in allowed
        and name not in protected
        and Path(name).suffix in CPP_SUFFIXES
        and Path(name).name != "CMakeLists.txt"
    )


def _preflight_patch(worktree, patch, allowed, protected, *, apply=False):
    if not patch or len(patch) > MAX_PATCH:
        raise PatchRejected("PATCH_APPLY_FAILED: 补丁为空或超限")
    with tempfile.NamedTemporaryFile(dir=worktree.path.parent, delete=False) as stream:
        filename = Path(stream.name)
        stream.write(patch)
    try:
        result = git_result(
            worktree.path, "apply", "--numstat", "-z", str(filename), limit=MAX_PATCH
        )
        if not result.ok:
            raise PatchRejected("PATCH_APPLY_FAILED: Git 无法解析补丁")
        records = result.stdout.split(b"\0")
        if records.pop() != b"" or not records:
            raise PatchRejected("FORBIDDEN_PATCH: numstat 结构无效")
        for record in records:
            parts = record.split(b"\t", 2)
            if len(parts) != 3 or not all(re.fullmatch(rb"[0-9]+", p) for p in parts[:2]):
                raise PatchRejected("FORBIDDEN_PATCH: 二进制或未知补丁格式")
            try:
                name = relative_file(parts[2].decode("utf-8"))
            except (UnicodeError, ReproPatchError) as exc:
                raise PatchRejected("FORBIDDEN_PATCH: 补丁路径非法") from exc
            if name not in worktree.initial_manifest.by_path or not _editable(
                name, allowed, protected
            ):
                raise PatchRejected("FORBIDDEN_PATCH: 补丁修改了 protected 路径")
        summary = git_result(worktree.path, "apply", "--summary", str(filename))
        if not summary.ok or summary.stdout:
            raise PatchRejected("FORBIDDEN_PATCH: 创建、删除、rename 或 mode 变化")
        if apply:
            checked = git_result(worktree.path, "apply", "--check", str(filename))
            if not checked.ok:
                raise PatchRejected("PATCH_APPLY_FAILED: 补丁不能应用到原始源码")
            result = git_result(worktree.path, "apply", str(filename))
            if not result.ok:
                raise InfrastructureError("PATCH_APPLY_ERROR: 预查通过后应用失败")
    finally:
        filename.unlink(missing_ok=True)


def apply_candidate(
    target: Worktree,
    candidate: CandidatePatch,
    root: Path,
    baseline: SourceManifest,
    allowed,
    protected=(),
):
    patch, manifest = candidate.load(root)
    if target.revision != candidate.base_commit or target.initial_manifest != baseline:
        raise InfrastructureError("BASELINE_CHANGED: 独立源码不符合原始清单")
    target.apply_patch(patch, allowed, protected)
    if target.manifest() != manifest or target.diff_bytes() != patch:
        raise PatchRejected("PATCH_ROUNDTRIP_MISMATCH: 应用后的完整 bytes/mode 或规范补丁不等价")
    current, changed = target.validate_changes(allowed, protected)
    if changed != candidate.changed_files or current.sha256 != candidate.source_tree_sha256:
        raise InfrastructureError("ARTIFACT_CORRUPT: 候选变化集合不符")
    return current


def copy_patch(source: Worktree, target: Worktree, allowed: tuple[str, ...]) -> None:
    with tempfile.TemporaryDirectory(
        prefix="repropatch-candidate-", dir=source.path.parent
    ) as directory:
        root = Path(directory)
        candidate = source.freeze_candidate(root, allowed)
        apply_candidate(target, candidate, root, source.initial_manifest, allowed)
