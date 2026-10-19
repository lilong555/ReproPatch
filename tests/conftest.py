import json
import shutil
import sys
from pathlib import Path

import pytest

from repropatch.models import MockModel
from repropatch.process import CommandResult, host_env, run_process
from repropatch.task import Task
from repropatch.workspace import git

ROOT = Path(__file__).resolve().parents[1]


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
    template = Task.load(ROOT / "examples" / "tasks" / "negative-maximum.yaml")
    from dataclasses import replace

    return replace(template, repository=repository)


@pytest.fixture
def model():
    return MockModel.load(ROOT / "examples" / "models" / "fix-negative-maximum.json")


class TrustedLocalSandbox:
    """TEST ONLY: executes this repository's trusted fixture, never user task manifests.

    Not exported by the package or CLI; it supplies real CMake/CTest evidence in
    environments without Docker. Its report always says isolated=false.
    """

    isolated = False
    image_id = None

    def __init__(self, source):
        self.source = source
        self.build = source.parent / (source.name + "-build")

    def __enter__(self):
        self.build.mkdir()
        return self

    def run(self, argv):
        converted = [
            str(self.source) if a == "/src" else str(self.build) if a == "/build" else a
            for a in argv
        ]
        candidate = Path(sys.executable).parent / converted[0]
        converted[0] = (
            str(candidate) if candidate.exists() else (shutil.which(converted[0]) or converted[0])
        )
        result = run_process(converted, cwd=self.build, timeout=30, env=host_env())
        return CommandResult(
            tuple(argv),
            result.returncode,
            result.output,
            result.duration_seconds,
            result.timed_out,
            result.output_truncated,
        )

    def __exit__(self, *_):
        pass


class SimulatedSandbox:
    """Unit tests only. Reads the fixture to return predetermined command results."""

    isolated = False
    image_id = None

    def __init__(self, source):
        self.source = source

    def __enter__(self):
        return self

    def run(self, argv):
        broken = "int best = 0;" in (self.source / "src" / "stats.cpp").read_text()
        failed = broken and argv[0] == "ctest"
        return CommandResult(
            tuple(argv), 8 if failed else 0, "expected -3, got 0" if failed else "pass", 0.001
        )

    def __exit__(self, *_):
        pass


def read_report(directory):
    return json.loads((directory / "report.json").read_text())
