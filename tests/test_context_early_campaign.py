"""Offline population, intervention, metering and complete-result contracts."""

import hashlib
import json
import sys
import tarfile
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import context_ablation as campaign
import context_early_campaign as early
from benchmark_budget import BudgetHooks, BudgetLimit, LocalUsageLedger

from repropatch.context import REQUEST_PURPOSE

PROTOCOL = campaign.ROOT / early.PROTOCOL


def protocol():
    return campaign.read_protocol(PROTOCOL)


def make_plan(tmp_path, monkeypatch, scope="full"):
    monkeypatch.setenv("GITHUB_RUN_ID", "early-offline-plan")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    output = tmp_path / f"plan-{scope}.json"
    campaign.plan(
        SimpleNamespace(protocol=PROTOCOL, scope=scope, output=output, github_output=None)
    )
    return output, campaign.load(output)


def test_fixed_hash_selection_and_complete_36_trial_registration():
    p = protocol()
    parent = campaign.read_protocol(campaign.ROOT / early.PARENT_PROTOCOL)
    expected = sorted(
        parent["tasks"],
        key=lambda task: hashlib.sha256(
            ("early-context-pilot-v1/" + task).encode("ascii")
        ).hexdigest(),
    )[:6]
    assert (
        p["tasks"]
        == expected
        == [
            "fmtlib__fmt-2070",
            "fmtlib__fmt-3819",
            "fmtlib__fmt-3750",
            "fmtlib__fmt-3713",
            "fmtlib__fmt-493",
            "fmtlib__fmt-3537",
        ]
    )
    rows = campaign.trials(p, "full")
    smoke = campaign.trials(p, "smoke")
    assert len(rows) == len({r["attempt_id"] for r in rows}) == 36
    assert Counter(r["arm"] for r in rows) == dict.fromkeys(early.ARMS, 12)
    assert set(Counter((r["instance_id"], r["repeat"]) for r in rows).values()) == {3}
    assert sum(r["request_cap"] for r in rows) == p["formal_request_cap"] == 864
    assert len(smoke) == 3 and sum(r["request_cap"] for r in smoke) == 72
    assert {r["instance_id"] for r in smoke} == {expected[0]}
    assert {r["repeat"] for r in smoke} == {1}
    old = campaign.trials(parent, "full")
    assert not ({r["attempt_id"] for r in rows + smoke} & {r["attempt_id"] for r in old})
    assert not ({r["attempt_id"] for r in rows} & {r["attempt_id"] for r in smoke})
    assert len(old) == 190 and parent["arms"] == list(campaign.ARMS)
    assert sum(r["request_cap"] for r in old) == 4560
    assert campaign.ARMS == ("baseline", "diagnostics", "dedup", "state", "combined")


@pytest.mark.parametrize(
    "arm,early_enabled,state,threshold,target",
    [
        ("baseline", False, False, 48000, 21600),
        ("early", True, False, 48000, 21600),
        ("early_state", True, True, 16000, 7200),
    ],
)
def test_policy_and_persisted_ledger_have_exact_treatment(
    tmp_path,
    arm,
    early_enabled,
    state,
    threshold,
    target,
):
    p = protocol()
    policy = campaign.context_policy(p, arm)
    assert policy.observation_recall is True
    assert policy.early_observation_reduction is early_enabled
    assert policy.state_aware_compaction is state
    assert policy.diagnostic_extraction is policy.deduplicate_results is False
    assert (policy.compact_trigger_tokens, policy.compact_target_tokens) == (threshold, target)
    assert policy.request_cap == 24 and policy.max_output_tokens == 8192
    ledger = LocalUsageLedger.create_scoped(
        tmp_path / "usage.sqlite3", {"trial": 24}, context_policy=policy
    )
    assert ledger.policy == policy and ledger.request_cap("trial") == 24
    assert ledger.summary()["requests"] == 0


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.update(parent_protocol="other.json"),
        lambda p: p.update(parent_protocol_sha256="0" * 64),
        lambda p: p["tasks"].reverse(),
        lambda p: p["task_contracts"][p["tasks"][0]].update(prepared_commit="0" * 40),
        lambda p: p["task_selection"].update(prefix="selected-from-success/"),
        lambda p: p["treatments"]["baseline"].update(observation_recall=False),
        lambda p: p["treatments"]["early"].update(early_observation_reduction=False),
        lambda p: p["treatments"]["early_state"].update(state_aware_compaction=False),
        lambda p: p["treatments"]["baseline"].update(early_observation_reduction=0),
        lambda p: p["context_policy_overrides"]["early_state"].update(compact_trigger_tokens=48000),
        lambda p: p["early_observation_policy"].update(minimum_observation_tokens_exclusive=501),
        lambda p: p["early_observation_policy"].update(max_auxiliary_requests_per_attempt=5),
        lambda p: p["early_observation_policy"].update(auxiliary_request_purpose="repair"),
        lambda p: p["auxiliary_budget_policy"].update(minimum_remaining_repair_requests=0),
        lambda p: p["auxiliary_budget_policy"].update(pre_send_rejection_counts_as_request=True),
        lambda p: p["execution_budget_override"].update(max_steps=28),
        lambda p: p.update(request_cap_per_attempt=28),
        lambda p: p.update(model="different-model"),
        lambda p: p.update(formal_request_cap=936),
        lambda p: p["smoke"].update(repeats=True),
        lambda p: p["smoke"].update(task=p["tasks"][1]),
        lambda p: p["execution_order"]["full"].reverse(),
        lambda p: p["initial_observation_policy"].update(hidden_oracle_or_candidate_input=True),
        lambda p: p.update(positive_results_only=True),
    ],
)
def test_protocol_rejects_task_treatment_budget_order_and_unknown_field_changes(tmp_path, mutation):
    p = campaign.load(PROTOCOL)
    mutation(p)
    path = tmp_path / "protocol.json"
    campaign.save(path, p)
    with pytest.raises(ValueError, match="EARLY_"):
        campaign.read_protocol(path)


def test_parent_file_hash_is_fixed_before_any_parent_parse(tmp_path):
    p = campaign.load(PROTOCOL)
    path = tmp_path / early.PARENT_PROTOCOL
    path.parent.mkdir(parents=True)
    path.write_bytes((campaign.ROOT / early.PARENT_PROTOCOL).read_bytes() + b"\n")
    with pytest.raises(ValueError, match="EARLY_PARENT_SOURCE_CHANGED"):
        early.validate_protocol(
            p,
            root=tmp_path,
            read_parent=lambda _: pytest.fail("unverified parent parsed"),
            archive_contracts=lambda _: pytest.fail("unverified archive parsed"),
        )


def test_manifest_freezes_source_run_and_new_protocol(tmp_path, monkeypatch):
    path, value = make_plan(tmp_path, monkeypatch)
    assert campaign.read_manifest(path, PROTOCOL, execution=True) == value
    assert value["protocol_sha256"] == campaign.sha(PROTOCOL)
    assert value["source_sha256"]["scripts/context_early_campaign.py"]
    monkeypatch.setattr(campaign, "source_hashes", lambda: {"source.py": "changed"})
    with pytest.raises(ValueError, match="EXECUTION_SOURCE_CHANGED"):
        campaign.read_manifest(path, PROTOCOL, execution=True)


def test_aggregate_uses_three_validated_arms_and_keeps_all_missing_failures(tmp_path, monkeypatch):
    path, manifest = make_plan(tmp_path, monkeypatch)
    source = tmp_path / "summaries"
    source.mkdir()
    row = manifest["attempts"][0]
    campaign.save(
        source / "observed/summary.json",
        {
            **row,
            "schema": "repropatch.context-ablation.result.v1",
            "manifest_sha256": manifest["manifest_sha256"],
            "source_sha256": manifest["source_sha256"],
            "classification": "candidate",
            "accepted": False,
            "failure": "F2P_FAILED",
            "stop_reason": "MODEL_FINISHED",
            "usage": {"unknown_usage_requests": 0, "input_tokens": 123, "output_tokens": 17},
        },
    )
    interrupted = manifest["attempts"][1]
    campaign.save(
        source / "interrupted/runner-status.json",
        {
            "attempt_id": interrupted["attempt_id"],
            "manifest_sha256": manifest["manifest_sha256"],
            "state": "WORKER_INFRASTRUCTURE_FAILED",
            "error_message": "fixture interruption",
        },
    )
    output = tmp_path / "aggregate"
    campaign.aggregate(
        SimpleNamespace(
            manifest=path, protocol=PROTOCOL, scope="full", source=source, output=output
        )
    )
    result = campaign.load(output / "results.json")
    assert result["registered_trials"] == len(result["attempts"]) == 36
    assert set(result["arms"]) == set(early.ARMS)
    assert all(values["N"] == 12 for values in result["arms"].values())
    assert sum(values["fail"] for values in result["arms"].values()) == 1
    assert sum(values["infrastructure"] for values in result["arms"].values()) == 1
    assert sum(values["missing"] for values in result["arms"].values()) == 34
    assert len(result["paired_differences"]) == 3
    assert all(pair["N"] == 12 for pair in result["paired_differences"])
    assert all(v["input_tokens"]["all_trial_mean"] is None for v in result["arms"].values())


def test_early_metrics_preserve_candidates_skips_recall_and_unknown_auxiliary_usage():
    p = protocol()
    raw = {
        "candidates": 5,
        "attempts": 3,
        "trigger_count": 2,
        "skip_counts": {"no_useful_ranges": 1},
        "saved_bytes": 7000,
        "auxiliary_requests": 3,
        "auxiliary_input_tokens": 2000,
        "auxiliary_output_tokens": 50,
        "auxiliary_cached_input_tokens": 400,
        "auxiliary_unknown_usage": 1,
        "recall_calls": 2,
        "recall_success": 1,
        "recall_rejections": 1,
    }
    worker = {"context": {"early_observation_state": {"metrics": raw}}}
    mechanisms = campaign.mechanism_metrics(worker, p, "early")
    row = {"classification": "candidate", "accepted": False, "mechanisms": mechanisms}
    stats = campaign.arm_statistics([row], flags=early.FLAGS)
    assert stats["mechanisms"]["early_observation_reduction"]["candidate_count"] == 5
    assert stats["mechanisms"]["early_observation_reduction"]["trigger_count"] == 2
    assert stats["mechanisms"]["early_observation_reduction"]["skip_reasons"] == {
        "no_useful_ranges": 1
    }
    assert stats["mechanisms"]["observation_recall"]["candidate_count"] == 2
    assert stats["mechanisms"]["observation_recall"]["trigger_count"] == 1
    assert stats["early_auxiliary_usage"]["auxiliary_requests"]["known_trial_sum"] == 3
    assert stats["early_auxiliary_usage"]["auxiliary_input_tokens"]["all_trial_mean"] is None
    raw["auxiliary_unknown_usage"] = 0
    complete = campaign.mechanism_metrics(worker, p, "early")
    assert (
        campaign.auxiliary_statistics([{"mechanisms": complete}], "auxiliary_input_tokens")[
            "all_trial_mean"
        ]
        == 2000
    )
    assert campaign.auxiliary_statistics([{}], "auxiliary_requests")["missing_trials"] == 1


@pytest.mark.sdk
@pytest.mark.parametrize("arm", early.ARMS)
def test_mock_transport_counts_compaction_in_same_24_request_cap(tmp_path, arm):
    import httpx2

    p = protocol()
    policy = campaign.context_policy(p, arm)
    attempt = f"offline/{arm}"
    ledger = LocalUsageLedger.create_scoped(
        tmp_path / "usage.sqlite3", {attempt: 24}, context_policy=policy
    )
    hooks = BudgetHooks(ledger, attempt, tmp_path / "http", local_luna=True)
    sent = []

    def serve(request):
        sent.append(json.loads(request.content))
        return httpx2.Response(
            200,
            json={
                "output": [],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 2,
                    "total_tokens": 12,
                    "input_tokens_details": {"cached_tokens": 3},
                },
            },
            request=request,
        )

    body = {
        "model": p["model"],
        "reasoning": {"effort": "max"},
        "max_output_tokens": 8192,
        "input": [{"role": "user", "content": "offline evidence"}],
        "tools": [],
    }
    with httpx2.Client(
        transport=httpx2.MockTransport(serve),
        event_hooks={"request": [hooks.request], "response": [hooks.response]},
    ) as client:
        for purpose in ["compact"] * 4 + ["repair"] * 20:
            token = REQUEST_PURPOSE.set(purpose)
            try:
                client.post(p["endpoint"] + "/responses", json=body)
            finally:
                REQUEST_PURPOSE.reset(token)
        with pytest.raises(BudgetLimit, match="BENCHMARK_REQUEST_LIMIT"):
            client.post(p["endpoint"] + "/responses", json=body)
    result = ledger.summary(attempt)
    assert len(sent) == result["requests"] == 24
    assert result["repair_requests"] == 20 and result["compact_requests"] == 4
    assert result["input_tokens"] == 240 and result["output_tokens"] == 48
    assert result["unknown_usage_requests"] == 0 and result["local_rejections"] == 1


def test_workflow_validates_early_contract_before_freezing_matrix():
    text = (campaign.ROOT / ".github/workflows/context-ablation.yml").read_text()
    assert text.index("tests/test_context_early*.py") < text.index("Freeze execution matrix")
    assert '--protocol "$ABLATION_PROTOCOL"' in text
    assert "context-raw-${{ github.run_id }}-${{ matrix.job_key }}" in text


def test_first_request_identity_uses_first_issued_repair_after_local_rejection(tmp_path):
    assert campaign.first_request_identity(tmp_path) is None
    ledger = LocalUsageLedger.create_scoped(tmp_path / "usage.sqlite3", {"trial": 3})
    body = {
        "model": "gpt-6-luna",
        "reasoning": {"effort": "max"},
        "max_output_tokens": 8192,
        "input": [{"role": "user", "content": "qualified task"}],
        "instructions": "repair contract",
        "tools": [{"type": "function", "name": "search_code", "parameters": {}}],
    }
    rejected = json.dumps({**body, "model": "rejected-local-model"}).encode()
    with pytest.raises(BudgetLimit, match="FORMAL_REQUEST_PARAMETERS"):
        ledger.reserve("trial", rejected, request_purpose="repair")
    assert campaign.first_request_identity(tmp_path) is None

    def issued(value, purpose):
        identity = ledger.reserve("trial", json.dumps(value).encode(), request_purpose=purpose)
        ledger.settle(
            identity,
            json.dumps({"usage": {"input_tokens": 10, "output_tokens": 2}}).encode(),
            200,
        )

    issued({**body, "instructions": "auxiliary contract", "tools": []}, "compact")
    assert campaign.first_request_identity(tmp_path) is None
    issued(body, "repair")
    expected = campaign.first_request_identity(tmp_path)
    assert expected["input_sha256"] == campaign.digest(body["input"])
    assert expected["instructions_sha256"] == campaign.digest(body["instructions"])
    assert expected["tools_sha256"] == campaign.digest(body["tools"])
    assert expected["tool_names"] == ["search_code"]
    issued({**body, "input": [{"role": "user", "content": "later task"}]}, "repair")
    assert campaign.first_request_identity(tmp_path) == expected


@pytest.mark.parametrize("changed", [None, "input", "instructions", "tools", "missing"])
def test_first_request_agreement_covers_all_contract_parts_and_missing_trials(changed):
    identity = {field + "_sha256": field + "-same" for field in ("input", "instructions", "tools")}
    rows = [
        {"instance_id": "task", "arm": arm, "repeat": 1, "first_request": dict(identity)}
        for arm in early.ARMS
    ]
    if changed == "missing":
        rows[-1]["first_request"] = None
    elif changed:
        rows[-1]["first_request"][changed + "_sha256"] = "different"
    result = campaign.input_identity_statistics(rows)[0]
    assert result["first_requests_observed"] == (2 if changed == "missing" else 3)
    assert result["first_requests_missing"] == (1 if changed == "missing" else 0)
    for field in ("input", "instructions", "tools"):
        assert result["byte_identical_first_" + field] is (
            None if changed == "missing" else changed != field
        )
    assert result["byte_identical_first_request"] is (
        None if changed == "missing" else changed is None
    )


@pytest.fixture(scope="module")
def early_qualification():
    p = protocol()
    records = {}
    for archive_path in campaign.qualification_archives(p):
        with tarfile.open(archive_path) as archive:
            names = set(archive.getnames())
            for task in p["tasks"]:
                prefix = f"qualification/{task}/"
                if prefix + "task.yaml" in names:
                    assert task not in records
                    records[task] = {
                        name: archive.extractfile(prefix + name).read()
                        for name in ("task.yaml", "result.json", "manifest.json")
                    }
    assert set(records) == set(p["tasks"])
    return p, records


@pytest.mark.parametrize("instance", campaign.load(PROTOCOL)["tasks"])
def test_selected_qualification_and_all_three_worker_startups_reserve_zero_requests(
    tmp_path,
    monkeypatch,
    capsys,
    early_qualification,
    instance,
):
    import run_benchmark_agent as worker
    from formal_benchmark import prepare_execution_contract

    p, records = early_qualification
    source = tmp_path / "qualification"
    source.mkdir()
    for name, content in records[instance].items():
        (source / name).write_bytes(content)
    prepared = prepare_execution_contract(
        source, tmp_path / "execution", p["model_timeout_seconds"], p["execution_budget_override"]
    )
    assert (
        campaign.sha(prepared / "task.yaml")
        == p["task_contracts"][instance]["execution_task_sha256"]
    )
    monkeypatch.setattr(worker, "repropatch_agent", lambda *a, **k: pytest.fail("model started"))
    monkeypatch.setattr(worker, "BudgetHooks", lambda *a, **k: pytest.fail("transport started"))
    for arm in early.ARMS:
        output = tmp_path / arm
        output.mkdir()
        attempt = f"offline-check/{instance}/{arm}"
        ledger = LocalUsageLedger.create_scoped(
            output / "usage.sqlite3", {attempt: 24}, context_policy=campaign.context_policy(p, arm)
        )
        row = {"attempt_id": attempt}
        command = campaign.worker_command(row, {"task": str(prepared / "task.yaml")}, output, p)
        monkeypatch.setattr(sys, "argv", command[1:] + ["--check-only"])
        assert worker.main() == 0
        assert json.loads(capsys.readouterr().out)["requests_reserved"] == 0
        assert ledger.summary()["requests"] == 0
        assert not (output / "worker").exists()
