"""使用公开脚本模型、真实 Harness 和独立验收运行确定性演示。"""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path

from .artifacts import EvidenceRef, private_write, read_regular
from .errors import ReproPatchError
from .events import read_events
from .harness import Harness
from .models import load_sdk_script, sdk_script_bytes
from .process import host_env, run_process
from .recovery import read_checkpoint, resume_run
from .reports import inspect_run
from .task import CTEST_TEMPLATE, IMAGE_ID, ImageIdentity, Task, canonical_json, inspect_image, text
from .workspace import git, git_argv

DEFAULT_IMAGE = "repropatch-cpp:0.1"
DEFAULT_OUTPUT = Path(".repropatch/demo")
SCENARIOS = ("repair", "rejection", "recovery")
DEMO_ASSETS = (
    "cpp-bugs/CMakeLists.txt",
    "cpp-bugs/src/stats.cpp",
    "cpp-bugs/src/stats.hpp",
    "cpp-bugs/tests/stats_test.cpp",
    "models/fix-negative-maximum.json",
)
_PAUSE_STEP = 3
_TEST_NAMES = {"negative_values", "positive_values", "empty_values", "mixed_values"}


def _scenarios(scenario):
    if scenario == "all":
        return SCENARIOS
    if not isinstance(scenario, str) or scenario not in SCENARIOS:
        raise ReproPatchError(
            "DEMO_SCENARIO_INVALID: scenario 须为 all、repair、rejection、recovery"
        )
    return (scenario,)


def _output_path(output):
    try:
        path = Path(output).absolute()
    except (TypeError, ValueError) as exc:
        raise ReproPatchError("DEMO_OUTPUT_UNSAFE: output 须为有效目录路径") from exc
    text(str(path), "demo.output", controls=True)
    if ".." in path.parts or ".git" in path.parts:
        raise ReproPatchError("DEMO_OUTPUT_UNSAFE: 输出路径含父目录跳转或 Git 元数据目录")
    package = Path(__file__).absolute().parent
    protected = [package]
    examples = package.parents[1] / "examples"
    if examples.exists():
        protected.append(examples)
    if any(path.is_relative_to(source) or source.is_relative_to(path) for source in protected):
        raise ReproPatchError("DEMO_ROOT_OVERLAP: 输出目录与示例或包源码目录重叠")
    if path in {
        Path("/"),
        Path("/home"),
        Path.home(),
        Path("/tmp"),
        Path("/var"),
        Path("/var/tmp"),
    } or any(
        path.is_relative_to(Path(root))
        for root in (
            "/etc",
            "/usr",
            "/bin",
            "/sbin",
            "/boot",
            "/proc",
            "/sys",
            "/dev",
            "/run",
            "/lib",
            "/lib64",
        )
    ):
        raise ReproPatchError("DEMO_OUTPUT_UNSAFE: 请使用专用输出目录")
    for component in reversed((path, *path.parents)):
        try:
            mode = component.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ReproPatchError("DEMO_OUTPUT_SYMLINK: 输出目录及父路径须为普通目录")
        if component == path:
            raise ReproPatchError(f"DEMO_OUTPUT_EXISTS: 请使用新的输出目录：{path}")
        if not stat.S_ISDIR(mode):
            raise ReproPatchError("DEMO_OUTPUT_UNSAFE: 输出目录的父路径须为普通目录")
        if (component / "events.sqlite3").exists() or (
            (component / ".git").exists()
            and (component / "src/stats.cpp").exists()
            and (component / "tests/stats_test.cpp").exists()
        ):
            raise ReproPatchError("DEMO_ROOT_OVERLAP: 输出目录与既有 Run 或 fixture 仓库重叠")
    return path


def _assets():
    root = files("repropatch").joinpath("demo_assets")
    assets = {}
    for name in DEMO_ASSETS:
        source = root.joinpath(*name.split("/"))
        if isinstance(source, Path):
            if any(parent.is_symlink() for parent in (source, *source.parents)):
                raise ReproPatchError("DEMO_ASSET_UNSAFE: 示例资源路径须为普通文件及目录")
            content, _ = read_regular(source, limit=256_000)
        else:
            content = source.read_bytes()
        if len(content) > 256_000:
            raise ReproPatchError("DEMO_ASSET_UNSAFE: 示例资源超过大小限制")
        assets[name] = content
    return assets


def _scripts(source, selected):
    scripts = {}
    for scenario in selected:
        script = json.loads(source)
        if scenario == "rejection":
            edit = script["steps"][2]["output"][0]
            arguments = json.loads(edit["arguments"])
            arguments["new"] = "int best = -1;"
            edit["arguments"] = json.dumps(arguments)
            script["steps"] = [*script["steps"][:3], script["steps"][-1]]
            script["steps"][-1]["output"][0]["content"][0]["text"] = "候选已完成修复。"
        content = canonical_json(script) + b"\n"
        sdk_script_bytes(content)
        scripts[scenario] = content
    return scripts


def _initialize_repository(repository):
    git(repository, "init", "-b", "main")
    git(repository, "add", "CMakeLists.txt", "src", "tests")
    date = "2000-01-01T00:00:00+00:00"
    result = run_process(
        git_argv(
            repository,
            "-c",
            "user.name=ReproPatch Demo",
            "-c",
            "user.email=demo@localhost",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            "负数最大值演示 fixture",
        ),
        env={**host_env(), "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date},
        timeout=60,
    )
    if not result.ok or result.output_truncated:
        raise ReproPatchError("DEMO_GIT_FAILED: 示例仓库提交创建失败")
    return git(repository, "rev-parse", "HEAD").strip()


def _task(output, repository, commit, image_id, scenario):
    return {
        "version": 2,
        "id": f"negative-maximum-demo-{scenario}",
        "repository": {"path": str(repository), "commit": commit},
        "environment": {"image": image_id},
        "bug": {
            "description": "修复 maximum_sample 对非空全负输入返回 0 的错误，"
            "保留空输入与完整 int 值域的行为。"
        },
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
        "workspace": {"root": str(output / "workspaces" / scenario), "retain": "none"},
        "outputs": {"root": str(output / "runs" / scenario)},
    }


def prepare_demo(
    output: Path = DEFAULT_OUTPUT,
    image: str = DEFAULT_IMAGE,
    scenario: str = "all",
    *,
    sandbox_factory=None,
) -> dict:
    """在全新目录准备自有仓库、锁定 Task 和脚本；注入测试后端时 image 须为固定 ID。"""
    selected = _scenarios(scenario)
    output = _output_path(output)
    text(image, "demo.image", controls=True)
    if sandbox_factory is not None and not callable(sandbox_factory):
        raise ReproPatchError("DEMO_SANDBOX_INVALID: 注入测试后端须为可调用工厂")
    if sandbox_factory is not None:
        if IMAGE_ID.fullmatch(image) is None or image == "sha256:" + "0" * 64:
            raise ReproPatchError("DEMO_TEST_IMAGE_INVALID: 注入测试后端须提供固定的非零 SHA256 ID")
        identity = ImageIdentity(image)
    else:
        identity = inspect_image(image)
    assets = _assets()
    scripts = _scripts(assets["models/fix-negative-maximum.json"], selected)
    _output_path(output)
    try:
        output.mkdir(mode=0o700, parents=True)
    except FileExistsError as exc:
        raise ReproPatchError(f"DEMO_OUTPUT_EXISTS: 请使用新的输出目录：{output}") from exc
    repository = output / "repository"
    repository.mkdir(mode=0o700)
    for name, content in assets.items():
        if name.startswith("cpp-bugs/"):
            private_write(repository / name.removeprefix("cpp-bugs/"), content)
    commit = _initialize_repository(repository)
    prepared = {
        "schema_version": 1,
        "output_directory": str(output),
        "requested_image": image,
        "image_id": identity.image_id,
        "model_kind": "scripted",
        "model_adapter": "agents.testing.ScriptedModel",
        "paid_model_requests": 0,
        "usage": {
            "synthetic": True,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        },
        "verification_backend": "docker" if sandbox_factory is None else "injected-test",
        "sandbox_type": "repropatch.sandbox.DockerSandbox"
        if sandbox_factory is None
        else (
            f"{getattr(sandbox_factory, '__module__', '')}."
            f"{getattr(sandbox_factory, '__qualname__', type(sandbox_factory).__qualname__)}"
        ),
        "repository": str(repository),
        "base_commit": commit,
        "scenarios": list(selected),
        "assets": [
            {
                "path": name,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
            }
            for name, content in assets.items()
        ],
        "tasks": {},
        "scripts": {},
    }
    for selected_scenario in selected:
        path = output / "tasks" / f"{selected_scenario}.yaml"
        raw = _task(output, repository, commit, identity.image_id, selected_scenario)
        source = canonical_json(raw) + b"\n"
        Task.from_dict(raw, path.parent, source_bytes=source)
        private_write(path, source)
        script_path = output / "scripts" / f"{selected_scenario}.json"
        private_write(script_path, scripts[selected_scenario])
        prepared["tasks"][selected_scenario] = str(path)
        prepared["scripts"][selected_scenario] = str(script_path)
    private_write(output / "prepared.json", canonical_json(prepared) + b"\n")
    return prepared


def _count(events, kind, tool=None):
    return sum(
        event["type"] == kind and (tool is None or event["payload"].get("name") == tool)
        for event in events
    )


def _resume_demo(report, output, sandbox_factory):
    if not report.get("paused"):
        return report, {"checks": {"paused_after_edit": False}}
    directory = Path(report["artifact_directory"])
    before = read_events(directory, report["run_id"])
    inspection = inspect_run(directory)
    manifest, reference = read_checkpoint(directory, before)
    patch = EvidenceRef(**manifest["patch"]).read(directory, limit=8 * 1024 * 1024)
    paused_report = EvidenceRef.save(
        output, "recovery/paused-report.json", canonical_json(report) + b"\n"
    )
    paused_events = EvidenceRef.save(output, "recovery/paused-events.jsonl", before.jsonl())
    resumed = resume_run(directory, sandbox_factory=sandbox_factory)
    after = read_events(directory, report["run_id"])
    checks = {
        "paused_after_edit": report["state"] == "INTERRUPTED"
        and before.run["segment_open"] == 0
        and manifest["step_id"] == _PAUSE_STEP
        and b"+    int best = samples.front();" in patch,
        "paused_evidence_complete": inspection["artifacts_complete"]
        and inspection["evidence_complete"],
        "same_run": resumed["run_id"] == report["run_id"]
        and resumed["artifact_directory"] == report["artifact_directory"],
        "event_prefix_preserved": after.events[: len(before.events)] == before.events,
        "baseline_once": _count(before.events, "baseline_finished")
        == _count(after.events, "baseline_finished")
        == 1,
        "edit_once": _count(before.events, "tool_started", "edit_file")
        == _count(after.events, "tool_started", "edit_file")
        == 1,
        "counters_continued": before.run["steps_used"] == _PAUSE_STEP
        and after.run["steps_used"] == 5
        and before.run["tool_calls_admitted"] == 3
        and after.run["tool_calls_admitted"] == 4,
        "deadline_preserved": before.run["deadline_at"] == after.run["deadline_at"],
        "recovery_recorded": after.run["recovery_attempt"] == before.run["recovery_attempt"] + 1,
        "checkpoint_source_preserved": manifest["source_tree_sha256"]
        == (resumed.get("candidate") or {}).get("source_tree_sha256"),
    }
    return resumed, {
        "pause_after_step": _PAUSE_STEP,
        "paused_run_id": report["run_id"],
        "resumed_run_id": resumed["run_id"],
        "paused_state": report["state"],
        "checkpoint_id": manifest["checkpoint_id"],
        "checkpoint_manifest": reference,
        "checkpoint_patch": manifest["patch"],
        "paused_report": asdict(paused_report),
        "paused_events": asdict(paused_events),
        "steps_before": before.run["steps_used"],
        "steps_after": after.run["steps_used"],
        "tool_calls_before": before.run["tool_calls_admitted"],
        "tool_calls_after": after.run["tool_calls_admitted"],
        "checks": checks,
    }


def _run_summary(scenario, report, prepared, recovery):
    directory = Path(report["artifact_directory"])
    inspection = inspect_run(directory)
    snapshot = read_events(directory, report["run_id"])
    baseline = report.get("baseline") or {}
    independent = report.get("independent") or {}
    candidate = report.get("candidate") or {}
    tests = independent.get("tests", [])
    baseline_tests = baseline.get("tests", [])
    expected_outcome = "REJECTED" if scenario == "rejection" else "ACCEPTED"
    expected_reason = "F2P_FAILED" if scenario == "rejection" else "VERIFICATION_PASSED"
    f2p_status = "failed" if scenario == "rejection" else "passed"
    checks = {
        "terminal_outcome": inspection["state"] == "FINISHED"
        and inspection["outcome"] == report["outcome"] == expected_outcome
        and inspection["reason_code"] == report["reason_code"] == expected_reason,
        "evidence_complete": inspection["evidence_complete"] and inspection["artifacts_complete"],
        "scripted_model": snapshot.run["engine_kind"] == "fake"
        and all(
            event["payload"]["engine"]["kind"] == "fake"
            for event in snapshot.events
            if event["type"] == "model_started"
        ),
        "zero_paid_model_requests": report["agent"]["http_attempts"] == 0,
        "synthetic_unknown_usage": report["usage"].get("synthetic") is True
        and all(
            report["usage"].get(name) is None
            for name in ("input_tokens", "output_tokens", "total_tokens")
        ),
        "baseline_reproduced": report.get("reproduced") is True
        and {item["name"] for item in baseline_tests} == _TEST_NAMES
        and any(
            item["name"] == "negative_values"
            and item["observed_status"] == "failed"
            and item["ctest_exit_code"] == 8
            and item["marker_seen"] is True
            for item in baseline_tests
        ),
        "candidate_roundtrip_verified": report.get("candidate_roundtrip_verified") is True,
        "independent_verification": independent.get("evaluation_role") == "independent"
        and independent.get("cleanup", {}).get("confirmed") is True,
        "independent_test_contract": {item["name"] for item in tests} == _TEST_NAMES,
        "f2p_expected": any(
            item["name"] == "negative_values"
            and item["observed_status"] == f2p_status
            and item["ctest_exit_code"] == (8 if scenario == "rejection" else 0)
            for item in tests
        ),
        "p2p_preserved": len([item for item in tests if item["group"] == "P2P"]) == 3
        and all(item["observed_status"] == "passed" for item in tests if item["group"] == "P2P"),
        "independent_source_matches_candidate": bool(candidate)
        and candidate.get("source_tree_sha256") == independent.get("source_tree_sha256")
        and candidate.get("changed_files") == ["src/stats.cpp"],
        "cold_independent": bool(independent) and independent.get("compiler_cache") is None,
        "task_image_locked": snapshot.run["image_id"] == prepared["image_id"],
        "execution_image_consistent": bool(report.get("evaluations"))
        and len({item["image_id"] for item in report["evaluations"]}) == 1,
        "cleanup_confirmed": report.get("cleanup", {}).get("active_code_stopped") is True
        and not report["cleanup"]["errors"],
    }
    if prepared["verification_backend"] == "docker":
        checks["docker_image_locked"] = bool(report.get("evaluations")) and all(
            item["image_id"] == prepared["image_id"] for item in report["evaluations"]
        )
        checks["docker_isolation"] = report.get("isolated") is True and all(
            item["isolated"] is True for item in report.get("evaluations", [])
        )
    if recovery is not None:
        checks.update(recovery["checks"])
    result = {
        "scenario": scenario,
        "run_id": report["run_id"],
        "artifact_directory": str(directory),
        "state": inspection["state"],
        "outcome": inspection["outcome"],
        "reason_code": inspection["reason_code"],
        "expected_outcome": expected_outcome,
        "expected_reason_code": expected_reason,
        "status": "passed" if all(checks.values()) else "failed",
        "harness_status": report["status"],
        "evidence_complete": inspection["evidence_complete"],
        "artifacts_complete": inspection["artifacts_complete"],
        "checks": checks,
        "isolated": report.get("isolated"),
        "image_id": report.get("provenance", {}).get("image_id"),
        "execution_image_id": independent.get("image_id"),
        "verification_backend": prepared["verification_backend"],
        "model_kind": "scripted",
        "paid_model_requests": 0,
        "usage": report["usage"],
        "agent": report["agent"],
        "reproduced": report.get("reproduced", False),
        "verified": report.get("verified", False),
        "candidate_roundtrip_verified": report.get("candidate_roundtrip_verified", False),
        "cleanup_confirmed": report.get("cleanup", {}).get("active_code_stopped", False),
        "candidate": report.get("candidate"),
        "baseline": report.get("baseline"),
        "independent": report.get("independent"),
        "evidence_errors": inspection["evidence_errors"],
        "inspection_errors": inspection["errors"],
    }
    if recovery is not None:
        result["recovery"] = recovery
    return result


def run_demo(
    output: Path = DEFAULT_OUTPUT,
    image: str = DEFAULT_IMAGE,
    scenario: str = "all",
    *,
    sandbox_factory=None,
) -> dict:
    """运行所选场景并核验预期；默认使用 Docker，注入工厂明确标记为测试后端。"""
    prepared = prepare_demo(output, image, scenario, sandbox_factory=sandbox_factory)
    output = Path(prepared["output_directory"])
    runs = []
    for selected in prepared["scenarios"]:
        task = Task.load(Path(prepared["tasks"][selected]))
        model, source = load_sdk_script(Path(prepared["scripts"][selected]), with_source=True)
        report = Harness(
            task,
            model,
            sandbox_factory=sandbox_factory,
            script_source=source,
            pause_after_step=_PAUSE_STEP if selected == "recovery" else None,
        ).run()
        recovery = None
        if selected == "recovery":
            report, recovery = _resume_demo(report, output, sandbox_factory)
        runs.append(_run_summary(selected, report, prepared, recovery))
    repository_unchanged = git(Path(prepared["repository"]), "status", "--porcelain") == ""
    result = {
        **prepared,
        "status": "passed"
        if repository_unchanged and all(run["status"] == "passed" for run in runs)
        else "failed",
        "repository_unchanged": repository_unchanged,
        "runs": runs,
    }
    private_write(output / "summary.json", canonical_json(result) + b"\n")
    private_write(output / "summary.md", demo_markdown(result).encode("utf-8"))
    return result


def demo_markdown(result: dict) -> str:
    """渲染演示状态、执行类型与各 Run 的独立验收证据路径。"""
    status = "通过" if result["status"] == "passed" else "失败"
    backend = (
        "Docker"
        if result["verification_backend"] == "docker"
        else f"注入测试后端（{result['sandbox_type']}）"
    )
    lines = [
        "# ReproPatch 确定性演示",
        "",
        f"状态：{status}",
        f"输出目录：{result['output_directory']}",
        f"镜像：{result['image_id']}",
        "模型：scripted（agents.testing.ScriptedModel）",
        "付费模型请求：0",
        "用量：合成；输入、输出及总 token 数未知",
        f"验证后端：{backend}",
        "",
        "| 场景 | Run ID | 结局 | 原因 | 证据完整 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for run in result["runs"]:
        evidence = "是" if run["evidence_complete"] and run["artifacts_complete"] else "否"
        lines.append(
            f"| {run['scenario']} | {run['run_id']} | {run['outcome']} | "
            f"{run['reason_code']} | {evidence} |"
        )
    for run in result["runs"]:
        lines.extend(["", f"{run['scenario']} 证据目录：{run['artifact_directory']}"])
        failed = [name for name, passed in run["checks"].items() if not passed]
        if failed:
            lines.append("未通过检查：" + "、".join(failed))
    return "\n".join(lines) + "\n"
