"""Frozen six-task, three-arm early-context pilot protocol.

Execution uses context_ablation's manifest, preparation, scoped usage ledger,
independent scorer and complete-result aggregation. This module validates the
new campaign independently of the original 19-task, five-arm protocol.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

CAMPAIGN = "context-early-20261107-v1"
SCHEMA = "repropatch.context-early.protocol.v1"
PROTOCOL = Path("benchmarks/context-early-20261107/protocol.json")
PARENT_PROTOCOL = "benchmarks/context-ablation/trigger-protocol.json"
SELECTION_PREFIX = "early-context-pilot-v1/"
ARMS = ("baseline", "early", "early_state")
FLAGS = (
    "diagnostic_extraction",
    "deduplicate_results",
    "state_aware_compaction",
    "early_observation_reduction",
    "observation_recall",
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def selected_tasks(parent):
    return sorted(
        parent["tasks"],
        key=lambda task: hashlib.sha256((SELECTION_PREFIX + task).encode("ascii")).hexdigest(),
    )[:6]


def expected_protocol(parent, parent_sha256):
    p = deepcopy(parent)
    tasks = selected_tasks(parent)
    for key in ("predecessor_protocol", "predecessor_protocol_sha256", "parent_contract_overrides"):
        p.pop(key, None)
    p.update(
        {
            "schema": SCHEMA,
            "campaign": CAMPAIGN,
            "batch_id": CAMPAIGN,
            "parent_protocol": PARENT_PROTOCOL,
            "parent_protocol_sha256": parent_sha256,
            "intervention_revision": "early-observation-line-extract-v1",
            "tasks": tasks,
            "task_count": 6,
            "task_contracts": {task: parent["task_contracts"][task] for task in tasks},
            "task_selection": {
                "population": "parent_protocol.tasks",
                "population_count": 19,
                "algorithm": "ascending SHA256(ASCII(prefix + instance_id)); first 6",
                "prefix": SELECTION_PREFIX,
                "selected_count": 6,
            },
            "arms": list(ARMS),
            "mechanism_flags": list(FLAGS),
            "treatments": {
                arm: {
                    flag: flag == "observation_recall"
                    or (flag == "early_observation_reduction" and arm != "baseline")
                    or (flag == "state_aware_compaction" and arm == "early_state")
                    for flag in FLAGS
                }
                for arm in ARMS
            },
            "context_policy_overrides": {
                "baseline": {},
                "early": {},
                "early_state": {"compact_trigger_tokens": 16000, "compact_target_tokens": 7200},
            },
            "early_observation_policy": {
                "token_estimator": "ceil(UTF-8 bytes / 3)",
                "minimum_observation_tokens_exclusive": 500,
                "subsequent_complete_repair_responses": 2,
                "max_auxiliary_requests_per_repair_response": 1,
                "max_auxiliary_requests_per_attempt": 4,
                "minimum_remaining_requests": 2,
                "selection": "source text line ranges",
                "auxiliary_request_purpose": "compact",
                "auxiliary_tools": [],
                "auxiliary_requests_share_attempt_cap": True,
                "original_observation_recall": True,
            },
            "auxiliary_budget_policy": {
                "all_arms": True,
                "request_cap": "min(task.budget.max_steps, context_policy.request_cap)",
                "minimum_remaining_repair_requests": 1,
                "applies_to": [
                    "early_observation_selection",
                    "history_compaction",
                    "state_aware_compaction",
                ],
                "pre_send_rejection_counts_as_request": False,
                "unknown_usage_policy": (
                    "count issued request; retain unknown usage; enforce usage-ledger settlement"
                ),
            },
            "initial_observation_policy": {
                "all_arms": "identical separate baseline_observation user message",
                "visible_content": "unchanged qualified baseline feedback",
                "task_contract": "fixed_items",
                "hidden_oracle_or_candidate_input": False,
            },
            "executor": {**parent["executor"], "tool_count": 7},
            "repeats": 2,
            "trial_count": 36,
            "formal_request_cap": 864,
            "smoke": {"task": tasks[0], "repeats": 1, "trial_count": 3, "request_cap": 72},
            "execution_order_seed": CAMPAIGN,
            "input_policy": (
                "identical qualified task, native legacy tools plus read_observation, "
                "separate content-equivalent baseline feedback; "
                "compare actual first request identities"
            ),
            "paired_analysis": (
                "task x repeat; all three pairwise differences; "
                "retain missing pairs; descriptive only"
            ),
        }
    )
    p["execution_order"] = {}
    for scope in ("smoke", "full"):
        scope_tasks = tasks if scope == "full" else tasks[:1]
        repeats = (1, 2) if scope == "full" else (1,)
        keys = [
            f"{task}/{arm}/repeat-{repeat}"
            for task in scope_tasks
            for arm in ARMS
            for repeat in repeats
        ]
        keys.sort(
            key=lambda key: hashlib.sha256(f"{CAMPAIGN}/{scope}/{key}".encode("ascii")).hexdigest()
        )
        p["execution_order"][scope] = keys
    return p


def validate_protocol(p, *, root, read_parent, archive_contracts):
    require(p.get("schema") == SCHEMA, "EARLY_PROTOCOL_SCHEMA")
    require(p.get("campaign") == CAMPAIGN, "EARLY_CAMPAIGN")
    require(p.get("parent_protocol") == PARENT_PROTOCOL, "EARLY_PARENT_PROTOCOL")
    path = Path(root) / PARENT_PROTOCOL
    parent_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    require(parent_sha256 == PARENT_SHA256, "EARLY_PARENT_SOURCE_CHANGED")
    require(p.get("parent_protocol_sha256") == PARENT_SHA256, "EARLY_PARENT_HASH")
    parent = read_parent(path)
    expected = expected_protocol(parent, parent_sha256)
    require(set(p) == set(expected), "EARLY_PROTOCOL_FIELDS")
    for key, value in expected.items():
        require(canonical(p[key]) == canonical(value), "EARLY_CONTRACT_CHANGED:" + key)
    rebuilt = archive_contracts(p)
    require(set(rebuilt) == set(p["tasks"]), "EARLY_ARCHIVE_TASK_SET")
    for task, actual in rebuilt.items():
        require(
            all(p["task_contracts"][task].get(key) == value for key, value in actual.items()),
            "EARLY_ARCHIVE_TASK_CONTRACT:" + task,
        )
    return p


# SHA-256 of the frozen parent qualification and execution contract.
PARENT_SHA256 = "ca4b66d28d0467a523c8c8a5413d5132d1b0eb9deb437122ef0391f3d3b7e9b3"
