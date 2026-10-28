"""固定 C++ 数据源、规范记录和项目内历史曝光索引。"""

import argparse
import hashlib
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE_REVISION = "3638632e8153a10ca422c1022bed79023084b5c9"
LIVE_FILE = "data/cpp-00000-of-00001.parquet"
LIVE_SHA256 = "8448db887817b63e4c0c284ca99de1ccda15023f48e5b2234a4084466e0768ae"
MULTISWE_REVISION = "56ff018c04a38e27ada1e9d0a6d5839a51f88f0d"
CPP_SUFFIXES = {".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hh", ".hxx"}
PRODUCTION_AREAS = {
    "fmtlib/fmt": ("include/", "src/", "fmt/"),
    "nlohmann/json": ("include/", "single_include/", "src/"),
    "catchorg/Catch2": ("src/", "include/", "single_include/", "single_include/catch2/"),
    "simdjson/simdjson": ("include/", "src/", "singleheader/"),
    "duckdb/duckdb": ("src/", "extension/"),
    "shader-slang/slang": ("source/", "include/", "prelude/"),
    "stephenberry/glaze": ("include/",),
    "luau-lang/luau": ("Analysis/", "Ast/", "CodeGen/", "Common/", "Compiler/", "Config/", "VM/"),
    "open-source-parsers/jsoncpp": ("include/", "src/lib_json/"),
    "pocoproject/poco": (
        "Foundation/",
        "Crypto/",
        "Net/",
        "NetSSL_OpenSSL/",
        "Util/",
        "XML/",
        "JSON/",
        "Data/",
    ),
    "ninja-build/ninja": ("src/",),
    "dragonflydb/dragonfly": ("src/",),
}


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            result.update(chunk)
    return result.hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def download(url, path, expected):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".download")
        with urllib.request.urlopen(url, timeout=90) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if digest(temporary) != expected:
            raise ValueError("CPP_SOURCE_SHA256_MISMATCH")
        temporary.replace(path)
    if digest(path) != expected:
        raise ValueError("CPP_SOURCE_SHA256_MISMATCH")


def normalize_live(row):
    org, repository = row["repo"].split("/")
    f2p, p2p = row["FAIL_TO_PASS"], row["PASS_TO_PASS"]
    if len(set(f2p + p2p)) != len(f2p + p2p):
        raise ValueError("CPP_SOURCE_TEST_IDENTITIES_DUPLICATED")
    return {
        "instance_id": row["instance_id"],
        "org": org,
        "repo": repository,
        "number": int(row["pull_number"]),
        "base": {"sha": row["base_commit"]},
        "fix_patch": row["patch"],
        "test_patch": row["test_patch"],
        "resolved_issues": [{"title": "", "body": row["problem_statement"]}],
        "issue_numbers": row["issue_numbers"],
        "dataset": "SWE-bench-Live/MultiLang",
        "dataset_revision": LIVE_REVISION,
        "declared_f2p": list(f2p),
        "declared_p2p": list(p2p),
        "fix_patch_result": {"passed_tests": sorted(f2p + p2p)},
        "native_log_parser": row["log_parser"],
        "native_test_commands": row["test_cmds"],
        "native_print_commands": row["print_cmds"],
        "source_docker_image": row["docker_image"],
    }


def load_records(directory):
    identity = json.loads((directory / "source-manifest.json").read_text())
    if identity.get("schema") != "repropatch.cpp-sources.v1":
        raise ValueError("CPP_SOURCE_MANIFEST_INVALID")
    records = []
    for source in identity["normalized_files"]:
        path = directory / source["path"]
        if path.resolve().parent != directory.resolve() or digest(path) != source["sha256"]:
            raise ValueError("CPP_NORMALIZED_SOURCE_SHA256_MISMATCH")
        records.extend(json.loads(line) for line in path.read_text().splitlines() if line.strip())
    if len({row["instance_id"] for row in records}) != len(records):
        raise ValueError("CPP_SOURCE_INSTANCES_DUPLICATED")
    return records


def patch_sections(patch):
    chunks = patch.split("diff --git ")
    if chunks[0].strip():
        raise ValueError("CPP_REFERENCE_PATCH_LAYOUT")
    for chunk in chunks[1:]:
        match = re.match(r"a/(\S+) b/(\S+)\n", chunk)
        if match is None or match[1] != match[2]:
            raise ValueError("CPP_REFERENCE_TREE_REVIEW_REQUIRED")
        yield match[1], "diff --git " + chunk


def production_path(record, name):
    repo = record["org"] + "/" + record["repo"]
    path = Path(name)
    return (
        name.startswith(PRODUCTION_AREAS.get(repo, ()))
        and path.suffix in CPP_SUFFIXES
        and not set(path.parts)
        & {"test", "tests", "testsuite", "sample", "samples", "benchmark", "benchmarks", "fuzzer"}
        and not re.search(r"(?:_test|_unittest|_bench)\.[^.]+$", name)
    )


def production_reference(record):
    selected, omitted = [], []
    for name, section in patch_sections(record["fix_patch"]):
        if production_path(record, name):
            if re.search(
                r"(?m)^(?:new file mode|deleted file mode|old mode|new mode|GIT binary patch)",
                section,
            ):
                raise ValueError("CPP_REFERENCE_TREE_REVIEW_REQUIRED")
            selected.append(section)
        else:
            omitted.append(name)
    if not selected:
        raise ValueError("NO_PRODUCTION_CPP_REPAIR")
    return "".join(selected), sorted(omitted)


def history_index():
    """递归检查已归档实验摘要，记录实际模型尝试的实例身份。"""
    exposed, sources = {}, {}

    def walk(value, pointer, source):
        if isinstance(value, dict):
            usage = value.get("usage") or value.get("worker_usage") or {}
            if isinstance(value.get("score"), dict):
                usage = value["score"].get("worker_usage") or usage
            issued = (
                usage.get("issued_requests", usage.get("requests", 0))
                if isinstance(usage, dict)
                else 0
            )
            has_attempt = (
                isinstance(issued, int)
                and issued > 0
                or value.get("prior_model_attempts") == "RECORDED"
                or bool(value.get("attempt_id") and value.get("arm") and value.get("score"))
            )
            if has_attempt:
                identity = value.get("instance_id") or value.get("task_id")
                if identity:
                    exposed.setdefault(identity.lower().replace("__", "-"), []).append(
                        {"file": source, "pointer": pointer}
                    )
            for key, child in value.items():
                walk(child, pointer + "/" + str(key), source)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, pointer + "/" + str(index), source)

    for path in sorted((ROOT / "benchmarks").rglob("*.json")):
        if "cross-repo" in path.parts:
            continue
        try:
            value = json.loads(path.read_text())
        except (ValueError, UnicodeError):
            continue
        relative = path.relative_to(ROOT).as_posix()
        sources[relative] = digest(path)
        walk(value, "", relative)
    return {"source_files": sources, "exposed_instances": exposed}


def build_index(records, history):
    reviews = []
    for record in records:
        repo = record["org"] + "/" + record["repo"]
        issues = record.get("issue_numbers") or [
            str(issue.get("number", "")) for issue in record.get("resolved_issues", [])
        ]
        review = {
            "instance_id": record["instance_id"],
            "repository": repo,
            "base_commit": record["base"]["sha"],
            "issue_numbers": issues,
            "description": "\n".join(
                (issue.get("title") or "") + "\n" + (issue.get("body") or "")
                for issue in record["resolved_issues"]
            ).strip(),
            "record_sha256": hashlib.sha256(encoded(record)).hexdigest(),
            "test_patch_sha256": hashlib.sha256(record["test_patch"].encode()).hexdigest(),
            "reference_patch_sha256": hashlib.sha256(record["fix_patch"].encode()).hexdigest(),
            "dataset": record.get("dataset", "ByteDance-Seed/Multi-SWE-bench"),
            "dataset_revision": record.get("dataset_revision", MULTISWE_REVISION),
            "historical_model_evidence": history["exposed_instances"].get(
                record["instance_id"].lower().replace("__", "-"), []
            ),
            "qualification_status": "PENDING",
            "model_requests": 0,
        }
        try:
            patch, omitted = production_reference(record)
            review.update(
                production_cpp_paths=[name for name, _ in patch_sections(patch)],
                production_reference_sha256=hashlib.sha256(patch.encode()).hexdigest(),
                omitted_reference_paths=omitted,
                scope_status="CPP_REFERENCE_REQUIRES_DYNAMIC_CONFIRMATION",
            )
        except ValueError as error:
            review.update(scope_status=str(error), qualification_status="STATIC_SCOPE_REJECTED")
        review["semantic_identity"] = hashlib.sha256(
            encoded({"repo": repo, "issues": sorted(issues), "base": record["base"]["sha"]})
        ).hexdigest()
        reviews.append(review)
    return {
        "schema": "repropatch.cpp-candidate-index.v1",
        "model_requests": 0,
        "counts": dict(Counter(row["repository"] for row in reviews)),
        "candidates": reviews,
    }


def prepare(output, index):
    import pyarrow.parquet as parquet

    output.mkdir(parents=True, exist_ok=True)
    live = output / "cpp-00000-of-00001.parquet"
    download(
        f"https://huggingface.co/datasets/SWE-bench-Live/MultiLang/resolve/{LIVE_REVISION}/{LIVE_FILE}",
        live,
        LIVE_SHA256,
    )
    rows = [normalize_live(row) for row in parquet.read_table(live).to_pylist()]
    if len(rows) != 142:
        raise ValueError("CPP_LIVE_RECORD_COUNT_CHANGED")
    normalized = output / "multilang-normalized.jsonl"
    normalized.write_bytes(b"\n".join(encoded(row) for row in rows) + b"\n")
    files = [
        {"path": normalized.name, "sha256": digest(normalized), "bytes": normalized.stat().st_size}
    ]
    coverage = json.loads((ROOT / "benchmarks/coverage.json").read_text())
    for entry in coverage["source_files"]:
        path = output / entry["path"]
        download(
            f"https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench/resolve/{MULTISWE_REVISION}/cpp/{entry['path']}",
            path,
            entry["sha256"],
        )
        files.append({"path": path.name, "sha256": digest(path), "bytes": path.stat().st_size})
    save(
        output / "source-manifest.json",
        {
            "schema": "repropatch.cpp-sources.v1",
            "model_requests": 0,
            "live_parquet": {
                "dataset": "SWE-bench-Live/MultiLang",
                "revision": LIVE_REVISION,
                "path": LIVE_FILE,
                "sha256": LIVE_SHA256,
                "bytes": live.stat().st_size,
            },
            "multiswe_revision": MULTISWE_REVISION,
            "normalized_files": files,
        },
    )
    history = history_index()
    save(index.parent / "history-snapshot.json", history)
    save(index, build_index(load_records(output), history))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.output, args.index)


if __name__ == "__main__":
    main()
