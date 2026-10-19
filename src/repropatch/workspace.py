"""Host Git operations never execute build code. Containers see exported files only."""

import hashlib
import os
import shutil
import stat
from pathlib import Path

from .errors import InfrastructureError, PolicyError
from .process import run_process
from .task import relative_file


def git(repo: Path, *args: str) -> str:
    result = run_process(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.autocrlf=false",
            "-C",
            str(repo),
            *args,
        ],
        output_limit=8_000_000,
    )
    if not result.ok or result.output_truncated:
        raise InfrastructureError(f"Git {args[0]} failed: {result.output[:2000]}")
    return result.output


class Worktree:
    def __init__(self, repository: Path, path: Path, revision: str):
        self.repository = repository
        self.path = path
        self.revision = revision
        self.created = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        git(self.repository, "worktree", "add", "--detach", str(self.path), self.revision)
        self.created = True
        return self

    def __exit__(self, *_):
        if self.created:
            git(self.repository, "worktree", "remove", "--force", str(self.path))

    def files(self) -> list[str]:
        return [p for p in git(self.path, "ls-files", "-z").split("\0") if p]

    def safe_path(self, name: str) -> Path:
        try:
            relative_file(name)
        except Exception as exc:
            raise PolicyError(str(exc)) from exc
        path = self.path / name
        for current in (path, *path.parents):
            if current == self.path:
                break
            if current.is_symlink():
                raise PolicyError("Symlink access is forbidden")
        if not path.is_file() or not path.resolve().is_relative_to(self.path.resolve()):
            raise PolicyError("Only existing regular workspace files are accessible")
        if name not in self.files():
            raise PolicyError("Only tracked files are accessible")
        return path

    def export(self, destination: Path) -> str:
        destination.mkdir(parents=True)
        digest = hashlib.sha256()
        total = 0
        for name in sorted(self.files()):
            source = self.safe_path(name)
            mode = source.stat().st_mode
            if not stat.S_ISREG(mode) or source.stat().st_nlink != 1:
                raise PolicyError("Only regular files without hard links may be exported")
            size = source.stat().st_size
            total += size
            if size > 2_000_000 or total > 32_000_000:
                raise PolicyError("MVP source snapshot size limit exceeded")
            content = source.read_bytes()
            for field in (name.encode(), str(mode & 0o777).encode(), content):
                digest.update(len(field).to_bytes(8, "big") + field)
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(0o755 if mode & stat.S_IXUSR else 0o644)
        # A non-root container must traverse the snapshot, even with a private run parent.
        for directory, _, _ in os.walk(destination):
            Path(directory).chmod(0o755)
        return digest.hexdigest()

    def changes(self) -> list[str]:
        return [
            p for p in git(self.path, "diff", "--name-only", "-z", "HEAD", "--").split("\0") if p
        ]

    def diff(self) -> str:
        return git(self.path, "diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--")


def copy_patch(source: Worktree, target: Worktree, allowed: tuple[str, ...]) -> None:
    changes = source.changes()
    if not changes or set(changes) - set(allowed):
        raise PolicyError("Patch is empty or changes protected files")
    for name in changes:
        before = target.safe_path(name)
        after = source.safe_path(name)
        if (before.stat().st_mode & 0o777) != (after.stat().st_mode & 0o777):
            raise PolicyError("File mode changes are forbidden")
        shutil.copyfile(after, before)
