"""云端按已合格题冻结五臂批次，保留全局清单与归档身份。"""

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
remote = importlib.import_module("freeze_cross_repo_remote")


def request():
    selected = [f"org__project-{number}" for number in range(30)]
    return {
        "model_requests": 0,
        "source_commit": "a" * 40,
        "repeat_instances": selected[:6],
        "ci_run": 123,
        "calibration_run": 456,
        "development_run": 789,
        "qualification_sources": [
            {
                "instance_id": instance,
                "run_id": 123,
                "artifact": f"cross-evidence-123-{instance}",
                "archive_sha256": "b" * 64,
            }
            for instance in selected
        ],
    }, {"instances": selected}


@pytest.mark.parametrize("defect", [None, "paid", "missing", "duplicate", "source", "hash"])
def test_freeze_requires_every_registered_source(defect):
    value, registry = request()
    if defect == "paid":
        value["model_requests"] = 1
    elif defect == "missing":
        value["qualification_sources"].pop()
    elif defect == "duplicate":
        value["qualification_sources"][-1] = value["qualification_sources"][0]
    elif defect == "source":
        value["qualification_sources"][0]["artifact"] = "different-artifact"
    elif defect == "hash":
        value["qualification_sources"][0]["archive_sha256"] = ""
    if defect:
        with pytest.raises(ValueError, match="REQUIRED"):
            remote.validate_request(value, registry)
    else:
        remote.validate_request(value, registry)


@pytest.mark.parametrize("defect", [None, "missing", "duplicate", "outside", "empty"])
def test_incremental_freeze_requires_exact_subset_evidence(defect):
    value, registry = request()
    value["instances"] = registry["instances"][:3]
    value["batch_key"] = "batch-01"
    value["qualification_sources"] = value["qualification_sources"][:3]
    if defect == "missing":
        value["qualification_sources"].pop()
    elif defect == "duplicate":
        value["instances"][1] = value["instances"][0]
    elif defect == "outside":
        value["instances"][0] = "other__repo-1"
    elif defect == "empty":
        value["instances"] = []
    if defect:
        with pytest.raises(ValueError, match="REQUIRED"):
            remote.validate_request(value, registry)
    else:
        remote.validate_request(value, registry)
