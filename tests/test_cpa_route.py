"""固定 SSH 路由、重试恢复和请求身份的离线验证。"""

import asyncio
import importlib
import json
import sys
from pathlib import Path

import pytest

from repropatch.cpa import cpa_route

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
server = importlib.import_module("cpa_lease_server")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8317/v1/responses",
        "http://localhost:18317/v1/responses",
        "http://127.0.0.2:18317/v1/responses",
        "http://127.0.0.1:18317/v1/responses?key=x",
        "http://user@127.0.0.1:18317/v1/responses",
        "http://127.0.0.1:18317/v1/models",
    ],
)
def test_ssh_route_keeps_exact_host_port_and_path(url):
    assert not cpa_route("azure-ssh").accepts(url)


def test_public_and_tunnel_have_separate_environment_proxy_policy():
    assert cpa_route("azure-ssh").accepts("http://127.0.0.1:18317/v1/responses")
    assert cpa_route("azure-ssh").trust_env is False
    assert cpa_route().trust_env is True
    assert not cpa_route().accepts("http://127.0.0.1:18317/v1/responses")


def test_retry_lease_restores_configuration_after_lost_heartbeat(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\napi-keys:\n  - test-private-value\n")
    inode = config.stat().st_ino
    now = [1.0]
    manager = server.LeaseManager(
        config, tmp_path / "state", clock=lambda: now[0], reload_probe=lambda expected: None
    )
    identity = {"owner": "cross-repo-20261028", "member": "job-1", "token": "a" * 64}
    assert manager.rpc({**identity, "action": "enter"})["request_retry"] == 0
    assert config.stat().st_ino == inode
    now[0] += 1199
    assert manager.rpc({"action": "status"})["request_retry"] == 0
    now[0] += 1
    assert manager.rpc({"action": "status"})["request_retry"] == 2
    assert "test-private-value" in config.read_text()
    assert "test-private-value" not in (tmp_path / "state/events.jsonl").read_text()


def test_active_jobs_preserve_lease_and_reject_conflicting_owner(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\n")
    manager = server.LeaseManager(config, tmp_path / "state", reload_probe=lambda expected: None)
    identity = {"owner": "batch", "member": "job-1", "token": "a" * 64}
    manager.rpc({**identity, "action": "enter"})
    manager.rpc({**identity, "member": "job-2", "action": "enter"})
    with pytest.raises(ValueError, match="BUSY"):
        manager.rpc({**identity, "owner": "other", "action": "enter"})
    with pytest.raises(ValueError, match="ACTIVE_MEMBERS"):
        manager.rpc({**identity, "action": "release"})
    manager.rpc({**identity, "member": "job-2", "action": "leave"})
    assert manager.rpc({**identity, "action": "release"})["request_retry"] == 2


def test_remote_attempt_claim_preserves_global_allocation(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\n")
    manager = server.LeaseManager(config, tmp_path / "state", reload_probe=lambda expected: None)
    request = {
        "action": "claim",
        "campaign": "cross-repository-20261028",
        "phase": "development",
        "attempt_id": "dev/task/full/first",
        "run_id": "123",
        "request_cap": 24,
    }
    assert manager.rpc(request)["allocated_phase_requests"] == 24
    with pytest.raises(ValueError, match="ALREADY_CLAIMED"):
        manager.rpc({**request, "run_id": "124"})
    for number in range(1, 20):
        manager.rpc({**request, "attempt_id": f"dev/task/{number}"})
    with pytest.raises(ValueError, match="BUDGET_EXHAUSTED"):
        manager.rpc({**request, "attempt_id": "dev/task/extra"})
    assert manager.retry() == 2


def test_open_campaign_keeps_unique_claims_and_separate_historical_allocation(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\n")
    manager = server.LeaseManager(config, tmp_path / "state", reload_probe=lambda expected: None)
    campaign = server.UNBOUNDED_CAMPAIGN
    request = {
        "action": "claim",
        "campaign": campaign,
        "phase": "development",
        "attempt_id": campaign + "/task/full/first",
        "run_id": "123",
        "request_cap": None,
    }
    for number in range(25):
        result = manager.rpc({**request, "attempt_id": f"{campaign}/task-{number}/full/first"})
        assert result["allocated_phase_requests"] is None
        assert result["allocated_campaign_attempts"] == number + 1
    with pytest.raises(ValueError, match="ALREADY_CLAIMED"):
        manager.rpc({**request, "attempt_id": f"{campaign}/task-0/full/first"})
    with pytest.raises(ValueError, match="CLAIM_INVALID"):
        manager.rpc({**request, "request_cap": 24})
    historical = manager.rpc(
        {
            **request,
            "campaign": "cross-repository-20261028",
            "attempt_id": "dev/task/full/first",
            "request_cap": 24,
        }
    )
    assert historical["allocated_phase_requests"] == 24
    assert manager.retry() == 2


def context_claim(phase="smoke", number=0, run="123"):
    campaign = "context-ablation-20261106"
    return {
        "action": "claim",
        "campaign": campaign,
        "phase": phase,
        "attempt_id": f"{campaign}/{phase}/task-{number}/baseline/repeat-1",
        "run_id": run,
        "request_cap": 24,
    }


def test_context_claim_persists_across_runs_and_lease_release(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\n")
    directory = tmp_path / "state"
    manager = server.LeaseManager(config, directory, reload_probe=lambda _: None)
    identity = {"owner": "context-ablation-20261106", "member": "job-1", "token": "a" * 64}
    manager.rpc({**identity, "action": "enter"})
    request = context_claim()
    assert manager.rpc(request)["allocated_phase_requests"] == 24
    manager.rpc({**identity, "action": "release"})
    saved = (directory / "claims.json").read_bytes()
    restarted = server.LeaseManager(config, directory, reload_probe=lambda _: None)
    with pytest.raises(ValueError, match="ALREADY_CLAIMED"):
        restarted.rpc({**request, "run_id": "124"})
    assert (directory / "claims.json").read_bytes() == saved
    assert json.loads(saved)[request["attempt_id"]]["run_id"] == "123"
    assert restarted.retry() == 2


@pytest.mark.parametrize("phases", [("smoke", "full"), ("full", "smoke")])
def test_context_claim_phase_limits_are_independent(tmp_path, phases):
    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\n")
    manager = server.LeaseManager(config, tmp_path / "state", reload_probe=lambda _: None)
    limits = {"smoke": 120, "full": 4560}
    for phase in phases:
        for number in range(limits[phase] // 24):
            result = manager.rpc(context_claim(phase, number))
            assert result["allocated_phase_requests"] == (number + 1) * 24
        with pytest.raises(ValueError, match="BUDGET_EXHAUSTED"):
            manager.rpc(context_claim(phase, 999))
    claims = json.loads((tmp_path / "state/claims.json").read_text())
    assert len(claims) == 195
    for phase, cap in limits.items():
        assert sum(row["request_cap"] for row in claims.values() if row["phase"] == phase) == cap
    historical = manager.rpc(
        {
            **context_claim(),
            "campaign": "cross-repository-20261028",
            "phase": "development",
            "attempt_id": "dev/task/full/first",
        }
    )
    assert historical["allocated_phase_requests"] == 24
    native = manager.rpc(
        {
            **context_claim(),
            "campaign": server.UNBOUNDED_CAMPAIGN,
            "phase": "development",
            "attempt_id": server.UNBOUNDED_CAMPAIGN + "/task/full/first",
            "request_cap": None,
        }
    )
    assert native["allocated_phase_requests"] is None


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"phase": "development"}, "ALLOCATION_REJECTED"),
        ({"attempt_id": "context-ablation-20261106/full/task/baseline/repeat-1"}, "CLAIM_INVALID"),
        ({"attempt_id": "context-ablation-20261106/smoke-extra/task"}, "CLAIM_INVALID"),
        ({"attempt_id": "other/smoke/task"}, "CLAIM_INVALID"),
        ({"request_cap": None}, "CLAIM_INVALID"),
        ({"request_cap": 1}, "CLAIM_INVALID"),
        ({"request_cap": 25}, "CLAIM_INVALID"),
        ({"request_cap": True}, "CLAIM_INVALID"),
    ],
)
def test_context_claim_validates_phase_prefix_and_fixed_attempt_cap(tmp_path, changes, reason):
    config = tmp_path / "config.yaml"
    config.write_text("request-retry: 2\n")
    manager = server.LeaseManager(config, tmp_path / "state", reload_probe=lambda _: None)
    with pytest.raises(ValueError, match=reason):
        manager.rpc({**context_claim(), **changes})
    assert not (tmp_path / "state/claims.json").exists()


@pytest.mark.sdk
def test_network_calibration_uses_twelve_claims_and_records_supplier_usage(tmp_path, monkeypatch):
    calibration = importlib.import_module("calibrate_cross_network")
    from types import SimpleNamespace

    from repropatch.context import encoded

    claims = []

    class Session:
        def __init__(self, *_):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def claim(self, attempt, phase, cap):
            claims.append((attempt, phase, cap))

    async def stream(client, url, payload, headers, trace, identity, ledger, **timeouts):
        import json

        body = json.loads(payload)
        assert body["reasoning"]["effort"] == "max"
        assert timeouts["total_timeout"] == 180
        completed = {"usage": {"input_tokens": 20, "output_tokens": 4}}
        ledger.settle(identity, encoded(completed), 200)
        return 200, b"", "text/event-stream", completed

    monkeypatch.setattr(calibration, "CPASession", Session)
    monkeypatch.setattr(calibration, "read_model_stream_async", stream)
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture")
    args = SimpleNamespace(
        campaign=Path(__file__).resolve().parents[1] / "benchmarks/cross-repo/campaign.json",
        output=tmp_path / "calibration",
    )
    assert asyncio.run(calibration.calibrate(args))
    import json

    result = json.loads((args.output / "calibration.json").read_text())
    assert len(claims) == 12 and len({c[0] for c in claims}) == 12
    assert all(c[1:] == ("calibration", 1) for c in claims)
    assert result["usage"]["issued_requests"] == 12
    assert result["usage"]["input_tokens"] == 240
    assert result["usage"]["output_tokens"] == 48
    assert result["status"] == "PASSED"
