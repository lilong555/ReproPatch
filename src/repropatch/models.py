"""公开 SDK 模型构造与有界原生测试脚本。"""

import json
import logging
import math
import os
import re
import stat
from contextlib import asynccontextmanager
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import urlsplit

from .errors import ReproPatchError

SDK_VERSIONS = {"openai-agents": "0.24.0", "openai": "3.35.1"}


def prepare_sdk():
    """仅在显式使用 SDK 时加载可选依赖，并关闭外发追踪与供应商日志。"""
    for package, expected in SDK_VERSIONS.items():
        try:
            installed = version(package)
        except PackageNotFoundError:
            raise ReproPatchError("ENGINE_DEPENDENCY_MISSING：请安装 repropatch[agent]") from None
        if installed != expected:
            raise ReproPatchError(f"SDK_VERSION_MISMATCH：{package} 必须为 {expected}")
    # 只配置公开日志接口；即使宿主启用 DEBUG，也不输出请求、响应或异常体。
    for name in ("openai.agents", "openai._base_client", "openai._client", "httpx2"):
        logging.getLogger(name).disabled = True
    os.environ["OPENAI_AGENTS_DONT_LOG_MODEL_DATA"] = "1"
    os.environ["OPENAI_AGENTS_DONT_LOG_TOOL_DATA"] = "1"
    from agents import set_tracing_disabled

    set_tracing_disabled(True)


def positive_timeout(value):
    """取消期限必须为有限正数。"""
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ReproPatchError("SDK timeout 必须为有限正数")
    return value


def validate_model_options(model_name, base_url, key_env, allow_paid):
    """在创建 Run 前审核不会含秘密的模型配置。"""
    if allow_paid is not True:
        raise ReproPatchError("PAID_MODEL_CONSENT_REQUIRED：真实模型必须显式授权")
    if not isinstance(model_name, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model_name
    ):
        raise ReproPatchError("必须显式提供有效模型名")
    if not isinstance(key_env, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", key_env):
        raise ReproPatchError("无效的模型凭据环境变量名")
    try:
        endpoint = urlsplit(base_url)
        valid_port = endpoint.port
    except (ValueError, TypeError):
        raise ReproPatchError("无效的模型端点") from None
    if (
        not isinstance(base_url, str)
        or endpoint.scheme != "https"
        or not endpoint.hostname
        or endpoint.username is not None
        or endpoint.password is not None
        or endpoint.query
        or endpoint.fragment
        or any(ord(char) <= 32 or ord(char) == 127 for char in base_url)
        or "\\" in base_url
        or valid_port == 0
    ):
        raise ReproPatchError("模型端点必须为不含凭据、查询或片段的 HTTPS URL")


@asynccontextmanager
async def responses_model(
    model_name: str,
    *,
    model_timeout: float,
    allow_paid: bool = False,
    base_url: str = "https://api.openai.com/v1",
    key_env: str = "OPENAI_API_KEY",
    use_env_proxy: bool = False,
    http_client=None,
):
    """构造公开 Responses 模型；凭据仅属于客户端，退出时关闭所属传输。"""
    validate_model_options(model_name, base_url, key_env, allow_paid)
    if type(use_env_proxy) is not bool:
        raise ReproPatchError("use_env_proxy 必须为布尔值")
    positive_timeout(model_timeout)
    prepare_sdk()
    key = os.environ.get(key_env, "")
    if not key or key.strip() != key or any(ord(c) <= 32 or ord(c) >= 127 for c in key):
        raise ReproPatchError("MODEL_CREDENTIAL_MISSING：指定环境变量须含有效凭据")
    from agents import OpenAIResponsesModel
    from httpx2 import AsyncClient
    from openai import AsyncOpenAI

    transport = http_client or AsyncClient(trust_env=use_env_proxy, follow_redirects=False)
    async with AsyncOpenAI(
        api_key=key,
        base_url=base_url,
        timeout=model_timeout,
        max_retries=0,
        http_client=transport,
    ) as client:
        yield OpenAIResponsesModel(model=model_name, openai_client=client)


def raw_token_usage(response) -> dict[str, int | None]:
    """只读取公开 raw_usage；SDK 累计器的缺省零不代表已观测消耗。"""
    raw = response.raw_usage
    return {
        key: raw[key]
        if isinstance(raw, dict) and type(raw.get(key)) is int and raw[key] >= 0
        else None
        for key in ("input_tokens", "output_tokens", "total_tokens")
    }


def load_sdk_script(path: Path, *, with_source=False, steps_used=0):
    """将有限的原生 JSON 转为公开 ScriptedModel；不加载代码或故障表达式。"""

    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("不是普通文件")
            content = stream.read(256_001)
        if len(content) > 256_000:
            raise ValueError("超限")
    except (OSError, ValueError, TypeError):
        raise ReproPatchError("INVALID_SDK_SCRIPT：需要有界普通 JSON 脚本") from None
    model = sdk_script_bytes(content, steps_used=steps_used)
    return (model, content) if with_source else model


def sdk_script_bytes(content, *, steps_used=0):
    """直接解析已核验的冻结 bytes，避免两次读取之间更换脚本。"""

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("重复键")
            result[key] = value
        return result

    def reject_constant(_):
        raise ValueError("非有限数字")

    try:
        if type(content) is not bytes or len(content) > 256000:
            raise ValueError("无效脚本字节")
        script = json.loads(content, object_pairs_hook=pairs, parse_constant=reject_constant)
        if (
            not isinstance(script, dict)
            or set(script) != {"version", "steps"}
            or type(script["version"]) is not int
            or script["version"] != 1
            or not isinstance(script["steps"], list)
            or not 1 <= len(script["steps"]) <= 100
        ):
            raise ValueError("无效脚本结构")
    except (OSError, ValueError, TypeError, RecursionError):
        raise ReproPatchError("INVALID_SDK_SCRIPT：需要有界普通 JSON 脚本") from None
    prepare_sdk()
    from agents import Usage
    from agents.testing import ModelStep, ScriptedModel
    from openai.types.responses import (
        ResponseFunctionToolCall,
        ResponseOutputMessage,
        ResponseReasoningItem,
    )

    types = {
        "message": ResponseOutputMessage,
        "function_call": ResponseFunctionToolCall,
        "reasoning": ResponseReasoningItem,
    }
    steps = []
    try:
        for step in script["steps"]:
            if (
                not isinstance(step, dict)
                or not {"output"} <= set(step) <= {"output", "usage"}
                or not isinstance(step["output"], list)
                or len(step["output"]) > 32
            ):
                raise ValueError("无效步骤")
            output = []
            for item in step["output"]:
                if not isinstance(item, dict) or item.get("type") not in types:
                    raise ValueError("不支持的原生项")
                output.append(types[item["type"]].model_validate(item, strict=True, extra="forbid"))
            usage = step.get("usage")
            if "usage" in step and (
                not isinstance(usage, dict)
                or not set(usage) <= {"input_tokens", "output_tokens", "total_tokens"}
                or any(type(v) is not int or v < 0 for v in usage.values())
            ):
                raise ValueError("无效合成用量")
            steps.append(
                ModelStep(output=output, usage=Usage(requests=1, **(usage or {})), raw_usage=usage)
            )
    except (ValueError, TypeError, KeyError, RecursionError):
        raise ReproPatchError("INVALID_SDK_SCRIPT：无效原生输出或合成用量") from None
    if type(steps_used) is not int or not 0 <= steps_used <= len(steps):
        raise ReproPatchError("INVALID_SDK_SCRIPT: 累计 turn 超过冻结脚本")
    model = ScriptedModel(steps=steps[steps_used:], emit_traces=False)
    return model


@dataclass(frozen=True)
class ResponsesConfig:
    """宿主模型配置；不持有凭据或实现模型协议。"""

    model: str
    url: str
    key_env: str
    allow_paid: bool
    use_env_proxy: bool = False

    def __post_init__(self):
        validate_model_options(self.model, self.url, self.key_env, self.allow_paid)
        if type(self.use_env_proxy) is not bool:
            raise ReproPatchError("use_env_proxy 必须为布尔值")
