"""拉取固定 C++ 镜像；仅对网络故障重试，保存资格开始前的失败证据。"""

import argparse
import json
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

IMAGE = re.compile(r"ghcr\.io/lilong555/repropatch-cross-cpp@sha256:[a-f0-9]{64}\Z")
TRANSIENT = re.compile(
    r"context deadline exceeded|TLS handshake timeout|i/o timeout|"
    r"connection (?:reset|refused)|temporary failure in name resolution|"
    r"no such host|unexpected EOF|request canceled|"
    r"(?:502|503|504) (?:Bad Gateway|Service Unavailable|Gateway Time-out)|"
    r"received unexpected HTTP status: (?:500|502|503|504)|toomanyrequests",
    re.IGNORECASE,
)


def pull_image(image, output, *, instance=None):
    if not IMAGE.fullmatch(image):
        raise ValueError("IMMUTABLE_CPP_IMAGE_REQUIRED")
    report = {
        "schema": "repropatch.image-pull.v1",
        "instance_id": instance,
        "image": image,
        "stage": "image_pull",
        "status": "IMAGE_PULL_FAILED",
        "model_requests": 0,
        "qualification_executed": False,
        "attempts": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 4):
        started = time.monotonic()
        try:
            process = subprocess.run(
                ["docker", "pull", image],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            code, message = process.returncode, process.stdout + process.stderr
            transient = code != 0 and bool(TRANSIENT.search(message))
        except subprocess.TimeoutExpired:
            code, message, transient = 124, "DOCKER_PULL_TIMEOUT", True
        except OSError as error:
            code, message, transient = 127, type(error).__name__, False
        # 镜像仓库错误可能包含签名下载地址，只保留主机与路径。
        message = re.sub(r'(https?://[^\s?"<>]+)\?[^\s"<>]+', r"\1?<redacted>", message)
        report["attempts"].append(
            {
                "attempt": attempt,
                "exit_code": code,
                "wall_seconds": time.monotonic() - started,
                "retryable_network_error": transient,
                "diagnostic": message[-4000:],
            }
        )
        report["status"] = "IMAGE_PULLED" if code == 0 else "IMAGE_PULL_FAILED"
        report["updated_at"] = datetime.now(UTC).isoformat()
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(
            json.dumps({"status": report["status"], "attempt": attempt, "exit_code": code}),
            flush=True,
        )
        if code == 0:
            return 0
        if not transient:
            break
        if attempt < 3:
            time.sleep(attempt * 2)
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--instance")
    args = parser.parse_args()
    return pull_image(args.image, args.output, instance=args.instance)


if __name__ == "__main__":
    raise SystemExit(main())
