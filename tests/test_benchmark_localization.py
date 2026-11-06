"""Offline measurements distinguish candidate paths, source bodies and byte costs."""

import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

from repropatch.localization import Localization
from repropatch.tools import Toolbox

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from benchmark_localization import (
    InputWorkspace,
    aggregate,
    archive_bytes,
    byte_parts,
    canonical,
    drill,
    exposure,
    fixed_stream,
    flatten_fixed,
    format_fixed,
    freeze,
    registered_input,
    replay,
    run_query,
    sha,
    unpack_verified,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTERED = ROOT / "benchmarks/code-index-20261106"


@pytest.fixture
def inputs(tmp_path):
    parent, entries = registered_input(REGISTERED)
    workspace = InputWorkspace(tmp_path / "input", entries)
    toolbox = Toolbox(workspace, (), None, readable=parent["query_scope"])
    return parent, entries, toolbox


def test_pinned_input_gold_and_original_search_response(inputs):
    parent, entries, toolbox = inputs
    assert len(parent["gold"]) == 12
    assert len(parent["query_scope"]) == 3
    responses = [toolbox.search_code(g["symbol"]) for g in parent["gold"]]
    assert sum(len(canonical(r)) for r in responses) == 6419
    assert all(
        exposure(r, g, entries)["target_anchor_body"]
        for r, g in zip(responses, parent["gold"], strict=True)
    )
    assert all(not r["truncated"] for r in responses)


def test_parent_protocol_tampering_is_rejected(tmp_path):
    (tmp_path / "protocol.json").write_text("{}")
    with pytest.raises(ValueError, match="protocol hash"):
        registered_input(tmp_path)


def test_archive_hash_tampering_is_rejected(tmp_path):
    (tmp_path / "protocol.json").write_bytes((REGISTERED / "protocol.json").read_bytes())
    (tmp_path / "fmt-input.tar").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="archive hash"):
        registered_input(tmp_path)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a//b", "a/./b", "a\\b"])
def test_archive_unsafe_paths_rejected(name):
    raw = archive_bytes({name: b"test"})
    with pytest.raises(ValueError, match="Unexpected archive member"):
        unpack_verified(raw, {name: sha(b"test")})


@pytest.mark.parametrize("kind", ["duplicate", "symlink", "missing", "wrong_hash"])
def test_archive_inventory_is_complete_regular_and_unique(kind):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as bundle:
        if kind != "missing":
            for _ in range(2 if kind == "duplicate" else 1):
                item = tarfile.TarInfo("a.cpp")
                if kind == "symlink":
                    item.type, item.linkname = tarfile.SYMTYPE, "/etc/passwd"
                    bundle.addfile(item)
                else:
                    item.size = 1
                    bundle.addfile(item, io.BytesIO(b"x"))
    hashes = {"a.cpp": sha(b"y" if kind == "wrong_hash" else b"x")}
    with pytest.raises(ValueError):
        unpack_verified(stream.getvalue(), hashes)


def test_source_identity_and_mutation_guard(inputs):
    parent, entries, toolbox = inputs
    workspace = toolbox.workspace
    path = parent["query_scope"][0]
    assert workspace.expected_manifest.by_path[path].sha256 == sha(entries[path])
    workspace.safe_path(path).write_text("altered source\n")
    with pytest.raises(ValueError, match="Input source changed"):
        toolbox.search_code("any")


def test_source_symlinks_rejected(inputs, tmp_path):
    parent, _, toolbox = inputs
    path = toolbox.workspace.safe_path(parent["query_scope"][0])
    path.unlink()
    outside = tmp_path / "outside"
    outside.write_text("source")
    path.symlink_to(outside)
    with pytest.raises(ValueError, match="Symlink"):
        toolbox.search_code("source")


def test_byte_partition_accounts_for_escaping_and_unicode():
    value = {"matches": [{"path": "src/a.cpp", "text": 'x = "汉字";\n\t'}], "truncated": False}
    parts = byte_parts(value)
    assert parts["source_text_utf8_bytes"] == len(value["matches"][0]["text"].encode())
    assert parts["path_utf8_bytes"] == len("src/a.cpp")
    assert parts["total_json_bytes"] == (
        parts["source_text_json_payload_bytes"]
        + parts["path_json_payload_bytes"]
        + parts["metadata_and_framing_json_bytes"]
    )
    assert parts["source_text_json_payload_bytes"] > parts["source_text_utf8_bytes"]


def test_summary_is_candidate_only_and_window_scores_actual_text(inputs):
    parent, entries, toolbox = inputs
    gold = parent["gold"][0]
    page = Localization(toolbox).search(gold["symbol"])
    score = exposure(page, gold, entries)
    assert score["target_file_candidate"]
    assert not score["target_anchor_body"] and score["source_lines"] == []
    assert byte_parts(page)["source_text_utf8_bytes"] == 0
    windows = drill(toolbox, [page])
    assert any(exposure(w["response"], gold, entries)["target_anchor_body"] for w in windows)
    assert all(w["arguments"]["max_lines"] == 200 for w in windows)


def test_candidate_or_line_number_alone_never_implies_body_hit(inputs):
    parent, entries, _ = inputs
    gold = parent["gold"][0]
    for text in ("", "invented text", "class"):
        response = {"matches": [{"path": gold["path"], "line": gold["line"], "text": text}]}
        assert not exposure(response, gold, entries)["target_anchor_body"]


def test_drill_is_gold_free_and_keeps_late_anchor_miss(tmp_path):
    entries = {"a.cpp": b"symbol first\n" + b"other\n" * 400 + b"symbol target\n"}
    work = InputWorkspace(tmp_path, entries)
    toolbox = Toolbox(work, (), None)
    page = Localization(toolbox).search("symbol")
    window = drill(toolbox, [page])[0]
    gold = {"path": "a.cpp", "line": 402, "anchor": "symbol target"}
    assert window["arguments"] == {"path": "a.cpp", "start_line": 1, "max_lines": 200}
    assert exposure(window["response"], gold, entries)["target_file_candidate"]
    assert not exposure(window["response"], gold, entries)["target_anchor_body"]


def test_fixed_format_preserves_full_stream_identity_order_and_text(inputs):
    parent, _, toolbox = inputs
    for gold in parent["gold"]:
        records = fixed_stream(toolbox, gold["symbol"])
        flat, grouped = format_fixed(records, False), format_fixed(records, True)
        assert flatten_fixed(flat) == flatten_fixed(grouped) == records
        assert (
            byte_parts(flat)["source_text_json_payload_bytes"]
            == byte_parts(grouped)["source_text_json_payload_bytes"]
        )
        assert [r["text"] for r in records] == [
            r["text"] for r in toolbox.search_code(gold["symbol"])["matches"]
        ]


def test_all_registered_queries_shared_pool_and_fallback(inputs):
    parent, entries, toolbox = inputs
    rows = [run_query(toolbox, gold, entries, 1, i) for i, gold in enumerate(parent["gold"])]
    assert all(all(row["sanity"].values()) for row in rows)
    assert all(row["fixed_candidates"]["baseline_same_match_stream"] for row in rows)
    result = aggregate(rows)
    assert result["methods"]["A_search"]["total_json_bytes"] == 6419
    assert result["methods"]["A_search"]["target_anchor_body_queries"] == 12
    assert result["methods"]["B_summary"]["target_anchor_body_queries"] == 0
    assert result["methods"]["B_summary"]["target_file_candidate_queries"] == 12
    assert result["sanity"]["shared_pool_and_fallback_passed"] == 12


def test_snapshot_run_and_replay_keep_inputs_and_metrics(tmp_path):
    output, repeated = tmp_path / "measured", tmp_path / "replayed"
    freeze(REGISTERED, output, 5, ROOT)
    replay(output, repeated)
    protocol = json.loads((output / "protocol.json").read_bytes())
    assert "src/repropatch/localization.py" in protocol["code_files"]
    assert "src/repropatch/tools.py" in protocol["code_files"]
    assert len(list((output / "raw").glob("*.json"))) == 60
    original = json.loads((output / "summary.json").read_bytes())
    second = json.loads((repeated / "summary.json").read_bytes())
    assert original["model_calls"] == 0
    assert original["sanity"] == second["sanity"]
    assert original["sanity"]["shared_pool_and_fallback_passed"] == 60
    for method in original["methods"]:
        for key in (
            "target_file_candidate_queries",
            "target_anchor_body_queries",
            "source_text_utf8_bytes",
            "path_utf8_bytes",
            "read_bytes",
        ):
            assert original["methods"][method][key] == second["methods"][method][key]
    with pytest.raises(FileExistsError):
        replay(output, repeated)
