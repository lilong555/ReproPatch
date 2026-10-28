"""固定 SSH 路由、重试恢复和请求身份的离线验证。"""

import asyncio
import importlib
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
