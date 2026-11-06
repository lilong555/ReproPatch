"""Deterministic, model-free benchmark of the pinned public code index."""

import argparse
import csv
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
import platform
import statistics
import subprocess
import sys
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path

PUBLIC_COMMIT = "9cf01099206131ba6f984661a97f7aa65ee8b68a"
FMT_COMMIT = "0fc31633e7d53ac895ae0a688b83b7d44f0b0c1f"
FILES = ("include/fmt/args.h", "include/fmt/ostream.h", "include/fmt/os.h")
# Gold is manually selected from source text, independently of parser output.
GOLD = (
    (FILES[0], "dynamic_arg_list", "class_specifier", "class dynamic_arg_list {"),
    (FILES[0], "push", "function_definition", "auto push(const Arg& arg)"),
    (FILES[0], "clear", "function_definition", "void clear() {"),
    (FILES[0], "reserve", "function_definition", "void reserve(size_t new_cap,"),
    (FILES[1], "file_access_tag", "struct_specifier", "struct file_access_tag {};"),
    (FILES[1], "write_buffer", "function_definition", "void write_buffer("),
    (FILES[1], "streamed", "function_definition", "constexpr auto streamed("),
    (FILES[1], "println", "function_definition", "void println(std::ostream&"),
    (FILES[2], "basic_cstring_view", "class_specifier", "class basic_cstring_view {"),
    (FILES[2], "c_str", "function_definition", "auto c_str() const"),
    (FILES[2], "system_category", "function_definition", "inline auto system_category()"),
    (FILES[2], "output_file", "function_definition", "inline auto output_file("),
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args],
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
    )


def archive(path, entries):
    with tarfile.open(path, "w") as bundle:
        for name, raw in sorted(entries.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(raw), 0o644, 0
            bundle.addfile(info, io.BytesIO(raw))


def load_public(source):
    """An isolated package name prevents imports from the editable checkout."""
    name = "_code_index_public"
    init = source / "src/repropatch/__init__.py"
    spec = importlib.util.spec_from_file_location(
        name, init, submodule_search_locations=[str(init.parent)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    semantic = importlib.import_module(name + ".semantic_state")
    tools = importlib.import_module(name + ".tools")
    return semantic.SemanticState, tools.Toolbox


class InputWorkspace:
    """Filesystem adapter only; production Toolbox owns scope and UTF-8 handling."""

    def __init__(self, path):
        self.path = path

    def safe_path(self, name):
        path = (self.path / name).resolve()
        if not path.is_relative_to(self.path.resolve()) or path.is_symlink():
            raise ValueError("Input path escaped the benchmark")
        return path

    def read_file(self, name):
        path = self.safe_path(name)
        return path.read_bytes(), path.stat()


def freeze_gold(entries):
    gold = []
    for path, symbol, kind, anchor in GOLD:
        lines = entries[path].decode("utf-8").splitlines()
        positions = [i for i, line in enumerate(lines, 1) if anchor in line]
        if len(positions) != 1:
            raise ValueError(f"Gold anchor must be unique: {path}: {anchor}")
        gold.append(dict(path=path, symbol=symbol, kind=kind, line=positions[0], anchor=anchor))
    return gold


def covered(method, result, gold):
    for item in result["matches"]:
        if item["path"] != gold["path"]:
            continue
        if method == "search_code":
            if item["line"] == gold["line"] and gold["anchor"] in item["text"]:
                return True
        elif (
            item["symbol"] == gold["symbol"]
            and item["kind"] == gold["kind"]
            and item["line"] <= gold["line"] <= item["end_line"]
        ):
            return True
    return False


def response_row(method, result, gold):
    # Same canonical serialization as the public implementation; pre-envelope bytes.
    raw = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return {
        "symbol": gold["symbol"],
        "method": method,
        "utf8_return_bytes": len(raw),
        "results": len(result["matches"]),
        "target_covered": covered(method, result, gold),
        "truncated": result.get("truncated", result.get("matches_truncated", False)),
        "previews_at_limit": sum(
            len(item["text"]) >= 300
            if method == "search_code"
            else len(item["text"].encode("utf-8")) >= 600
            for item in result["matches"]
        ),
        "next_offset": result.get("next_offset"),
        "parse_notes": result.get("parse_notes", []),
        "response_sha256": digest(raw),
        "response": result,
    }


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def measure(source, root, protocol):
    semantic_type, toolbox_type = load_public(source)
    work = InputWorkspace(root / "inputs/fmt")
    toolbox = toolbox_type(work, (), None, readable=FILES)
    samples = []
    for repeat in range(protocol["repeats"]):
        state = semantic_type(toolbox)
        for condition in ("initial_index", "same_source_cache"):
            before = dict(state.state)
            start = time.perf_counter_ns()
            result = state.query("definitions", "write_buffer")
            elapsed = (time.perf_counter_ns() - start) / 1e9
            sample = {
                "repeat": repeat + 1,
                "condition": condition,
                "wall_seconds": elapsed,
                "parse_delta": state.state["parse_count"] - before["parse_count"],
                "cache_hit_delta": state.state["cache_hits"] - before["cache_hits"],
                "index_seconds": (
                    state.state["index_seconds_total"] - before["index_seconds_total"]
                ),
                "parse_seconds": (
                    state.state["parse_seconds_total"] - before["parse_seconds_total"]
                ),
                "response": result,
                "files": dict(state.state["files"]),
            }
            samples.append(sample)
            write_json(root / f"raw/timing-{repeat + 1}-{condition}.json", sample)
    rows = []
    state = semantic_type(toolbox)
    for gold in protocol["gold"]:
        for method in ("search_code", "definitions"):
            result = (
                toolbox.search_code(gold["symbol"])
                if method == "search_code"
                else state.query("definitions", gold["symbol"])
            )
            row = response_row(method, result, gold)
            rows.append(row)
            write_json(root / f"raw/{gold['symbol']}-{method}.json", row)
    target = next(g for g in protocol["gold"] if g["symbol"] == "file_access_tag")
    path = work.path / target["path"]
    original = path.read_bytes()
    old_hash = state.cache[target["path"]]["sha256"]
    before = dict(state.state)
    changed = original.replace(b"file_access_tag", b"benchmark_file_access_tag")
    path.write_bytes(changed)
    try:
        response = state.query("definitions", "benchmark_file_access_tag")
        after_change = dict(state.state)
        new_hash = state.cache[target["path"]]["sha256"]
        changed_gold = {**target, "symbol": "benchmark_file_access_tag"}
        invalidation = {
            "before_sha256": old_hash,
            "after_sha256": new_hash,
            "expected_after_sha256": digest(changed),
            "mutation": "replace all file_access_tag with benchmark_file_access_tag",
            "parse_delta": after_change["parse_count"] - before["parse_count"],
            "cache_hit_delta": after_change["cache_hits"] - before["cache_hits"],
            "new_definition_covered": covered("definitions", response, changed_gold),
            "stale_definition_records": sum(
                r["symbol"] == target["symbol"]
                for r in state.cache[target["path"]]["records"]
                if r["kind"] == target["kind"]
            ),
            "response": response,
        }
        invalidation["passed"] = (
            old_hash != new_hash == digest(changed)
            and invalidation["parse_delta"] == 1
            and invalidation["cache_hit_delta"] == len(FILES) - 1
            and invalidation["new_definition_covered"]
            and invalidation["stale_definition_records"] == 0
        )
        write_json(root / "invalidation.json", invalidation)
    finally:
        path.write_bytes(original)
    write_json(root / "queries.json", rows)
    write_json(root / "timings.json", samples)
    write_csv(
        root / "queries.csv",
        rows,
        ("symbol", "method", "utf8_return_bytes", "results", "target_covered", "truncated"),
    )
    write_csv(
        root / "timings.csv",
        samples,
        (
            "repeat",
            "condition",
            "wall_seconds",
            "parse_delta",
            "cache_hit_delta",
            "index_seconds",
            "parse_seconds",
        ),
    )
    summary = {"methods": {}, "timing_medians_seconds": {}, "invalidation": invalidation["passed"]}
    for method in ("search_code", "definitions"):
        selected = [r for r in rows if r["method"] == method]
        summary["methods"][method] = {
            "queries": len(selected),
            "utf8_return_bytes": sum(r["utf8_return_bytes"] for r in selected),
            "results": sum(r["results"] for r in selected),
            "targets_covered": sum(r["target_covered"] for r in selected),
            "truncated_queries": sum(r["truncated"] for r in selected),
            "previews_at_limit": sum(r["previews_at_limit"] for r in selected),
            "queries_with_parse_notes": sum(bool(r["parse_notes"]) for r in selected),
        }
    for condition in ("initial_index", "same_source_cache"):
        summary["timing_medians_seconds"][condition] = statistics.median(
            s["wall_seconds"] for s in samples if s["condition"] == condition
        )
    summary["pairwise_equal_responses"] = all(
        samples[i]["response"] == samples[i + 1]["response"] for i in range(0, len(samples), 2)
    )
    summary["restored_input_hashes_match"] = all(
        digest((work.path / p).read_bytes()) == protocol["fmt_files"][p] for p in FILES
    )
    write_json(root / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--fmt-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.repeats < 5:
        parser.error("At least five retained paired repetitions are required")
    args.output.mkdir(parents=True, exist_ok=False)
    tracked = git(args.repo, "ls-tree", "-r", "--name-only", PUBLIC_COMMIT).decode().splitlines()
    public = {}
    for name in tracked:
        if name.startswith("src/repropatch/") or name in ("LICENSE", "pyproject.toml"):
            expected = git(args.repo, "show", f"{PUBLIC_COMMIT}:{name}")
            if (args.source / name).read_bytes() != expected:
                raise ValueError(f"Snapshot differs from fixed public commit: {name}")
            public[name] = expected
    fmt = {name: git(args.fmt_repo, "show", f"{FMT_COMMIT}:{name}") for name in (*FILES, "LICENSE")}
    gold = freeze_gold(fmt)
    for name, raw in fmt.items():
        target = args.output / "inputs/fmt" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    archive(args.output / "fmt-input.tar", fmt)
    archive(args.output / "public-source.tar", public)
    protocol = {
        "frozen_at": datetime.now(UTC).isoformat(),
        "public_commit": PUBLIC_COMMIT,
        "public_repository": "https://github.com/lilong555/ReproPatch",
        "public_license": "Apache-2.0",
        "public_files": {p: digest(v) for p, v in public.items()},
        "fmt_commit": FMT_COMMIT,
        "fmt_repository": "https://github.com/fmtlib/fmt",
        "fmt_license": "MIT",
        "fmt_files": {p: digest(v) for p, v in fmt.items()},
        "archives": {
            p: digest((args.output / p).read_bytes())
            for p in ("fmt-input.tar", "public-source.tar")
        },
        "driver_sha256": digest(Path(__file__).read_bytes()),
        "selection": "Three small optional headers; four manually anchored definitions per file.",
        "gold": gold,
        "repeats": args.repeats,
        "model_calls": 0,
        "query_scope": sorted(FILES),
        "semantics": {
            "search_code": "Case-sensitive literal lines, including comments and uses.",
            "definitions": "Syntactic declaration/definition records; substring in name or text.",
            "coverage": "One anchored gold target per query; no precision/all-definition recall.",
            "bytes": "Canonical UTF-8 JSON return body, before runtime envelope or folding.",
            "timing": "Fresh SemanticState then identical query, same process; all retained.",
            "cache": "In-memory AST cache; each hit still reads and SHA256-hashes the source.",
            "cold": "Empty application index; OS filesystem cache remains uncontrolled.",
            "workspace": "InputWorkspace adapter; production Worktree orchestration excluded.",
            "limits": "Search: 100 rows/300 chars; definitions: 60 records/600 UTF-8 text bytes.",
            "truncation": "Result truncation and text previews reaching their caps reported separately.",
            "claims": "Return volume only; no token, tool-step, task, or model benefit inference.",
        },
        "invalidation": "Rename file_access_tag in one copy; retain cache; expect one reparse.",
    }
    write_json(args.output / "protocol.json", protocol)
    write_json(
        args.output / "environment.json",
        {
            "platform": platform.platform(),
            "python": sys.version,
            "executable": sys.executable,
            "cpu_count": os.cpu_count(),
            "cpu_affinity": sorted(os.sched_getaffinity(0)),
            "packages": {
                p: importlib.metadata.version(p)
                for p in ("tree-sitter", "tree-sitter-cpp", "pytest", "ruff", "PyYAML")
            },
            "source": str(args.source.resolve()),
            "command": sys.argv,
        },
    )
    try:
        print(json.dumps(measure(args.source, args.output, protocol), indent=2))
    except Exception as error:
        write_json(
            args.output / "failure.json",
            {"type": type(error).__name__, "message": str(error)},
        )
        raise


if __name__ == "__main__":
    main()
