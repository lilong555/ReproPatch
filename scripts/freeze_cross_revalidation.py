"""以独立 Attempt 身份登记基础设施复验，保留原始评分与请求账本。"""

import argparse
import copy
import json
from pathlib import Path

from cross_repo_campaign import validate_protocol
from qualify_cpp_batch import save, sha


def revalidation(source, results, selected):
    validate_protocol(source)
    rows = results.get("attempts", [])
    original = {row["attempt_id"]: row for row in source["attempts"]}
    observed = {row["attempt_id"]: row for row in rows}
    if (
        len(observed) != len(rows)
        or len(set(selected)) != len(selected)
        or not 1 <= len(selected) <= 20
    ):
        raise ValueError("CROSS_REVALIDATION_REGISTRY_INVALID")
    attempts = []
    for identity in selected:
        row = observed.get(identity, {})
        if (
            identity not in original
            or row.get("score", {}).get("classification") != "infrastructure"
            or row.get("score", {}).get("accepted") is True
        ):
            raise ValueError("CROSS_REVALIDATION_INFRASTRUCTURE_EVIDENCE_REQUIRED")
        registered = original[identity]
        if any(row.get(key) != registered[key] for key in ("instance_id", "arm")):
            raise ValueError("CROSS_REVALIDATION_ATTEMPT_IDENTITY_MISMATCH")
        attempts.append(
            {
                **registered,
                "attempt_id": identity + "/infrastructure-revalidation",
                "original_attempt_id": identity,
            }
        )
    value = copy.deepcopy(source)
    value.update(
        phase="infrastructure-revalidation",
        attempts=attempts,
        execution_order=attempts,
        tasks=sorted({row["instance_id"] for row in attempts}),
        formal_request_cap=len(attempts) * 24,
    )
    value["qualification_contracts"] = {
        task: source["qualification_contracts"][task] for task in value["tasks"]
    }
    validate_protocol(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--attempts", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("CROSS_FROZEN_PROTOCOL_ALREADY_EXISTS")
    results = json.loads(args.results.read_text())
    if results.get("protocol_sha256") != sha(args.protocol):
        raise ValueError("CROSS_REVALIDATION_RESULTS_PROTOCOL_MISMATCH")
    value = revalidation(json.loads(args.protocol.read_text()), results, args.attempts.split(","))
    value.update(
        original_protocol_sha256=sha(args.protocol), original_results_sha256=sha(args.results)
    )
    save(args.output, value)


if __name__ == "__main__":
    main()
