"""运行固定案例的真实 Docker 验收，并保存可独立核查的原始证据。"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="先构建固定验收镜像")
    parser.add_argument("--image", default="repropatch-cpp:0.1", help="验收使用的本地工具链镜像")
    parser.add_argument("--output", type=Path, help="新的证据目录，不覆盖已有目录")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output or (
        root
        / ".repropatch/docker-gates"
        / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    )
    output = output.resolve()
    try:
        output.mkdir(parents=True)
    except OSError as exc:
        parser.error(f"无法创建新的证据目录：{exc}")
    runtime = root / ".repropatch/gate-tests" / uuid.uuid4().hex
    runtime.parent.mkdir(parents=True, exist_ok=True)
    environment = dict(
        os.environ,
        REPROPATCH_DOCKER_TESTS="1",
        REPROPATCH_TEST_IMAGE=args.image,
        PYTEST_ADDOPTS="",
    )
    summary = {
        "gate": "V-DOCKER",
        "task_format_version": 2,
        "started_at": datetime.now(UTC).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "status": "error",
        "image": args.image,
        "image_id": None,
        "commands": [],
    }
    source_paths = sorted(
        path
        for directory in (
            "src",
            "tests",
            "scripts",
            "docker",
            "examples",
            ".github",
            "requirements",
        )
        for path in (root / directory).rglob("*")
        if path.is_file()
        and not {".git", "__pycache__"}.intersection(path.parts)
        and not any(part.endswith(".egg-info") for part in path.parts)
    ) + [root / "pyproject.toml", root / "uv.lock"]
    manifest = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_paths
    }
    (output / "source-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    def execute(name, argv, timeout):
        print(f"执行 {name}，日志：{output / (name + '.log')}", flush=True)
        record = {"name": name, "argv": argv, "returncode": None}
        summary["commands"].append(record)
        started = time.monotonic()
        with (output / f"{name}.log").open("wb") as stream:
            result = subprocess.run(
                argv,
                cwd=root,
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
        record["returncode"] = result.returncode
        record["duration_seconds"] = time.monotonic() - started
        if result.returncode:
            raise RuntimeError(f"{name} 失败，退出码 {result.returncode}")
        return (output / f"{name}.log").read_text(encoding="utf-8")

    exit_code = 1
    try:
        summary["source_commit"] = execute(
            "source-commit", ["git", "rev-parse", "HEAD"], 10
        ).strip()
        execute("source-status", ["git", "status", "--short"], 10)
        execute("docker-version", ["docker", "version"], 30)
        if args.build:
            execute(
                "image-build",
                ["docker", "build", "-t", summary["image"], "-f", "docker/Dockerfile", "docker"],
                900,
            )
        summary["image_id"] = execute(
            "image-id", ["docker", "image", "inspect", "--format", "{{.Id}}", summary["image"]], 30
        ).strip()
        execute(
            "doctor",
            [sys.executable, "-m", "repropatch", "doctor", "--image", summary["image"]],
            30,
        )
        execute(
            "docker-tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "-m",
                "docker",
                "-v",
                f"--basetemp={runtime}",
                f"--junitxml={output / 'docker-tests.xml'}",
            ],
            600,
        )
        cases = list(ET.parse(output / "docker-tests.xml").iter("testcase"))
        required = {
            "test_docker_cpp_end_to_end",
            "test_docker_wrong_patch_is_rejected",
            "test_sdk_pause_preserves_checkpoint_after_real_container_cleanup",
            "test_real_docker_resume_uses_checkpoint_and_independent_verification",
            "test_real_docker_controller_death_cleans_owned_live_container_before_refusal",
            "test_real_container_boundary",
            "test_real_timeout_removes_container",
            "test_docker_roundtrip_preserves_bom_crlf_and_missing_final_newline",
            "test_real_output_limit_removes_entire_container[stdout]",
            "test_real_output_limit_removes_entire_container[stderr]",
            "test_real_output_limit_removes_entire_container[both]",
            "test_real_derived_process_timeout_and_evaluation_tmpfs_lifetime",
            "test_real_interrupt_confirms_entire_container_removal",
            "test_external_patch_docker_baseline_and_independent[correct]",
            "test_external_patch_docker_baseline_and_independent[wrong]",
            "test_external_patch_docker_refuses_required_test_evasion[skip]",
            "test_external_patch_docker_refuses_required_test_evasion[missing]",
            "test_external_patch_docker_literal_test_name",
            "test_sdk_shell_and_budget_real_docker[shell]",
            "test_sdk_shell_and_budget_real_docker[timeout]",
            "test_sdk_shell_and_budget_real_docker[budget]",
            "test_shell_persistent_build_and_independent_cold_oracle",
            "test_shell_readonly_paths_network_and_rename_protection",
            "test_shell_output_limit_stops_container_and_preserves_candidate",
            "test_shell_model_error_removes_frozen_container",
            "test_shell_controller_death_cleans_persistent_container[checkpoint]",
            "test_shell_controller_death_cleans_persistent_container[tool_finished]",
            "test_shell_cli_example_uses_no_paid_model",
        }
        if not required <= {case.get("name") for case in cases} or any(
            case.find(tag) is not None for case in cases for tag in ("failure", "error", "skipped")
        ):
            raise RuntimeError("真实 Docker 验收要求指定场景全部通过，且没有跳过或错误")
        summary.update(status="passed", tests_passed=len(cases))
        exit_code = 0
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ET.ParseError) as exc:
        summary["error"] = str(exc)
    except KeyboardInterrupt:
        summary.update(status="interrupted", error="验收被中断")
        exit_code = 130
    finally:
        summary["reports"] = []
        summary["sandbox_evidence"] = []
        try:
            for report in sorted(runtime.glob("*/runs/*/report.json")):
                if (runtime / report.relative_to(runtime).parts[0]).is_symlink():
                    continue
                target = output / "runs" / report.parent.parent.parent.name / report.parent.name
                shutil.copytree(report.parent, target)
                summary["reports"].append(str((target / "report.json").relative_to(output)))
                snapshots = (
                    Path(json.loads(report.read_bytes())["workspace_directory"]) / "snapshots"
                )
                for snapshot in sorted(snapshots.glob("*")):
                    if snapshot.is_dir() and not snapshot.is_symlink():
                        shutil.copytree(snapshot, target / "retained-snapshots" / snapshot.name)
            for source in sorted(runtime.glob("*/sandbox-evidence")):
                if source.is_symlink() or source.parent.is_symlink():
                    continue
                target = output / "sandboxes" / source.parent.name
                shutil.copytree(source, target)
                summary["sandbox_evidence"].append(
                    str((target / "summary.json").relative_to(output))
                )
        except OSError as exc:
            summary.update(status="error", evidence_error=str(exc))
            exit_code = 1
        summary["finished_at"] = datetime.now(UTC).isoformat()
        (output / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(
            json.dumps({"status": summary["status"], "evidence": str(output)}, ensure_ascii=False)
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
