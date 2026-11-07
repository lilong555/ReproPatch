"""Early-context CPA claims match the frozen pilot and preserve existing leases."""

import hashlib
import importlib
import json
import sys
from itertools import product
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
server = importlib.import_module("cpa_lease_server")
CAMPAIGN = "context-early-20261107-v1"
TASKS = (
    "fmtlib__fmt-2070",
    "fmtlib__fmt-3819",
    "fmtlib__fmt-3750",
    "fmtlib__fmt-3713",
    "fmtlib__fmt-493",
    "fmtlib__fmt-3537",
)
ARMS = ("baseline", "early", "early_state")


@pytest.fixture
def manager(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\n")
    return server.LeaseManager(
        config, tmp_path / "state", clock=lambda: 1000, reload_probe=lambda _: None
    )


def request(phase="smoke", task=TASKS[0], arm="baseline", repeat=1):
    return {
        "action": "claim",
        "campaign": CAMPAIGN,
        "phase": phase,
        "attempt_id": f"{CAMPAIGN}/{phase}/{task}/{arm}/repeat-{repeat}",
        "request_cap": 24,
        "run_id": "123",
    }


def requests(phase):
    tasks = TASKS if phase == "full" else TASKS[:1]
    repeats = (1, 2) if phase == "full" else (1,)
    return [
        request(phase, task, arm, repeat) for task, arm, repeat in product(tasks, ARMS, repeats)
    ]


def test_frozen_protocol_agrees_with_independently_selected_allocation():
    protocol = json.loads((ROOT / "benchmarks/context-early-20261107/protocol.json").read_text())
    parent = json.loads((ROOT / protocol["parent_protocol"]).read_text())
    selected = sorted(
        parent["tasks"],
        key=lambda task: hashlib.sha256(("early-context-pilot-v1/" + task).encode()).hexdigest(),
    )[:6]
    assert len(parent["tasks"]) == 19
    assert selected == protocol["tasks"] == list(TASKS)
    assert protocol["campaign"] == CAMPAIGN
    assert protocol["arms"] == list(ARMS)
    assert protocol["request_cap_per_attempt"] == 24
    assert protocol["repeats"] == 2
    assert protocol["trial_count"] == len(requests("full")) == 36
    assert protocol["formal_request_cap"] == len(requests("full")) * 24 == 864
    assert protocol["smoke"] == {
        "task": TASKS[0],
        "repeats": 1,
        "trial_count": 3,
        "request_cap": 72,
    }
    for phase in ("smoke", "full"):
        assert {row["attempt_id"] for row in requests(phase)} == {
            f"{CAMPAIGN}/{phase}/{key}" for key in protocol["execution_order"][phase]
        }


@pytest.mark.parametrize("phases", [("smoke", "full"), ("full", "smoke")])
def test_all_legal_attempts_allocate_exact_independent_phase_caps(manager, phases):
    config = manager.config.read_bytes()
    for phase in phases:
        for index, row in enumerate(requests(phase), start=1):
            result = manager.rpc(row)
            assert result["status"] == "CLAIMED"
            assert result["allocated_phase_requests"] == index * 24
        assert result["allocated_phase_requests"] == {"smoke": 72, "full": 864}[phase]
    records = json.loads((manager.directory / "claims.json").read_text())
    assert len(records) == 39
    assert sum(row["request_cap"] for row in records.values()) == 936
    assert manager.config.read_bytes() == config
    assert manager.state() is None


def test_repeated_attempt_remains_claimed_across_new_manager_and_run_id(manager):
    row = request()
    manager.rpc(row)
    path = manager.directory / "claims.json"
    events = manager.directory / "events.jsonl"
    original, original_events = path.read_bytes(), events.read_bytes()
    restarted = server.LeaseManager(
        manager.config, manager.directory, clock=lambda: 1000, reload_probe=lambda _: None
    )
    with pytest.raises(ValueError, match="CPA_ATTEMPT_ALREADY_CLAIMED"):
        restarted.rpc({**row, "run_id": "456"})
    assert path.read_bytes() == original
    assert events.read_bytes() == original_events


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"campaign": "context-early-20261107-v2"}, "ALLOCATION_REJECTED"),
        ({"phase": "development"}, "ALLOCATION_REJECTED"),
        ({"phase": "full"}, "CLAIM_INVALID"),
        ({"request_cap": None}, "CLAIM_INVALID"),
        ({"request_cap": True}, "CLAIM_INVALID"),
        ({"request_cap": False}, "CLAIM_INVALID"),
        ({"request_cap": 24.0}, "CLAIM_INVALID"),
        ({"request_cap": "24"}, "CLAIM_INVALID"),
        ({"request_cap": 23}, "CLAIM_INVALID"),
        ({"request_cap": 25}, "CLAIM_INVALID"),
        ({"request_cap": -24}, "CLAIM_INVALID"),
        ({"run_id": 123}, "CLAIM_INVALID"),
        ({"run_id": "invalid"}, "CLAIM_INVALID"),
        ({"attempt_id": None}, "CLAIM_INVALID"),
        ({"attempt_id": "other/smoke/fmtlib__fmt-2070/baseline/repeat-1"}, "CLAIM_INVALID"),
        ({"attempt_id": CAMPAIGN + "/smoke/fmtlib__fmt-3819/early/repeat-1"}, "CLAIM_INVALID"),
        ({"attempt_id": CAMPAIGN + "/smoke/fmtlib__fmt-2070/early/repeat-2"}, "CLAIM_INVALID"),
        ({"attempt_id": CAMPAIGN + "/smoke/fmtlib__fmt-2070/combined/repeat-1"}, "CLAIM_INVALID"),
        ({"attempt_id": CAMPAIGN + "/smoke/fmtlib__fmt-2070/early/repeat-0"}, "CLAIM_INVALID"),
        ({"attempt_id": CAMPAIGN + "/smoke/fmtlib__fmt-2070/early/repeat-3"}, "CLAIM_INVALID"),
        (
            {"attempt_id": CAMPAIGN + "/smoke/fmtlib__fmt-2070/early/repeat-1/extra"},
            "CLAIM_INVALID",
        ),
        (
            {"phase": "full", "attempt_id": CAMPAIGN + "/full/fmtlib__fmt-3732/early/repeat-1"},
            "CLAIM_INVALID",
        ),
        (
            {"phase": "full", "attempt_id": CAMPAIGN + "/full/fmtlib__fmt-9999/early/repeat-1"},
            "CLAIM_INVALID",
        ),
    ],
)
def test_unregistered_scope_and_identity_preserve_prior_claims(manager, change, reason):
    manager.rpc(request("full", TASKS[1], "early_state", 2))
    path = manager.directory / "claims.json"
    original = path.read_bytes()
    with pytest.raises(ValueError, match=reason):
        manager.rpc({**request(), **change})
    assert path.read_bytes() == original


def test_new_claims_keep_active_lease_retry_and_other_campaigns(manager):
    owner = "context-ablation-trigger-20261106"
    identity = {"owner": owner, "member": "job-1", "token": "a" * 64}
    manager.rpc({**identity, "action": "enter"})
    config, lease = manager.config.read_bytes(), (manager.directory / "lease.json").read_bytes()
    for row in requests("full"):
        manager.rpc(row)
    for campaign in ("context-ablation-20261106", owner):
        result = manager.rpc(
            {
                **request(),
                "campaign": campaign,
                "attempt_id": campaign + "/smoke/fmtlib__fmt-2310/baseline/repeat-1",
            }
        )
        assert result["allocated_phase_requests"] == 24
    localization = "localization-ablation-20261106"
    assert (
        manager.rpc(
            {
                **request(),
                "campaign": localization,
                "attempt_id": localization + "/smoke/fmtlib__fmt-2310/native/repeat-1",
            }
        )["allocated_phase_requests"]
        == 24
    )
    recovery = "recovery-costs-20261107-v1"
    for task, arm, repeat in product(("3732", "3727"), ("resume", "restart"), (1, 2)):
        result = manager.rpc(
            {
                **request("full"),
                "campaign": recovery,
                "attempt_id": f"{recovery}/full/fmtlib__fmt-{task}/{arm}/repeat-{repeat}",
            }
        )
    assert result["allocated_phase_requests"] == 192
    assert manager.config.read_bytes() == config
    assert (manager.directory / "lease.json").read_bytes() == lease
    assert manager.retry() == 0
    assert manager.state()["owner"] == owner
