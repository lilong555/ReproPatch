"""Small tools with exact schemas and a narrow, source-only mutation policy."""

from pathlib import Path

from .errors import PolicyError, ReproPatchError
from .workspace import Worktree


def _schema(name, description, properties):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }


TOOL_SCHEMAS = [
    _schema(
        "read_file", "Read a tracked UTF-8 source file; at most 64 KB", {"path": {"type": "string"}}
    ),
    _schema(
        "search_code", "Search literal text in tracked UTF-8 files", {"query": {"type": "string"}}
    ),
    _schema(
        "edit_file",
        "Replace exactly one matching fragment in an allowed C++ source file",
        {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
    ),
    _schema(
        "run_command",
        "Run configured build and reproduce/verify in a fresh sandbox",
        {"name": {"type": "string", "enum": ["reproduce", "verify"]}},
    ),
]


class Toolbox:
    def __init__(self, workspace: Worktree, allowed: tuple[str, ...], check):
        self.workspace = workspace
        self.allowed = allowed
        self.check = check

    def invoke(self, name: str, arguments: object) -> dict:
        schema = next((s["function"] for s in TOOL_SCHEMAS if s["function"]["name"] == name), None)
        if schema is None:
            raise PolicyError("Unknown tool")
        props = schema["parameters"]["properties"]
        if not isinstance(arguments, dict) or set(arguments) != set(props):
            raise PolicyError("Tool arguments do not match the schema")
        if any(
            not isinstance(value, str) or len(value) > 64_000 or "\x00" in value
            for value in arguments.values()
        ):
            raise PolicyError("Tool arguments must be bounded strings")
        return getattr(self, name)(**arguments)

    def _text(self, name: str) -> tuple[Path, str]:
        path = self.workspace.safe_path(name)
        if path.stat().st_size > 64_000:
            raise PolicyError("File exceeds 64 KB tool budget")
        try:
            content = path.read_text(encoding="utf-8")
            if "\x00" in content:
                raise ValueError("binary file")
            return path, content
        except (UnicodeError, ValueError) as exc:
            raise PolicyError("Only UTF-8 text files are supported") from exc

    def read_file(self, path: str) -> dict:
        _, content = self._text(path)
        return {"path": path, "content": content}

    def search_code(self, query: str) -> dict:
        if not query or len(query) > 1024:
            raise PolicyError("Search query must contain 1 to 1024 characters")
        matches = []
        total = 0
        for name in sorted(self.workspace.files()):
            try:
                _, content = self._text(name)
            except ReproPatchError:
                continue
            for line, text in enumerate(content.splitlines(), 1):
                if query in text:
                    match = {"path": name, "line": line, "text": text[:300]}
                    matches.append(match)
                    total += len(match["text"])
                    if len(matches) >= 50 or total >= 12_000:
                        return {"matches": matches, "truncated": True}
        return {"matches": matches, "truncated": False}

    def edit_file(self, path: str, old: str, new: str) -> dict:
        if path not in self.allowed:
            raise PolicyError("This file is not in editable_paths")
        destination, content = self._text(path)
        if not old or content.count(old) != 1:
            raise PolicyError("old must match exactly once; re-read the file")
        updated = content.replace(old, new, 1)
        if len(updated.encode()) > 64_000:
            raise PolicyError("Edited file exceeds 64 KB")
        destination.write_text(updated, encoding="utf-8")
        return {"path": path, "changed": updated != content}

    def run_command(self, name: str) -> dict:
        if name not in {"reproduce", "verify"}:
            raise PolicyError("Only configured reproduce/verify commands are allowed")
        results = self.check(name)
        return {
            "passed": all(r.ok for r in results),
            "commands": [{**r.to_dict(), "output": r.output[:8000]} for r in results],
        }
