"""CPU-only source checkpoint projections and compaction-stage accounting."""

import json
import socket
from copy import deepcopy

import pytest

from repropatch.context import (
    SUMMARY_KEYS,
    ContextLimit,
    ContextPolicy,
    ContextState,
    complete_rounds,
    encoded,
)
from repropatch.context_state_projection import CHANGE_FIELDS, CHECK_FIELDS, state_checkpoint
from repropatch.task import canonical_json

SOURCE = "a" * 64


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("State projection tests are CPU-only")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


def reference(identity):
    return {"path": f"agent/tool-results/{identity}.json", "sha256": "f" * 64, "size_bytes": 30_000}


def check(phase="verify", *, sequence=1, epoch=3, source=SOURCE, passed=False):
    identity = f"check-{sequence}"
    return {
        "phase": phase,
        "tool_id": identity,
        "sequence": sequence,
        "source_tree_sha256": source,
        "source_epoch": epoch,
        "passed": passed,
        "ok": True,
        "diagnostic": "expected -3",
        "failed_tests": [{"name": "negative_values", "observed_status": "failed"}],
        "evidence": reference(identity),
    }


def semantic(*, large=False):
    state = {
        "source_tree_sha256": SOURCE,
        "source_epoch": 3,
        "checks": [check()],
        "current_changes": [],
    }
    if large:
        state["checks"] += [
            {
                **check(f"run_shell:{index}", sequence=index + 2, epoch=2),
                "diagnostic": "historical log\n" * 2000,
            }
            for index in range(30)
        ]
        state["checks"][0]["diagnostic"] = "compiler output\n" * 10_000
        state["checks"][0]["failed_tests"] *= 1000
        state["current_changes"] = [
            {
                "path": f"src/{index}.cpp",
                "before_sha256": "b" * 64,
                "after_sha256": "c" * 64,
                "tool_id": f"edit-{index}",
                "evidence": reference(f"edit-{index}"),
                "edit_text": "content\n" * 2000,
            }
            for index in range(100)
        ]
    return state


def policy(**overrides):
    return ContextPolicy(
        **{
            "compact_trigger_tokens": 48_000,
            "compact_target_tokens": 21_600,
            "state_aware_compaction": True,
            **overrides,
        }
    )


def body(*, long=False):
    return {
        "input": [{"role": "user", "content": "Repair src/stats.cpp"}]
        + [
            {"type": "function_call", "call_id": "check", "name": "run_command", "arguments": "{}"},
            {
                "type": "function_call_output",
                "call_id": "check",
                "output": "x" * (150_000 if long else 100),
            },
        ]
    }


def metrics(state):
    return state.optimization_state["metrics"]["state_aware_compaction"]


def test_full_state_retains_receipt_and_does_not_mutate_input():
    state = semantic()
    original = deepcopy(state)
    projected = state_checkpoint(state, maximum=12_000)
    assert projected["fallback"] is False
    assert projected["checks"] == [{**state["checks"][0], "currency": "current"}]
    assert projected["pending_checks"] == ["reproduce", "verify"]
    assert not any(projected["omitted"].values())
    assert state == original
    projected["checks"][0]["evidence"]["path"] = "modified"
    assert state == original


@pytest.mark.parametrize("maximum", [512, 1200, 2400, 12_000])
def test_large_state_uses_bounded_fallback_with_exact_counts(maximum):
    state = semantic(large=True)
    original = deepcopy(state)
    projected = state_checkpoint(state, maximum=maximum)
    assert projected is not None
    assert projected["fallback"] is True
    assert len(canonical_json(projected)) <= maximum
    assert projected["source_tree_sha256"] == SOURCE
    assert projected["source_epoch"] == 3
    assert projected["pending_checks"] == ["reproduce", "verify"]
    assert projected["omitted"]["changes"] + len(projected["changes"]) == 100
    assert projected["omitted"]["current_checks"] + len(projected["checks"]) == 1
    assert projected["omitted_current_checks"] + len(projected["checks"]) == 1
    assert projected["omitted"]["historical_checks"] + len(projected["historical_check_refs"]) == 30
    if maximum >= 1200:
        latest = projected["checks"][0]
        assert latest["tool_id"] == "check-1"
        assert latest["passed"] is False
        assert latest["source_epoch"] == 3
        assert latest["source_tree_sha256"] == SOURCE
        assert latest["evidence"] == reference("check-1")
        assert latest["details_in_evidence"] is True
        assert "diagnostic" not in latest and "failed_tests" not in latest
    assert state == original


def test_huge_command_details_leave_current_exit_status_and_evidence():
    state = semantic()
    receipt = check("run_shell:build", sequence=2)
    receipt.update(command="cmake " * 20_000, exit_code=2, status="exited")
    state["checks"].append(receipt)
    projected = state_checkpoint(state, maximum=2400)
    retained = next(item for item in projected["checks"] if item["phase"] == "run_shell:build")
    assert retained["exit_code"] == 2 and retained["status"] == "exited"
    assert retained["passed"] is False
    assert retained["evidence"] == receipt["evidence"]
    assert "command" not in retained


def test_minimal_change_records_have_zero_omitted_details():
    state = semantic()
    state["checks"] = []
    state["current_changes"] = [
        {"path": f"src/{index}.cpp", "before_sha256": "b" * 64, "after_sha256": "c" * 64}
        for index in range(100)
    ]
    original = deepcopy(state)
    projected = state_checkpoint(state, maximum=1200)
    assert projected["fallback"] is True
    assert len(projected["changes"]) == 4
    assert projected["omitted"]["changes"] == 96
    assert projected["omitted"]["change_details"] == 0
    assert projected["changes"] == list(reversed(state["current_changes"]))[:4]
    assert len(canonical_json(projected)) <= 1200
    assert state == original


@pytest.mark.parametrize("maximum", [512, 1200, 2400, 12_000])
@pytest.mark.parametrize("with_details", [False, True])
def test_omitted_details_count_only_retained_records_with_removed_fields(maximum, with_details):
    state = semantic(large=True)
    state["checks"] = [check("reproduce", sequence=1), check("verify", sequence=2)]
    for index, item in enumerate(state["checks"]):
        item.pop("diagnostic")
        item.pop("failed_tests")
        if with_details and index == 0:
            item["diagnostic"] = "large diagnostic\n" * 2000
            item["failed_tests"] = []
    for index, item in enumerate(state["current_changes"]):
        item.pop("edit_text")
        if with_details and index % 2:
            item["edit_text"] = "large edit\n" * 2000
            item["extra_detail"] = None
    original = deepcopy(state)
    projected = state_checkpoint(state, maximum=maximum)
    assert projected["fallback"] is True
    assert len(canonical_json(projected)) <= maximum
    for key, fields, detail_key, count_key, source_key in (
        ("checks", CHECK_FIELDS, "check_details", "current_checks", "checks"),
        ("changes", CHANGE_FIELDS, "change_details", "changes", "current_changes"),
    ):
        originals = {item["tool_id"]: item for item in state[source_key]}
        expected = 0
        for retained in projected[key]:
            source = originals[retained["tool_id"]]
            removed = source.keys() - retained.keys()
            assert removed == source.keys() - fields
            expected += bool(removed)
            assert retained.get("details_in_evidence", False) == bool(removed)
        assert projected["omitted"][detail_key] == expected
        assert projected["omitted"][count_key] + len(projected[key]) == len(originals)
    assert state == original


def test_oversized_identifiers_are_omitted_whole_without_fabricating_references():
    state = semantic()
    state["checks"][0]["evidence"]["path"] = "x" * 20_000
    projected = state_checkpoint(state, maximum=1200)
    assert projected["fallback"] is True
    assert projected["checks"] == []
    assert projected["omitted"]["current_checks"] == 1
    assert projected["pending_checks"] == ["reproduce", "verify"]


@pytest.mark.parametrize("passed", [False, None, 0, 1, "passed"])
def test_only_explicit_current_success_clears_pending_work(passed):
    state = semantic()
    state["checks"] = [check(passed=passed)]
    projected = state_checkpoint(state, maximum=12_000)
    assert projected["pending_checks"] == ["reproduce", "verify"]


def test_current_and_historical_receipts_require_both_source_and_epoch():
    state = semantic()
    state["checks"] = [
        check(sequence=20, epoch=2, passed=True),
        check(sequence=30, source="b" * 64, passed=True),
        check(sequence=10, passed=False),
        check(sequence=9, passed=True),
        check("reproduce", sequence=11, passed=True),
    ]
    projected = state_checkpoint(state, maximum=12_000)
    current = {item["phase"]: item for item in projected["checks"]}
    assert current["verify"]["sequence"] == 10
    assert current["reproduce"]["passed"] is True
    assert projected["pending_checks"] == ["verify"]
    assert projected["historical_check_refs"][0]["source_tree_sha256"] == "b" * 64
    assert projected["historical_check_refs"][0]["source_epoch"] == 3
    assert projected["omitted"]["current_checks"] == 1
    assert projected["omitted"]["historical_checks"] == 1


def test_same_source_after_revert_keeps_prior_epoch_historical():
    state = semantic()
    state["source_epoch"] = 4
    state["checks"] = [check(passed=True)]
    projected = state_checkpoint(state, maximum=12_000)
    assert projected["checks"] == []
    assert projected["pending_checks"] == ["reproduce", "verify"]
    assert projected["historical_check_refs"][0]["source_epoch"] == 3
    assert projected["historical_check_refs"][0]["currency"] == "historical"


@pytest.mark.parametrize("maximum", [0, 10, 100, -1])
def test_tiny_budget_returns_none(maximum):
    assert state_checkpoint(semantic(), maximum=maximum) is None


@pytest.mark.parametrize(
    "state",
    [
        None,
        {},
        {"source_tree_sha256": SOURCE},
        {"source_tree_sha256": SOURCE, "source_epoch": True},
    ],
)
def test_missing_source_state_returns_none(state):
    assert state_checkpoint(state, maximum=12_000) is None


def test_below_threshold_records_attempt_and_real_estimate_without_trigger():
    state = ContextState(policy(), semantic_state=semantic())
    payload = body()
    estimate = state.estimator.estimate(payload)["estimated_input_tokens"]
    assert estimate < 48_000
    assert state.plan(payload) is None
    assert metrics(state)["attempts"] == 1
    assert metrics(state)["candidates"] == metrics(state)["triggers"] == 0
    assert metrics(state)["peak_estimated_input_tokens"] == estimate
    assert metrics(state)["last_estimated_input_tokens"] == estimate
    assert metrics(state)["skip_reasons"]["below_threshold"] == 1
    assert state.optimization_state["decisions"][-1]["stage"] == "plan"
    restored = ContextState.restore(state.policy, json.loads(encoded(state.to_dict())))
    assert restored.to_dict() == state.to_dict()


@pytest.mark.parametrize("estimate", [47_999, 48_000, 48_001])
def test_exact_threshold_boundary_uses_native_estimator(estimate):
    state = ContextState(policy(), semantic_state=semantic())
    payload = body(long=True)
    initial = state.estimator.estimate(payload)["estimated_input_tokens"]
    payload["input"][-1]["output"] = "x" * (150_000 + (estimate - initial) * 3)
    assert state.estimator.estimate(payload)["estimated_input_tokens"] == estimate
    plan = state.plan(payload)
    assert (plan is not None) == (estimate >= 48_000)
    assert metrics(state)["peak_estimated_input_tokens"] == estimate
    assert metrics(state)["triggers"] == 0


def test_state_compaction_keeps_recent_complete_tool_pairs():
    state = ContextState(policy(), semantic_state=semantic(large=True))
    payload = body(long=True)
    for identity in ("two", "three", "four"):
        payload["input"].extend(
            [
                {
                    "type": "function_call",
                    "call_id": identity,
                    "name": "run_command",
                    "arguments": "{}",
                },
                {"type": "function_call_output", "call_id": identity, "output": "complete"},
            ]
        )
    original = deepcopy(payload)
    plan = state.plan(payload)
    assert plan["retained"] == payload["input"][-4:]
    summary = json.dumps({key: [] for key in SUMMARY_KEYS})
    replacement = state.replace(payload, plan, summary, sequence=10, duration_seconds=0)
    complete_rounds(replacement)
    assert replacement[-4:] == payload["input"][-4:]
    assert payload == original


def test_threshold_peak_and_candidate_are_separate_from_committed_trigger():
    state = ContextState(policy(), semantic_state=semantic(large=True))
    payload = body(long=True)
    original_semantic = deepcopy(state.semantic_state)
    baseline = ContextState(policy(state_aware_compaction=False)).plan(payload)
    plan = state.plan(payload)
    for key in ("fixed", "retained", "folded_items", "pre_compact_tokens", "pre_transport_bytes"):
        assert plan[key] == baseline[key]
    assert metrics(state)["peak_estimated_input_tokens"] > 48_000
    assert metrics(state)["attempts"] == metrics(state)["threshold_reached"] == 1
    assert metrics(state)["projection_attempts"] == metrics(state)["candidates"] == 1
    assert metrics(state)["triggers"] == 0
    assert plan["state_projection"]["fallback"] is True
    assert plan["state_projection"]["checkpoint_bytes"] <= 12_000
    assert metrics(state)["fallback_candidates"] == 1
    summary = json.dumps({key: [] for key in SUMMARY_KEYS})
    replacement = state.replace(payload, plan, summary, sequence=10, duration_seconds=0)
    complete_rounds(replacement)
    assert metrics(state)["triggers"] == metrics(state)["fallback_triggers"] == 1
    assert metrics(state)["attempts"] == 1
    assert state.compactions[-1]["context_optimization"][0]["stage"] == "replace_committed"
    assert state.compactions[-1]["context_optimization"][0]["fallback"] is True
    assert metrics(state)["saved_bytes"] == 0
    assert metrics(state)["added_bytes"] == len(encoded(plan["state_checkpoint"]))
    assert state.semantic_state == original_semantic
    peak = metrics(state)["peak_estimated_input_tokens"]
    assert state.plan({**payload, "input": replacement}) is None
    assert metrics(state)["attempts"] == 2
    assert metrics(state)["peak_estimated_input_tokens"] == peak


@pytest.mark.parametrize(
    "summary", ["invalid", "{}", json.dumps({key: "x" * 40_000 for key in SUMMARY_KEYS})]
)
def test_failed_replacement_preserves_committed_state_and_candidate_metrics(summary):
    state = ContextState(policy(deduplicate_results=True), semantic_state=semantic(large=True))
    state.optimization_state["dedup_index"] = {"receipt": "keep"}
    payload = body(long=True)
    plan = state.plan(payload)
    original = deepcopy(state.to_dict())
    with pytest.raises(ContextLimit, match="COMPACTION_FAILED"):
        state.replace(payload, plan, summary, sequence=10, duration_seconds=0)
    assert state.to_dict() == original
    assert metrics(state)["candidates"] == 1 and metrics(state)["triggers"] == 0
    assert state.compactions == []


def test_unsafe_pair_is_observed_and_rejected():
    state = ContextState(policy(), semantic_state=semantic())
    payload = body(long=True)
    payload["input"].pop()
    with pytest.raises(ContextLimit, match="COMPACTION_UNSAFE"):
        state.plan(payload)
    assert metrics(state)["skip_reasons"]["unsafe_tool_history"] == 1
    assert metrics(state)["triggers"] == 0


@pytest.mark.parametrize(
    "value,reason", [(None, "missing_semantic_state"), ({}, "missing_source_state")]
)
def test_missing_state_keeps_plain_compaction_plan_with_explicit_reason(value, reason):
    state = ContextState(policy(), semantic_state=value)
    plan = state.plan(body(long=True))
    assert plan is not None and "state_checkpoint" not in plan
    assert metrics(state)["skip_reasons"][reason] == 1
    assert metrics(state)["projection_attempts"] == 1
    assert metrics(state)["candidates"] == 0


def test_checkpoint_that_cannot_fit_has_explicit_limit_reason():
    state = ContextState(
        policy(), semantic_state={**semantic(), "source_tree_sha256": "a" * 20_000}
    )
    plan = state.plan(body(long=True))
    assert "state_checkpoint" not in plan
    assert metrics(state)["skip_reasons"]["checkpoint_exceeds_limit"] == 1
    assert state.optimization_state["decisions"][-1]["maximum_bytes"] == 12_000


def test_disabled_compaction_records_reason_without_changing_threshold():
    state = ContextState(policy(compaction_enabled=False), semantic_state=semantic())
    assert state.plan(body(long=True)) is None
    assert metrics(state)["skip_reasons"]["compaction_disabled"] == 1
    assert metrics(state)["trigger_threshold_tokens"] == 48_000


def test_oversized_fixed_prefix_records_reason_before_raising():
    state = ContextState(policy(), semantic_state=semantic())
    with pytest.raises(ContextLimit, match="COMPACTION_FAILED"):
        state.plan({"input": [{"role": "user", "content": "x" * 150_000}]})
    assert metrics(state)["skip_reasons"]["fixed_prefix_exceeds_target"] == 1


def test_no_history_reason_with_anchored_estimator_measurement(monkeypatch):
    state = ContextState(policy(), semantic_state=semantic())
    payload = {"input": [{"role": "user", "content": "Repair source"}]}
    monkeypatch.setattr(
        state.estimator,
        "estimate",
        lambda item: {
            "estimated_input_tokens": 50_000 if item is payload else 100,
        },
    )
    assert state.plan(payload) is None
    assert metrics(state)["skip_reasons"]["no_compressible_history"] == 1


def test_disabled_state_strategy_preserves_unobserved_policy():
    state = ContextState(policy(state_aware_compaction=False))
    state.plan(body())
    assert state.optimization_state == {}
