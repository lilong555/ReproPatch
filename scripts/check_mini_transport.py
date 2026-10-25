"""用本地 HTTP 夹具检查原生 mini Responses 客户端，供应商请求数为零。"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path


def check(source, output):
    output.mkdir(parents=True, exist_ok=False)
    os.environ["MSWEA_SILENT_STARTUP"] = "1"
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    sys.path.insert(0, str(source / "src"))
    import httpx
    import litellm
    from litellm.llms.custom_httpx.http_handler import HTTPHandler
    from minisweagent.models.litellm_response_model import LitellmResponseModel

    for name in ("LiteLLM", "litellm", "httpx", "openai"):
        logging.getLogger(name).disabled = True
    litellm.telemetry = False
    litellm.num_retries = 0
    received = []

    def respond(request):
        body = json.loads(request.content)
        assert body["model"] == "gpt-6-luna"
        assert body["reasoning"] == {"effort": "max"}
        assert body["max_output_tokens"] == 8192
        received.append(body)
        (output / "request.json").write_bytes(request.content)
        return httpx.Response(
            200,
            json={
                "id": "resp_offline",
                "object": "response",
                "created_at": 0,
                "model": "gpt-6-luna",
                "status": "completed",
                "output": [],
                "reasoning": {"effort": "max"},
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond), trust_env=False) as client:
        model = LitellmResponseModel(
            model_name="openai/gpt-6-luna",
            cost_tracking="ignore_errors",
            model_kwargs={
                "api_base": "https://offline.invalid/v1",
                "api_key": "offline-fixture",
                "max_output_tokens": 8192,
                "stream": False,
                "store": False,
                "num_retries": 0,
                "timeout": 90,
                "reasoning": {"effort": "max"},
            },
        )
        response = model._query(
            [{"role": "user", "content": "离线客户端检查"}],
            client=HTTPHandler(client=client, follow_redirects=False),
        )
    assert len(received) == 1 and response.reasoning["effort"] == "max"
    result = {"passed": True, "paid_model_requests": 0, "fixture_requests": 1}
    (output / "result.json").write_text(json.dumps(result) + "\n")
    print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mini-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(args.mini_source.resolve(strict=True), args.output)


if __name__ == "__main__":
    main()
