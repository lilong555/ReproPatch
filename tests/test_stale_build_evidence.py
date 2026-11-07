"""Evidence checks require the same source, real tests and production rejection."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_stale_build_evidence import TEST_NAMES, verdict_checks, xml_states


def measured_row():
    observed = {n: "failed" if n == "empty_values" else "passed" for n in TEST_NAMES}
    return {
        "stale_exit_code": 0,
        "stale_tests": dict.fromkeys(TEST_NAMES, "passed"),
        "old_binary_sha256": "old",
        "stale_binary_sha256": "old",
        "fresh_binary_sha256": "fresh",
        "rebuilt_exit_code": 0,
        "rebuilt_test_exit_code": 8,
        "rebuilt_tests": observed,
        "protected_unchanged": True,
        "frozen_patch_sha256": "patch",
        "final_source_sha256": "source",
        "outcome": "REJECTED",
        "reason_code": "REGRESSION_FAILED",
        "cold_xml_verified": True,
        "exploration_container_id": "exploration",
        "exploration_cleanup_confirmed": True,
        "candidate": {"source_tree_sha256": "source", "patch": {"sha256": "patch"}},
        "independent": {
            "source_tree_sha256": "source",
            "compiler_cache": None,
            "evaluation_role": "independent",
            "cleanup_confirmed": True,
            "cleanup": {"container_id": "cold"},
            "tests": [{"name": n, "observed_status": s} for n, s in observed.items()],
        },
    }


def test_positive_evidence_links_stale_binary_to_cold_source():
    assert all(verdict_checks(measured_row()).values())


@pytest.mark.parametrize(
    "mutation",
    [
        {"stale_tests": {}},
        {"stale_exit_code": 8},
        {"rebuilt_exit_code": 2},
        {"fresh_binary_sha256": "old"},
        {"final_source_sha256": "changed"},
        {"protected_unchanged": False},
        {"outcome": "ERROR"},
        {"cold_xml_verified": False},
        {"frozen_patch_sha256": "another"},
        {"reason_code": "FORBIDDEN_PATCH"},
    ],
)
def test_incomplete_or_different_evidence_is_preserved_as_failed(mutation):
    row = measured_row()
    row.update(mutation)
    assert not all(verdict_checks(row).values())


def test_reused_cold_container_is_detected():
    row = copy.deepcopy(measured_row())
    row["independent"]["cleanup"]["container_id"] = "exploration"
    assert not verdict_checks(row)["distinct_cold_container"]


def test_actual_tests_are_required_for_stale_pass():
    with pytest.raises(ValueError, match="four actual tests"):
        xml_states('<testsuite tests="0"/>')
    raw = "<testsuite>" + "".join(f'<testcase name="{n}"/>' for n in TEST_NAMES) + "</testsuite>"
    assert xml_states(raw) == dict.fromkeys(TEST_NAMES, "passed")
