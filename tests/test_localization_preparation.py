"""Real Git preparation and cross-job nonempty-patch scoring with private-input isolation."""

import hashlib
import io
import json
import shutil
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import localization_ablation as c
from actions_benchmark import pack
from qualify_cpp_batch import ADAPTER, BUILD_TEST, CONFIGURE, FORMAT, archive


@pytest.fixture
def small_qualification(tmp_path, task, monkeypatch):
    base = tmp_path / "base"
    (base / "src").mkdir(parents=True)
    (base / "test").mkdir()
    (base / "src/stats.cpp").write_text("int result() { return 0; }\n")
    (base / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.16)\n")
    (base / "test/CMakeLists.txt").write_text("  add_test(NAME ${name} COMMAND ${name})\n")
    (base / "test/demo-test.cc").write_text("int test() { return 0; }\n")
    c.preparation_git(base, "init", "--template=", "-q")
    c.preparation_git(base, "add", ".")
    c.preparation_git(base, "commit", "-qm", "base")
    base_commit = c.preparation_git(base, "rev-parse", "HEAD").decode().strip()
    (base / "test/demo-test.cc").write_text("int test() { return 1; }\n")
    test_patch = c.preparation_git(base, "diff").decode()
    (base / "test/demo-test.cc").write_text("int test() { return 0; }\n")
    (base / "src/stats.cpp").write_text("int result() { return 1; }\n")
    fix_patch = c.preparation_git(base, "diff").decode()
    (base / "src/stats.cpp").write_text("int result() { return 0; }\n")
    template = tmp_path / "template"
    archive(base, base_commit, template)
    c.preparation_git(template, "init", "--template=", "-q")
    patch_file = tmp_path / "test.patch"
    patch_file.write_text(test_patch)
    c.preparation_git(template, "apply", str(patch_file))
    (template / "test/CMakeLists.txt").write_text(
        ADAPTER.replace("__CONDITION__", 'name STREQUAL "demo-test"')
    )
    (template / "test/repropatch-build-test.cmake").write_text(BUILD_TEST)
    c.preparation_git(template, "add", "-f", ".")
    c.preparation_git(
        template, "commit", "-qm", "Freeze official regression tests and target-build CTest adapter"
    )
    commit = c.preparation_git(template, "rev-parse", "HEAD").decode().strip()
    raw = task.to_dict()
    raw["id"] = "fmtlib-fmt-2310"
    raw["repository"] = {"path": str(tmp_path / "prepared-repository"), "commit": commit}
    raw["budget"]["model_timeout_seconds"] = 90
    original = c.Task.from_dict(raw, tmp_path)
    p = c.read_protocol()
    raw["budget"].update({**p["execution_budget_override"], "model_timeout_seconds": 600})
    execution = c.Task.from_dict(raw, tmp_path)
    p["task_contracts"]["fmtlib__fmt-2310"] = {
        "prepared_commit": commit,
        "execution_task_sha256": hashlib.sha256(execution.source_bytes).hexdigest(),
    }
    record = {
        "instance_id": "fmtlib__fmt-2310",
        "org": "fmtlib",
        "repo": "fmt",
        "base": {"sha": base_commit},
        "test_patch": test_patch,
        "fix_patch": fix_patch,
        "fix_patch_result": {"passed_tests": ["demo-test", "regression-test"]},
    }
    files = {
        "task.yaml": original.source_bytes,
        "control/test.patch": test_patch.encode(),
        "control/reference.patch": fix_patch.encode(),
        "control/record.json": json.dumps(record).encode(),
        "commands.json": b"[]",
    }
    for phase in ("baseline", "reference", "native-oracle"):
        files[phase + "-inventory.json"] = b"{}"
        files[phase + "-results.xml"] = b"<testsuite/>"
        for stage in ("configure", "build", "ctest", "inventory"):
            files[f"logs/{phase}-{stage}.log"] = (
                b"PUBLIC BASELINE" if phase == "baseline" else b"PRIVATE ORACLE"
            )
    qualification = {
        **FORMAT,
        "instance_id": record["instance_id"],
        "status": "QUALIFIED",
        "backend": "docker",
        "optimization": "O3",
        "upstream_commit": base_commit,
        "prepared_commit": commit,
        "required_tests": ["demo-test", "regression-test"],
        "f2p": ["demo-test"],
        "p2p": ["regression-test"],
        "image_id": original.environment.image,
        "configure": [*CONFIGURE, "-DCMAKE_CXX_FLAGS_RELEASE=-O3 -DNDEBUG"],
        "task_file_sha256": hashlib.sha256(original.source_bytes).hexdigest(),
        "test_patch_sha256": hashlib.sha256(test_patch.encode()).hexdigest(),
    }
    files["result.json"] = json.dumps(qualification).encode()
    manifest = {
        name: {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in files.items()
    }
    with c.Worktree(template, tmp_path / "template-worktree", commit) as work:
        manifest.update(
            {
                "repository/" + f.path: {"size": f.size_bytes, "sha256": f.sha256}
                for f in work.initial_manifest.files
            }
        )
    files["manifest.json"] = json.dumps(manifest).encode()
    prefix = "qualification/fmtlib__fmt-2310/"
    members = {prefix + name: data for name, data in files.items()}
    members["qualification/other/control/reference.patch"] = b"PRIVATE OTHER TASK"
    members["archive-manifest.json"] = json.dumps(
        {
            "files": [
                {"path": name, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in members.items()
            ]
        }
    ).encode()
    path = tmp_path / "qualification.tar.gz"
    with tarfile.open(path, "w:gz") as bundle:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            bundle.addfile(info, io.BytesIO(data))
    monkeypatch.setattr(c.shared, "qualification_archives", lambda protocol: [path])
    monkeypatch.setattr(c, "fetch_public_base", lambda *args: (base, base_commit))
    return SimpleNamespace(
        p=p,
        original=original,
        execution=execution,
        record=record,
        base=base,
        archive=path,
        commit=commit,
        instance=record["instance_id"],
    )


def test_generation_reads_only_current_public_members(small_qualification, tmp_path, monkeypatch):
    from repropatch.localization_runtime import validate_feedback

    fixture = small_qualification
    original = tarfile.TarFile.extractfile
    opened = []

    def guarded(archive, member):
        name = member if isinstance(member, str) else member.name
        assert "reference" not in name and "oracle" not in name and "record.json" not in name
        if name.startswith("qualification/"):
            prefix = "qualification/fmtlib__fmt-2310/"
            assert name.startswith(prefix)
            assert name.removeprefix(prefix) in c.PUBLIC_TASK_FILES | {"manifest.json"}
        opened.append(name)
        return original(archive, member)

    monkeypatch.setattr(tarfile.TarFile, "extractfile", guarded)
    output = tmp_path / "generation"
    actual = c.prepare_public_task(fixture.p, fixture.instance, output)
    tree_hash = c.freeze_base_source(actual, output)
    feedback = c.visible_feedback(fixture.p, fixture.instance, tree_hash)
    assert validate_feedback(feedback, actual, source_tree_sha256=tree_hash) == feedback
    raw_feedback = {**feedback, "instance_id": fixture.instance}
    del raw_feedback["feedback_sha256"]
    raw_feedback["feedback_sha256"] = hashlib.sha256(c.canonical_json(raw_feedback)).hexdigest()
    assert validate_feedback(raw_feedback, actual, source_tree_sha256=tree_hash) == raw_feedback
    assert fixture.instance != actual.id
    assert actual.source_bytes == fixture.execution.source_bytes
    assert (
        c.preparation_git(actual.repository, "rev-parse", "HEAD").decode().strip() == fixture.commit
    )
    assert (actual.repository / ".git").is_dir()
    assert "qualification/fmtlib__fmt-2310/control/test.patch" in opened
    assert not (output / "qualified-contract/result.json").exists()
    assert not list(output.rglob("reference.patch"))


def test_real_public_prepare_worker_entry(small_qualification, tmp_path, monkeypatch):
    from repropatch.localization_runtime import validate_feedback

    fixture = small_qualification
    row = c.trials(fixture.p, "smoke")[0]
    manifest = {
        "protocol": fixture.p,
        "attempts": [row],
        "manifest_sha256": "a" * 64,
        "scope": "smoke",
    }
    monkeypatch.setattr(c, "read_manifest", lambda *args, **kwargs: manifest)
    monkeypatch.setenv("RUNNER_NAME", "local-prepare-fixture")
    monkeypatch.setattr(c, "ROOT", tmp_path)
    monkeypatch.setattr(c, "ensure_image", lambda *args: None)
    output = tmp_path / "worker-entry"
    assert (
        c.prepare(
            SimpleNamespace(
                manifest=tmp_path / "manifest.json",
                protocol=c.PROTOCOL,
                attempt_id=row["attempt_id"],
                scope="smoke",
                output=output,
            )
        )
        == 0
    )
    assert c.load(output / "runner-status.json")["state"] == "PREPARED"
    settings = c.load(output / "prepared/prepared.json")
    task = c.Task.load(Path(settings["task"]))
    feedback = c.load(output / "visible-feedback.json")
    frozen = c.load(output / "prepared-identity.json")
    command = c.worker_command(row, settings, output, fixture.p)
    assert command[command.index("--task") + 1] == settings["task"]
    assert command[command.index("--localization-feedback-file") + 1] == str(
        output / "visible-feedback.json"
    )
    assert task.source_bytes == fixture.execution.source_bytes
    assert validate_feedback(feedback, task, source_tree_sha256=frozen["source_tree_sha256"])
    assert c.LocalUsageLedger(output / "usage.sqlite3").summary()["requests"] == 0


def test_cross_job_nonempty_patch_uses_real_prepared_git(
    small_qualification, tmp_path, monkeypatch
):
    import check_qualified_cpp_candidate as oracle

    fixture = small_qualification
    generation = tmp_path / "attempt"
    prepared = generation / "prepared"
    task = c.prepare_public_task(fixture.p, fixture.instance, prepared)
    tree_hash = c.freeze_base_source(task, prepared)
    c.save(generation / "manifest.json", {"protocol": fixture.p})
    c.save(generation / "trial.json", {"instance_id": fixture.instance})
    c.save(
        generation / "prepared-identity.json",
        {
            "source_tree_sha256": tree_hash,
            "task_sha256": hashlib.sha256(task.source_bytes).hexdigest(),
            "source_base_sha256": c.sha(prepared / "source-base.tar"),
            "source_bundle_sha256": c.sha(prepared / "source-base.bundle"),
        },
    )
    tar = tmp_path / "generation.tar.gz"
    pack(SimpleNamespace(source=generation, output=tar))
    shutil.rmtree(generation)
    shutil.rmtree(task.repository)
    c.unpack(SimpleNamespace(archive=tar, output=generation))
    unrelated = tmp_path / "unrelated-broken-checkout"
    unrelated.mkdir()
    (unrelated / ".git").write_text("gitdir: /missing/repository\n")
    monkeypatch.chdir(unrelated)
    c.restore_scoring_base(generation)
    settings = c.load(prepared / "prepared.json")
    qualification = Path(settings["qualification"])
    repo = qualification.parent / "repository"
    assert (repo / ".git").is_dir()
    assert c.preparation_git(repo, "rev-parse", "HEAD").decode().strip() == fixture.commit
    candidate = tmp_path / "candidate.patch"
    candidate.write_text(fixture.record["fix_patch"])
    monkeypatch.setattr(oracle, "records", lambda *args: [fixture.record])
    calls = []

    class Executor:
        def __init__(self, backend, image, output, *args):
            assert backend == "docker"
            self.configure = [*CONFIGURE, "-DCMAKE_CXX_FLAGS_RELEASE=-O3 -DNDEBUG"]
            self.commands = []
            self.build_root = output / "build"

        def suite(self, source, phase, required):
            assert (source / "src/stats.cpp").read_text() == "int result() { return 1; }\n"
            assert (source / "test/demo-test.cc").read_text() == "int test() { return 1; }\n"
            calls.append(phase)
            return {"status": "PASSED", "tests": {name: "passed" for name in required}}

    monkeypatch.setattr(oracle, "Executor", Executor)
    verdict = oracle.check(
        SimpleNamespace(
            qualification=qualification,
            dataset=tmp_path,
            repository=fixture.base,
            candidate=candidate,
            output=tmp_path / "cold-score",
            timeout=30,
            build_jobs=2,
        )
    )
    assert verdict["status"] == "ORACLE_PASSED", verdict
    assert verdict["accepted"] is True and verdict["cold_build"] is True
    assert calls == ["native-oracle"]
