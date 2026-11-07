"""Protect the denominator and independent-test evidence semantics."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_false_positives import (
    AuditError,
    check_record,
    classify_pair,
    select_final_check,
    summarize,
    xml_results,
)


def check(seq, source="current", state="passed", names=("target",)):
    return {
        "event_seq": seq,
        "source_tree_sha256": source,
        "source_identity_verified": True,
        "status": state,
        "tests": [{"name": name} for name in names],
    }


def test_cold_failure_with_untested_final_patch_is_outside_pass_denominator():
    prior = check(1, source="old")
    last = select_final_check([prior], "current")
    result = classify_pair(last, "ORACLE_TESTS_FAILED", {"target": "failed"})
    assert last is None
    assert result["eligible"] is False
    assert result["false_accept"] is False


def test_last_check_overrides_earlier_success_even_on_same_patch():
    last = select_final_check([check(1), check(8, state="build_failed")], "current")
    result = classify_pair(last, "ORACLE_BUILD_FAILED", {})
    assert result["eligible"] is False


def test_additional_regression_is_separate_from_shared_test_failure():
    extra = classify_pair(
        check(1), "ORACLE_TESTS_FAILED", {"target": "passed", "regression": "failed"}
    )
    shared = classify_pair(
        check(1), "ORACLE_TESTS_FAILED", {"target": "failed", "regression": "passed"}
    )
    assert extra["false_accept"] is True
    assert extra["disagreement"] == "additional_test_failure"
    assert extra["additional_failed_tests"] == ["regression"]
    assert shared["disagreement"] == "shared_test_name_failure"


def test_zero_tests_and_infrastructure_outcome_do_not_enter_denominator():
    assert not classify_pair(check(1, state="zero_tests", names=()), "ORACLE_TESTS_FAILED", {})[
        "eligible"
    ]
    assert not classify_pair(check(1), "ORACLE_INFRASTRUCTURE_ERROR", {})["eligible"]


def test_source_identity_is_required_even_for_same_string():
    candidate = check(1)
    candidate["source_identity_verified"] = False
    assert select_final_check([candidate], "current") is None


def test_xml_distinguishes_real_empty_failed_and_skipped_tests():
    assert xml_results(b'<testsuite tests="0"/>') == {}
    assert xml_results(
        b'<testsuite><testcase name="a"/><testcase name="b"><failure/></testcase>'
        b'<testcase name="c"><skipped/></testcase></testsuite>'
    ) == {"a": "passed", "b": "failed", "c": "skipped"}


@pytest.mark.parametrize(
    "raw",
    [
        b'<testsuite><testcase name="a"/><testcase name="a"/></testsuite>',
        b'<!DOCTYPE a [<!ENTITY x "value">]><testsuite/>',
        b"<testsuite><testcase/></testsuite>",
    ],
)
def test_ambiguous_xml_is_rejected(raw):
    with pytest.raises(AuditError):
        xml_results(raw)


def test_no_valid_pass_denominator_reports_unknown_ratio():
    row = {
        "eligible": False,
        "false_accept": False,
        "audit_status": "evidence_missing",
        "candidate_available": False,
        "candidate_identity_verified": False,
        "final_source_identity_verified": False,
        "cold_identity_verified": False,
        "exploration_check_count": 0,
        "final_patch_check_count": 0,
        "final_check_status": "not_observed",
        "cold_accepted": False,
    }
    summary = summarize([row])
    assert summary["expected"] == 1
    assert summary["false_accept_fraction"] is None
    assert summary["cold_failures"] == 1
    assert summary["false_accepts"] == 0


@pytest.mark.parametrize(
    "xml,build_code,have_tests,expected",
    [
        (b'<testsuite><testcase name="target"/></testsuite>', 0, True, "passed"),
        (b'<testsuite tests="0"/>', 0, True, "pass_evidence_incomplete"),
        (
            b'<testsuite><testcase name="target"><failure/></testcase></testsuite>',
            0,
            True,
            "pass_evidence_incomplete",
        ),
        (b'<testsuite><testcase name="target"/></testsuite>', 2, True, "build_failed"),
        (b'<testsuite tests="0"/>', 0, False, "zero_tests"),
    ],
)
def test_full_evaluation_checks_actual_xml_and_build(xml, build_code, have_tests, expected):
    command = {"status": "exited", "exit_code": 0, "command_id": "test"}
    evidence = {
        "evaluation_id": "eval",
        "configure": command,
        "build": {**command, "exit_code": build_code},
        "commands": [command],
        "tests": (
            [
                {
                    "name": "target",
                    "observed_status": "passed",
                    "ctest_exit_code": 0,
                    "result": {"path": "xml", "sha256": "fixture"},
                    "command_id": "test",
                }
            ]
            if have_tests
            else []
        ),
    }
    bodies = {
        "result": json.dumps(
            {
                "ok": True,
                "data": {
                    "evaluation_role": "agent_check",
                    "evaluation_id": "eval",
                    "evidence": {"path": "evidence", "sha256": "fixture"},
                    "passed": True,
                },
            }
        ).encode(),
        "evidence": json.dumps(evidence).encode(),
        "xml": xml,
    }

    class FixtureArchive:
        def read_ref(self, ref, root):
            return bodies[ref["path"]]

    result = check_record(
        FixtureArchive(),
        "root/",
        {"seq": 1, "payload": {"result_ref": {"path": "result", "sha256": "fixture"}}},
    )
    assert result["status"] == expected
