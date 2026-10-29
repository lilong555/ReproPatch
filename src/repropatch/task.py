"""Task v2 的唯一解析边界、不可变配置及规范执行契约。"""

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path, PurePosixPath

import yaml
from yaml.events import AliasEvent

from .errors import ReproPatchError

MAX_TASK_BYTES = 512 * 1024
CTEST_TEMPLATE = ("ctest", "--test-dir", "/build", "--output-on-failure", "--no-tests=error")
OID = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})\Z")
IMAGE_ID = re.compile(r"sha256:[a-f0-9]{64}\Z")
IMAGE = re.compile(r"(?:[a-z0-9][a-z0-9._:/-]*@)?sha256:[a-f0-9]{64}\Z")


def canonical_json(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def fail(path: str, message: str):
    raise ReproPatchError(f"{path}: {message}")


def text(value, path, *, limit=None, controls=False):
    if not isinstance(value, str) or not value or "\x00" in value:
        fail(path, "期望非空字符串")
    if controls and any(ord(c) < 32 or 127 <= ord(c) < 160 for c in value):
        fail(path, "不允许控制字符")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        fail(path, "内容必须是有效 UTF-8")
    if limit is not None and size > limit:
        fail(path, f"UTF-8 内容超过 {limit} 字节")
    return value


def relative_file(value: object) -> str:
    value = text(value, "path", controls=True)
    path = PurePosixPath(value)
    if (
        "\\" in value
        or path.is_absolute()
        or any(p in {"..", ".git", ".repropatch"} for p in path.parts)
    ):
        fail("path", "禁止路径穿越、Git 元数据及控制产物")
    if str(path) != value or value == ".":
        fail("path", "期望规范 POSIX 文件路径")
    return value


def mapping(raw, path, required, optional=()):
    if not isinstance(raw, dict) or any(not isinstance(k, str) for k in raw):
        fail(path, "期望字符串键对象")
    missing = set(required) - raw.keys()
    unknown = raw.keys() - set(required) - set(optional)
    if missing or unknown:
        fail(path, f"缺少字段 {sorted(missing)}；未知字段 {sorted(unknown)}")
    return raw


def positive(value, path):
    if type(value) is not int or value <= 0:
        fail(path, "期望正整数，不能使用 bool 或字符串数字")
    return value


def path_list(value, path, *, directories=False):
    if not isinstance(value, list) or not value:
        fail(path, "期望非空路径数组")
    result = []
    for i, item in enumerate(value):
        item = text(item, f"{path}[{i}]", controls=True)
        is_directory = directories and item.endswith("/")
        normalized = relative_file(item[:-1] if is_directory else item)
        result.append(normalized + ("/" if is_directory else ""))
    if len(result) != len(set(result)):
        fail(path, "路径不能重复")
    return tuple(result)


class UniqueLoader(yaml.SafeLoader):
    """只在 YAML 边界拒绝别名、锚点、过深结构及重复键。"""

    def __init__(self, stream):
        super().__init__(stream)
        self.depth = 0

    def compose_node(self, parent, index):
        event = self.peek_event()
        if isinstance(event, AliasEvent) or getattr(event, "anchor", None) is not None:
            fail("task", "不支持 YAML anchor/alias")
        self.depth += 1
        try:
            if self.depth > 12:
                fail("task", "YAML 结构深度超过 12")
            return super().compose_node(parent, index)
        finally:
            self.depth -= 1


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            mark = key_node.start_mark
            fail(
                "task",
                f"YAML 键必须是唯一字符串（unique），行 {mark.line + 1} 列 {mark.column + 1}",
            )
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


@dataclass(frozen=True)
class Environment:
    image: str
    platform: str = "linux/amd64"
    cpu_limit: float = 2.0
    memory_mib: int = 2048
    pids_limit: int = 128
    build_tmpfs_mib: int = 1024
    tmp_executable: bool = False


@dataclass(frozen=True)
class Budget:
    max_steps: int = 24
    max_tool_calls: int = 80
    wall_seconds: int = 900
    verification_reserve_seconds: int = 240
    model_timeout_seconds: int = 60
    command_timeout_seconds: int = 120
    max_output_tokens: int = 2048


@dataclass(frozen=True)
class Failure:
    name: str
    expected_exit_code: int
    output_contains: str


@dataclass(frozen=True)
class Tests:
    fail_to_pass: tuple[Failure, ...]
    pass_to_pass: tuple[str, ...]
    protected_paths: tuple[str, ...]


@dataclass(frozen=True)
class Commands:
    configure: tuple[str, ...]
    build: tuple[str, ...]
    reproduce: tuple[str, ...]
    verify: tuple[str, ...]

    def __getitem__(self, name):
        if name not in {"configure", "build", "reproduce", "verify"}:
            raise KeyError(name)
        return getattr(self, name)

    def to_dict(self):
        return {name: list(argv) for name, argv in asdict(self).items()}


@dataclass(frozen=True)
class Task:
    id: str
    repository: Path
    revision: str
    prompt: str
    editable_paths: tuple[str, ...]
    readable_paths: tuple[str, ...]
    environment: Environment
    commands: Commands
    tests: Tests
    budget: Budget
    workspace_root: Path
    output_root: Path
    retain: str = "on_failure"
    source_bytes: bytes = field(default=b"", repr=False, compare=False)
    version: int = field(default=2, init=False)

    @property
    def max_steps(self):
        return self.budget.max_steps

    @property
    def timeout_seconds(self):
        return self.budget.command_timeout_seconds

    @classmethod
    def load(cls, path: Path):
        with path.open("rb") as stream:
            source = stream.read(MAX_TASK_BYTES + 1)
        if len(source) > MAX_TASK_BYTES:
            fail("task", f"清单超过 {MAX_TASK_BYTES // 1024} KiB")
        try:
            raw = yaml.load(source.decode("utf-8"), Loader=UniqueLoader)
            return cls.from_dict(raw, path.resolve().parent, source_bytes=source)
        except (yaml.YAMLError, UnicodeError, RecursionError, ValueError) as exc:
            raise ReproPatchError(f"task: YAML 解析错误：{exc}") from exc

    @classmethod
    def from_dict(cls, raw, base: Path, *, source_bytes=None):
        if (
            isinstance(raw, dict)
            and "version" in raw
            and (type(raw["version"]) is not int or raw["version"] != 2)
        ):
            fail(
                "version",
                "TASK_VERSION_UNSUPPORTED: 仅支持 version 2；"
                "迁移见 specs/2026-10-19.2/docs/TASK_FORMAT.md#4-v1-迁移",
            )
        raw = mapping(
            raw,
            "task",
            ("version", "id", "repository", "environment", "bug", "commands", "tests", "files"),
            ("budget", "workspace", "outputs"),
        )
        task_id = text(raw["id"], "id")
        if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", task_id) is None:
            fail("id", "期望小写任务标签 [a-z0-9][a-z0-9._-]{0,63}")
        repository = raw["repository"]
        if isinstance(repository, dict) and "url" in repository:
            fail("repository.url", "Phase 1 仅支持操作者提供的本地仓库")
        repository = mapping(repository, "repository", ("path", "commit"))
        path = text(repository["path"], "repository.path", controls=True)
        commit = text(repository["commit"], "repository.commit")
        if OID.fullmatch(commit) is None:
            fail(
                "repository.commit",
                "必须是 40 或 64 位小写完整 commit OID，不接受 HEAD、tag 或缩写",
            )
        environment = mapping(
            raw["environment"],
            "environment",
            ("image",),
            tuple(set(Environment.__dataclass_fields__) - {"image"}),
        )
        image = text(environment["image"], "environment.image")
        if (
            IMAGE.fullmatch(image) is None
            or image.startswith("/")
            or ".." in image.split("/")
            or "//" in image
        ):
            fail(
                "environment.image", "必须是固定 sha256 image ID 或 name@sha256:digest，不接受 tag"
            )
        values = asdict(Environment(image)) | environment
        if values["platform"] != "linux/amd64":
            fail("environment.platform", "Phase 1 仅支持 linux/amd64")
        cpu = values["cpu_limit"]
        try:
            valid_cpu = type(cpu) in (int, float) and math.isfinite(cpu) and cpu > 0
        except OverflowError:
            valid_cpu = False
        if not valid_cpu:
            fail("environment.cpu_limit", "期望有限正数")
        values["cpu_limit"] = float(cpu)
        for key in ("memory_mib", "pids_limit", "build_tmpfs_mib"):
            positive(values[key], f"environment.{key}")
        if type(values["tmp_executable"]) is not bool:
            fail("environment.tmp_executable", "期望布尔值")
        if values["build_tmpfs_mib"] >= values["memory_mib"]:
            fail("environment.build_tmpfs_mib", "必须小于 memory_mib")
        bug = mapping(raw["bug"], "bug", ("description",))
        description = text(bug["description"], "bug.description", limit=32 * 1024)
        commands = mapping(raw["commands"], "commands", Commands.__dataclass_fields__)
        argv = {}
        for name, command in commands.items():
            if not isinstance(command, list) or not command:
                fail(f"commands.{name}", "期望非空 argv 字符串数组")
            argv[name] = tuple(
                text(part, f"commands.{name}[{i}]") for i, part in enumerate(command)
            )
        configure = argv["configure"]
        if configure[0] != "cmake" or any(
            x in configure for x in ("-P", "--build", "--install", "--workflow", "--find-package")
        ):
            fail("commands.configure", "仅支持 cmake 配置命令")
        for option, location in (("-S", "/src"), ("-B", "/build")):
            if option + location not in configure and not any(
                configure[i : i + 2] == (option, location) for i in range(len(configure) - 1)
            ):
                fail("commands.configure", f"必须指定 {option} {location}")
        if argv["build"][:3] != ("cmake", "--build", "/build"):
            fail("commands.build", "必须使用 cmake --build /build")
        for name in ("reproduce", "verify"):
            command = argv[name]
            if (
                command.count("--verbose") > 1
                or tuple(x for x in command if x != "--verbose") != CTEST_TEMPLATE
            ):
                fail(f"commands.{name}", "必须采用固定 CTest 模板，仅允许额外一个 --verbose")
        tests = mapping(raw["tests"], "tests", ("fail_to_pass", "pass_to_pass", "protected_paths"))
        failures = tests["fail_to_pass"]
        if not isinstance(failures, list) or not failures:
            fail("tests.fail_to_pass", "期望至少一个失败用例")
        f2p = []
        for i, entry in enumerate(failures):
            prefix = f"tests.fail_to_pass[{i}]"
            entry = mapping(entry, prefix, ("name", "expected_exit_code", "output_contains"))
            name = text(entry["name"], prefix + ".name", controls=True)
            code = positive(entry["expected_exit_code"], prefix + ".expected_exit_code")
            if code > 255:
                fail(prefix + ".expected_exit_code", "必须在 1..255")
            marker = text(entry["output_contains"], prefix + ".output_contains", limit=4 * 1024)
            f2p.append(Failure(name, code, marker))
        passes = tests["pass_to_pass"]
        if not isinstance(passes, list) or not passes:
            fail("tests.pass_to_pass", "期望至少一个回归用例")
        passes = tuple(
            text(name, f"tests.pass_to_pass[{i}]", controls=True) for i, name in enumerate(passes)
        )
        all_names = [failure.name for failure in f2p] + list(passes)
        if len(all_names) != len(set(all_names)):
            fail("tests", "F2P/P2P 用例不能重复或相交")
        protected = path_list(tests["protected_paths"], "tests.protected_paths", directories=True)
        files = mapping(raw["files"], "files", ("readable", "editable"))
        readable = path_list(files["readable"], "files.readable", directories=True)
        editable = path_list(files["editable"], "files.editable")
        if any(
            PurePosixPath(p).suffix
            not in {".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hh", ".hxx"}
            or any(c in p for c in "*?[")
            for p in editable
        ):
            fail("files.editable", "只能逐个列举已有 C/C++ 普通文件，不能使用目录或 glob")
        budget = mapping(raw.get("budget", {}), "budget", (), Budget.__dataclass_fields__)
        budget = asdict(Budget()) | budget
        for name, number in budget.items():
            positive(number, "budget." + name)
        if budget["wall_seconds"] <= budget["verification_reserve_seconds"] + 10:
            fail("budget.wall_seconds", "必须大于 verification_reserve_seconds + 10")
        workspace = mapping(raw.get("workspace", {}), "workspace", (), ("root", "retain"))
        outputs = mapping(raw.get("outputs", {}), "outputs", (), ("root",))
        retain = workspace.get("retain", "on_failure")
        if retain not in ("none", "on_failure", "always"):
            fail("workspace.retain", "期望 none/on_failure/always")
        workspace_root = text(
            workspace.get("root", ".repropatch/workspaces"), "workspace.root", controls=True
        )
        output_root = text(outputs.get("root", ".repropatch/runs"), "outputs.root", controls=True)
        return cls(
            id=task_id,
            repository=(base / path).resolve(),
            revision=commit,
            prompt=description,
            editable_paths=editable,
            readable_paths=readable,
            environment=Environment(**values),
            commands=Commands(**argv),
            tests=Tests(tuple(f2p), passes, protected),
            budget=Budget(**budget),
            workspace_root=(base / workspace_root).resolve(),
            output_root=(base / output_root).resolve(),
            retain=retain,
            source_bytes=source_bytes if source_bytes is not None else canonical_json(raw),
        )

    def to_dict(self):
        return {
            "version": 2,
            "id": self.id,
            "repository": {"path": str(self.repository), "commit": self.revision},
            "environment": asdict(self.environment),
            "bug": {"description": self.prompt},
            "commands": self.commands.to_dict(),
            "tests": {
                "fail_to_pass": [asdict(f) for f in self.tests.fail_to_pass],
                "pass_to_pass": list(self.tests.pass_to_pass),
                "protected_paths": list(self.tests.protected_paths),
            },
            "files": {"readable": list(self.readable_paths), "editable": list(self.editable_paths)},
            "budget": asdict(self.budget),
            "workspace": {"root": str(self.workspace_root), "retain": self.retain},
            "outputs": {"root": str(self.output_root)},
        }


TaskSpec = Task


@dataclass(frozen=True)
class ImageIdentity:
    image_id: str
    repo_digests: tuple[str, ...] = ()
    platform: str = "linux/amd64"
    docker_version: str | None = None


def inspect_image(reference: str) -> ImageIdentity:
    """只查询本地镜像，不下载、不构建，也不读取模型密钥。"""
    import os
    import platform
    import shutil
    import sys

    from .process import run_process

    if sys.platform != "linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        fail("environment.platform", "PLATFORM_UNSUPPORTED: 需要 Linux amd64 主机")
    host = os.environ.get("DOCKER_HOST", "")
    if host and not host.startswith("unix://"):
        fail("environment", "REMOTE_DOCKER_UNSUPPORTED: 只支持本地 daemon")
    executable = shutil.which("docker")
    if executable is None:
        fail("environment.image", "DOCKER_UNAVAILABLE: 需要本地 Docker")
    result = run_process([executable, "image", "inspect", reference], timeout=15)
    if not result.ok or result.output_truncated:
        fail("environment.image", "IMAGE_NOT_FOUND: 请先准备固定的本地镜像")
    try:
        images = json.loads(result.output)
        if not isinstance(images, list) or len(images) != 1:
            raise ValueError("镜像数量错误")
        image = images[0]
        image_id = image["Id"]
        platform_name = image["Os"] + "/" + image["Architecture"]
        repo_digests = image.get("RepoDigests") or []
        if not isinstance(image_id, str) or IMAGE_ID.fullmatch(image_id) is None:
            raise ValueError("镜像 ID 错误")
        if not isinstance(repo_digests, list) or any(not isinstance(d, str) for d in repo_digests):
            raise ValueError("RepoDigests 错误")
        if platform_name != "linux/amd64":
            fail("environment.platform", "PLATFORM_UNSUPPORTED: 镜像必须为 linux/amd64")
    except (KeyError, TypeError, ValueError) as exc:
        raise ReproPatchError("environment.image: IMAGE_INSPECT_INVALID") from exc
    version = run_process([executable, "version", "--format", "{{.Server.Version}}"], timeout=15)
    if not version.ok or version.output_truncated:
        fail("environment", "DOCKER_UNAVAILABLE: 无法查询本地 Engine 版本")
    return ImageIdentity(
        image_id, tuple(sorted(repo_digests)), platform_name, version.output.strip()
    )


@dataclass(frozen=True)
class ResolvedTask:
    task: Task
    task_source_sha256: str
    task_sha256: str
    repository_path: Path
    base_commit: str
    image_id: str
    image_repo_digests: tuple[str, ...]
    readable_files: frozenset[str]
    editable_files: frozenset[str]
    protected_files: frozenset[str]
    workspace_root: Path
    output_root: Path
    tool_versions: tuple[tuple[str, str | None], ...]

    def execution_contract(self):
        environment = asdict(self.task.environment)
        environment["image"] = self.image_id
        return {
            "version": 2,
            "id": self.task.id,
            "base_commit": self.base_commit,
            "environment": environment,
            "bug": {"description": self.task.prompt},
            "commands": self.task.commands.to_dict(),
            "tests": {
                "fail_to_pass": [asdict(f) for f in self.task.tests.fail_to_pass],
                "pass_to_pass": list(self.task.tests.pass_to_pass),
            },
            "files": {
                "readable": sorted(self.readable_files),
                "editable": sorted(self.editable_files),
                "protected": sorted(self.protected_files),
            },
            "budget": asdict(self.task.budget),
        }

    def to_dict(self):
        return {
            "task": self.task.to_dict(),
            "task_source_sha256": self.task_source_sha256,
            "task_sha256": self.task_sha256,
            "repository_path": str(self.repository_path),
            "base_commit": self.base_commit,
            "image_id": self.image_id,
            "image_repo_digests": list(self.image_repo_digests),
            "readable_files": sorted(self.readable_files),
            "editable_files": sorted(self.editable_files),
            "protected_files": sorted(self.protected_files),
            "workspace_root": str(self.workspace_root),
            "output_root": str(self.output_root),
            "tool_versions": dict(self.tool_versions),
            "execution_contract": self.execution_contract(),
        }


def task_roots(task: Task, output_root=None):
    """写入 Run 目录之前验证专用根，避免错误输入污染源码仓库。"""
    repository = task.repository.resolve()
    if repository.exists():
        from .workspace import audit_git, git

        audit_git(repository)
        bare = git(repository, "rev-parse", "--is-bare-repository").strip() == "true"
        option = "--absolute-git-dir" if bare else "--show-toplevel"
        actual_root = Path(git(repository, "rev-parse", option).removesuffix("\n")).resolve()
        if repository != actual_root:
            fail("repository.path", "REPOSITORY_ROOT_REQUIRED: 必须指定仓库根，不能指定仓库子目录")
    workspace = task.workspace_root.resolve()
    output = (Path(output_root) if output_root is not None else task.output_root).resolve()
    for name, path in (("workspace.root", workspace), ("outputs.root", output)):
        if path.is_relative_to(repository) or repository.is_relative_to(path):
            fail(name, "ROOT_OVERLAP: 专用根不能位于源码中或包含源码仓库")
        if path in {
            Path("/"),
            Path("/home"),
            Path.home(),
            Path("/tmp"),
            Path("/var"),
            Path("/var/tmp"),
        } or any(
            path.is_relative_to(Path(p))
            for p in (
                "/etc",
                "/usr",
                "/bin",
                "/sbin",
                "/boot",
                "/proc",
                "/sys",
                "/dev",
                "/run",
                "/lib",
                "/lib64",
            )
        ):
            fail(name, "UNSAFE_ROOT: 不能使用系统目录作为工作区或产物根")
    if workspace.is_relative_to(output) or output.is_relative_to(workspace):
        fail("workspace.root", "ROOT_OVERLAP: 工作区和产物根不能互相包含")
    return repository, workspace, output


def resolve_task(task: Task, *, output_root=None, image_identity=None) -> ResolvedTask:
    """对已读取一次的配置做动态核验；不执行源码或重新加载 YAML。"""
    from .workspace import audit_attributes, git, git_blob, git_tree

    repository, workspace, output = task_roots(task, output_root)
    repository = repository.resolve(strict=True)
    object_format = git(repository, "rev-parse", "--show-object-format").strip()
    if object_format not in ("sha1", "sha256") or len(task.revision) != (
        40 if object_format == "sha1" else 64
    ):
        fail("repository.commit", "COMMIT_FORMAT_MISMATCH: OID 长度与仓库对象格式不符")
    if git(repository, "cat-file", "-t", task.revision).strip() != "commit":
        fail("repository.commit", "COMMIT_TYPE_INVALID: 必须直接指向 commit，不能是 tag 对象")
    entries = git_tree(repository, task.revision)
    audit_attributes(repository, task.revision, entries)
    tracked = {entry.path: entry.oid for entry in entries}

    def expand(paths, label):
        result = set()
        for path in paths:
            selected = (
                {p for p in tracked if p.startswith(path)}
                if path.endswith("/")
                else ({path} if path in tracked else set())
            )
            if not selected:
                fail(label, f"TASK_PATH_NOT_FOUND: {path}")
            result.update(selected)
        return frozenset(result)

    readable = expand(task.readable_paths, "files.readable")
    editable = expand(task.editable_paths, "files.editable")
    protected = expand(task.tests.protected_paths, "tests.protected_paths") | frozenset(
        p for p in tracked if PurePosixPath(p).name == "CMakeLists.txt" or p.endswith(".cmake")
    )
    if not editable <= readable:
        fail("files.editable", "必须是展开后 readable 集合的子集")
    if editable & protected:
        fail("files.editable", "FORBIDDEN_EDITABLE_PATH: 与 protected 集合相交")
    for path in sorted(readable):
        content = git_blob(repository, tracked[path])
        try:
            content.decode("utf-8")
        except UnicodeError:
            fail("files.readable", f"UNSUPPORTED_TEXT_FILE: {path} 必须是 UTF-8 文本")
        if b"\x00" in content:
            fail("files.readable", f"UNSUPPORTED_TEXT_FILE: {path} 含二进制 NUL")
    image = image_identity if image_identity is not None else inspect_image(task.environment.image)
    if IMAGE_ID.fullmatch(image.image_id) is None or image.image_id == "sha256:" + "0" * 64:
        fail("environment.image", "IMAGE_PLACEHOLDER: 需要真实的非占位镜像 ID")
    if task.environment.image.startswith("sha256:") and image.image_id != task.environment.image:
        fail("environment.image", "IMAGE_ID_MISMATCH: 本地对象与声明 ID 不一致")
    if image.platform != task.environment.platform:
        fail("environment.platform", "PLATFORM_UNSUPPORTED: 镜像平台不匹配")
    resolved = ResolvedTask(
        task,
        hashlib.sha256(task.source_bytes).hexdigest(),
        "",
        repository,
        task.revision,
        image.image_id,
        image.repo_digests,
        readable,
        editable,
        protected,
        workspace,
        output,
        (("git", git(repository, "--version").strip()), ("docker", image.docker_version)),
    )
    return replace(
        resolved,
        task_sha256=hashlib.sha256(canonical_json(resolved.execution_contract())).hexdigest(),
    )
