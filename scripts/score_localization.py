"""Generate private old-source labels or score exact delivered source offline."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from repropatch.artifacts import MAX_AUDIT_BYTES, private_write, read_regular
from repropatch.errors import ReproPatchError
from repropatch.events import _json
from repropatch.localization_scoring import generate_labels, score_run
from repropatch.task import Task
from repropatch.workspace import git


def load(path):
    return _json(read_regular(Path(path), limit=MAX_AUDIT_BYTES)[0])


def protect_output(output, inputs=(), roots=()):
    if any(
        output.resolve() == path.resolve()
        or (output.exists() and path.exists() and output.samefile(path))
        for path in inputs
    ):
        raise ValueError("OUTPUT_OVERWRITES_INPUT")
    if any(output.resolve().is_relative_to(root.resolve()) for root in roots):
        raise ValueError("OUTPUT_MUST_BE_OUTSIDE_EVIDENCE_TREE")


def score_request(request_path, output):
    """Consume the campaign handoff only on its independent scoring runner."""
    from qualify_cpp_batch import records

    request = load(request_path)
    required = {
        "attempt_id",
        "instance_id",
        "arm",
        "repeat",
        "worker_result",
        "dataset",
        "execution_task",
        "prepared_commit",
        "source_sha256",
        "protocol_sha256",
        "budgets",
    }
    if (
        request.get("schema") != "repropatch.localization-score.request.v1"
        or not required <= request.keys()
    ):
        raise ValueError("INVALID_SCORE_REQUEST")
    if (
        type(request["repeat"]) is not int
        or request["repeat"] < 1
        or not isinstance(request["arm"], str)
        or any(
            not re.fullmatch(r"[a-f0-9]{64}", str(request[k]))
            for k in ("source_sha256", "protocol_sha256")
        )
    ):
        raise ValueError("INVALID_REQUEST_IDENTITY")
    task = Task.load(Path(request["execution_task"]))
    worker = load(request["worker_result"])
    expected_task = request["instance_id"].replace("__", "-").lower()
    if (
        worker.get("schema") != "repropatch.benchmark-attempt.v1"
        or worker.get("agent") != "repropatch"
        or worker.get("attempt_id") != request["attempt_id"]
        or worker.get("task_id") != task.id
        or task.id != expected_task
        or worker.get("prepared_commit") != task.revision
        or task.revision != request["prepared_commit"]
        or worker.get("task_sha256") != hashlib.sha256(task.source_bytes).hexdigest()
        or git(task.repository, "rev-parse", "HEAD").decode().strip() != task.revision
        or git(task.repository, "diff", "HEAD", "--")
    ):
        raise ValueError("REQUEST_WORKER_TASK_IDENTITY_MISMATCH")
    matching = [
        record
        for record in records(Path(request["dataset"]))
        if record["instance_id"] == request["instance_id"]
    ]
    if len(matching) != 1:
        raise ValueError("REFERENCE_TASK_MISSING_OR_DUPLICATE")
    run_id = worker.get("native_run_id")
    if run_id is not None and (
        not isinstance(run_id, str) or not re.fullmatch(r"[a-f0-9]{32}", run_id)
    ):
        raise ValueError("INVALID_NATIVE_RUN_ID")
    run_dir = Path(request["worker_result"]).parent / "runs" / (run_id or "0" * 32)
    cold_path = Path(request["cold_score"]) if request.get("cold_score") else None
    cold = load(cold_path) if cold_path and cold_path.is_file() else None
    if cold is not None and (
        cold.get("schema") != "repropatch.benchmark-score.v1"
        or cold.get("attempt_id") != request["attempt_id"]
        or cold.get("task_id") not in {None, task.id}
    ):
        raise ValueError("REQUEST_COLD_SCORE_IDENTITY_MISMATCH")
    inputs = [request_path, Path(request["worker_result"]), Path(request["execution_task"])]
    if cold_path:
        inputs.append(cold_path)
    label_path = output.with_name(output.stem + "-labels.json")
    for target in (output, label_path):
        protect_output(target, inputs, [task.repository, run_dir])
    labels = generate_labels(
        matching[0]["fix_patch"].encode("utf-8"), task.repository, task_id=request["instance_id"]
    )
    result = score_run(
        run_dir, labels, tool_budget=request["budgets"]["localization_tools"], cold_score=cold
    )
    if result["run_id"] is not None and result["run_id"] != run_id:
        raise ValueError("REQUEST_RUN_IDENTITY_MISMATCH")
    result.update(
        status="scored",
        attempt_id=request["attempt_id"],
        instance_id=request["instance_id"],
        arm=request["arm"],
        repeat_id=request["repeat"],
        repeat=request["repeat"],
        protocol_sha256=request["protocol_sha256"],
        implementation_sha256=request["source_sha256"],
        prepared_commit=task.revision,
        worker_status=worker.get("native_status"),
        worker_stop_reason=worker.get("stop_reason"),
        worker_usage=worker.get("usage"),
        labels_file=label_path.name,
        budgets=request["budgets"],
    )
    private_write(label_path, canonical_bytes(labels))
    return result


def canonical_bytes(value):
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    labels = commands.add_parser("labels")
    labels.add_argument("--patch", required=True, type=Path)
    labels.add_argument("--source-root", required=True, type=Path)
    labels.add_argument("--task-id")
    labels.add_argument("--output", required=True, type=Path)
    score = commands.add_parser("score")
    score.add_argument("--run-dir", type=Path)
    score.add_argument("--labels", type=Path)
    score.add_argument("--request", type=Path)
    score.add_argument("--tool-budget", type=int, default=8)
    score.add_argument("--phase", choices=("localization", "repair", "all"), default="localization")
    score.add_argument("--task-id")
    score.add_argument("--arm")
    score.add_argument("--repeat-id", type=int)
    score.add_argument("--cold-score", type=Path)
    score.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        output = args.output.absolute()
        if args.command == "score" and args.request:
            if (
                args.run_dir
                or args.labels
                or args.cold_score
                or args.task_id
                or args.arm
                or args.repeat_id
            ):
                raise ValueError("REQUEST_AND_DIRECT_ARGUMENTS_ARE_EXCLUSIVE")
            result = score_request(args.request, output)
            private_write(output, canonical_bytes(result))
            print(
                json.dumps(
                    {
                        "output": str(output),
                        "status": result["status"],
                        "attempt_id": result["attempt_id"],
                        "scoring_model_requests": 0,
                    }
                )
            )
            return 0
        if args.command == "score" and (not args.run_dir or not args.labels):
            raise ValueError("DIRECT_SCORE_REQUIRES_RUN_DIR_AND_LABELS")
        protected = [args.patch] if args.command == "labels" else [args.labels]
        if args.command == "score" and args.cold_score:
            protected.append(args.cold_score)
        protected_root = args.source_root if args.command == "labels" else args.run_dir
        protect_output(output, protected, [protected_root])
        if args.command == "labels":
            result = generate_labels(
                read_regular(args.patch, limit=MAX_AUDIT_BYTES)[0],
                args.source_root,
                task_id=args.task_id or args.source_root.name,
            )
        else:
            labels = _json(read_regular(args.labels, limit=MAX_AUDIT_BYTES)[0])
            if args.task_id and args.task_id != labels["task_id"]:
                raise ValueError("TASK_ID_MISMATCH")
            cold = (
                _json(read_regular(args.cold_score, limit=MAX_AUDIT_BYTES)[0])
                if args.cold_score
                else None
            )
            if cold and (
                cold.get("schema") != "repropatch.benchmark-score.v1"
                or cold.get("task_id") not in {None, labels["task_id"]}
            ):
                raise ValueError("INVALID_COLD_SCORE_IDENTITY")
            result = score_run(
                args.run_dir,
                labels,
                tool_budget=args.tool_budget,
                phase=args.phase,
                cold_score=cold,
            )
            result.update(status="scored", arm=args.arm, repeat_id=args.repeat_id)
        private_write(
            output,
            (json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2) + "\n").encode(),
        )
        print(
            json.dumps(
                {
                    "output": str(output),
                    "schema": result["schema"],
                    "eligible": result["eligible"],
                    "scoring_model_requests": 0,
                }
            )
        )
        return 0
    except (OSError, ValueError, TypeError, KeyError, ReproPatchError) as exc:
        parser.exit(2, f"{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
