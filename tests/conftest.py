import json
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from repropatch.models import load_sdk_script
from repropatch.process import CommandResult
from repropatch.task import Task
from repropatch.workspace import Worktree, git

ROOT = Path(__file__).resolve().parents[1]


def created_payload(mode="verify-patch", engine="none"):
    now = datetime.now(UTC)
    return {
        "task_id": "fixture",
        "input_mode": mode,
        "engine": {"kind": engine},
        "created_at": now.isoformat(),
        "deadline_at": (now + timedelta(seconds=60)).isoformat(),
        "usage": {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "synthetic": engine == "fake",
        },
    }


@pytest.fixture
def repository(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(
        ROOT / "examples" / "cpp-bugs", repo, ignore=shutil.ignore_patterns(".git", "build")
    )
    git(repo, "init", "-b", "main")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-m", "fixture")
    return repo


@pytest.fixture
def task(repository):
    raw = yaml.safe_load((ROOT / "examples/tasks/negative-maximum.v2.yaml").read_text())
    raw["repository"] = {
        "path": str(repository),
        "commit": git(repository, "rev-parse", "HEAD").strip(),
    }
    raw["workspace"] = {"root": str(repository.parent / "workspaces")}
    raw["outputs"] = {"root": str(repository.parent / "runs")}
    return Task.from_dict(raw, repository.parent)


@pytest.fixture
def model():
    return load_sdk_script(ROOT / "examples" / "models" / "fix-negative-maximum.json")


class SimulatedSandbox:
    """受信任测试适配器：提供明确 JSON、原始日志和逐用例 JUnit。"""

    isolated = False
    image_id = None

    def __init__(self, source):
        self.source = source
        self.results = {}

    def __enter__(self):
        return self

    def result(self, argv, code=0, output=b"", *, status="exited", stderr=b""):
        import uuid
        from dataclasses import replace

        from repropatch.artifacts import EvidenceRef

        output = output.encode() if isinstance(output, str) else output
        cid = uuid.uuid4().hex
        if getattr(self, "audit_log", None) is not None:
            self.audit_log.command_started(cid, argv, "/build", None, self.audit_payload)
        out = EvidenceRef.save(self.log_root, f"logs/{cid}/stdout.bin", output)
        err = EvidenceRef.save(self.log_root, f"logs/{cid}/stderr.bin", stderr)
        # 两级日志父目录必须与生产控制目录采用相同权限。
        (self.log_root / "logs").chmod(0o700)
        value = CommandResult(
            tuple(argv),
            code,
            (output + stderr).decode("utf-8", "replace"),
            0.001,
            status == "timed_out",
            status=status,
            command_id=cid,
            stdout=output.decode("utf-8", "replace"),
            stderr=stderr.decode("utf-8", "replace"),
            stdout_bytes=len(output),
            stderr_bytes=len(stderr),
            stdout_log=out,
            stderr_log=err,
        )
        value = replace(value, cwd="/build")
        if getattr(self, "audit_log", None) is not None:
            self.audit_log.command_finished(value, self.audit_payload)
        return value

    def inventory(self):
        return {
            "kind": "ctestInfo",
            "version": {"major": 1, "minor": 0},
            "tests": [
                {
                    "name": name,
                    "command": ["/build/stats_test", name],
                    "properties": [{"name": "WORKING_DIRECTORY", "value": "/build"}],
                }
                for name in ("negative_values", "positive_values", "empty_values", "mixed_values")
            ],
        }

    def execute_test(self, name):
        broken = "int best = 0;" in (self.source / "src/stats.cpp").read_text()
        failed = broken and name == "negative_values"
        return (8, "failed", "expected -3, got 0") if failed else (0, "passed", "pass")

    def run(self, argv):
        import re
        import xml.etree.ElementTree as ET

        if argv[0] == "ctest" and "--show-only=json-v1" in argv:
            return self.result(argv, output=json.dumps(self.inventory()))
        if argv[0] == "ctest":
            selector = argv[argv.index("-R") + 1]
            names = [
                item["name"]
                for item in self.inventory()["tests"]
                if re.fullmatch(selector, item["name"])
            ]
            assert len(names) == 1
            name = names[0]
            code, status, output = self.execute_test(name)
            suite = ET.Element(
                "testsuite",
                tests="1",
                failures=str(int(status in {"failed", "crashed", "timed_out"})),
                skipped=str(int(status == "skipped")),
                disabled=str(int(status == "not_run")),
            )
            case = ET.SubElement(
                suite,
                "testcase",
                name=name,
                classname=name,
                time="0.001",
                status={
                    "passed": "run",
                    "failed": "fail",
                    "skipped": "notrun",
                    "not_run": "disabled",
                    "crashed": "fail",
                    "timed_out": "fail",
                }[status],
            )
            if status in {"failed", "crashed", "timed_out"}:
                ET.SubElement(
                    case,
                    "failure",
                    message={"failed": "Failed", "crashed": "SEGFAULT", "timed_out": "Timeout"}[
                        status
                    ],
                )
            if status == "skipped":
                ET.SubElement(case, "skipped", message="SKIP_RETURN_CODE=77")
            ET.SubElement(case, "properties")
            ET.SubElement(case, "system-out").text = output
            self.results[argv[argv.index("--output-junit") + 1]] = ET.tostring(
                suite, encoding="utf-8"
            )
            return self.result(argv, code, output)
        if argv[0] == "/bin/sh" and len(argv) > 3 and argv[3] == "repropatch-read":
            return self.result(argv, output=self.results[argv[-1]])
        return self.result(argv)

    def __exit__(self, *_):
        pass


class TrustedLocalSandbox:
    """只执行自有 fixture 的宿主测试适配器；不作为产品后端导出。"""

    isolated = False
    image_id = None

    def __init__(self, source):
        self.source = source
        # 同一 Run 的固定路径每次全新创建，真实 inventory 身份可直接比较。
        self.build = source.parent.parent / "trusted-build"

    def __enter__(self):
        self.build.mkdir()
        return self

    def run(self, argv):
        from dataclasses import replace

        from repropatch.process import run_logged_process

        converted = [
            a.replace("/src", str(self.source)).replace("/build", str(self.build)) for a in argv
        ]
        candidate = Path(sys.executable).parent / converted[0]
        converted[0] = (
            str(candidate) if candidate.exists() else (shutil.which(converted[0]) or converted[0])
        )
        result = run_logged_process(
            converted,
            root=self.log_root,
            budget=self.audit_budget,
            timeout=getattr(self, "timeout", 30),
            on_started=(
                lambda cid: self.audit_log.command_started(
                    cid, argv, "/build", None, self.audit_payload
                )
            )
            if getattr(self, "audit_log", None) is not None
            else None,
        )
        result = replace(result, argv=tuple(argv))
        if getattr(self, "audit_log", None) is not None:
            self.audit_log.command_finished(result, self.audit_payload)
        return result

    def __exit__(self, *_):
        shutil.rmtree(self.build)


def read_report(directory):
    return json.loads((directory / "report.json").read_text())


@pytest.fixture
def external_patch(task, tmp_path):
    def create(new="int best = samples.front();", *, context=3):
        with Worktree(
            task.repository,
            tmp_path / ("producer-" + str(len(list(tmp_path.glob("producer-*"))))),
            task.revision,
        ) as work:
            work.edit_text("src/stats.cpp", "int best = 0;", new)
            content = git(
                work.path,
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                f"--unified={context}",
                "--",
                "src/stats.cpp",
            ).encode()
        path = tmp_path / "candidate.patch"
        path.write_bytes(content)
        return path

    return create


def scripted(actions):
    """将测试中固定动作向量构造成公开原生 ModelStep；不提供生产兼容格式。"""
    from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call

    return ScriptedModel(
        [
            ModelStep(output=[assistant_message(action["finish"])])
            if "finish" in action
            else ModelStep(
                output=[
                    function_call(
                        action["tool"], action.get("arguments", {}), call_id=f"test-{index}"
                    )
                ]
            )
            for index, action in enumerate(actions)
        ]
    )
