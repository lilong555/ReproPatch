"""Strict task manifest parsing; manifests are operator-trusted, model input is not."""

import math
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import yaml

from .errors import ReproPatchError


def relative_file(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ReproPatchError("Expected a relative POSIX file path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in {"..", ".git"} for p in path.parts):
        raise ReproPatchError("Path escapes the workspace or accesses Git metadata")
    if str(path) != value or value == ".":
        raise ReproPatchError("File paths must be normalized")
    return value


class UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise ReproPatchError("YAML keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


@dataclass(frozen=True)
class Task:
    id: str
    repository: Path
    revision: str
    prompt: str
    editable_paths: tuple[str, ...]
    commands: dict[str, tuple[str, ...]]
    failure_exit_code: int = 8
    failure_contains: str = ""
    timeout_seconds: float = 60
    max_steps: int = 24

    @classmethod
    def load(cls, path: Path) -> "Task":
        if path.stat().st_size > 256_000:
            raise ReproPatchError("Task manifest exceeds 256 KB")
        try:
            raw = yaml.load(path.read_text(), Loader=UniqueLoader)
            return cls.from_dict(raw, path.resolve().parent)
        except (yaml.YAMLError, TypeError, ValueError, KeyError) as exc:
            raise ReproPatchError(f"Invalid task manifest: {exc}") from exc

    @classmethod
    def from_dict(cls, raw: object, base: Path) -> "Task":
        required = {"version", "id", "repository", "prompt", "editable_paths", "commands"}
        optional = {
            "revision",
            "failure_exit_code",
            "failure_contains",
            "timeout_seconds",
            "max_steps",
        }
        if (
            not isinstance(raw, dict)
            or not required <= raw.keys()
            or raw.keys() - required - optional
        ):
            raise ReproPatchError("Task has missing or unknown fields")
        if type(raw["version"]) is not int or raw["version"] != 1:
            raise ReproPatchError("Only task version 1 is supported")
        if not isinstance(raw["id"], str) or not re.fullmatch(
            r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", raw["id"]
        ):
            raise ReproPatchError("Invalid task id")
        for key in ("prompt", "repository"):
            if not isinstance(raw[key], str) or not raw[key] or "\x00" in raw[key]:
                raise ReproPatchError(f"Invalid {key}")
        revision = raw.get("revision", "HEAD")
        if not isinstance(revision, str) or not re.fullmatch(
            r"[a-zA-Z0-9_][a-zA-Z0-9_./~-]*", revision
        ):
            raise ReproPatchError("Invalid Git revision")
        paths = raw["editable_paths"]
        if (
            not isinstance(paths, list)
            or not paths
            or any(not isinstance(p, str) for p in paths)
            or len(paths) != len(set(paths))
        ):
            raise ReproPatchError("editable_paths must contain unique file paths")
        editable = tuple(relative_file(p) for p in paths)
        if any(
            Path(p).suffix not in {".cpp", ".cc", ".cxx", ".c", ".hpp", ".h", ".hh", ".hxx"}
            for p in editable
        ):
            raise ReproPatchError("Only explicit C/C++ source files may be edited in MVP")
        commands = raw["commands"]
        if not isinstance(commands, dict) or set(commands) != {
            "configure",
            "build",
            "reproduce",
            "verify",
        }:
            raise ReproPatchError("commands must define configure, build, reproduce, verify")
        for argv in commands.values():
            if not isinstance(argv, list) or not argv or len(argv) > 64:
                raise ReproPatchError(
                    "Each command must be a bounded argv list, not a shell string"
                )
            if any(not isinstance(s, str) or not s or "\x00" in s or len(s) > 4096 for s in argv):
                raise ReproPatchError("Invalid command argument")
            if argv[0] not in {"cmake", "ctest"}:
                raise ReproPatchError("MVP command executables are restricted to cmake and ctest")
        code = raw.get("failure_exit_code", 8)
        marker = raw.get("failure_contains", "")
        seconds = raw.get("timeout_seconds", 60)
        steps = raw.get("max_steps", 24)
        if type(code) is not int or code not in range(1, 125):
            raise ReproPatchError("failure_exit_code must be between 1 and 124")
        if not isinstance(marker, str) or len(marker) > 4096:
            raise ReproPatchError("Invalid reproduction failure marker")
        if (
            type(seconds) not in {int, float}
            or not math.isfinite(seconds)
            or not 0 < seconds <= 600
        ):
            raise ReproPatchError("timeout_seconds must be finite and in (0, 600]")
        if type(steps) is not int or not 1 <= steps <= 100:
            raise ReproPatchError("max_steps must be between 1 and 100")
        return cls(
            raw["id"],
            (base / raw["repository"]).resolve(),
            revision,
            raw["prompt"],
            editable,
            {k: tuple(v) for k, v in commands.items()},
            code,
            marker,
            seconds,
            steps,
        )
