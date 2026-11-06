"""Model-free localization microbenchmark on the registered public fmt input."""

import argparse
import hashlib
import io
import json
import os
import platform
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

PARENT_SHA256 = "2a30d24aab5cddd2cc183ec45bf258bbead30a2744d90728366ea936ae6be5a3"
DRIVER = "scripts/benchmark_localization.py"
METHODS = ("A_search", "B_summary", "C_no_evidence")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def archive_bytes(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as bundle:
        for name, raw in sorted(entries.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(raw), 0o644, 0
            bundle.addfile(info, io.BytesIO(raw))
    return output.getvalue()


def unpack_verified(raw, expected):
    """Validate the complete regular-file inventory before writing any member."""
    entries = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as bundle:
        for member in bundle:
            path = PurePosixPath(member.name)
            if (
                not member.isfile()
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in member.name
                or str(path) != member.name
                or member.name not in expected
                or member.name in entries
                or member.size > 16 * 1024 * 1024
            ):
                raise ValueError(f"Unexpected archive member: {member.name}")
            content = bundle.extractfile(member).read()
            if sha(content) != expected[member.name]:
                raise ValueError(f"Archived source hash mismatch: {member.name}")
            entries[member.name] = content
    if set(entries) != set(expected):
        raise ValueError("Incomplete archive inventory")
    return entries


def materialize(root, entries):
    for name, raw in entries.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def registered_input(registered):
    raw = (registered / "protocol.json").read_bytes()
    if sha(raw) != PARENT_SHA256:
        raise ValueError("Registered protocol hash mismatch")
    parent = json.loads(raw)
    bundle = (registered / "fmt-input.tar").read_bytes()
    if sha(bundle) != parent["archives"]["fmt-input.tar"]:
        raise ValueError("Registered fmt archive hash mismatch")
    entries = unpack_verified(bundle, parent["fmt_files"])
    for gold in parent["gold"]:
        lines = entries[gold["path"]].decode().splitlines()
        positions = [n for n, line in enumerate(lines, 1) if gold["anchor"] in line]
        if positions != [gold["line"]]:
            raise ValueError(f"Registered anchor mismatch: {gold['symbol']}")
    return parent, entries


class InputWorkspace:
    """Read-only snapshot adapter with production source identities and I/O counters."""

    def __init__(self, path, entries):
        from repropatch.workspace import SourceFile, SourceManifest

        self.path = path.resolve()
        materialize(self.path, entries)
        self.expected_manifest = SourceManifest(
            tuple(SourceFile(p, sha(raw), len(raw), "100644") for p, raw in sorted(entries.items()))
        )
        self.reads = []

    def files(self):
        return sorted(self.expected_manifest.by_path)

    def safe_path(self, name):
        candidate = self.path / name
        if name not in self.expected_manifest.by_path:
            raise ValueError("Unregistered input path")
        if any(p.is_symlink() for p in (candidate, *candidate.parents)):
            raise ValueError("Symlink in input path")
        if not candidate.resolve().is_relative_to(self.path):
            raise ValueError("Input path escaped snapshot")
        return candidate

    def read_file(self, name):
        path = self.safe_path(name)
        raw = path.read_bytes()
        entry = self.expected_manifest.by_path[name]
        if sha(raw) != entry.sha256 or len(raw) != entry.size_bytes:
            raise ValueError("Input source changed")
        self.reads.append({"path": name, "bytes": len(raw)})
        return raw, path.stat()


def timed(operation, workspace=None):
    offset = len(workspace.reads) if workspace else 0
    wall, cpu = time.perf_counter_ns(), time.process_time_ns()
    value = operation()
    cost = {
        "cpu_ns": time.process_time_ns() - cpu,
        "wall_ns": time.perf_counter_ns() - wall,
    }
    if workspace:
        reads = workspace.reads[offset:]
        cost.update(read_calls=len(reads), read_bytes=sum(r["bytes"] for r in reads))
    return value, cost


def byte_parts(value):
    """Disjoint encoded payload fields plus the remaining JSON framing/metadata."""
    parts = {
        "total_json_bytes": len(canonical(value)),
        "source_text_utf8_bytes": 0,
        "path_utf8_bytes": 0,
        "source_text_json_payload_bytes": 0,
        "path_json_payload_bytes": 0,
    }

    def visit(item):
        if isinstance(item, dict):
            for key, child in item.items():
                field = "source_text" if key == "text" else "path" if key == "path" else None
                if field and isinstance(child, str):
                    parts[field + "_utf8_bytes"] += len(child.encode())
                    parts[field + "_json_payload_bytes"] += len(canonical(child)) - 2
                else:
                    visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    parts["metadata_and_framing_json_bytes"] = (
        parts["total_json_bytes"]
        - parts["source_text_json_payload_bytes"]
        - parts["path_json_payload_bytes"]
    )
    return parts


def exposure(value, gold, entries):
    """Score an anchored definition only when its actual source text was returned."""
    candidates, body_hit, body_lines = [], False, set()
    for item in value.get("matches", []):
        path, number, text = item["path"], item["line"], item["text"]
        candidates.append(path)
        original = entries[path].decode().splitlines()[number - 1]
        if text and original.startswith(text):
            body_lines.add((path, number))
            body_hit |= path == gold["path"] and number == gold["line"] and gold["anchor"] in text
    for item in value.get("candidates", []):
        candidates.append(item["path"])
    if "text" in value and "start_line" in value:
        path = value["path"]
        candidates.append(path)
        original = entries[path].decode().splitlines()
        for number, text in enumerate(value["text"].splitlines(), value["start_line"]):
            if text and 1 <= number <= len(original) and original[number - 1].startswith(text):
                body_lines.add((path, number))
                body_hit |= (
                    path == gold["path"] and number == gold["line"] and gold["anchor"] in text
                )
    ordered = list(dict.fromkeys(candidates))
    return {
        "ordered_candidate_paths": ordered,
        "target_file_candidate": gold["path"] in ordered,
        "target_file_top5": gold["path"] in ordered[:5],
        "target_anchor_body": bool(body_hit),
        "source_lines": [list(pair) for pair in sorted(body_lines)],
    }


def record_response(value, cost, gold, entries):
    return {
        "response": value,
        "response_sha256": sha(canonical(value)),
        "bytes": byte_parts(value),
        "timing": cost,
        "exposure": exposure(value, gold, entries),
    }


def summaries(core, query):
    pages, cursor = [], None
    for _ in range(64):
        page = core.search(query, cursor=cursor)
        pages.append(page)
        cursor = page["next_cursor"]
        if cursor is None:
            return pages
    raise ValueError("Summary pagination exceeded registered safety limit")


def drill(toolbox, pages):
    """One existing 200-line window per returned file; navigation never reads gold."""
    responses, seen = [], set()
    for page in pages:
        for item in page["candidates"]:
            if item["path"] in seen:
                continue
            seen.add(item["path"])
            start = max(1, item["hit_lines"][0] - 20)
            arguments = {"path": item["path"], "start_line": start, "max_lines": 200}
            value, cost = timed(lambda args=arguments: toolbox.read_file(**args), toolbox.workspace)
            responses.append({"arguments": arguments, "response": value, "timing": cost})
    return responses


def fixed_stream(toolbox, query):
    """Separate full literal-match collector; the production baseline is unchanged."""
    records = []
    manifest = toolbox.workspace.expected_manifest
    for path in toolbox._scope("."):
        _, text = toolbox._text(path)
        for number, line in enumerate(text.splitlines(), 1):
            if query in line:
                row = {"path": path, "line": number, "text": line[:300]}
                row["candidate_id"] = sha(canonical([manifest.sha256, query, row]))
                records.append(row)
    return records


def format_fixed(records, grouped):
    if not grouped:
        return {"matches": records}
    files = {}
    for row in records:
        files.setdefault(row["path"], []).append({k: v for k, v in row.items() if k != "path"})
    return {"files": [{"path": path, "matches": matches} for path, matches in files.items()]}


def flatten_fixed(value):
    if "matches" in value:
        return value["matches"]
    return [{"path": f["path"], **r} for f in value["files"] for r in f["matches"]]


def run_query(toolbox, gold, entries, repeat, query_index):
    from repropatch.localization import Localization

    query, rows, outputs = gold["symbol"], {}, {}
    shift = (repeat - 1 + query_index) % len(METHODS)
    order = METHODS[shift:] + METHODS[:shift]
    for method in order:
        if method == "A_search":
            value, cost = timed(lambda: toolbox.search_code(query), toolbox.workspace)
            rows[method] = [record_response(value, cost, gold, entries)]
            outputs[method] = [value]
        else:
            mode = "bounded" if method == "B_summary" else "feedback"
            core, setup = timed(lambda m=mode: Localization(toolbox, m))
            pages, cost = timed(lambda c=core: summaries(c, query), toolbox.workspace)
            rows[method] = [record_response(page, {}, gold, entries) for page in pages]
            outputs[method] = pages
            rows[method][0]["timing"] = cost
            rows[method][0]["setup_timing"] = setup
    windows = drill(toolbox, outputs["B_summary"])
    rows["B_drill"] = [
        {**record_response(r["response"], r["timing"], gold, entries), "arguments": r["arguments"]}
        for r in windows
    ]
    b, c = outputs["B_summary"], outputs["C_no_evidence"]

    def candidates(pages):
        return [x["candidate_id"] for p in pages for x in p["candidates"]]

    sanity = {
        "candidate_ids_and_order_equal": candidates(b) == candidates(c),
        "candidate_pool_hashes_equal": [p["candidate_pool_sha256"] for p in b]
        == [p["candidate_pool_sha256"] for p in c],
        "scan_work_equal": [[p["scan"][k] for k in ("files", "bytes", "skipped_files")] for p in b]
        == [[p["scan"][k] for k in ("files", "bytes", "skipped_files")] for p in c],
        "feedback_fallback": all(p["fallback_reason"] == "no_registered_feedback" for p in c),
    }
    records, generation = timed(lambda: fixed_stream(toolbox, query), toolbox.workspace)
    fixed = {"stream": records, "stream_sha256": sha(canonical(records)), "generation": generation}
    for grouped in (False, True):
        name = "grouped" if grouped else "flat"
        rendered, cost = timed(lambda g=grouped: canonical(format_fixed(records, g)))
        value = json.loads(rendered)
        fixed[name] = {
            "response": value,
            "response_sha256": sha(rendered),
            "bytes": byte_parts(value),
            "format_and_serialize_timing": cost,
        }
    fixed["same_records_order_content"] = (
        flatten_fixed(fixed["flat"]["response"])
        == flatten_fixed(fixed["grouped"]["response"])
        == records
    )
    fixed["baseline_same_match_stream"] = [
        {k: v for k, v in r.items() if k != "candidate_id"} for r in records
    ] == outputs["A_search"][0]["matches"]
    return {
        "query_id": query_index + 1,
        "query": query,
        "scope": ".",
        "repeat": repeat,
        "order": order,
        "gold": gold,
        "methods": rows,
        "fixed_candidates": fixed,
        "sanity": sanity,
    }


def aggregate(rows):
    output = {
        "model_calls": 0,
        "queries": len({r["query_id"] for r in rows}),
        "primary_repeat": 1,
        "methods": {},
        "fixed": {},
    }
    for method in (*METHODS, "B_drill", "B_summary_plus_drill"):
        selected, exposure_rows, timings = [], [], []
        repeat_bytes, setup_times = {}, []
        for row in rows:
            names = ("B_summary", "B_drill") if method == "B_summary_plus_drill" else (method,)
            responses = [r for name in names for r in row["methods"][name]]
            timings.append(
                {k: sum(r["timing"].get(k, 0) for r in responses) for k in ("cpu_ns", "wall_ns")}
            )
            setup_times.append(
                {
                    k: sum(r.get("setup_timing", {}).get(k, 0) for r in responses)
                    for k in ("cpu_ns", "wall_ns")
                }
            )
            repeat_bytes.setdefault(row["repeat"], 0)
            repeat_bytes[row["repeat"]] += sum(r["bytes"]["total_json_bytes"] for r in responses)
            if row["repeat"] == 1:
                selected.extend(responses)
                paths = list(
                    dict.fromkeys(
                        p for r in responses for p in r["exposure"]["ordered_candidate_paths"]
                    )
                )
                exposure_rows.append(
                    {
                        "target_file_candidate": row["gold"]["path"] in paths,
                        "target_file_top5": row["gold"]["path"] in paths[:5],
                        "target_anchor_body": any(
                            r["exposure"]["target_anchor_body"] for r in responses
                        ),
                    }
                )
        totals = {k: sum(r["bytes"][k] for r in selected) for k in selected[0]["bytes"]}
        output["methods"][method] = {
            **totals,
            **{k + "_queries": sum(e[k] for e in exposure_rows) for k in exposure_rows[0]},
            "response_count": len(selected),
            "read_calls": sum(r["timing"].get("read_calls", 0) for r in selected),
            "read_bytes": sum(r["timing"].get("read_bytes", 0) for r in selected),
            "query_wall_ms_median": statistics.median(t["wall_ns"] for t in timings) / 1e6,
            "query_cpu_ms_median": statistics.median(t["cpu_ns"] for t in timings) / 1e6,
            "setup_wall_ms_median": statistics.median(t["wall_ns"] for t in setup_times) / 1e6,
            "setup_cpu_ms_median": statistics.median(t["cpu_ns"] for t in setup_times) / 1e6,
            "repeat_total_json_bytes": repeat_bytes,
        }
    for name in ("flat", "grouped"):
        samples = [r["fixed_candidates"][name] for r in rows]
        primary = [r["fixed_candidates"][name] for r in rows if r["repeat"] == 1]
        output["fixed"][name] = {
            k: sum(r["bytes"][k] for r in primary) for k in primary[0]["bytes"]
        }
        output["fixed"][name].update(
            {
                f"format_{axis}_us_median": statistics.median(
                    r["format_and_serialize_timing"][axis + "_ns"] for r in samples
                )
                / 1000
                for axis in ("wall", "cpu")
            }
        )
    output["fixed"]["generation_wall_ms_median"] = (
        statistics.median(r["fixed_candidates"]["generation"]["wall_ns"] for r in rows) / 1e6
    )
    output["fixed"]["generation_cpu_ms_median"] = (
        statistics.median(r["fixed_candidates"]["generation"]["cpu_ns"] for r in rows) / 1e6
    )
    output["sanity"] = {
        "samples": len(rows),
        "shared_pool_and_fallback_passed": sum(all(r["sanity"].values()) for r in rows),
        "fixed_records_preserved": sum(
            r["fixed_candidates"]["same_records_order_content"] for r in rows
        ),
        "baseline_full_stream_equal": sum(
            r["fixed_candidates"]["baseline_same_match_stream"] for r in rows
        ),
    }
    return output


def run_worker(output):
    from repropatch.localization import LocalizationLimits
    from repropatch.tools import Toolbox

    protocol = json.loads((output / "protocol.json").read_bytes())
    snapshot = Path(__file__).resolve().parents[1]
    for name, expected in protocol["code_files"].items():
        if sha((snapshot / name).read_bytes()) != expected:
            raise ValueError(f"Snapshot code changed: {name}")
    parent, entries = registered_input(output / "registered")
    with tempfile.TemporaryDirectory(prefix="localization-input-") as temp:
        work = InputWorkspace(Path(temp), entries)
        toolbox = Toolbox(work, (), None, readable=parent["query_scope"])
        write_json(output / "source-manifest.json", work.expected_manifest.to_dict())
        write_json(
            output / "environment.json",
            {
                "platform": platform.platform(),
                "python": sys.version,
                "cpu_count": os.cpu_count(),
                "cpu_affinity": sorted(os.sched_getaffinity(0)),
                "localization_limits": asdict(LocalizationLimits()),
                "source_tree_sha256": work.expected_manifest.sha256,
            },
        )
        rows = []
        for repeat in range(1, protocol["repeats"] + 1):
            for index, gold in enumerate(parent["gold"]):
                row = run_query(toolbox, gold, entries, repeat, index)
                rows.append(row)
                write_json(output / f"raw/r{repeat:02}-q{index + 1:02}.json", row)
        for path in parent["query_scope"]:
            work.read_file(path)
    summary = aggregate(rows)
    write_json(output / "summary.json", summary)
    artifacts = {
        p.relative_to(output).as_posix(): sha(p.read_bytes())
        for p in sorted(output.rglob("*.json"))
    }
    write_json(output / "artifact-hashes.json", artifacts)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


def launch(output, entries):
    with tempfile.TemporaryDirectory(prefix="localization-code-") as temp:
        snapshot = Path(temp)
        materialize(snapshot, entries)
        subprocess.run(
            [sys.executable, str(snapshot / DRIVER), "--worker", str(output.resolve())],
            check=True,
            cwd=snapshot,
            env={**os.environ, "PYTHONPATH": str(snapshot / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
        )


def freeze(registered, output, repeats, source):
    if repeats < 5:
        raise ValueError("At least five retained timing repeats are required")
    parent, _ = registered_input(registered)
    names = [DRIVER, "LICENSE", "pyproject.toml"] + [
        p.relative_to(source).as_posix() for p in sorted((source / "src/repropatch").rglob("*.py"))
    ]
    code = {name: (source / name).read_bytes() for name in names}
    if any((source / name).read_bytes() != raw for name, raw in code.items()):
        raise ValueError("Production source changed during snapshot; retry freezing")
    bundle = archive_bytes(code)
    protocol = {
        "schema_version": 1,
        "frozen_at": datetime.now(UTC).isoformat(),
        "parent_protocol_sha256": PARENT_SHA256,
        "fmt_commit": parent["fmt_commit"],
        "fmt_files": parent["fmt_files"],
        "gold": parent["gold"],
        "code_files": {name: sha(raw) for name, raw in code.items()},
        "production_source_tar_sha256": sha(bundle),
        "repeats": repeats,
        "model_calls": 0,
        "query_scope": parent["query_scope"],
        "source_git_head": subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_identity": "Exact file hashes and archive include uncommitted production code.",
        "protocol": {
            "queries": (
                "All 12 preregistered strings, case-sensitive literal; scope is all 3 headers."
            ),
            "baseline": "Current production Toolbox.search_code, unchanged.",
            "bounded": (
                "Localization(mode=bounded).search; drain file/scan pages, at most 64 pages."
            ),
            "drill": (
                "One read_file per candidate, start=max(1, first_hit-20), max_lines=200; gold-free."
            ),
            "fixed": (
                "One full literal match stream, 300-char line previews; identical IDs, text and "
                "order in flat and file-grouped JSON."
            ),
            "scoring": (
                "Registered definition-anchor proxy; candidate paths and actual anchor text "
                "scored separately after navigation."
            ),
            "bytes": (
                "Canonical UTF-8 JSON before runtime envelope; primary repeat 1. Every repeat "
                "retained. Text/path encoded payloads disjoint; remainder metadata/framing."
            ),
            "timing": (
                "perf_counter_ns/process_time_ns; all repeated queries retained. Production "
                "work includes identity checks and adapter I/O; filesystem cache uncontrolled. "
                "Setup and fixed-stream generation separate."
            ),
            "order": "Rotate A/B/C order by (repeat-1+query_index)%3; B drill afterwards.",
            "sanity": (
                "C without feedback, same candidate pool and order, same scan work, "
                "explicit fallback."
            ),
            "scope": (
                "Offline static tool responses; model tokens, localization decisions "
                "and repair outcomes unmeasured."
            ),
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    materialize(
        output / "registered",
        {name: (registered / name).read_bytes() for name in ("protocol.json", "fmt-input.tar")},
    )
    (output / "production-source.tar").write_bytes(bundle)
    write_json(output / "protocol.json", protocol)
    launch(output, code)


def replay(registered, output):
    protocol = json.loads((registered / "protocol.json").read_bytes())
    bundle = (registered / "production-source.tar").read_bytes()
    if sha(bundle) != protocol["production_source_tar_sha256"]:
        raise ValueError("Production archive hash mismatch")
    code = unpack_verified(bundle, protocol["code_files"])
    registered_input(registered / "registered")
    output.mkdir(parents=True, exist_ok=False)
    materialize(
        output,
        {
            name: (registered / name).read_bytes()
            for name in (
                "protocol.json",
                "production-source.tar",
                "registered/protocol.json",
                "registered/fmt-input.tar",
            )
        },
    )
    launch(output, code)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registered", type=Path, default=Path("benchmarks/code-index-20261106"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        run_worker(args.worker)
    elif args.output is None:
        parser.error("--output is required")
    elif args.replay:
        replay(args.replay, args.output)
    else:
        freeze(args.registered, args.output, args.repeats, Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
