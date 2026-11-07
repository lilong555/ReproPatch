"""Measure one stale-build injection scenario with real Docker and cold Harness checks.

The registered scenario compiles a correct binary, changes only production C++
source to introduce an empty-input regression, runs the old binary, and submits
the frozen changed source as a patch to the production independent verifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import traceback
import xml.etree.ElementTree as ET
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from repropatch.artifacts import AuditBudget, EvidenceRef
from repropatch.harness import Harness
from repropatch.sandbox import DockerSandbox
from repropatch.task import CTEST_TEMPLATE, Task, inspect_image
from repropatch.workspace import SourceManifest, Worktree, source_manifest

LOG = logging.getLogger(__name__)
TEST_NAMES = {"negative_values", "positive_values", "empty_values", "mixed_values"}
SCHEMA = "repropatch.stale-build-injection.v1"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def execute(argv, *, cwd=None, env=None, timeout=120):
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
    require(
        result.returncode == 0, f"command failed: {argv}: {result.stderr.decode(errors='replace')}"
    )
    return result.stdout


def xml_states(raw):
    root = ET.fromstring(raw)
    states = {}
    for case in root.iter("testcase"):
        name = case.get("name")
        require(name in TEST_NAMES and name not in states, "unexpected or duplicate test")
        states[name] = (
            "failed"
            if case.find("failure") is not None or case.find("error") is not None
            else "skipped"
            if case.find("skipped") is not None
            else "passed"
        )
    require(set(states) == TEST_NAMES, "four actual tests are required")
    return states


def fixture(source, destination):
    shutil.copytree(source, destination)
    for path in (destination, *destination.rglob("*")):
        path.chmod(0o755 if path.is_dir() else 0o644)


def make_task(assets, directory, image_id):
    repository = directory / "repository"
    fixture(assets, repository)
    for args in (["init", "-b", "main"], ["add", "CMakeLists.txt", "src", "tests"]):
        execute(["git", "-C", str(repository), *args])
    execute(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=ReproPatch Evidence",
            "-c",
            "user.email=evidence@localhost",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-m",
            "C++ maximum fixture",
        ],
        env={
            **os.environ,
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
        },
    )
    commit = execute(["git", "-C", str(repository), "rev-parse", "HEAD"]).decode().strip()
    config = {
        "version": 2,
        "id": "stale-build-injection",
        "repository": {"path": str(repository), "commit": commit},
        "environment": {"image": image_id},
        "bug": {"description": "修复全负样本最大值，并保留空输入和完整 int 范围行为。"},
        "commands": {
            "configure": ["cmake", "-S", "/src", "-B", "/build", "-DCMAKE_BUILD_TYPE=Debug"],
            "build": ["cmake", "--build", "/build", "--parallel", "2"],
            "reproduce": list(CTEST_TEMPLATE),
            "verify": list(CTEST_TEMPLATE),
        },
        "tests": {
            "fail_to_pass": [
                {
                    "name": "negative_values",
                    "expected_exit_code": 8,
                    "output_contains": "expected -3, got 0",
                }
            ],
            "pass_to_pass": ["positive_values", "empty_values", "mixed_values"],
            "protected_paths": ["CMakeLists.txt", "tests/"],
        },
        "files": {"readable": ["CMakeLists.txt", "src/", "tests/"], "editable": ["src/stats.cpp"]},
        "budget": {"max_steps": 12},
        "workspace": {"root": str(directory / "workspaces"), "retain": "none"},
        "outputs": {"root": str(directory / "runs")},
    }
    path = directory / "task.json"
    save(path, config)
    return Task.load(path), commit


def verdict_checks(row):
    independent = row.get("independent") or {}
    candidate = row.get("candidate") or {}
    tests = {t["name"]: t["observed_status"] for t in independent.get("tests", [])}
    return {
        "old_binary_four_tests_pass": row.get("stale_exit_code") == 0
        and row.get("stale_tests") == dict.fromkeys(TEST_NAMES, "passed"),
        "old_binary_unchanged_after_source_edit": bool(row.get("old_binary_sha256"))
        and row.get("old_binary_sha256") == row.get("stale_binary_sha256"),
        "changed_source_builds": row.get("rebuilt_exit_code") == 0,
        "fresh_binary_differs": bool(row.get("fresh_binary_sha256"))
        and row.get("fresh_binary_sha256") != row.get("old_binary_sha256"),
        "rebuilt_empty_test_fails": row.get("rebuilt_test_exit_code") == 8
        and row.get("rebuilt_tests")
        == {n: "failed" if n == "empty_values" else "passed" for n in TEST_NAMES},
        "protected_test_inputs_unchanged": row.get("protected_unchanged") is True,
        "frozen_patch_replayed": row.get("frozen_patch_sha256")
        == candidate.get("patch", {}).get("sha256")
        and bool(row.get("frozen_patch_sha256")),
        "same_final_source": row.get("final_source_sha256")
        == candidate.get("source_tree_sha256")
        == independent.get("source_tree_sha256")
        and bool(row.get("final_source_sha256")),
        "cold_compiler_cache_disabled": independent.get("evaluation_role") == "independent"
        and independent.get("compiler_cache") is None,
        "production_rejects_regression": row.get("outcome") == "REJECTED"
        and row.get("reason_code") == "REGRESSION_FAILED"
        and tests == {n: "failed" if n == "empty_values" else "passed" for n in TEST_NAMES},
        "cold_xml_verified": row.get("cold_xml_verified") is True,
        "distinct_cold_container": bool(independent.get("cleanup", {}).get("container_id"))
        and independent.get("cleanup", {}).get("container_id")
        != row.get("exploration_container_id"),
        "exploration_cleanup_confirmed": row.get("exploration_cleanup_confirmed") is True,
        "cold_cleanup_confirmed": independent.get("cleanup_confirmed") is True,
    }


def measure_repeat(args, image_id, assets, repeat):
    directory = args.output_dir / f"repeat-{repeat}"
    directory.mkdir()
    row = {
        "schema": SCHEMA,
        "scenario": "stale_binary_after_source_edit",
        "repeat": repeat,
        "status": "registered",
        "new_model_requests": 0,
    }
    save(directory / "registration.json", row)
    try:
        task, commit = make_task(assets, directory, image_id)
        row.update(base_commit=commit, image_id=image_id)
        source = directory / "exploration-source"
        fixture(assets, source)
        original = (source / "src/stats.cpp").read_text()
        repaired = original.replace("int best = 0;", "int best = samples.front();")
        broken = repaired.replace("return std::nullopt;", "return 0;")
        require(original != repaired != broken, "fixture replacements required")
        (source / "src/stats.cpp").write_text(repaired)
        repaired_source = source_manifest(source)
        save(directory / "repaired-source-manifest.json", repaired_source.to_dict())
        (directory / "repaired-stats.cpp").write_text(repaired)
        protected_before = {
            p: sha((source / p).read_bytes()) for p in ("CMakeLists.txt", "tests/stats_test.cpp")
        }
        logs = directory / "exploration-logs"
        logs.mkdir()
        sandbox = DockerSandbox(
            source,
            image_id,
            timeout=120,
            run_id=f"stale-build-evidence-{repeat}-{sha(str(directory).encode())[:12]}",
            purpose="stale-build-injection",
            log_root=logs,
            audit_budget=AuditBudget(logs),
            record=lambda owner: save(directory / "sandbox-owner.json", owner),
        )

        def run(name, argv):
            result = sandbox.run(tuple(argv))
            save(directory / f"{name}.json", result.to_dict())
            return result

        def copy_binary(name):
            destination = directory / name
            argv = [sandbox.executable, "exec", sandbox.container_id, "cat", "/build/stats_test"]
            raw = execute(argv)
            destination.write_bytes(raw)
            value = sha(raw)
            live = run(name + "-sha256", ["sha256sum", "/build/stats_test"])
            require(live.ok and live.stdout.split()[0] == value, "binary extraction hash")
            save(
                directory / f"{name}-read.json",
                {"command": argv, "bytes": len(raw), "sha256": value},
            )
            return value

        with sandbox:
            row["exploration_container_id"] = sandbox.container_id
            require(sandbox.preflight().ok, "sandbox preflight")
            require(run("configure", task.commands.configure).ok, "correct source configure")
            require(run("correct-build", task.commands.build).ok, "correct source build")
            row["old_binary_sha256"] = copy_binary("old-stats-test")
            (source / "src/stats.cpp").write_text(broken)
            final_source = source_manifest(source)
            save(directory / "final-source-manifest.json", final_source.to_dict())
            row["final_source_sha256"] = final_source.sha256
            row["protected_unchanged"] = protected_before == {
                p: sha((source / p).read_bytes()) for p in protected_before
            }
            row["protected_sha256"] = protected_before
            stale = run(
                "stale-test",
                [
                    "ctest",
                    "--test-dir",
                    "/build",
                    "--output-on-failure",
                    "--no-tests=error",
                    "--output-junit",
                    "/build/stale.xml",
                ],
            )
            raw = run("stale-xml-read", ["cat", "/build/stale.xml"])
            require(raw.ok, "stale XML read")
            (directory / "stale.xml").write_text(raw.stdout)
            row.update(
                stale_exit_code=stale.returncode,
                stale_tests=xml_states(raw.stdout),
                stale_binary_sha256=copy_binary("stale-stats-test"),
            )
            rebuilt = run(
                "rebuilt", ["cmake", "--build", "/build", "--clean-first", "--parallel", "2"]
            )
            row.update(
                rebuilt_exit_code=rebuilt.returncode,
                fresh_binary_sha256=copy_binary("fresh-stats-test"),
            )
            fresh = run(
                "rebuilt-test",
                [
                    "ctest",
                    "--test-dir",
                    "/build",
                    "--output-on-failure",
                    "--no-tests=error",
                    "--output-junit",
                    "/build/fresh.xml",
                ],
            )
            raw = run("fresh-xml-read", ["cat", "/build/fresh.xml"])
            require(raw.ok, "fresh XML read")
            (directory / "fresh.xml").write_text(raw.stdout)
            row.update(
                rebuilt_test_exit_code=fresh.returncode, rebuilt_tests=xml_states(raw.stdout)
            )
        row["exploration_cleanup_confirmed"] = sandbox.cleanup_confirmed
        producer = directory / "producer-freeze"
        producer.mkdir()
        with Worktree(directory / "repository", directory / "producer-worktree", commit) as work:
            work.edit_text("src/stats.cpp", original, broken)
            frozen = work.freeze_candidate(
                producer, {"src/stats.cpp"}, {"CMakeLists.txt", "tests/stats_test.cpp"}
            )
            require(
                frozen.source_tree_sha256 == row["final_source_sha256"], "producer final source"
            )
            patch = frozen.patch.read(producer, limit=8 * 1024 * 1024)
        patch_path = directory / "candidate.patch"
        patch_path.write_bytes(patch)
        row["frozen_patch_sha256"] = sha(patch_path.read_bytes())
        report = Harness(task, patch_file=patch_path, producer="stale-build-injection").run()
        save(directory / "production-report.json", report)
        row.update(
            {
                k: report.get(k)
                for k in (
                    "run_id",
                    "artifact_directory",
                    "outcome",
                    "reason_code",
                    "candidate",
                    "independent",
                )
            }
        )
        artifact = Path(report["artifact_directory"])
        candidate = report.get("candidate") or {}
        if candidate:
            manifest = SourceManifest.from_dict(
                json.loads(
                    EvidenceRef(**candidate["manifest"]).read(artifact, limit=8 * 1024 * 1024)
                )
            )
            require(manifest.sha256 == row["final_source_sha256"], "replayed source manifest")
            require(
                sha(EvidenceRef(**candidate["patch"]).read(artifact, limit=8 * 1024 * 1024))
                == row["frozen_patch_sha256"],
                "frozen candidate bytes",
            )
        independent = report.get("independent") or {}
        verified = []
        for test in independent.get("tests", []):
            raw = EvidenceRef(**test["result"]).read(artifact, limit=4 * 1024 * 1024)
            root = ET.fromstring(raw)
            cases = list(root.iter("testcase"))
            require(
                len(cases) == 1 and cases[0].get("name") == test["name"], "cold test XML identity"
            )
            state = (
                "failed"
                if cases[0].find("failure") is not None or cases[0].find("error") is not None
                else "passed"
            )
            verified.append(state == test["observed_status"])
        row["cold_xml_verified"] = len(verified) == 4 and all(verified)
        row["checks"] = verdict_checks(row)
        row["status"] = "measured" if all(row["checks"].values()) else "check_failed"
    except Exception as error:
        row.update(status="error", error=repr(error), traceback=traceback.format_exc())
    save(directory / "result.json", row)
    LOG.info(
        "repeat %s: %s %s", repeat, row["status"], row.get("reason_code", row.get("error", ""))
    )
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--repeats", type=int, choices=(1, 3), default=3)
    args = parser.parse_args()
    args.output_dir = args.output_dir.absolute()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    require(not args.output_dir.exists(), "new output directory required")
    args.output_dir.mkdir(parents=True)
    identity = inspect_image(args.image)
    inventory = {
        str(path.relative_to(args.source_root)): sha(path.read_bytes())
        for path in sorted((args.source_root / "src/repropatch").rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    registration = {
        "schema": SCHEMA,
        "scenario_count": 1,
        "registered_repeats": args.repeats,
        "scope": "smoke" if args.repeats == 1 else "fixed-three-repeats",
        "registered_at": datetime.now(UTC).isoformat(),
        "source_commit": args.source_commit,
        "script_sha256": sha(Path(__file__).read_bytes()),
        "source_inventory": inventory,
        "image": asdict(identity),
        "new_model_requests": 0,
        "scenario": (
            "fixed-source regression observed through stale build then production cold verification"
        ),
    }
    save(args.output_dir / "protocol.json", registration)
    assets = args.source_root / "src/repropatch/demo_assets/cpp-bugs"
    rows = [measure_repeat(args, identity.image_id, assets, i) for i in range(1, args.repeats + 1)]
    result = {
        "schema": SCHEMA,
        "source_commit": args.source_commit,
        "scenario_count": 1,
        "registered_repeats": args.repeats,
        "measured_repeats": sum(r["status"] == "measured" for r in rows),
        "injected_false_passes": sum(
            r.get("checks", {}).get("old_binary_four_tests_pass", False) for r in rows
        ),
        "production_rejections": sum(
            r.get("checks", {}).get("production_rejects_regression", False) for r in rows
        ),
        "all_evidence_checks": sum(
            bool(r.get("checks")) and all(r["checks"].values()) for r in rows
        ),
        "new_model_requests": 0,
        "rows": rows,
    }
    save(args.output_dir / "summary.json", result)
    return int(result["all_evidence_checks"] != args.repeats)


if __name__ == "__main__":
    raise SystemExit(main())
