"""复用冻结候选执行冷 Oracle，保留原始评分与模型账本。"""

import argparse
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from cross_repo_inputs import extract_verified
from check_native_cpp_candidate import restore_repository
from qualify_cpp_batch import save, sha
from score_benchmark_attempt import score

ROOT = Path(__file__).resolve().parents[1]


def rescore(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    proof = args.archive.with_suffix(args.archive.suffix + ".sha256")
    original = output / "original"
    extract_verified(args.archive, original, proof.read_text().split()[0])
    if sha(original / "protocol.json") != sha(args.protocol):
        raise ValueError("CROSS_RESCORE_PROTOCOL_IDENTITY_MISMATCH")
    protocol = json.loads(args.protocol.read_text())
    summary = json.loads((original / "summary.json").read_text())
    rows = summary["attempts"]
    if len(rows) != 1 or rows[0]["instance_id"] != args.instance or rows[0]["arm"] != args.arm:
        raise ValueError("CROSS_RESCORE_ATTEMPT_IDENTITY_MISMATCH")
    row = rows[0]
    registered = next(a for a in protocol["attempts"] if a["attempt_id"] == row["attempt_id"])
    if any(row[key] != registered[key] for key in ("instance_id", "arm", "request_cap")):
        raise ValueError("CROSS_RESCORE_ATTEMPT_IDENTITY_MISMATCH")
    archive = next(a for a in protocol["qualification_archives"] if args.instance in a["instances"])
    subprocess.run(
        [
            "gh",
            "run",
            "download",
            str(archive["run_id"]),
            "--repo",
            "lilong555/ReproPatch",
            "--name",
            f"cross-inputs-{archive['run_id']}",
            "--dir",
            str(ROOT / ".repropatch"),
        ],
        check=True,
    )
    qualification = original / "execution-contract/result.json"
    if not qualification.exists():
        destination = output / "qualification-archive"
        subprocess.run(
            [
                "gh",
                "run",
                "download",
                str(archive["run_id"]),
                "--repo",
                "lilong555/ReproPatch",
                "--name",
                archive["artifact"],
                "--dir",
                str(destination),
            ],
            check=True,
        )
        extract_verified(
            destination / "cross-evidence.tar.gz", output / "qualification", archive["sha256"]
        )
        qualification = output / "qualification" / args.instance / "result.json"
    source = qualification.parent / "repository"
    if not source.exists():
        restore_repository(qualification.parent, json.loads(qualification.read_text()), source)
    subprocess.run(["docker", "pull", protocol["image"]], check=True)
    identity = subprocess.check_output(
        [
            "docker",
            "image",
            "inspect",
            "--format",
            "{{.Id}}",
            protocol["image"],
        ],
        text=True,
    ).strip()
    if identity != protocol["image_id"]:
        raise ValueError("CROSS_RESCORE_IMAGE_IDENTITY_MISMATCH")
    verdict = score(
        SimpleNamespace(
            worker_result=original / args.arm / "result.json",
            qualification=qualification,
            candidate=original / args.arm / "candidate.patch",
            attempt_id=row["attempt_id"],
            dataset=ROOT / ".repropatch/cross-inputs",
            repository=output / "repository",
            output=output / "score",
            timeout=3600,
            build_jobs=2,
            check_only=False,
        )
    )
    row.update(
        original_score=row["score"],
        score=verdict,
        source_run_id=args.source_run,
        source_artifact_sha256=sha(args.archive),
        oracle_result="PASS"
        if verdict.get("accepted") is True
        else "FAIL"
        if verdict.get("accepted") is False
        else verdict["status"],
        rescore_model_requests=0,
    )
    row.setdefault("metrics", {})["cold_oracle_seconds"] = verdict["wall_seconds"]
    save(args.summary / "summary.json", {"instance_id": args.instance, "attempts": [row]})
    save(
        output / "provenance.json",
        {
            "source_run_id": args.source_run,
            "source_archive_sha256": sha(args.archive),
            "source_protocol_sha256": sha(args.protocol),
            "attempt_id": row["attempt_id"],
            "model_requests": 0,
        },
    )
    print(
        json.dumps(
            {
                "attempt_id": row["attempt_id"],
                "score": verdict["status"],
                "accepted": verdict.get("accepted"),
                "model_requests": 0,
            }
        ),
        flush=True,
    )
    return verdict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--source-run", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    verdict = rescore(parser.parse_args())
    raise SystemExit(0 if type(verdict.get("accepted")) is bool else 1)


if __name__ == "__main__":
    main()
