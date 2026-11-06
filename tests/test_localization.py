"""Shared-pool localization, visible evidence and adversarial cursor contracts."""

import hashlib
import json
import time
from copy import deepcopy

import pytest

from repropatch.errors import PolicyError, SourceChanged
from repropatch.localization import Localization, LocalizationLimits
from repropatch.task import canonical_json
from repropatch.tools import Toolbox
from repropatch.workspace import SourceFile, SourceManifest, Worktree


class MemoryWorkspace:
    """Small CPU-only source fixture; security tests below use real Worktree."""

    def __init__(self, path, files):
        self.path = path
        self.contents = {p: v.encode() if isinstance(v, str) else v for p, v in files.items()}
        self.reads = []
        self.refresh()

    def refresh(self):
        self.path.mkdir(parents=True, exist_ok=True)
        for name, data in self.contents.items():
            target = self.path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        self.expected_manifest = SourceManifest(
            tuple(
                SourceFile(p, hashlib.sha256(v).hexdigest(), len(v), "100644")
                for p, v in sorted(self.contents.items())
            )
        )

    def files(self):
        return sorted(self.contents)

    def safe_path(self, name):
        return self.path / name

    def read_file(self, name):
        self.reads.append(name)
        return (self.path / name).read_bytes(), None


@pytest.fixture
def make_toolbox(tmp_path):
    def make(files, *, readable=None):
        workspace = MemoryWorkspace(tmp_path / "source", files)
        return Toolbox(workspace, (), None, readable=readable)

    return make


def observe(core, text, identity="receipt-1", **extra):
    return core.observe(
        "run_command",
        {"name": "reproduce"},
        {"ok": True, "data": {"stderr": text, **extra}},
        receipt_id=identity,
        source_tree_sha256=core.toolbox.workspace.expected_manifest.sha256,
    )


def drain(core, query, path="."):
    output, pages, cursor = [], [], None
    for _ in range(200):
        page = core.search(query, path, cursor)
        pages.append(page)
        output.extend(page["candidates"])
        cursor = page["next_cursor"]
        if cursor is None:
            return output, pages
    pytest.fail("pagination made no progress")


def test_aggregate_before_display_limit_and_resume_all_files(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle\n" * 250, "b.cpp": "needle\n"})
    assert len(toolbox.search_code("needle")["matches"]) == 100
    core = Localization(toolbox, limits=LocalizationLimits(page_files=1, hit_lines=3))
    result = core.search("needle")
    assert result["matched_files"] == 2
    assert result["scan_complete"] and not result["count_is_lower_bound"]
    assert result["candidates"][0]["match_count"] == 250
    assert result["candidates"][0]["hit_lines"] == [1, 2, 3]
    assert "text" not in result["candidates"][0]
    assert result["continuation"] == "files"
    restored = Localization(
        toolbox, state=json.loads(canonical_json(core.to_dict())), limits=core.limits
    )
    second = restored.search("needle", cursor=result["next_cursor"])
    assert [c["path"] for c in second["candidates"]] == ["b.cpp"]
    assert second["next_cursor"] is None


def test_dense_file_hit_line_continuation_reaches_beyond_100(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle\nmiss\n" * 121})
    core = Localization(toolbox, limits=LocalizationLimits(hit_lines=8))
    first = core.search("needle")
    candidate = first["candidates"][0]
    hits = candidate["hit_lines"][:]
    cursor = candidate["hit_lines_next_cursor"]
    while cursor:
        page = core.search("needle", cursor=cursor)
        assert page["page_kind"] == "hits"
        row = page["candidates"][0]
        assert row["match_count"] == 121 and row["candidate_id"] == candidate["candidate_id"]
        hits.extend(row["hit_lines"])
        cursor = page["next_cursor"]
    assert hits == list(range(1, 242, 2))


def test_scan_budget_independent_of_page_budget_and_counts_lower_bound(make_toolbox):
    toolbox = make_toolbox({f"{i:03}.cpp": "needle\n" for i in range(7)})
    limits = LocalizationLimits(scan_files=3, scan_bytes=21, page_files=2)
    core = Localization(toolbox, limits=limits)
    rows, pages = drain(core, "needle")
    assert [r["path"] for r in rows] == toolbox.workspace.files()
    assert pages[0]["scan"]["files"] == 3
    assert pages[0]["matched_files"] == 3 and pages[0]["count_is_lower_bound"]
    assert pages[-1]["matched_files"] == 7
    assert pages[-1]["scan_complete"] and not pages[-1]["count_is_lower_bound"]
    assert {p["continuation"] for p in pages} == {"files", "scan", None}
    assert all(p["scan"]["bytes"] <= 21 for p in pages)
    assert core.to_dict()["metrics"]["scan_bytes"] == sum(p["scan"]["bytes"] for p in pages)


def test_shared_candidate_pool_scans_and_ids_with_feedback_reranking(make_toolbox):
    files = {"a.cpp": "needle\nother\n", "b.cpp": "needle\nother\n", "z.cpp": "needle\n"}
    toolbox = make_toolbox(files)
    bounded, feedback = Localization(toolbox), Localization(toolbox, "feedback")
    diagnostics = "/src/a.cpp:2:2: error: bad\n/src/z.cpp:1:2: error: bad\n"
    observe(bounded, diagnostics)
    observe(feedback, diagnostics)
    a, b = bounded.search("needle"), feedback.search("needle")
    assert [c["path"] for c in a["candidates"]] == ["a.cpp", "b.cpp", "z.cpp"]
    assert [c["path"] for c in b["candidates"]] == ["z.cpp", "a.cpp", "b.cpp"]
    assert a["candidate_pool_sha256"] == b["candidate_pool_sha256"]
    assert sorted(c["candidate_id"] for c in a["candidates"]) == sorted(
        c["candidate_id"] for c in b["candidates"]
    )
    for key in ("files", "bytes", "skipped_files"):
        assert a["scan"][key] == b["scan"][key]
    assert [c["ranking"]["reason"] for c in b["candidates"]] == [
        "direct_location",
        "same_file",
        "text_order",
    ]
    reference = b["candidates"][0]["ranking"]["evidence"][0]
    assert reference["receipt_id"] == "receipt-1"
    full = next(
        item
        for item in feedback.to_dict()["receipts"][0]["evidence"]
        if item["evidence_id"] == reference["evidence_id"]
    )
    assert full["file_sha256"] == toolbox.workspace.expected_manifest.by_path["z.cpp"].sha256
    assert len(full["evidence_sha256"]) == 64
    assert "path" not in reference and "file_sha256" not in reference
    assert b["fallback_reason"] is None


def test_direct_location_uses_all_hits_not_first_displayed_hits(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle\n" * 200, "z.cpp": "needle\n" * 200})
    core = Localization(toolbox, "feedback")
    observe(core, "/src/z.cpp:199:1: error: bad")
    page = core.search("needle")
    assert page["candidates"][0]["path"] == "z.cpp"
    assert page["candidates"][0]["ranking"]["reason"] == "direct_location"


def test_feedback_keeps_candidates_in_scan_chunk_and_never_adds_files(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle", "b.cpp": "needle", "z.cpp": "other"})
    core = Localization(toolbox, "feedback", limits=LocalizationLimits(scan_files=1))
    observe(core, "/src/b.cpp:1: error: bad\n/src/z.cpp:1: error: bad")
    first = core.search("needle")
    assert [c["path"] for c in first["candidates"]] == ["a.cpp"]
    assert first["fallback_reason"] == "evidence_outside_candidate_pool"
    rows, pages = drain(core, "needle")
    assert [r["path"] for r in rows] == ["a.cpp", "b.cpp"]
    assert pages[-1]["matched_files"] == 2


@pytest.mark.parametrize(
    "text,kind",
    [
        ("/src/z.cpp:2:8: fatal error: missing type", "compiler"),
        ("z.cpp:2: warning: narrow", "compiler"),
        (
            "[ RUN      ] Suite.Failure\n/src/z.cpp:2: Failure\n"
            "Expected: 1\n[ FAILED ] Suite.Failure",
            "gtest",
        ),
        ("#0  0xabc in fn() at /src/z.cpp:2", "stack"),
        ("    #1 0xabc in fn /src/z.cpp:2:4", "stack"),
    ],
)
def test_visible_compiler_gtest_and_stack_sources(make_toolbox, text, kind):
    toolbox = make_toolbox({"a.cpp": "needle\n", "z.cpp": "other\nneedle\n"})
    core = Localization(toolbox, "feedback")
    registration = observe(core, text)
    assert registration["evidence_count"] == 1
    result = core.search("needle")
    evidence = result["candidates"][0]["ranking"]["evidence"][0]
    assert (
        evidence["kind"] == kind
        and result["candidates"][0]["path"] == "z.cpp"
        and evidence["line"] == 2
    )
    if kind == "gtest":
        assert core.to_dict()["receipts"][0]["evidence"][0]["test_name"] == "Suite.Failure"


def test_only_public_fields_and_never_open_archives(make_toolbox, tmp_path):
    toolbox = make_toolbox({"a.cpp": "needle", "z.cpp": "needle"})
    core = Localization(toolbox, "feedback")
    secret = tmp_path / "oracle.log"
    secret.write_text("/src/z.cpp:1: error: answer")
    value = {
        "ok": True,
        "data": {
            "stdout_log": {"path": str(secret), "sha256": "f" * 64},
            "reference_patch": "/src/z.cpp:1: error: hidden",
            "tests": [{"visibility": "hidden", "diagnostic": "/src/z.cpp:1: error: hidden"}],
            "stderr": "normal visible output",
        },
    }
    registration = core.observe(
        "run_command",
        {},
        value,
        receipt_id="r",
        source_tree_sha256=toolbox.workspace.expected_manifest.sha256,
    )
    assert registration["evidence_count"] == 0
    assert toolbox.workspace.reads == []
    assert core.search("needle")["fallback_reason"] == "no_location_evidence"


def test_visible_projected_diagnostic_json(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle", "z.cpp": "needle"})
    core = Localization(toolbox, "feedback")
    value = {
        "ok": True,
        "data": {
            "failed_commands": [
                {
                    "command_id": "cmd",
                    "exit_code": 1,
                    "stderr": {
                        "diagnostics": [
                            {"file": "/src/z.cpp", "line": 1, "message": "bad", "severity": "error"}
                        ]
                    },
                }
            ]
        },
    }
    core.observe(
        "run_command",
        {},
        json.dumps(value),
        receipt_id="r",
        source_tree_sha256=toolbox.workspace.expected_manifest.sha256,
    )
    assert core.search("needle")["candidates"][0]["path"] == "z.cpp"
    record = core.to_dict()["receipts"][0]["evidence"][0]
    assert record["metadata"]["command_id"] == "cmd"
    assert record["fragment_pointer"] == "/data/failed_commands/0/stderr/diagnostics/0"


@pytest.mark.parametrize(
    "location",
    [
        "../../z.cpp",
        "/src/../z.cpp",
        "/etc/z.cpp",
        "/src2/z.cpp",
        "secret.cpp",
        "sub/../z.cpp",
        r"sub\z.cpp",
    ],
)
def test_diagnostic_path_restrictions(make_toolbox, location):
    toolbox = make_toolbox(
        {"a.cpp": "needle", "z.cpp": "needle", "secret.cpp": "hidden"}, readable={"a.cpp", "z.cpp"}
    )
    core = Localization(toolbox, "feedback")
    result = observe(core, f"{location}:1: error: bad")
    assert result["evidence_count"] == 0 and result["rejections"]
    assert not toolbox.workspace.reads


@pytest.mark.parametrize("path", ["../", "/src", "a/../b", "a//b", "a/./b"])
def test_search_inherits_scope_policy(make_toolbox, path):
    core = Localization(make_toolbox({"a.cpp": "needle"}))
    with pytest.raises(PolicyError):
        core.search("needle", path)


def test_manifest_edit_invalidates_cursor_and_evidence(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle", "z.cpp": "needle"})
    core = Localization(toolbox, "feedback", limits=LocalizationLimits(page_files=1))
    observe(core, "/src/z.cpp:1: error: bad")
    first = core.search("needle")
    toolbox.workspace.contents["a.cpp"] = b"needle updated"
    toolbox.workspace.refresh()
    with pytest.raises(PolicyError, match="CURSOR_STALE"):
        core.search("needle", cursor=first["next_cursor"])
    page = core.search("needle")
    assert page["candidates"][0]["path"] == "a.cpp"
    assert page["fallback_reason"] == "stale_evidence" and page["stale_evidence_count"] == 1
    observe(core, "/src/z.cpp:1: error: new observation", "new")
    assert core.search("needle")["candidates"][0]["path"] == "z.cpp"


def test_unrecorded_file_mutation_is_detected_even_without_manifest_refresh(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle"})
    core = Localization(toolbox, "feedback")
    (toolbox.workspace.path / "a.cpp").write_bytes(b"other")
    with pytest.raises(SourceChanged):
        core.search("needle")
    with pytest.raises(SourceChanged):
        observe(core, "/src/a.cpp:1: error: bad")


def test_cursor_rejects_query_scope_policy_and_ranking_changes(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle", "z.cpp": "needle"})
    core = Localization(toolbox, "feedback", limits=LocalizationLimits(page_files=1))
    cursor = core.search("needle")["next_cursor"]
    for query, path in (("other", "."), ("needle", "a.cpp")):
        with pytest.raises(PolicyError, match="CURSOR_STALE"):
            core.search(query, path, cursor)
    observe(core, "/src/z.cpp:1: error: bad")
    with pytest.raises(PolicyError, match="CURSOR_STALE"):
        core.search("needle", cursor=cursor)
    with pytest.raises(PolicyError, match="STATE_INVALID"):
        Localization(toolbox, state=core.to_dict(), limits=LocalizationLimits(page_files=2))


@pytest.mark.parametrize("cursor", ["", "not-a-cursor", "a.abc", "a" * 5000, True, 12, "!!!!.x"])
def test_invalid_cursor_is_rejected(make_toolbox, cursor):
    with pytest.raises(PolicyError, match="CURSOR_INVALID"):
        Localization(make_toolbox({"a.cpp": "needle"})).search("needle", cursor=cursor)


def test_cursor_mac_detects_payload_edit(make_toolbox):
    import base64

    core = Localization(
        make_toolbox({"a.cpp": "needle", "z.cpp": "needle"}),
        limits=LocalizationLimits(page_files=1),
    )
    cursor = core.search("needle")["next_cursor"]
    encoded, mac = cursor.split(".")
    raw = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    raw["offset"] = -1
    edited = base64.urlsafe_b64encode(canonical_json(raw)).decode().rstrip("=") + "." + mac
    with pytest.raises(PolicyError, match="CURSOR_INVALID"):
        core.search("needle", cursor=edited)


def test_baseline_idempotency_conflicts_and_checkpoint_integrity(make_toolbox):
    toolbox = make_toolbox({"z.cpp": "needle"})
    core = Localization(toolbox, "feedback")
    value = {"stderr": "/src/z.cpp:1: error: bad"}
    args = {"source_tree_sha256": toolbox.workspace.expected_manifest.sha256}
    assert core.register_baseline(value, **args)["evidence_count"] == 1
    assert core.register_baseline(value, **args)["reason"] == "already_registered"
    with pytest.raises(PolicyError, match="RECEIPT_CONFLICT"):
        core.register_baseline({"stderr": "changed"}, **args)
    state = core.to_dict()
    restored = Localization(toolbox, "feedback", state=json.loads(canonical_json(state)))
    assert restored.search("needle")["candidates"][0]["ranking"]["reason"] == "direct_location"
    corrupted = deepcopy(state)
    corrupted["receipts"][0]["evidence"][0]["line"] = 2
    with pytest.raises(PolicyError, match="STATE_INVALID"):
        Localization(toolbox, "feedback", state=corrupted)
    assert core.to_dict() == state


def test_receipt_source_identity_and_hidden_roles(make_toolbox):
    core = Localization(make_toolbox({"z.cpp": "needle"}))
    with pytest.raises(PolicyError, match="EVIDENCE_SOURCE_MISMATCH"):
        core.register_baseline({"stderr": "visible"}, source_tree_sha256="f" * 64)
    for value in (
        {"evaluation_role": "oracle"},
        {"evaluation_role": "independent"},
        {"visibility": "hidden", "data": {}},
        {"hidden": True},
    ):
        with pytest.raises(PolicyError, match="EVIDENCE_NOT_VISIBLE"):
            core.register_baseline(
                value, source_tree_sha256=core.toolbox.workspace.expected_manifest.sha256
            )


def test_binary_files_keep_lower_bound_across_scan_pages(make_toolbox):
    core = Localization(
        make_toolbox({"a.bin": b"\0\xff", "b.cpp": "needle"}),
        limits=LocalizationLimits(scan_files=1),
    )
    rows, pages = drain(core, "needle")
    assert [r["path"] for r in rows] == ["b.cpp"]
    assert pages[-1]["count_is_lower_bound"] and pages[-1]["scan_complete"]


def test_empty_scope_and_literal_case_sensitive_matching(make_toolbox):
    core = Localization(make_toolbox({"a.cpp": "NEEDLE\na.*[b]\naZZb"}))
    assert core.search("needle")["candidates"] == []
    assert core.search("a.*[b]")["candidates"][0]["hit_lines"] == [2]
    assert core.search("needle", "missing")["scan_complete"]


def test_64k_json_output_has_gap_free_pages_for_long_paths(make_toolbox):
    names = [f"{i:03}-" + "/".join(["a" * 240] * 15) + ".cpp" for i in range(30)]
    core = Localization(
        make_toolbox(dict.fromkeys(names, "needle")), limits=LocalizationLimits(page_files=32)
    )
    rows, pages = drain(core, "needle")
    assert [row["path"] for row in rows] == sorted(names)
    assert len(pages) >= 2 and all(len(canonical_json(page)) <= 65536 for page in pages)


def test_real_worktree_edit_and_symlink_escape(repository, tmp_path):
    with Worktree(repository, tmp_path / "work", "HEAD") as work:
        toolbox = Toolbox(
            work, ("src/stats.cpp",), None, readable={"src/stats.cpp", "src/stats.hpp"}
        )
        core = Localization(toolbox, "feedback")
        observe(core, "/src/src/stats.cpp:3:1: error: symbol")
        assert core.search("maximum_sample")["candidates"][0]["path"] == "src/stats.cpp"
        toolbox.edit_file("src/stats.cpp", "maximum_sample", "best_sample")
        assert core.search("best_sample")["fallback_reason"] == "stale_evidence"
        file = work.path / "src/stats.cpp"
        original = file.read_bytes()
        external = tmp_path / "secret.cpp"
        external.write_bytes(original)
        file.unlink()
        file.symlink_to(external)
        try:
            with pytest.raises(SourceChanged, match="Symlink"):
                core.search("best_sample")
            with pytest.raises(SourceChanged, match="Symlink"):
                observe(core, "/src/src/stats.cpp:3: error: bad", "symlink")
        finally:
            file.unlink()
            file.write_bytes(original)


def test_large_visible_feedback_and_dense_search_complete_with_bounded_state(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle\n" * 100000, "z.cpp": "needle\n"})
    core = Localization(toolbox, "feedback")
    text = ("[ FAILED ] " + "x" * 250 + "\n") * 6000 + "/src/z.cpp:1: error: bad\n"
    start = time.perf_counter()
    registration = observe(core, text)
    result = core.search("needle")
    elapsed = time.perf_counter() - start
    assert registration["evidence_count"] == 1
    assert result["candidates"][0]["path"] == "z.cpp"
    assert next(c for c in result["candidates"] if c["path"] == "a.cpp")["match_count"] == 100000
    assert len(canonical_json(core.to_dict())) < 32768
    assert elapsed < 5, f"bounded CPU fixture took {elapsed:.3f}s"


def test_long_path_dense_hit_cursor_stays_bounded(make_toolbox):
    name = "/".join(["a" * 240] * 15) + ".cpp"
    core = Localization(make_toolbox({name: "needle\n" * 12}))
    first = core.search("needle")
    cursor = first["candidates"][0]["hit_lines_next_cursor"]
    assert len(cursor) < 4096
    page = core.search("needle", cursor=cursor)
    assert page["candidates"][0]["hit_lines"] == [9, 10, 11, 12]
    assert page["next_cursor"] is None


def test_parse_limit_retains_bounded_fallback(make_toolbox):
    core = Localization(make_toolbox({"a.cpp": "needle"}), "feedback")
    result = observe(core, "", tests=[{}] * 4097)
    assert result["parse_limited"] and result["evidence_count"] == 0
    assert core.search("needle")["fallback_reason"] == "feedback_parse_limited"


def test_scan_bytes_is_a_strict_configured_limit(make_toolbox):
    core = Localization(
        make_toolbox({"a.cpp": "needle\n" * 100}), limits=LocalizationLimits(scan_bytes=20)
    )
    with pytest.raises(PolicyError, match="SCAN_FILE_EXCEEDS_BUDGET"):
        core.search("needle")
    assert core.toolbox.workspace.reads == []


def test_evidence_hash_checked_beneath_state_checksum(make_toolbox):
    core = Localization(make_toolbox({"a.cpp": "needle"}), "feedback")
    observe(core, "/src/a.cpp:1: error: bad")
    state = core.to_dict()
    state["receipts"][0]["evidence"][0]["line"] = 10
    receipt = state["receipts"][0]
    receipt["record_sha256"] = hashlib.sha256(
        canonical_json({k: v for k, v in receipt.items() if k != "record_sha256"})
    ).hexdigest()
    state["state_sha256"] = hashlib.sha256(
        canonical_json({k: v for k, v in state.items() if k != "state_sha256"})
    ).hexdigest()
    with pytest.raises(PolicyError, match="EVIDENCE_HASH_MISMATCH"):
        Localization(core.toolbox, "feedback", state=state)


def test_receipt_window_and_metrics_survive_restore(make_toolbox):
    core = Localization(make_toolbox({"a.cpp": "needle"}), "feedback")
    for i in range(35):
        observe(core, "/src/a.cpp:1: error: bad", str(i))
    state = core.to_dict()
    assert len(state["receipts"]) == 32 and state["metrics"]["receipts_evicted"] == 3
    restored = Localization(core.toolbox, "feedback", state=state)
    assert restored.to_dict() == state
    assert restored.search("needle")["fallback_reason"] is None


def test_epoch_revert_keeps_prior_feedback_and_cursor_stale(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle", "z.cpp": "needle"})
    core = Localization(toolbox, "feedback", limits=LocalizationLimits(page_files=1))
    observe(core, "/src/z.cpp:1: error: bad")
    first = core.search("needle")
    original_source = toolbox.workspace.expected_manifest.sha256
    for number, value in enumerate((b"needle changed", b"needle"), 1):
        toolbox.workspace.contents["a.cpp"] = value
        toolbox.workspace.refresh()
        core.observe(
            "edit_file",
            {},
            {"ok": True},
            receipt_id=f"edit-{number}",
            source_tree_sha256=toolbox.workspace.expected_manifest.sha256,
        )
    assert toolbox.workspace.expected_manifest.sha256 == original_source
    assert core.to_dict()["source_epoch"] == 2
    result = core.search("needle")
    assert result["fallback_reason"] == "stale_evidence"
    with pytest.raises(PolicyError, match="CURSOR_STALE"):
        core.search("needle", cursor=first["next_cursor"])


def test_restore_across_rebuilt_workspace_path_preserves_source_identity(make_toolbox, tmp_path):
    core = Localization(
        make_toolbox({"a.cpp": "needle", "z.cpp": "needle"}),
        "feedback",
        limits=LocalizationLimits(page_files=1),
    )
    observe(core, "/src/z.cpp:1: error: bad")
    page = core.search("needle")
    state = core.to_dict()
    core.toolbox.workspace.path = tmp_path / "rebuilt"
    core.toolbox.workspace.refresh()
    restored = Localization(core.toolbox, "feedback", state, limits=core.limits)
    assert restored.search("needle", cursor=page["next_cursor"])["candidates"][0]["path"] == "a.cpp"
    assert restored.search("needle")["candidates"][0]["path"] == "z.cpp"


def test_runtime_model_evaluation_direct_and_wrapped_bind_source(make_toolbox):
    from repropatch.tools import model_evaluation

    toolbox = make_toolbox({"a.cpp": "needle", "z.cpp": "needle"})
    source = toolbox.workspace.expected_manifest.sha256
    record = {
        "evaluation_id": "eval-1",
        "evaluation_role": "baseline",
        "source_tree_sha256": source,
        "tests": [],
        "commands": [
            {
                "command_id": "cmd-1",
                "status": "exited",
                "exit_code": 1,
                "stderr": "/src/z.cpp:1: error: bad",
            }
        ],
    }
    baseline = model_evaluation(record)
    core = Localization(toolbox, "feedback")
    result = core.observe(
        "baseline", {}, baseline, receipt_id="baseline", source_tree_sha256=source
    )
    assert result["evidence_count"] == 1
    wrapped = {"ok": True, "data": model_evaluation({**record, "evaluation_role": "agent_check"})}
    result = core.observe(
        "run_command", {"name": "verify"}, wrapped, receipt_id="tool-1", source_tree_sha256=source
    )
    assert result["evidence_count"] == 1
    assert core.search("needle")["candidates"][0]["path"] == "z.cpp"
    assert (
        core.to_dict()["receipts"][0]["evidence"][0]["fragment_pointer"]
        == "/failed_commands/0/stderr"
    )
    assert (
        core.to_dict()["receipts"][1]["evidence"][0]["fragment_pointer"]
        == "/data/failed_commands/0/stderr"
    )


def fixed_feedback(core):
    from repropatch.localization import FEEDBACK_LOG_NAMES, FEEDBACK_SCHEMA

    value = {
        "schema": FEEDBACK_SCHEMA,
        "instance_id": "fixture",
        "prepared_commit": "a" * 40,
        "source_tree_sha256": core.toolbox.workspace.expected_manifest.sha256,
        "logs": [
            {"name": name, "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest()}
            for name, text in zip(
                FEEDBACK_LOG_NAMES,
                (
                    "configure completed",
                    "/src/z.cpp:1: error: visible compiler error\n",
                    "[ RUN ] Suite.Failure\n/src/z.cpp:2: Failure\n[ FAILED ] Suite.Failure\n",
                ),
                strict=True,
            )
        ],
    }
    value["feedback_sha256"] = hashlib.sha256(canonical_json(value)).hexdigest()
    return value


def resign_feedback(value):
    value["feedback_sha256"] = hashlib.sha256(
        canonical_json({key: item for key, item in value.items() if key != "feedback_sha256"})
    ).hexdigest()


def test_trusted_fixed_baseline_logs_are_parsed_with_traceable_hashes(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle", "z.cpp": "needle\nneedle"})
    bounded, feedback = Localization(toolbox), Localization(toolbox, "feedback")
    value = fixed_feedback(feedback)
    before = deepcopy(value)
    for core in (bounded, feedback):
        result = core.observe(
            "baseline",
            {},
            value,
            receipt_id="baseline",
            source_tree_sha256=value["source_tree_sha256"],
        )
        assert result["evidence_count"] == 2
    assert value == before
    a, c = bounded.search("needle"), feedback.search("needle")
    assert a["candidate_pool_sha256"] == c["candidate_pool_sha256"]
    assert c["candidates"][0]["path"] == "z.cpp"
    records = feedback.to_dict()["receipts"][0]["evidence"]
    assert [e["fragment_pointer"] for e in records] == ["/logs/1/text", "/logs/2/text"]
    assert records[0]["metadata"]["log_sha256"] == value["logs"][1]["sha256"]
    assert records[0]["metadata"]["feedback_sha256"] == value["feedback_sha256"]


@pytest.mark.parametrize(
    "name,schema", [("run_command", True), ("run_shell", True), ("baseline", False)]
)
def test_logs_text_is_closed_outside_registered_baseline_schema(make_toolbox, name, schema):
    core = Localization(make_toolbox({"z.cpp": "needle\nneedle"}), "feedback")
    value = fixed_feedback(core)
    if not schema:
        value["schema"] = "unknown"
    result = core.observe(
        name, {}, value, receipt_id="r", source_tree_sha256=value["source_tree_sha256"]
    )
    assert result["evidence_count"] == 0
    assert core.toolbox.workspace.reads == []


@pytest.mark.parametrize(
    "change", ["path", "hash", "payload_hash", "extra_field", "duplicate_name", "missing_log"]
)
def test_fixed_feedback_rejects_unrecognized_paths_and_tampering(make_toolbox, change):
    core = Localization(make_toolbox({"z.cpp": "needle\nneedle"}), "feedback")
    value = fixed_feedback(core)
    if change == "path":
        value["logs"][0]["name"] = "../baseline-configure.log"
    elif change == "hash":
        value["logs"][0]["sha256"] = "f" * 64
    elif change == "extra_field":
        value["logs"][0]["path"] = "/hidden/log"
    elif change == "duplicate_name":
        value["logs"][1]["name"] = value["logs"][0]["name"]
    elif change == "missing_log":
        value["logs"].pop()
    if change == "payload_hash":
        value["feedback_sha256"] = "f" * 64
    else:
        resign_feedback(value)
    with pytest.raises(PolicyError, match="FEEDBACK_"):
        core.register_baseline(value, source_tree_sha256=value["source_tree_sha256"])
    assert not core.to_dict()["receipts"] and not core.toolbox.workspace.reads


@pytest.mark.parametrize("output_bytes", [65536, 22528, 16384])
def test_long_path_common_pagination_scans_once_in_both_arms(make_toolbox, output_bytes):
    names = [f"{i:02}-" + "/".join(["a" * 240] * 15) + ".cpp" for i in range(12)]
    toolbox = make_toolbox(dict.fromkeys(names, "needle\nother\nother\n"))
    assert all((toolbox.workspace.path / name).is_file() and len(name) > 3600 for name in names)
    feedback = "\n".join(
        f"/src/{name}:{line}: error: diagnostic {j}"
        for i, name in enumerate(names)
        for j, line in enumerate((2, 3) if i < 6 else (1, 2))
    )
    records = []
    for mode in ("bounded", "feedback"):
        core = Localization(toolbox, mode, limits=LocalizationLimits(output_bytes=output_bytes))
        assert observe(core, feedback)["evidence_count"] == 24
        before = len(toolbox.workspace.reads)
        rows, pages = drain(core, "needle")
        assert len(toolbox.workspace.reads) - before == 12
        assert sorted(r["path"] for r in rows) == sorted(names)
        assert all(len(canonical_json(p)) <= output_bytes for p in pages)
        assert all(p["cache"]["hit"] and p["scan"]["bytes"] == 0 for p in pages[1:])
        assert all(p["scan"]["validation_read_bytes"] == 0 for p in pages)
        metrics = core.to_dict()["metrics"]
        assert metrics["cache_builds"] == 1
        assert metrics["source_read_bytes"] == sum(
            len(v) for v in toolbox.workspace.contents.values()
        )
        records.append((rows, pages, metrics))
    b_rows, b_pages, b_metrics = records[0]
    c_rows, c_pages, c_metrics = records[1]
    assert [r["path"] for r in b_rows] != [r["path"] for r in c_rows]
    assert [len(p["candidates"]) for p in b_pages] == [len(p["candidates"]) for p in c_pages]
    assert [p["common_page_files"] for p in b_pages] == [p["common_page_files"] for p in c_pages]
    for key in ("scan_bytes", "source_read_bytes", "metadata_checks", "cache_hits", "cache_builds"):
        assert b_metrics[key] == c_metrics[key]
    print(
        f"long-path output={output_bytes}: B/C pages={len(b_pages)}/{len(c_pages)}, "
        f"source_bytes={b_metrics['source_read_bytes']}/{c_metrics['source_read_bytes']}"
    )


@pytest.mark.parametrize("matches", [4000, 8000, 100000])
def test_dense_hit_pagination_linear_physical_source_cost(make_toolbox, matches):
    data = "needle\n" * matches
    toolbox = make_toolbox({"dense.cpp": data})
    core = Localization(toolbox, limits=LocalizationLimits(output_bytes=22528))
    started = time.perf_counter()
    first = core.search("needle")
    seen = first["candidates"][0]["hit_lines"][:]
    cursor = first["candidates"][0]["hit_lines_next_cursor"]
    pages = 1
    while cursor:
        page = core.search("needle", cursor=cursor)
        assert page["scan"]["bytes"] == page["scan"]["source_read_bytes"] == 0
        assert page["scan"]["validation_read_bytes"] == 0
        assert page["cache"]["hit"] and page["scan"]["metadata_checks"] > 0
        seen.extend(page["candidates"][0]["hit_lines"])
        cursor = page["next_cursor"]
        pages += 1
    elapsed = time.perf_counter() - started
    assert seen == list(range(1, matches + 1))
    assert toolbox.workspace.reads == ["dense.cpp"]
    metrics = core.to_dict()["metrics"]
    assert metrics["scan_bytes"] == metrics["source_read_bytes"] == len(data)
    assert metrics["cache_builds"] == metrics["scan_files"] == 1
    assert metrics["cache_hits"] == pages - 1
    assert metrics["validation_read_bytes"] == 0
    assert metrics["metadata_checks"] <= pages * 2 + 4
    print(
        f"dense matches={matches}: pages={pages}, source_bytes={len(data)}, "
        f"reads={len(toolbox.workspace.reads)}, seconds={elapsed:.3f}"
    )


def test_resume_rebuilds_hit_cache_once_then_uses_indices(make_toolbox):
    toolbox = make_toolbox({"dense.cpp": "needle\n" * 40})
    core = Localization(toolbox)
    first = core.search("needle")
    state = core.to_dict()
    assert "cache" not in state
    restored = Localization(toolbox, state=state)
    page = restored.search("needle", cursor=first["candidates"][0]["hit_lines_next_cursor"])
    assert page["cache"]["builds"] == 1 and page["scan"]["bytes"] == 280
    next_page = restored.search("needle", cursor=page["next_cursor"])
    assert next_page["cache"]["hit"] and next_page["scan"]["bytes"] == 0
    assert next_page["candidates"][0]["hit_lines"] == list(range(17, 25))
    assert len(toolbox.workspace.reads) == 2
    assert restored.to_dict()["metrics"]["cache_builds"] == 2


def test_cache_validation_never_reopens_source(make_toolbox, monkeypatch):
    toolbox = make_toolbox({"dense.cpp": "needle\n" * 16})
    core = Localization(toolbox)
    first = core.search("needle")

    def unexpected_read(*args):
        pytest.fail("cached pagination reread source content")

    monkeypatch.setattr(toolbox, "_text", unexpected_read)
    monkeypatch.setattr(toolbox.workspace, "read_file", unexpected_read)
    page = core.search("needle", cursor=first["candidates"][0]["hit_lines_next_cursor"])
    assert page["candidates"][0]["hit_lines"] == list(range(9, 17))
    assert page["scan"]["validation_read_bytes"] == 0


def test_direct_core_detects_source_aba_from_ctime_without_manifest_update(make_toolbox):
    import os

    toolbox = make_toolbox({"a.cpp": "needle\n" * 16})
    core = Localization(toolbox, "feedback")
    observe(core, "/src/a.cpp:1: error: visible")
    first = core.search("needle")
    cursor = first["candidates"][0]["hit_lines_next_cursor"]
    path = toolbox.workspace.path / "a.cpp"
    before = path.stat()
    original = path.read_bytes()
    path.write_bytes(b"x" * len(original))
    path.write_bytes(original)
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    with pytest.raises(SourceChanged):
        core.search("needle", cursor=cursor)
    assert core.to_dict()["source_epoch"] == 1
    assert core.search("needle")["fallback_reason"] == "stale_evidence"
    with pytest.raises(PolicyError, match="CURSOR_STALE"):
        core.search("needle", cursor=cursor)


def test_public_track_source_invalidates_aba_without_registering_evidence(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle\n" * 16})
    core = Localization(toolbox)
    first = core.search("needle")
    assert core._cache
    for value in (b"changed", b"needle\n" * 16):
        toolbox.workspace.contents["a.cpp"] = value
        toolbox.workspace.refresh()
        assert core.track_source() == toolbox.workspace.expected_manifest.sha256
        assert not core._cache and core._cache_bytes == 0
    assert core.to_dict()["source_epoch"] == 2 and core.to_dict()["receipts"] == []
    with pytest.raises(PolicyError, match="CURSOR_STALE"):
        core.search("needle", cursor=first["candidates"][0]["hit_lines_next_cursor"])


def test_cache_lru_is_bounded_across_queries(make_toolbox):
    from repropatch.localization import MAX_CACHE_BYTES, MAX_CACHE_CHUNKS

    core = Localization(make_toolbox({"a.cpp": "needle"}))
    for i in range(MAX_CACHE_CHUNKS + 2):
        core.search("needle" + str(i))
        assert len(core._cache) <= MAX_CACHE_CHUNKS
        assert core._cache_bytes <= MAX_CACHE_BYTES
    assert core.to_dict()["metrics"]["cache_evictions"] == 2


def test_output_limit_is_bound_into_policy_and_cursor(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle"})
    core = Localization(toolbox, limits=LocalizationLimits(output_bytes=22528))
    with pytest.raises(PolicyError, match="STATE_INVALID"):
        Localization(toolbox, state=core.to_dict(), limits=LocalizationLimits(output_bytes=65536))
    for bad in (0, 16383, 65537, True, 22528.0):
        with pytest.raises(PolicyError, match="INVALID_LIMIT_OUTPUT_BYTES"):
            LocalizationLimits(output_bytes=bad)


def test_deferred_observation_keeps_prepared_epoch_stale_after_aba(make_toolbox):
    toolbox = make_toolbox({"a.cpp": "needle"})
    core = Localization(toolbox, "feedback")
    prepared_source = core.track_source()
    prepared_epoch = core.to_dict()["source_epoch"]
    for value in (b"changed", b"needle"):
        toolbox.workspace.contents["a.cpp"] = value
        toolbox.workspace.refresh()
        core.track_source()
    core.observe(
        "run_command",
        {"name": "reproduce"},
        {"ok": True, "data": {"stderr": "/src/a.cpp:1: error: prepared earlier"}},
        receipt_id="deferred",
        source_tree_sha256=prepared_source,
        source_epoch=prepared_epoch,
    )
    assert core.to_dict()["receipts"][0]["source_epoch"] == 0
    assert core.to_dict()["source_epoch"] == 2
    assert core.search("needle")["fallback_reason"] == "stale_evidence"
    with pytest.raises(PolicyError, match="EVIDENCE_EPOCH_INVALID"):
        core.observe(
            "baseline", {}, {}, receipt_id="bad", source_tree_sha256=prepared_source, source_epoch=3
        )
