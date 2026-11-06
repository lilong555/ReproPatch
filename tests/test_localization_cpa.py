"""Localization CPA allocation is finite and independent of frozen context campaigns."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cpa_lease_server as server
import localization_ablation as campaign


@pytest.fixture
def manager(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\n")
    return server.LeaseManager(config, tmp_path / "state", reload_probe=lambda expected: None)


def claim(row):
    return {
        "action": "claim",
        "campaign": campaign.CAMPAIGN,
        "attempt_id": row["attempt_id"],
        "phase": row["scope"],
        "request_cap": 24,
        "run_id": "123",
    }


def test_localization_allocation_is_exact_and_namespaced(manager):
    protocol = campaign.read_protocol()
    for scope, cap in (("smoke", 72), ("full", 2736)):
        for row in campaign.trials(protocol, scope):
            result = manager.rpc(claim(row))
        assert result["allocated_phase_requests"] == cap
    records = json.loads((manager.directory / "claims.json").read_text())
    assert len(records) == 117
    assert sum(r["request_cap"] for r in records.values()) == 2808
    with pytest.raises(ValueError, match="ALREADY_CLAIMED"):
        manager.rpc(claim(campaign.trials(protocol, "smoke")[0]))
    # Existing context namespaces retain their own limits and claims.
    previous = {
        "action": "claim",
        "campaign": "context-ablation-20261106",
        "run_id": "123",
        "phase": "full",
        "request_cap": 24,
        "attempt_id": "context-ablation-20261106/full/task-1/baseline/repeat-1",
    }
    assert manager.rpc(previous)["allocated_phase_requests"] == 24


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"campaign": "localization-ablation-unregistered"}, "ALLOCATION_REJECTED"),
        ({"phase": "development"}, "ALLOCATION_REJECTED"),
        ({"phase": "full"}, "CLAIM_INVALID"),
        ({"request_cap": 25}, "CLAIM_INVALID"),
        ({"request_cap": True}, "CLAIM_INVALID"),
        ({"request_cap": None}, "CLAIM_INVALID"),
        (
            {"attempt_id": "context-ablation-20261106/smoke/fmtlib__fmt-2310/native/repeat-1"},
            "CLAIM_INVALID",
        ),
        (
            {"attempt_id": campaign.CAMPAIGN + "/smoke/fmtlib__fmt-2310/combined/repeat-1"},
            "CLAIM_INVALID",
        ),
        (
            {"attempt_id": campaign.CAMPAIGN + "/smoke/fmtlib__fmt-1390/native/repeat-1"},
            "CLAIM_INVALID",
        ),
        (
            {"attempt_id": campaign.CAMPAIGN + "/smoke/fmtlib__fmt-2310/native/repeat-2"},
            "CLAIM_INVALID",
        ),
        (
            {
                "attempt_id": campaign.CAMPAIGN + "/full/fmtlib__fmt-9999/native/repeat-1",
                "phase": "full",
            },
            "CLAIM_INVALID",
        ),
    ],
)
def test_localization_allowlist_validates_campaign_mode_task_repeat(manager, change, reason):
    row = campaign.trials(campaign.read_protocol(), "smoke")[0]
    with pytest.raises(ValueError, match=reason):
        manager.rpc({**claim(row), **change})
    assert not (manager.directory / "claims.json").exists()


def test_localization_claim_is_persistent_across_run_ids(manager):
    request = claim(campaign.trials(campaign.read_protocol(), "smoke")[0])
    manager.rpc(request)
    original = (manager.directory / "claims.json").read_bytes()
    with pytest.raises(ValueError, match="ALREADY_CLAIMED"):
        manager.rpc({**request, "run_id": "456"})
    assert (manager.directory / "claims.json").read_bytes() == original
