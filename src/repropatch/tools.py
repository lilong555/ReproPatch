"""六个静态异步 SDK 工具与受控文件操作。"""

from pathlib import Path
from typing import Literal

from .errors import PolicyError
from .task import canonical_json
from .workspace import MAX_EDIT_FILE, Worktree

PREVIEW_LIMIT = 64 * 1024


def model_command(record):
    """模型只接收一次双流预览；旧 output 别名不重复增加上下文。"""
    record = dict(record)
    if record.get("stdout_log") is not None or record.get("stderr_log") is not None:
        record.pop("output", None)
    else:
        record["output"] = record.get("output", "")[:8000]
    return record


def model_baseline(record):
    """初始提示保留全部测试观察和失败诊断；完整命令与 JUnit 留在原始证据中。"""
    tests = [
        {
            key: item.get(key)
            for key in (
                "group",
                "name",
                "observed_status",
                "ctest_exit_code",
                "marker_seen",
                "diagnostic",
            )
        }
        for item in record["tests"]
    ]
    failed = {
        item["command_id"]
        for item in record["tests"]
        if item["observed_status"] != "passed" and item.get("command_id") is not None
    }

    def build_status(name):
        command = record.get(name)
        if command is None:
            return None
        return {
            key: command.get(key)
            for key in (
                "command_id",
                "status",
                "exit_code",
                "error_code",
                "stdout_log",
                "stderr_log",
            )
        }

    return {
        "view_version": 1,
        "evaluation_id": record["evaluation_id"],
        "evidence": record.get("evidence"),
        "source_manifest": record.get("source_manifest"),
        "source_tree_sha256": record.get("source_tree_sha256"),
        "image_id": record.get("image_id"),
        "isolated": record.get("isolated"),
        "configure": build_status("configure"),
        "build": build_status("build"),
        "tests": tests,
        "failed_commands": [
            model_command(item) for item in record["commands"] if item.get("command_id") in failed
        ],
    }


class Toolbox:
    def __init__(self, workspace: Worktree, allowed: tuple[str, ...], check, *, readable=None):
        self.workspace = workspace
        self.allowed = allowed
        self.check = check
        self.readable = frozenset(workspace.files() if readable is None else readable)

    @staticmethod
    def bounded(value, limit=MAX_EDIT_FILE):
        try:
            valid = isinstance(value, str) and "\0" not in value and len(value.encode()) <= limit
        except UnicodeError:
            valid = False
        if not valid:
            raise PolicyError("INVALID_ARGUMENT: 参数必须为有界 UTF-8 文本")

    def _scope(self, path):
        self.bounded(path, 4096)
        if path != "." and (
            path.startswith("/") or any(p in {"", ".", ".."} for p in path.split("/"))
        ):
            raise PolicyError("PATH_NOT_READABLE: 非法相对路径")
        return sorted(
            n for n in self.readable if path == "." or n == path or n.startswith(path + "/")
        )

    def list_directory(self, path="."):
        entries = {}
        prefix = "" if path == "." else path + "/"
        for name in self._scope(path):
            if not name.startswith(prefix):
                continue
            item, *rest = name[len(prefix) :].split("/")
            entries[item] = {"name": item, "type": "directory" if rest else "file"}
        result = [entries[name] for name in sorted(entries)]
        value = {"entries": result[:200], "truncated": len(result) > 200}
        while len(canonical_json(value)) > PREVIEW_LIMIT:
            value["entries"].pop()
            value["truncated"] = True
        return value

    def _text(self, name: str) -> tuple[Path, str]:
        if name not in self.readable:
            raise PolicyError("PATH_NOT_READABLE: 文件不在 files.readable 集合中")
        path = self.workspace.safe_path(name)
        raw, _ = self.workspace.read_file(name)
        try:
            content = raw.decode("utf-8")
            if "\x00" in content:
                raise ValueError("binary file")
            return path, content
        except (UnicodeError, ValueError) as exc:
            raise PolicyError("NOT_UTF8: 只支持 UTF-8 文本") from exc

    def read_file(self, path: str, start_line=1, max_lines=200) -> dict:
        self.bounded(path, 4096)
        if (
            type(start_line) is not int
            or start_line < 1
            or type(max_lines) is not int
            or not 1 <= max_lines <= 400
        ):
            raise PolicyError("INVALID_ARGUMENT: 行号必须为正整数，行数为 1–400")
        _, content = self._text(path)
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)
        content = "".join(lines[start_line - 1 : start_line - 1 + max_lines])
        limit = min(len(content), PREVIEW_LIMIT)
        lower = 0
        upper = limit
        while lower < upper:
            middle = (lower + upper + 1) // 2
            payload = {
                "path": path,
                "content": content[:middle],
                "truncated": middle < len(content),
            }
            if len(canonical_json(payload)) <= PREVIEW_LIMIT:
                lower = middle
            else:
                upper = middle - 1
        result = {
            "path": path,
            "start_line": start_line,
            "text": content[:lower],
            "total_lines": total_lines,
            "truncated": lower < len(content) or start_line - 1 + max_lines < total_lines,
        }
        while len(canonical_json(result)) > PREVIEW_LIMIT:
            result["text"] = result["text"][:-256]
            result["truncated"] = True
        result["end_line"] = start_line + len(result["text"].splitlines()) - 1
        while len(canonical_json(result)) > PREVIEW_LIMIT:
            result["text"] = result["text"][:-256]
            result["truncated"] = True
            result["end_line"] = start_line + len(result["text"].splitlines()) - 1
        return result

    def search_code(self, query: str, path=".") -> dict:
        self.bounded(query, 1024)
        if not query:
            raise PolicyError("Search query must contain 1 to 1024 characters")
        matches = []
        total = 0
        for name in self._scope(path):
            try:
                _, content = self._text(name)
            except PolicyError:
                continue
            for line, text in enumerate(content.splitlines(), 1):
                if query in text:
                    match = {"path": name, "line": line, "text": text[:300]}
                    if (
                        len(canonical_json({"matches": matches + [match], "truncated": True}))
                        > PREVIEW_LIMIT
                    ):
                        return {"matches": matches, "truncated": True}
                    matches.append(match)
                    total += len(match["text"])
                    if len(matches) >= 100:
                        return {"matches": matches, "truncated": True}
        return {"matches": matches, "truncated": False}

    def edit_file(self, path: str, old: str, new: str) -> dict:
        for value in (path, old, new):
            self.bounded(value)
        if path not in self.allowed:
            raise PolicyError("PATH_NOT_EDITABLE: 文件不在 editable 集合")
        _, content = self._text(path)
        count = content.count(old) if old else 0
        if not old or count != 1:
            code = "EDIT_MATCH_NOT_UNIQUE" if count > 1 else "EDIT_MATCH_NOT_FOUND"
            raise PolicyError(f"{code}: old 必须恰好匹配一次")
        before = self.workspace.expected_manifest.by_path[path].sha256
        self.workspace.edit_text(path, old, new)
        return {
            "path": path,
            "before_sha256": before,
            "after_sha256": self.workspace.expected_manifest.by_path[path].sha256,
        }

    def run_command(self, name: str) -> dict:
        if name not in {"reproduce", "verify"}:
            raise PolicyError("Only configured reproduce/verify commands are allowed")
        return self.check(name)


def sdk_tools_sha256(tools=None):
    """公开静态工具 schema 的身份；只构造回调，不调用任何工具。"""
    import hashlib

    from .task import canonical_json

    registered = sdk_tools(None, None, None) if tools is None else tools
    return hashlib.sha256(
        canonical_json(
            [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.params_json_schema,
                    "strict": tool.strict_json_schema,
                }
                for tool in registered
            ]
        )
    ).hexdigest()


def sdk_tools(toolbox, boundary, shell):
    """schema 只由 SDK 从六个真正的 async 回调生成。"""
    from agents import function_tool
    from pydantic import StrictInt

    @function_tool(failure_error_function=None)
    async def list_directory(path: str = ".") -> str:
        """列出 frozen readable 集合中的直接子项。"""
        return await boundary("list_directory", lambda: toolbox.list_directory(path))

    @function_tool(failure_error_function=None)
    async def read_file(path: str, start_line: StrictInt = 1, max_lines: StrictInt = 200) -> str:
        """读取授权 UTF-8 文本的有限行范围。"""
        return await boundary("read_file", lambda: toolbox.read_file(path, start_line, max_lines))

    @function_tool(failure_error_function=None)
    async def search_code(query: str, path: str = ".") -> str:
        """在授权范围内搜索区分大小写的字面文本。"""
        return await boundary("search_code", lambda: toolbox.search_code(query, path))

    @function_tool(failure_error_function=None)
    async def edit_file(path: str, old: str, new: str) -> str:
        """在 editable 文件精确替换唯一文本片段并返回前后哈希。"""
        return await boundary("edit_file", lambda: toolbox.edit_file(path, old, new))

    @function_tool(failure_error_function=None)
    async def run_command(name: Literal["reproduce", "verify"]) -> str:
        """在全新只读源码容器中执行固定自查。"""
        return await boundary("run_command", lambda: toolbox.run_command(name))

    @function_tool(failure_error_function=None)
    async def run_shell(
        command: str,
        cwd: Literal["/src", "/build"] = "/src",
        timeout_seconds: StrictInt | None = None,
    ) -> str:
        """在一次性 Docker 容器内执行 Shell，源码只读。"""
        return await boundary("run_shell", lambda: shell(command, cwd, timeout_seconds))

    return [list_directory, read_file, search_code, edit_file, run_command, run_shell]
