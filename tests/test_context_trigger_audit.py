"""CPU-only archive fixtures for the read-only tool projection audit."""

import gzip
import io
import json
import os
import sys
import tarfile
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_context_triggers as audit

from repropatch.context import ContextPolicy, fold_tool_output
from repropatch.context_optimization import ContextOptimizer
from repropatch.task import canonical_json

ROOT = "worker/runs/fixture/"
SOURCE_A = "a" * 64
SOURCE_B = "b" * 64


def read_call(text=None):
    return (
        "read_file",
        {"path": "src/main.cpp", "start_line": 1},
        {
            "ok": True,
            "data": {
                "path": "src/main.cpp",
                "text": text if text is not None else "int repeated_name = 123;\n" * 200,
                "start_line": 1,
                "end_line": 200,
                "total_lines": 200,
                "truncated": False,
            },
            "progress": {"model_steps_remaining": 12},
        },
    )


def fixture_files(batches=None, sources=None, policy=None):
    batches = batches or [[read_call()], [read_call()]]
    sources = sources or [SOURCE_A] * (len(batches) + 1)
    policy = policy or ContextPolicy(
        deduplicate_results=True, compact_trigger_tokens=48000, compact_target_tokens=21600
    )
    files, events = {}, []

    def save(name, value, binary=False):
        raw = value if binary else canonical_json(value) + b"\n"
        files[ROOT + name] = raw
        return {"path": name, "size_bytes": len(raw), "sha256": audit.digest(raw)}

    def emit(kind, payload, step=None, tool_id=None):
        events.append(
            {
                "run_id": "fixture",
                "seq": len(events) + 1,
                "type": kind,
                "step_id": step,
                "tool_call_id": tool_id,
                "payload": payload,
            }
        )

    config_ref = save(
        "execution-config.json",
        {"context_policy": policy.to_dict(), "implementation_sha256": "c" * 64},
    )
    emit("inputs_frozen", {"configuration": config_ref, "base_commit": "d" * 40})

    def checkpoint(step):
        source = {
            "schema_version": 1,
            "files": [
                {
                    "path": "src/main.cpp",
                    "sha256": sources[step],
                    "size_bytes": 12,
                    "git_mode": "100644",
                }
            ],
        }
        ref = save(f"checkpoints/{step + 1}/source-manifest.json", source)
        manifest = {
            "boundary": "model_input_ready",
            "step_id": step,
            "source_tree_sha256": audit.digest(canonical_json(source)),
            "source_manifest": ref,
            "input_fingerprints": {"configuration": config_ref},
        }
        ref = save(f"checkpoints/{step + 1}/manifest.json", manifest)
        emit("checkpoint_committed", {"step_id": step, "manifest_ref": ref}, step=step)

    checkpoint(0)
    for step, batch in enumerate(batches, 1):
        output, admitted = [], []
        for index, (name, arguments, _) in enumerate(batch, 1):
            identity = f"s{step:06d}.t{index:02d}"
            output.append(
                {
                    "type": "function_call",
                    "name": name,
                    "arguments": json.dumps(arguments),
                    "call_id": identity,
                }
            )
            admitted.append({"tool_call_id": identity, "provider_call_id": identity, "name": name})
        ref = save(f"agent/native/{step:04d}-output.json", {"output": output})
        emit("model_finished", {"native": ref, "request_purpose": "repair"}, step=step)
        emit("tool_batch_admitted", {"calls": admitted}, step=step)
        for index, (name, _, value) in enumerate(batch, 1):
            identity = f"s{step:06d}.t{index:02d}"
            ref = save(f"agent/tool-results/{identity}.json", value)
            emit(
                "tool_finished",
                {"provider_call_id": identity, "name": name, "result_ref": ref},
                step=step,
                tool_id=identity,
            )
        checkpoint(step)
    files[ROOT + "events.jsonl"] = b"".join(canonical_json(event) + b"\n" for event in events)
    return files


def write_archive(path, files, extra=(), inventory=True):
    rows = list(files.items())
    if inventory:
        rows.append(
            (
                "archive-manifest.json",
                canonical_json(
                    {
                        "files": [
                            {"path": name, "size_bytes": len(raw), "sha256": audit.digest(raw)}
                            for name, raw in rows
                        ]
                    }
                ),
            )
        )
    with tarfile.open(path, "w:gz") as archive:
        for name, raw in rows:
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            archive.addfile(info, io.BytesIO(raw))
        for info, raw in extra:
            archive.addfile(info, io.BytesIO(raw))
    return path


def change_events(files, change):
    events = [json.loads(line) for line in files[ROOT + "events.jsonl"].splitlines()]
    change(events)
    files[ROOT + "events.jsonl"] = b"".join(canonical_json(event) + b"\n" for event in events)


def run_fixture(tmp_path, files=None):
    result = audit.audit_archives(
        [write_archive(tmp_path / "attempt.tar.gz", files or fixture_files())]
    )
    return result, result["archives"][0]["runs"][0]


def test_positive_read_dedup_preserves_original_policy_and_raw_receipts(tmp_path):
    files = fixture_files()
    original = deepcopy(files)
    result, run = run_fixture(tmp_path, files)
    assert files == original
    assert result["measurement"] == "offline_tool_context_bytes"
    assert result["model_requests"] == 0
    assert run["context_policy"]["compact_trigger_tokens"] == 48000
    assert run["checkpoint_errors"] == []
    assert run["audit_skip_reasons"] == {}
    assert run["metrics"]["deduplicate_results"]["attempts"] == 2
    assert run["metrics"]["deduplicate_results"]["candidates"] == 1
    assert run["metrics"]["deduplicate_results"]["triggers"] == 1
    assert run["rows"][1]["projected_bytes"] < run["rows"][1]["native_bytes"]
    assert run["rows"][0]["decisions"][0]["reason"] == "first_observation"
    assert run["rows"][1]["decisions"][0]["outcome"] == "projected"
    assert result["archives"][0]["archive_inventory_verified"]
    assert "scripts/audit_context_triggers.py" in result["audit_source_sha256"]


def test_native_fold_is_baseline_and_folded_reads_stay_visible(tmp_path):
    policy = ContextPolicy(
        deduplicate_results=True,
        tool_output_max_bytes=1024,
        compact_trigger_tokens=48000,
        compact_target_tokens=21600,
    )
    _, run = run_fixture(tmp_path, fixture_files(policy=policy))
    for row in run["rows"]:
        expected = fold_tool_output(
            canonical_json(read_call()[2]).decode(),
            1024,
            lambda _, item=row: f"agent/tool-results/{item['tool_id']}.json",
        )
        assert row["native_bytes"] == len(expected.encode())
        assert row["raw_bytes"] > row["native_bytes"] == row["projected_bytes"]
    assert run["metrics"]["deduplicate_results"]["skip_reasons"] == {
        "first_result_not_fully_visible": 2
    }


def test_insufficient_savings_is_candidate_not_trigger(tmp_path):
    _, run = run_fixture(tmp_path, fixture_files([[read_call("short")], [read_call("short")]]))
    metric = run["metrics"]["deduplicate_results"]
    assert (metric["attempts"], metric["candidates"], metric["triggers"]) == (2, 1, 0)
    assert metric["skip_reasons"]["insufficient_savings"] == 1
    assert run["bytes"]["saved_bytes"] == 0


def test_state_policy_reported_without_request_level_replay(tmp_path):
    policy = ContextPolicy(
        state_aware_compaction=True, compact_trigger_tokens=48000, compact_target_tokens=21600
    )
    _, run = run_fixture(tmp_path, fixture_files(policy=policy))
    assert run["state_aware_compaction"] == {
        "scope": "request_level_not_replayed",
        "compact_trigger_tokens": 48000,
    }
    assert all(row["decisions"][2]["reason"] == "request_level_strategy" for row in run["rows"])


def test_tool_result_mutation_isolated_from_archive_and_next_receipt(tmp_path, monkeypatch):
    project = ContextOptimizer.project
    observed = []

    def mutating(self, name, arguments, value, reference, **kwargs):
        observed.append(deepcopy(value))
        output = project(self, name, arguments, value, reference, **kwargs)
        value["data"]["text"] = "mutated"
        reference["sha256"] = "0" * 64
        return output

    monkeypatch.setattr(ContextOptimizer, "project", mutating)
    result, run = run_fixture(tmp_path)
    assert observed[0] == observed[1] == read_call()[2]
    assert run["metrics"]["deduplicate_results"]["triggers"] == 1
    run["rows"][0]["decisions"][0]["reason"] = "changed"
    assert run["metrics"]["deduplicate_results"]["skip_reasons"] == {"first_observation": 1}
    assert result["model_requests"] == 0


@pytest.mark.parametrize(
    "path",
    ["../escape", "/absolute", "a/../escape", "a//b", "./worker", "C:/escape", "a\\b", "bad\nname"],
)
def test_rejects_unsafe_tar_paths(tmp_path, path):
    with pytest.raises(audit.AuditError, match="unsafe_path"):
        audit.Archive(write_archive(tmp_path / "bad.tar.gz", {path: b"x"}, inventory=False))


def test_rejects_duplicate_tar_members(tmp_path):
    info = tarfile.TarInfo("manifest.json")
    with pytest.raises(audit.AuditError, match="duplicate_member"):
        audit.Archive(
            write_archive(tmp_path / "bad.tar.gz", {"manifest.json": b"{}"}, [(info, b"")])
        )


@pytest.mark.parametrize(
    "kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE]
)
def test_rejects_links_and_special_files(tmp_path, kind):
    info = tarfile.TarInfo("escape")
    info.type, info.linkname = kind, "/etc/passwd"
    with pytest.raises(audit.AuditError, match="unsupported_member_type"):
        audit.Archive(write_archive(tmp_path / "bad.tar.gz", {}, [(info, b"")], inventory=False))


def test_rejects_file_directory_collision(tmp_path):
    with pytest.raises(audit.AuditError, match="file_directory_collision"):
        audit.Archive(
            write_archive(tmp_path / "bad.tar.gz", {"worker": b"x", "worker/runs/a": b"y"})
        )


@pytest.mark.parametrize(
    "limit,value,expected",
    [
        ("MAX_MEMBER_BYTES", 1024, "member_size_limit"),
        ("MAX_FILES", 1, "member_count_limit"),
        ("MAX_CACHED_BYTES", 1024, "cache_size_limit"),
        ("MAX_EXPANDED_BYTES", 1024, "expanded_archive_limit"),
    ],
)
def test_enforces_archive_limits(tmp_path, monkeypatch, limit, value, expected):
    path = write_archive(tmp_path / "bad.tar.gz", fixture_files())
    monkeypatch.setattr(audit, limit, value)
    with pytest.raises(audit.AuditError, match=expected):
        audit.Archive(path)


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("sha256", "0" * 64, "reference_sha_mismatch"),
        ("size_bytes", 1, "reference_size_mismatch"),
        ("path", "../outside", "unsafe_path"),
        ("path", "missing.json", "missing_reference"),
    ],
)
def test_bad_tool_references_are_explicit_and_excluded(tmp_path, field, value, expected):
    files = fixture_files()

    def alter(events):
        for event in events:
            if event["type"] == "tool_finished":
                event["payload"]["result_ref"][field] = value

    change_events(files, alter)
    _, run = run_fixture(tmp_path, files)
    assert run["compared_tool_count"] == 0
    assert all(
        row["status"] == "evidence_error" and row["reason"] == expected for row in run["rows"]
    )
    assert run["metrics"]["deduplicate_results"]["triggers"] == 0


def test_missing_native_file_and_missing_checkpoint_are_reported(tmp_path):
    files = fixture_files()
    del files[ROOT + "agent/native/0001-output.json"]
    del files[ROOT + "checkpoints/2/manifest.json"]
    _, run = run_fixture(tmp_path, files)
    assert run["rows"][0]["reason"] == "missing_reference"
    assert run["rows"][1]["source_status"] == "missing_source"
    assert run["rows"][1]["source_tree_sha256"] is None
    assert run["checkpoint_errors"]


def test_source_changes_use_pre_read_checkpoint_and_invalidate_dedup(tmp_path):
    edit = ("edit_file", {"path": "src/main.cpp"}, {"ok": True, "data": {"changed": True}})
    files = fixture_files(
        [[read_call()], [edit], [read_call()], [read_call()]],
        [SOURCE_A, SOURCE_A, SOURCE_B, SOURCE_B, SOURCE_B],
    )
    _, run = run_fixture(tmp_path, files)
    rows = run["rows"]
    assert rows[0]["source_tree_sha256"] != rows[2]["source_tree_sha256"]
    assert (
        rows[1]["source_tree_sha256"]
        == rows[2]["source_tree_sha256"]
        == rows[3]["source_tree_sha256"]
    )
    assert rows[2]["decisions"][0]["reason"] == "first_observation"
    assert rows[3]["decisions"][0]["outcome"] == "projected"


def test_mixed_batch_explicitly_unsupported_without_final_source(tmp_path):
    edit = ("edit_file", {}, {"ok": True, "data": {}})
    files = fixture_files([[read_call(), edit, read_call()]], [SOURCE_A, SOURCE_B])
    _, run = run_fixture(tmp_path, files)
    assert all(row["status"] == "unsupported" for row in run["rows"])
    assert all(row["source_tree_sha256"] is None for row in run["rows"])
    assert run["audit_skip_reasons"] == {"mixed_read_write_batch": 3}
    assert run["metrics"]["deduplicate_results"]["triggers"] == 0


def test_compaction_event_invalidates_replay_dedup(tmp_path):
    files = fixture_files()

    def alter(events):
        index = next(
            i
            for i, event in enumerate(events)
            if event["type"] == "model_finished" and event["step_id"] == 2
        )
        events.insert(index, {"type": "context_compacted", "payload": {}, "run_id": "fixture"})
        for seq, event in enumerate(events, 1):
            event["seq"] = seq

    change_events(files, alter)
    _, run = run_fixture(tmp_path, files)
    assert run["metrics"]["deduplicate_results"]["triggers"] == 0
    assert run["rows"][1]["decisions"][0]["reason"] == "first_observation"


def test_nested_log_reference_is_verified(tmp_path):
    call = read_call()
    call[2]["extra"] = {"log": {"path": "logs/missing.bin", "sha256": "f" * 64, "size_bytes": 1}}
    _, run = run_fixture(tmp_path, fixture_files([[call]]))
    assert run["rows"][0]["reason"] == "missing_reference"


def test_diagnostic_replays_real_callback_and_records_trigger(tmp_path):
    log = ("src/main.cpp:10:4: error: invalid conversion\n" * 300).encode()
    log_ref = {
        "path": "logs/compile/stderr.bin",
        "sha256": audit.digest(log),
        "size_bytes": len(log),
    }
    call = (
        "run_shell",
        {"command": "cmake --build ."},
        {
            "ok": True,
            "data": {
                "status": "exited",
                "exit_code": 1,
                "stdout": "",
                "stderr": log.decode(),
                "stderr_log": log_ref,
                "truncated": False,
            },
        },
    )
    policy = ContextPolicy(
        diagnostic_extraction=True, compact_trigger_tokens=48000, compact_target_tokens=21600
    )
    files = fixture_files([[call]], policy=policy)
    files[ROOT + log_ref["path"]] = log
    _, run = run_fixture(tmp_path, files)
    assert run["metrics"]["diagnostic_extraction"]["triggers"] == 1
    assert run["rows"][0]["saved_bytes"] > 0


def test_cli_writes_reproducible_private_reports(tmp_path):
    path = write_archive(tmp_path / "attempt.tar.gz", fixture_files())
    before = path.read_bytes()
    output = tmp_path / "reports"
    assert audit.main(["--archive", str(path), "--output", str(output)]) == 0
    first = (output / "results.json").read_bytes()
    assert audit.main(["--archive", str(path), "--output", str(output)]) == 0
    assert first == (output / "results.json").read_bytes()
    assert "offline_tool_context_bytes" in (output / "summary.md").read_text()
    assert path.read_bytes() == before
    assert (output / "results.json").stat().st_mode & 0o777 == 0o600


def test_duplicate_archive_is_counted_once(tmp_path):
    path = write_archive(tmp_path / "attempt.tar.gz", fixture_files())
    result = audit.audit_archives([path, path])
    assert result["unique_run_count"] == result["duplicate_run_count"] == 1
    assert result["metrics"]["deduplicate_results"]["triggers"] == 1
    assert result["archives"][1]["runs"] == []


def test_output_symlink_rejected(tmp_path):
    path = write_archive(tmp_path / "attempt.tar.gz", fixture_files())
    output = tmp_path / "out"
    output.mkdir()
    target = tmp_path / "keep"
    target.write_text("keep")
    (output / "results.json").symlink_to(target)
    with pytest.raises(audit.AuditError, match="unsafe_output_path"):
        audit.main(["--archive", str(path), "--output", str(output)])
    assert target.read_text() == "keep"


@pytest.mark.parametrize("damage", ["hash", "size", "duplicate", "unlisted"])
def test_archive_inventory_is_verified(tmp_path, damage):
    rows = {"manifest.json": b"{}"}
    ref = {"path": "manifest.json", "size_bytes": 2, "sha256": audit.digest(b"{}")}
    entries = [ref]
    if damage == "hash":
        ref["sha256"] = "0" * 64
    elif damage == "size":
        ref["size_bytes"] = 1
    elif damage == "duplicate":
        entries.append(deepcopy(ref))
    else:
        rows["unexpected.json"] = b"{}"
    rows["archive-manifest.json"] = canonical_json({"files": entries})
    with pytest.raises(audit.AuditError):
        audit.Archive(write_archive(tmp_path / "bad.tar.gz", rows, inventory=False))


def test_missing_config_fails_closed(tmp_path):
    files = fixture_files()
    del files[ROOT + "execution-config.json"]
    with pytest.raises(audit.AuditError, match="missing_execution_config"):
        run_fixture(tmp_path, files)


def test_reference_read_limit_is_enforced(tmp_path, monkeypatch):
    path = write_archive(tmp_path / "attempt.tar.gz", fixture_files())
    archive = audit.Archive(path)
    name = "agent/tool-results/s000001.t01.json"
    raw = archive.files[ROOT + name]
    monkeypatch.setattr(audit, "MAX_READ_BYTES", 10)
    with pytest.raises(audit.AuditError, match="invalid_reference"):
        archive.read_ref({"path": name, "size_bytes": len(raw), "sha256": audit.digest(raw)}, ROOT)


def test_inconsistent_checkpoint_source_is_never_used(tmp_path):
    files = fixture_files()
    name = "checkpoints/2/manifest.json"
    manifest = json.loads(files[ROOT + name])
    manifest["source_tree_sha256"] = "f" * 64
    raw = files[ROOT + name] = canonical_json(manifest)

    def alter(events):
        event = next(
            event
            for event in events
            if event["type"] == "checkpoint_committed" and event["payload"]["step_id"] == 1
        )
        event["payload"]["manifest_ref"] = {
            "path": name,
            "sha256": audit.digest(raw),
            "size_bytes": len(raw),
        }

    change_events(files, alter)
    _, run = run_fixture(tmp_path, files)
    assert run["checkpoint_errors"][0]["reason"] == "checkpoint_source_mismatch"
    assert run["rows"][1]["source_tree_sha256"] is None
    assert run["rows"][1]["decisions"][0]["reason"] == "missing_source_identity"


def test_truncated_diagnostics_reads_verified_full_streams(tmp_path, monkeypatch):
    log = ("src/main.cpp:10:4: error: invalid conversion\n" * 300).encode()
    refs = {
        "stdout": {"path": "logs/build/stdout.bin", "size_bytes": 0, "sha256": audit.digest(b"")},
        "stderr": {
            "path": "logs/build/stderr.bin",
            "size_bytes": len(log),
            "sha256": audit.digest(log),
        },
    }
    call = (
        "run_shell",
        {"command": "cmake --build ."},
        {
            "ok": True,
            "data": {
                "status": "exited",
                "exit_code": 1,
                "stdout": "",
                "stderr": log[:8000].decode(),
                "stdout_log": refs["stdout"],
                "stderr_log": refs["stderr"],
                "truncated": True,
            },
        },
    )
    policy = ContextPolicy(
        diagnostic_extraction=True, compact_trigger_tokens=48000, compact_target_tokens=21600
    )
    files = fixture_files([[call]], policy=policy)
    files[ROOT + refs["stdout"]["path"]] = b""
    files[ROOT + refs["stderr"]["path"]] = log
    observed, read = [], audit.Archive.read_ref

    def tracked(self, ref, root):
        observed.append(ref["path"])
        return read(self, ref, root)

    monkeypatch.setattr(audit.Archive, "read_ref", tracked)
    _, run = run_fixture(tmp_path, files)
    assert run["metrics"]["diagnostic_extraction"]["triggers"] == 1
    assert refs["stdout"]["path"] in observed and refs["stderr"]["path"] in observed


@pytest.mark.parametrize("changed_ref", ["frozen", "checkpoint", "both"])
def test_conflicting_configuration_references_are_rejected(tmp_path, changed_ref):
    files = fixture_files()
    config = json.loads(files[ROOT + "execution-config.json"])
    config["context_policy"]["deduplicate_results"] = False
    raw = files[ROOT + "frozen-config.json"] = canonical_json(config)
    alternate = {"path": "frozen-config.json", "size_bytes": len(raw), "sha256": audit.digest(raw)}

    def alter(events):
        for event in events:
            if event["type"] == "inputs_frozen" and changed_ref in {"frozen", "both"}:
                event["payload"]["configuration"] = deepcopy(alternate)
            if event["type"] == "checkpoint_committed" and changed_ref in {"checkpoint", "both"}:
                ref = event["payload"]["manifest_ref"]
                manifest = json.loads(files[ROOT + ref["path"]])
                manifest["input_fingerprints"]["configuration"] = deepcopy(alternate)
                raw = files[ROOT + ref["path"]] = canonical_json(manifest)
                ref.update(size_bytes=len(raw), sha256=audit.digest(raw))

    change_events(files, alter)
    expected = (
        "checkpoint_configuration_mismatch"
        if changed_ref == "checkpoint"
        else "frozen_configuration_mismatch"
    )
    path = write_archive(tmp_path / "bad.tar.gz", files)
    assert audit.Archive(path).inventory_verified
    with pytest.raises(audit.ConfigurationMismatch, match=expected):
        audit.audit_archives([path])


def test_missing_freeze_prevents_replay(tmp_path):
    files = fixture_files()
    change_events(files, lambda events: events.pop(0))
    with pytest.raises(audit.AuditError, match="missing_frozen_configuration"):
        run_fixture(tmp_path, files)


@pytest.mark.parametrize(
    "missing",
    ["size_bytes", "sha256", "path", "configuration", "input_fingerprints", "invalid_type"],
)
def test_incomplete_checkpoint_configuration_prevents_replay(tmp_path, missing):
    files = fixture_files()

    def alter(events):
        event = next(item for item in events if item["type"] == "checkpoint_committed")
        ref = event["payload"]["manifest_ref"]
        manifest = json.loads(files[ROOT + ref["path"]])
        if missing == "input_fingerprints":
            del manifest["input_fingerprints"]
        elif missing == "invalid_type":
            manifest["input_fingerprints"] = []
        elif missing == "configuration":
            del manifest["input_fingerprints"]["configuration"]
        else:
            del manifest["input_fingerprints"]["configuration"][missing]
        raw = files[ROOT + ref["path"]] = canonical_json(manifest)
        ref.update(size_bytes=len(raw), sha256=audit.digest(raw))

    change_events(files, alter)
    with pytest.raises(audit.ConfigurationMismatch, match="checkpoint_configuration_invalid"):
        run_fixture(tmp_path, files)


@pytest.mark.parametrize("representation", ["gzip_header", "tar_order"])
def test_repackaged_run_is_counted_once(tmp_path, representation):
    files = fixture_files()
    first = write_archive(tmp_path / "first.tar.gz", files)
    second = tmp_path / "second.tar.gz"
    if representation == "gzip_header":
        raw_tar = gzip.decompress(first.read_bytes())
        first.write_bytes(gzip.compress(raw_tar, mtime=1))
        second.write_bytes(gzip.compress(raw_tar, mtime=2))
    else:
        write_archive(second, dict(reversed(list(files.items()))))
    assert first.read_bytes() != second.read_bytes()
    result = audit.audit_archives([first, second])
    assert result["unique_run_count"] == result["duplicate_run_count"] == 1
    assert sum(run["tool_count"] for archive in result["archives"] for run in archive["runs"]) == 2
    assert result["metrics"]["deduplicate_results"]["attempts"] == 2
    assert result["metrics"]["deduplicate_results"]["triggers"] == 1
    assert result["archives"][1]["duplicate_runs"][0]["run_id"] == "fixture"


def test_same_run_with_conflicting_evidence_is_rejected(tmp_path):
    first = write_archive(tmp_path / "first.tar.gz", fixture_files())
    files = fixture_files([[read_call("changed")], [read_call()]])
    second = write_archive(tmp_path / "second.tar.gz", files)
    with pytest.raises(audit.AuditError, match="conflicting_run_evidence: fixture"):
        audit.audit_archives([first, second])


@pytest.mark.parametrize("output_name", ["results.json", "summary.md"])
def test_output_hardlink_to_archive_is_rejected_without_input_mutation(tmp_path, output_name):
    archive = write_archive(tmp_path / "evidence.tar.gz", fixture_files())
    alias = tmp_path / "input-alias.tar.gz"
    os.link(archive, alias)
    output = tmp_path / "out"
    output.mkdir()
    target = output / output_name
    os.link(archive, target)
    before, identity = archive.read_bytes(), archive.stat().st_ino
    with pytest.raises(audit.AuditError, match="unsafe_output_path"):
        audit.main(["--archive", str(alias), "--output", str(output)])
    assert archive.read_bytes() == alias.read_bytes() == target.read_bytes() == before
    assert archive.stat().st_ino == alias.stat().st_ino == target.stat().st_ino == identity
    assert list(output.iterdir()) == [target]


def test_report_replacement_preserves_existing_inode_contents(tmp_path):
    archive = write_archive(tmp_path / "evidence.tar.gz", fixture_files())
    output = tmp_path / "out"
    output.mkdir()
    report = output / "results.json"
    report.write_text("previous report")
    with report.open("rb") as old_inode:
        audit.main(["--archive", str(archive), "--output", str(output)])
        assert old_inode.read() == b"previous report"
        assert os.fstat(old_inode.fileno()).st_ino != report.stat().st_ino
    assert json.loads(report.read_text())["unique_run_count"] == 1
    assert sorted(path.name for path in output.iterdir()) == ["results.json", "summary.md"]
