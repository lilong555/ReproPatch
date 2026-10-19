"""Run only the checked-in, trusted C++ fixture without Docker and retain evidence.

This development script is deliberately not an installed backend. It does not
accept a task file, repository, model, or shell command from the caller.
"""

import argparse
import json
import sys
from pathlib import Path

from repropatch.harness import Harness
from repropatch.models import MockModel
from repropatch.task import Task

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "tests"))
from conftest import TrustedLocalSandbox  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=root / ".repropatch" / "fixture-evidence")
args = parser.parse_args()
print(
    "Executing the trusted built-in fixture on host; Docker isolation is NOT verified.",
    file=sys.stderr,
)
report = Harness(
    Task.load(root / "examples/tasks/negative-maximum.yaml"),
    MockModel.load(root / "examples/models/fix-negative-maximum.json"),
    args.output,
    sandbox_factory=TrustedLocalSandbox,
).run()
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["status"] == "passed" else 1)
