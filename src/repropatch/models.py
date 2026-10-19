"""Interchangeable model protocol; scripted tests never use a paid service."""

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

from .errors import ReproPatchError


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Turn:
    text: str = ""
    calls: list[ToolCall] = field(default_factory=list)

    def message(self) -> dict:
        message = {"role": "assistant", "content": self.text or None}
        if self.calls:
            message["tool_calls"] = [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                }
                for c in self.calls
            ]
        return message


class Model(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> Turn: ...


class MockModel:
    """A deterministic script, deliberately not a simulated intelligent repairer."""

    def __init__(self, actions: list[dict]):
        self.actions = iter(actions)
        self.index = 0

    @classmethod
    def load(cls, path: Path):
        if path.stat().st_size > 256_000:
            raise ReproPatchError("Mock script exceeds 256 KB")
        try:
            actions = json.loads(path.read_text())
        except (ValueError, OSError) as exc:
            raise ReproPatchError("Invalid mock script") from exc
        if not isinstance(actions, list) or len(actions) > 100:
            raise ReproPatchError("Mock script must be a list of at most 100 actions")
        return cls(actions)

    def complete(self, messages, tools):
        self.index += 1
        action = next(self.actions, {"finish": "Script complete"})
        if not isinstance(action, dict):
            raise ReproPatchError("Mock action must be an object")
        if "finish" in action:
            return Turn(text=str(action["finish"]))
        return Turn(
            calls=[
                ToolCall(f"mock-{self.index}", action.get("tool", ""), action.get("arguments", {}))
            ]
        )


class OpenAICompatibleModel:
    """Host-side Chat Completions tool calling. Never mounted into the sandbox."""

    def __init__(
        self,
        model: str,
        *,
        base_url: str = "https://api.openai.com/v1",
        key_env: str = "OPENAI_API_KEY",
        allow_paid: bool = False,
    ):
        if not allow_paid:
            raise ReproPatchError("Paid model use requires explicit --allow-paid-model consent")
        try:
            endpoint = urlsplit(base_url)
        except ValueError as exc:
            raise ReproPatchError("Invalid model endpoint") from exc
        if (
            endpoint.scheme != "https"
            or not endpoint.hostname
            or endpoint.username
            or endpoint.query
            or endpoint.fragment
        ):
            raise ReproPatchError("Model base URL must be HTTPS without credentials/query")
        self.key = os.environ.get(key_env, "")
        if not self.key:
            raise ReproPatchError(f"Model key environment variable {key_env} is unset")
        self.model = model
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.usage: list[dict] = []

    def complete(self, messages, tools):
        body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "max_completion_tokens": 2048,
            }
        ).encode()
        if len(body) > 1_000_000:
            raise ReproPatchError("Model context budget exceeded")
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )

        # Reject redirects: never forward an API credential to another endpoint.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        try:
            opener = urllib.request.build_opener(NoRedirect())
            with opener.open(request, timeout=60) as response:
                raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ReproPatchError("Model response exceeds 1 MB")

            def reject_constant(value):
                raise ValueError("Non-finite JSON number")

            payload = json.loads(raw, parse_constant=reject_constant)
            choice = payload["choices"][0]
            if choice.get("finish_reason") not in {"stop", "tool_calls"}:
                raise ReproPatchError("Model response is incomplete")
            message = choice["message"]
            calls = message.get("tool_calls", [])
            if not isinstance(calls, list) or len(calls) > 8:
                raise ReproPatchError("Model returned too many tool calls")
            self.usage.append(payload.get("usage", {}))
            parsed = [
                ToolCall(c["id"], c["function"]["name"], json.loads(c["function"]["arguments"]))
                for c in calls
            ]
            if any(
                not isinstance(c.id, str)
                or not c.id
                or len(c.id) > 128
                or not isinstance(c.name, str)
                or not c.name
                or len(c.name) > 128
                for c in parsed
            ):
                raise ReproPatchError("Invalid model tool call identity")
            if len({c.id for c in parsed}) != len(parsed):
                raise ReproPatchError("Duplicate model tool call IDs")
            content = message.get("content") or ""
            if not isinstance(content, str):
                raise ReproPatchError("Model content must be text")
            return Turn(content, parsed)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ReproPatchError("Model request failed; check endpoint and credentials") from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ReproPatchError("Malformed model response") from exc
