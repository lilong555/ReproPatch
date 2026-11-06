"""Successor campaign isolation preserves the running experiment and CPA claims."""

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import context_ablation as campaign
from cpa_lease_server import LeaseManager

PROTOCOL = campaign.ROOT / "benchmarks/context-ablation/trigger-protocol.json"


def test_successor_preserves_population_budgets_and_has_disjoint_attempt_ids():
    original = campaign.read_protocol()
    successor = campaign.read_protocol(PROTOCOL)
    for field in (
        "tasks",
        "task_contracts",
        "context_policy",
        "execution_budget_override",
        "model",
        "reasoning_effort",
        "model_timeout_seconds",
        "max_parallel",
        "image_id",
        "treatments",
        "request_cap_per_attempt",
        "qualification_archive_sha256",
    ):
        assert successor[field] == original[field], field
    assert successor["predecessor_protocol_sha256"] == campaign.sha(campaign.PROTOCOL)
    assert successor["execution_order"]["full"] == original["execution_order"]["full"]
    assert successor["smoke"]["task"] == "fmtlib__fmt-2310"
    old = campaign.trials(original, "full") + campaign.trials(original, "smoke")
    new = campaign.trials(successor, "full") + campaign.trials(successor, "smoke")
    assert not ({row["attempt_id"] for row in old} & {row["attempt_id"] for row in new})
    assert len({row["attempt_id"] for row in new}) == 195
    assert Counter(row["arm"] for row in campaign.trials(successor, "full")) == dict.fromkeys(
        campaign.ARMS,
        38,
    )
    assert sum(row["request_cap"] for row in campaign.trials(successor, "smoke")) == 120


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("campaign", "unregistered-campaign", "CAMPAIGN"),
        ("predecessor_protocol", "other.json", "PREDECESSOR_PROTOCOL"),
        ("predecessor_protocol_sha256", "a" * 64, "PREDECESSOR_CHANGED"),
        ("intervention_revision", "unknown", "INTERVENTION_REVISION"),
    ],
)
def test_successor_requires_registered_identity_and_frozen_predecessor(
    tmp_path, field, value, error
):
    protocol = json.loads(PROTOCOL.read_text())
    protocol[field] = value
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol))
    with pytest.raises(ValueError, match=error):
        campaign.read_protocol(path)


def test_cpa_keeps_both_campaign_claims_and_enforces_separate_caps(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\n")
    manager = LeaseManager(config, tmp_path / "state", reload_probe=lambda expected: None)
    claims = []
    for name in ("context-ablation-20261106", campaign.TRIGGER_CAMPAIGN):
        for index in range(5):
            request = {
                "action": "claim",
                "campaign": name,
                "phase": "smoke",
                "attempt_id": f"{name}/smoke/task/arm-{index}/repeat-1",
                "run_id": "123",
                "request_cap": 24,
            }
            result = manager.rpc(request)
            assert result["allocated_phase_requests"] == (index + 1) * 24
            claims.append(request)
        with pytest.raises(ValueError, match="BUDGET_EXHAUSTED"):
            manager.rpc({**request, "attempt_id": f"{name}/smoke/extra/arm/repeat-1"})
    stored = json.loads((tmp_path / "state/claims.json").read_text())
    assert len(stored) == 10
    for request in claims:
        with pytest.raises(ValueError, match="ALREADY_CLAIMED"):
            manager.rpc({**request, "run_id": "456"})
    assert len(json.loads((tmp_path / "state/claims.json").read_text())) == 10


def test_new_campaign_waits_for_existing_owner_to_release_lease(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\n")
    manager = LeaseManager(config, tmp_path / "state", reload_probe=lambda expected: None)
    identity = {"owner": "context-ablation-20261106", "member": "old-job", "token": "a" * 64}
    manager.rpc({**identity, "action": "enter"})
    with pytest.raises(ValueError, match="BUSY"):
        manager.rpc(
            {**identity, "owner": campaign.TRIGGER_CAMPAIGN, "member": "new-job", "action": "enter"}
        )
    assert manager.state()["owner"] == identity["owner"]
    assert set(manager.state()["members"]) == {"old-job"}
    assert manager.retry() == 0


def test_decision_summary_distinguishes_missing_telemetry_from_zero_trigger():
    flag = "state_aware_compaction"
    rows = [
        {
            "mechanisms": {
                flag: {
                    "metrics": {
                        "candidates": 0,
                        "skip_reasons": {"below_threshold": 24},
                    }
                }
            }
        },
        {
            "mechanisms": {
                flag: {
                    "metrics": {
                        "candidates": 1,
                        "skip_reasons": {"below_threshold": 10, "missing_source_state": 1},
                    }
                }
            }
        },
        {"mechanisms": {flag: {"metrics": {"triggers": 0}}}},
        {},
    ]
    stats = campaign.mechanism_decisions(rows, flag)
    assert stats == {
        "candidate_count": 1,
        "candidate_observed_trials": 2,
        "skip_reasons": {"below_threshold": 34, "missing_source_state": 1},
        "skip_reason_observed_trials": 2,
    }
    assert campaign.mechanism_decisions([{}, {}], flag)["candidate_count"] is None
