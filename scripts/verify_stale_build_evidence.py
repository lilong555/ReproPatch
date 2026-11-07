"""Verify downloaded stale-build evidence without Docker or model requests."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from benchmark_stale_build_evidence import (
    TEST_NAMES,
    require,
    save,
    sha,
    verdict_checks,
    xml_states,
)

from repropatch.artifacts import EvidenceRef
from repropatch.events import read_events
from repropatch.workspace import SourceManifest, source_manifest


def load(path):
    return json.loads(path.read_bytes())


def verify(root):
    protocol = load(root / "protocol.json")
    summary = load(root / "summary.json")
    for name, digest in protocol["source_inventory"].items():
        require(sha((root.parent / name).read_bytes()) == digest, "registered production source")
    require(
        sha((root.parent / "scripts/benchmark_stale_build_evidence.py").read_bytes())
        == protocol["script_sha256"],
        "registered measurement script",
    )
    require(
        load(root.parent / "image.json")[0]["Id"] == protocol["image"]["image_id"],
        "registered Docker image",
    )
    rows = []
    for repeat in range(1, protocol["registered_repeats"] + 1):
        directory = root / f"repeat-{repeat}"
        row = load(directory / "result.json")
        require(row["repeat"] == repeat, "repeat identity")
        report = load(directory / "production-report.json")
        artifact = directory / "runs" / report["run_id"]
        require(artifact.is_dir(), "production artifact directory")
        source = source_manifest(directory / "exploration-source")
        saved_source = SourceManifest.from_dict(load(directory / "final-source-manifest.json"))
        require(source == saved_source, "final source contents and modes")
        candidate = report["candidate"]
        manifest = SourceManifest.from_dict(
            json.loads(EvidenceRef(**candidate["manifest"]).read(artifact, limit=8 * 1024 * 1024))
        )
        require(manifest == source, "production replayed source")
        patch = EvidenceRef(**candidate["patch"]).read(artifact, limit=8 * 1024 * 1024)
        require(patch == (directory / "candidate.patch").read_bytes(), "production frozen patch")
        commands = {}
        for name in ("configure", "correct-build", "stale-test", "rebuilt", "rebuilt-test"):
            command = load(directory / f"{name}.json")
            for stream in ("stdout", "stderr"):
                raw = EvidenceRef(**command[stream + "_log"]).read(
                    directory / "exploration-logs", limit=4 * 1024 * 1024
                )
                require(
                    raw.decode("utf-8", errors="replace") == command[stream], "raw command output"
                )
            commands[name] = command
        require(
            commands["configure"]["exit_code"] == commands["correct-build"]["exit_code"] == 0,
            "correct binary build",
        )
        verified_tests = []
        independent = report["independent"]
        for test in independent["tests"]:
            raw = EvidenceRef(**test["result"]).read(artifact, limit=4 * 1024 * 1024)
            cases = list(ET.fromstring(raw).iter("testcase"))
            require(len(cases) == 1 and cases[0].get("name") == test["name"], "cold test identity")
            observed = (
                "failed"
                if cases[0].find("failure") is not None or cases[0].find("error") is not None
                else "skipped"
                if cases[0].find("skipped") is not None
                else "passed"
            )
            require(observed == test["observed_status"], "cold XML observation")
            verified_tests.append(test["name"])
        require(set(verified_tests) == TEST_NAMES, "cold four tests")
        require(
            independent["configure"]["exit_code"] == independent["build"]["exit_code"] == 0,
            "changed source cold compilation",
        )
        require(independent["image_id"] == protocol["image"]["image_id"], "cold image identity")
        require(report["base_commit"] == row["base_commit"], "base commit")
        events = read_events(artifact, report["run_id"])
        require(events.run["outcome"] == report["outcome"], "persisted outcome")
        require(not any(e["type"] == "model_started" for e in events.events), "zero model calls")
        observed = {
            **row,
            "candidate": candidate,
            "independent": independent,
            "outcome": report["outcome"],
            "reason_code": report["reason_code"],
            "final_source_sha256": source.sha256,
            "frozen_patch_sha256": sha(patch),
            "stale_tests": xml_states((directory / "stale.xml").read_bytes()),
            "rebuilt_tests": xml_states((directory / "fresh.xml").read_bytes()),
            "stale_exit_code": commands["stale-test"]["exit_code"],
            "rebuilt_exit_code": commands["rebuilt"]["exit_code"],
            "rebuilt_test_exit_code": commands["rebuilt-test"]["exit_code"],
            "protected_unchanged": all(
                sha((directory / "exploration-source" / name).read_bytes()) == digest
                for name, digest in row["protected_sha256"].items()
            ),
            "old_binary_sha256": sha((directory / "old-stats-test").read_bytes()),
            "stale_binary_sha256": sha((directory / "stale-stats-test").read_bytes()),
            "fresh_binary_sha256": sha((directory / "fresh-stats-test").read_bytes()),
            "cold_xml_verified": True,
            "exploration_container_id": load(directory / "sandbox-owner.json")["container_id"],
            "exploration_cleanup_confirmed": load(directory / "sandbox-owner.json")[
                "cleanup_confirmed"
            ],
        }
        checks = verdict_checks(observed)
        require(all(checks.values()), f"injection evidence checks: {checks}")
        require(row["checks"] == checks, "recorded evidence checks")
        rows.append(
            {
                "repeat": repeat,
                "run_id": report["run_id"],
                "outcome": report["outcome"],
                "reason_code": report["reason_code"],
                "checks": checks,
                "source_tree_sha256": source.sha256,
                "candidate_sha256": sha(patch),
                "persisted_events": len(events.events),
            }
        )
    require(summary["all_evidence_checks"] == len(rows), "summary count")
    return {
        "schema": "repropatch.stale-build-offline-audit.v1",
        "scenario_count": 1,
        "registered_repeats": protocol["registered_repeats"],
        "production_source_files_verified": len(protocol["source_inventory"]),
        "script_sha256_verified": True,
        "image_id_verified": True,
        "verified_repeats": len(rows),
        "new_model_requests": 0,
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.evidence_dir)
    save(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
