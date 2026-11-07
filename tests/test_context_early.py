"""Deterministic checks for source-bound selective observation reduction."""

import json
from dataclasses import asdict

import pytest

from repropatch.artifacts import EvidenceRef
from repropatch.context import ContextPolicy, ContextState, complete_rounds, encoded
from repropatch.context_early import EarlyObservations
from repropatch.errors import InfrastructureError, PolicyError


@pytest.fixture
def store(tmp_path):
    root = tmp_path / "evidence"
    root.mkdir(mode=0o700)
    state = ContextState(ContextPolicy(early_observation_reduction=True, observation_recall=True))

    def make(state):
        return EarlyObservations(
            state,
            read_evidence=lambda ref: EvidenceRef(**ref).read(root, limit=2 * 1024 * 1024),
            save_view=lambda identity, raw: asdict(
                EvidenceRef.save(root, f"views/{identity}", raw)
            ),
        )

    return root, state, make(state), make


def add_read(store, identity="read", *, first=10, tool="read_file", content=None):
    root, _, early, _ = store
    content = content or "".join(
        f"int value_{i} = {i}; // visible source evidence\n" for i in range(80)
    )
    value = {
        "ok": True,
        "data": {
            "path": "src/code.cc",
            "start_line": first,
            "end_line": first + len(content.splitlines()) - 1,
            "text": content,
        },
    }
    raw = asdict(EvidenceRef.save(root, f"raw/{identity}.json", encoded(value)))
    early.register(
        tool_id=identity,
        provider_call_id=identity,
        tool=tool,
        arguments={"path": "src/code.cc"},
        raw_ref=raw,
        rendered=encoded(value).decode(),
        source_tree_sha256="a" * 64,
        file_sha256="b" * 64,
        model_step=1,
    )
    return early.observations.get(identity)


def body(early):
    items = [{"role": "user", "content": "Fix code.cc while preserving relevant declarations."}]
    for record in early.observations.values():
        if record["provider_call_id"] is None:
            continue
        items += [
            {
                "type": "function_call",
                "call_id": record["provider_call_id"],
                "name": record["tool"],
                "arguments": "{}",
            },
            {
                "type": "function_call_output",
                "call_id": record["provider_call_id"],
                "output": early.read_evidence(record["view_ref"]).decode(),
            },
        ]
    return {"input": items, "instructions": "repair", "tools": []}


def mature(store):
    _, _, early, _ = store
    early.complete_repair({"input": []}, 1)
    record = add_read(store)
    current = body(early)
    early.complete_repair(current, 2)
    early.complete_repair(current, 3)
    return early, record, current


def selection(record, ranges):
    return encoded(
        {
            "decision": "SELECT",
            "tool_id": record["tool_id"],
            "source_tree_sha256": record["source_tree_sha256"],
            "ranges": ranges,
        }
    ).decode()


def test_disabled_policy_keeps_original_bytes_and_state_shape():
    expected = {
        "context_window_tokens": 128000,
        "compact_trigger_tokens": 80000,
        "compact_target_tokens": 32000,
        "max_output_tokens": 8192,
        "transport_max_bytes": 2097152,
        "response_max_bytes": 2097152,
        "request_cap": 24,
        "context_policy_version": "v1.0-unified-compaction",
        "tool_growth_tokens": 16000,
        "estimation_margin_tokens": 8000,
        "retain_rounds": 2,
        "tool_output_max_bytes": 24576,
        "compaction_enabled": True,
    }
    assert encoded(ContextPolicy().to_dict()) == encoded(expected)
    assert "early_observation_state" not in ContextState(ContextPolicy()).to_dict()
    assert ContextPolicy.from_dict(expected).to_dict() == expected


def test_delay_counts_completed_repair_responses_and_multi_tool_response_once(store):
    _, _, early, _ = store
    early.complete_repair({"input": []}, 1)
    add_read(store, "a")
    add_read(store, "b")
    assert early.state["repair_responses"] == 1
    current = body(early)
    early.complete_repair(current, 2)
    early.complete_repair(current, 2)  # Re-entered boundary retains the same response identity.
    assert early.prepare(current, remaining_requests=10) is None
    early.complete_repair(current, 4)  # Step 3 may have been auxiliary; only this repair advances.
    plan = early.prepare(current, remaining_requests=10)
    assert plan["record"]["tool_id"] == "a"
    early.start_attempt(plan)
    early.finish(plan, '{"decision":"KEEP"}')
    assert early.prepare(current, remaining_requests=9) is None
    assert early.state["repair_responses"] == 3
    assert early.state["attempts_used"] == 1


def test_selection_copies_only_original_lines_and_preserves_call_pairs(store):
    early, record, current = mature(store)
    plan = early.prepare(current, remaining_requests=4)
    early.start_attempt(plan)
    early.finish(plan, selection(record, [[10, 12], [20, 21]]))
    replaced = early.project(current["input"])
    complete_rounds(replaced)
    assert [x.get("call_id") for x in replaced] == [x.get("call_id") for x in current["input"]]
    view = json.loads(replaced[-1]["output"])
    assert view["data"]["snippets"][0]["text"] == "".join(plan["lines"][:3])
    assert view["data"]["snippets"][1]["text"] == "".join(plan["lines"][10:12])
    assert view["historical_observation"]["original_result_ref"] == record["raw_ref"]
    assert early.metrics["trigger_count"] == 1 and early.metrics["saved_bytes"] > 0
    assert early.project(replaced) == replaced


@pytest.mark.parametrize(
    "ranges",
    [
        [],
        [[9, 10]],
        [[10, 90]],
        [[12, 11]],
        [[10, True]],
        [[10, 12], [12, 14]],
        [[11, 11], [10, 10]],
        [[10.0, 11]],
    ],
)
def test_invalid_ranges_keep_exact_original_and_do_not_retry(store, ranges):
    early, record, current = mature(store)
    plan = early.prepare(current, remaining_requests=4)
    early.start_attempt(plan)
    early.finish(plan, selection(record, ranges))
    assert early.project(current["input"]) == current["input"]
    early.complete_repair(current, 5)
    assert early.prepare(current, remaining_requests=4) is None
    assert early.metrics["skip_counts"]["invalid_selection"] == 1


@pytest.mark.parametrize(
    "bad",
    [
        '{"decision":"SELECT","text":"invented"}',
        '{"decision":"KEEP","decision":"KEEP"}',
        "not json",
    ],
)
def test_unconstrained_or_duplicate_json_output_is_kept(store, bad):
    early, record, current = mature(store)
    plan = early.prepare(current, remaining_requests=4)
    early.start_attempt(plan)
    early.finish(plan, bad)
    assert record["status"] == "kept" and "projection" not in record


def test_wrong_source_identity_and_no_net_gain_are_kept(store):
    early, record, current = mature(store)
    plan = early.prepare(current, remaining_requests=4)
    early.start_attempt(plan)
    early.finish(plan, selection(record, [[10, 89]]))
    assert early.metrics["skip_counts"]["no_net_reduction"] == 1
    record["status"] = "pending"
    wrong = json.loads(selection(record, [[10, 11]]))
    wrong["source_tree_sha256"] = "c" * 64
    early.finish(plan, json.dumps(wrong))
    assert early.metrics["skip_counts"]["invalid_selection"] == 1


def test_last_request_and_run_limit_preserve_input_without_auxiliary_request(store):
    early, _, current = mature(store)
    assert early.prepare(current, remaining_requests=1) is None
    early.state["attempts_used"] = 4
    assert early.prepare(current, remaining_requests=20) is None
    assert early.metrics["auxiliary_requests"] == 0
    assert early.metrics["skip_counts"] == {
        "insufficient_request_budget": 1,
        "run_attempt_limit": 1,
    }


def test_recall_requires_observed_registration_and_checks_artifact_hash(store):
    root, _, early, _ = store
    early.complete_repair({"input": []}, 1)
    record = add_read(store)
    for identity in ("unregistered", "../private", "read"):
        with pytest.raises(PolicyError, match="OBSERVATION_NOT_VISIBLE"):
            early.recall(identity)
    early.complete_repair(body(early), 2)
    page = early.recall("read", max_chars=64)
    assert len(page["text"]) == 64 and page["next_offset"] == 64
    assert page["source_tree_sha256"] == "a" * 64
    assert early.recall("read", offset=64, max_chars=64)["offset"] == 64
    (root / record["raw_ref"]["path"]).write_text("tampered")
    with pytest.raises(InfrastructureError, match="ARTIFACT_CORRUPT"):
        early.recall("read")


def test_recall_output_is_excluded_and_state_roundtrip_keeps_projection(store):
    _, context, early, make = store
    early, record, current = mature(store)
    plan = early.prepare(current, remaining_requests=4)
    early.start_attempt(plan)
    early.finish(plan, selection(record, [[10, 11]]))
    add_read(store, "recall", tool="read_observation")
    assert "recall" not in early.observations
    restored = make(ContextState.restore(context.policy, json.loads(encoded(context.to_dict()))))
    assert restored.project(current["input"]) == early.project(current["input"])
    assert restored.state["repair_responses"] == 3
    assert restored.prepare(current, remaining_requests=4) is None


def test_prepared_checkpoint_still_has_unspent_candidate(store):
    _, context, early, make = store
    early, _, current = mature(store)
    assert early.prepare(current, remaining_requests=4) is not None
    restored = make(ContextState.restore(context.policy, json.loads(encoded(context.to_dict()))))
    assert restored.state["attempts_used"] == 0
    assert restored.prepare(current, remaining_requests=4) is not None


def test_short_file_and_long_error_receipts_keep_original_content(store):
    root, _, early, _ = store
    early.complete_repair({"input": []}, 1)
    add_read(store, "short", content="int f();\n")
    error = {"ok": False, "error": {"code": "PATH_NOT_ALLOWED", "message": "detail " * 500}}
    raw = asdict(EvidenceRef.save(root, "raw/error.json", encoded(error)))
    early.register(
        tool_id="error",
        provider_call_id="error",
        tool="read_file",
        arguments={"path": "private.cc"},
        raw_ref=raw,
        rendered=encoded(error).decode(),
        source_tree_sha256="a" * 64,
        model_step=1,
    )
    current = body(early)
    early.complete_repair(current, 2)
    early.complete_repair(current, 3)
    assert early.prepare(current, remaining_requests=8) is None
    assert early.project(current["input"]) == current["input"]
    assert early.metrics["attempts"] == early.metrics["auxiliary_requests"] == 0
    assert early.metrics["skip_counts"]["nonselectable_visible_view"] == 1


def test_selection_always_receives_visible_task_contract_with_large_recent_cues(store):
    early, _, current = mature(store)
    early.context.fixed_items = current["input"][:1]
    current["input"] += [{"role": "user", "content": "recent feedback " * 1400}]
    plan = early.prepare(current, remaining_requests=3)
    assert plan["prompt"]["task_contract"] == early.context.fixed_items
    assert early.context.fixed_items[0] not in plan["prompt"]["visible_context"]


@pytest.mark.parametrize(
    "offset,maximum", [(-1, 4), (True, 4), (0, 0), (0, 4001), (0, 2.5), (999999, 4)]
)
def test_recall_rejects_invalid_page_bounds(store, offset, maximum):
    early, _, _ = mature(store)
    with pytest.raises(PolicyError, match="INVALID_ARGUMENT"):
        early.recall("read", offset=offset, max_chars=maximum)
    assert early.metrics["recall_rejections"] == 1
    assert early.metrics["recall_success"] == 0
