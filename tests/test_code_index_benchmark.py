"""Focused checks for independent scoring, freezing and retained benchmark evidence."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/benchmark_code_index.py"
SPEC = importlib.util.spec_from_file_location("code_index_benchmark", SCRIPT)
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)
ROOT = SCRIPT.parents[1] / "benchmarks/code-index-20261106"


def test_utf8_return_bytes_and_no_container_false_positive():
    gold = {
        "path": "a.h",
        "symbol": "target",
        "kind": "function_definition",
        "line": 2,
        "anchor": "void target()",
    }
    response = {
        "matches": [
            {
                "path": "a.h",
                "symbol": "container",
                "kind": "class_specifier",
                "line": 1,
                "end_line": 4,
                "text": "class X { void target(); }; // \u4e2d",
            }
        ]
    }
    assert not BENCH.covered("definitions", response, gold)
    row = BENCH.response_row("definitions", response, gold)
    raw = json.dumps(response, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert row["utf8_return_bytes"] == len(raw.encode("utf-8"))
    assert row["utf8_return_bytes"] > len(raw)


def test_search_requires_gold_anchor_line():
    gold = {"path": "a.h", "symbol": "target", "line": 2, "anchor": "void target()"}
    response = {"matches": [{"path": "a.h", "line": 1, "text": "// void target()"}]}
    assert not BENCH.covered("search_code", response, gold)
    response["matches"][0].update(line=2, text="void target() {}")
    assert BENCH.covered("search_code", response, gold)


def test_ambiguous_gold_anchor_is_rejected():
    entries = {p: b"" for p in BENCH.FILES}
    with pytest.raises(ValueError, match="unique"):
        BENCH.freeze_gold(entries)


def test_retained_results_and_invalidation():
    protocol = json.loads((ROOT / "protocol.json").read_text())
    samples = json.loads((ROOT / "timings.json").read_text())
    rows = json.loads((ROOT / "queries.json").read_text())
    invalidation = json.loads((ROOT / "invalidation.json").read_text())
    assert protocol["public_commit"] == BENCH.PUBLIC_COMMIT
    assert len(protocol["gold"]) == 12
    assert len(samples) == 2 * protocol["repeats"] >= 10
    assert len(rows) == 24
    for index in range(0, len(samples), 2):
        cold, hot = samples[index : index + 2]
        assert cold["parse_delta"] == 3 and cold["cache_hit_delta"] == 0
        assert hot["parse_delta"] == 0 and hot["cache_hit_delta"] == 3
        assert cold["response"] == hot["response"]
    for name, expected in protocol["archives"].items():
        assert BENCH.digest((ROOT / name).read_bytes()) == expected
    for name, expected in protocol["fmt_files"].items():
        assert BENCH.digest((ROOT / "inputs/fmt" / name).read_bytes()) == expected
    assert invalidation["passed"]
    assert invalidation["parse_delta"] == 1
    assert invalidation["cache_hit_delta"] == 2
    assert BENCH.digest((ROOT / "driver.py").read_bytes()) == protocol["driver_sha256"]
    for row in rows:
        target = next(g for g in protocol["gold"] if g["symbol"] == row["symbol"])
        assert row == BENCH.response_row(row["method"], row["response"], target)


def test_replay_rejects_tampered_archive(tmp_path):
    (tmp_path / "protocol.json").write_text(json.dumps({"archives": {"source.tar": "invalid"}}))
    (tmp_path / "source.tar").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        BENCH.replay(tmp_path, tmp_path / "new-output")
    assert not (tmp_path / "new-output").exists()
