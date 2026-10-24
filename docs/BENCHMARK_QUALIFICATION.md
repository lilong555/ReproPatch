# Batch C++ task qualification

`scripts/qualify_cpp_batch.py` dynamically checks the 41 fmt records in the
frozen Multi-SWE-bench C++ dataset. The candidate index remains 129 tasks:
41 fmt, 55 nlohmann/json, 20 simdjson, 12 Catch2 and one cpp-httplib task.
`benchmarks/task-status.json` records the 10 previously qualified, model-exposed
tasks and the evidence used to classify their exposure.

## Qualification contract

Each instance has three checks in the same fixed toolchain and build profile:

1. **Prepared baseline:** apply the official test patch to the fixed upstream
   commit, build, discover the exact recorded native test inventory, and run
   every test. At least one test must actually fail and at least one must pass.
   Every failure must be a target touched by the official test patch; all other
   tests must pass. A missing executable, skipped test or missing inventory
   member prevents qualification.
2. **Reference adapter:** apply the production reference patch in another
   source tree, then build and execute the observed F2P targets. This checks the
   adapter's behavior without repeating a full reference suite here.
3. **Independent native oracle:** reconstruct the original upstream source,
   apply the same official test patch and reference patch, and perform a cold
   full build and full native CTest run. The native CMake files have no
   ReproPatch test adapter. All required F2P and P2P members must pass, with
   exact inventory equality. Compiler launchers are disabled in this stage.

The protected adapter keeps each native test name and executable. For targets
changed by the test patch, it moves compilation into that test's CTest node.
This makes a real compilation regression observable as F2P. The dynamic
result supplies F2P/P2P; `NONE` in historical dataset metadata is retained as
metadata and supplies no failure evidence.
The recorded test unit is a native CTest node, which may run many GoogleTest
cases. F2P/P2P counts therefore describe targets/nodes rather than individual
assertions or additional independent benchmark tasks.

All framework candidates for Docker-qualified tasks can be checked with
`scripts/check_qualified_cpp_candidate.py`. The entry point validates the
qualified task, production edit scope, fixed test patch and build profile,
applies the submitted candidate to a fresh native tree, and runs the same cold
native suite. Empty candidates, invalid patches, scope violations, build/test
failures and infrastructure errors have separate outcomes. Reference patches
live under each task's `control/` directory, outside the source tree exposed
to repair agents.

## Run a bounded batch

Use one shared upstream object pool. Fetch the selected base commits before
running qualification so repository preparation remains independent of build
execution. `scripts/actions_benchmark.py prepare` performs this preparation
for the workflow.

```bash
python scripts/qualify_cpp_batch.py \
  --dataset .repropatch/inputs/dataset \
  --repository .repropatch/inputs/fmt \
  --instances fmtlib__fmt-4055,fmtlib__fmt-3863 \
  --backend docker --image sha256:ACTUAL_IMAGE_ID \
  --output .repropatch/qualification-NEW_BATCH \
  --jobs 1 --build-jobs 2 --task-timeout 1800
```

`--instances all` attempts all 41 fmt records. A comma-separated list controls
each matrix shard. `--download` downloads the one required public dataset
file when absent, then verifies its SHA-256 against `benchmarks/coverage.json`.
Dataset revision is fixed to `56ff018c04a38e27ada1e9d0a6d5839a51f88f0d`.

`--optimization O3` is the default. `--optimization O0` is a separate,
explicitly recorded preparation profile: Release's `NDEBUG` is preserved,
and baseline, reference and native oracle all use `-O0 -DNDEBUG`. An instance
that loses its baseline failure at O0 is rejected in that profile. Compare
agents within the same frozen profile and report O0/O3 results separately.

For host preflight, select `--backend native`. The successful state is
`HOST_QUALIFIED`; no Docker Task v2 file or isolated score is generated.
Repeat with an immutable Docker image to obtain `QUALIFIED` and `task.yaml`.
The host environment file records compiler/CMake/Ninja versions and hashes.
Host qualification executes the fixed upstream tests and published reference
patch. It does not authorize native execution of arbitrary agent candidates.

## Output and continuation

The new output directory contains `batch-summary.json`, `environment.json`
and one directory per attempted task. Each task retains:

- `result.json` with state, F2P/P2P, source and patch identity, exposure,
  configuration and per-stage wall times;
- full bounded command logs, exact CTest inventories and JUnit output;
- `control/record.json`, official test patch and reference patch;
- the frozen prepared source repository, and `task.yaml` for Docker-qualified
  tasks;
- a SHA-256 manifest of evidence files.

Build directories use temporary runner scratch. The current implementation
records each phase's build bytes and removes that build after the phase,
unless `--keep-builds` is explicitly selected. A later phase always creates
its own build. Reference/native temporary
source copies are removed after their checks. The shared upstream object pool
is reused across tasks. A new output directory is required for every attempt;
completed results are immutable. Continue with an explicit list of remaining
instance IDs and preserve earlier failed or cancelled preparation records.

The process handles SIGTERM/SIGINT, stops active command process groups and
records cancellation. Docker containers carry
`repropatch.batch=$REPROPATCH_BATCH_ID`, allowing the workflow's final cleanup
to select only its own containers. The outer resource wrapper should allow a
90-second termination grace period for container deletion and evidence writes.
A hard runner termination can still interrupt upload; the aggregation report
must retain the missing-evidence state.
Git preparation, including a partial clone's implicit fetch during archive,
uses the same task deadline and cancellation event as compilation. Task
timeout, output limit, cleanup failure and evidence-manifest failure have
separate terminal states. `execution-source/` and `source-manifest.json`
preserve the implementation loaded for each batch, allowing earlier evidence
to remain auditable when subsequent improvements change the implementation.

## Verify evidence before counting a qualification

```bash
python scripts/verify_qualification_evidence.py \
  --batch .repropatch/qualification-NEW_BATCH \
  --output .repropatch/audit-NEW_BATCH \
  --summary-output .repropatch/audited-NEW_BATCH/batch-summary.json \
  --recover-commands
```

This checks every file in each task's original manifest, including prepared
source, logs, JUnit and control inputs, as well as the batch's implementation
snapshot when present. Aggregate the new audited summary. A raw execution
verdict alone does not establish that its evidence is complete.

Audited rows retain `execution_status` and add `evidence_status`: only
`VERIFIED` or `RECOVERED_EXACT` can keep `QUALIFIED`/`HOST_QUALIFIED`.
Incomplete positive verdicts become `EVIDENCE_INCOMPLETE`; cancelled or
failed preparation remains a separate outcome. The original summary and all
original files stay unchanged.

Optional recovery is limited to redundant command metadata. `commands.json`
may be reconstructed from `result.json.commands` only if the bytes match the
originally recorded SHA-256 and size exactly. Recovered bytes go under the
audit's `recovered-files/` directory. Truncated diagnostic logs are not
re-created from guesses or accepted by replacing their recorded checksums;
the affected instance needs an explicitly recorded new preparation attempt.

## Candidate oracle

```bash
python scripts/check_qualified_cpp_candidate.py \
  --qualification .repropatch/qualification-NEW_BATCH/fmtlib__fmt-3863/result.json \
  --dataset .repropatch/inputs/dataset \
  --repository .repropatch/inputs/fmt \
  --candidate candidate.patch \
  --output .repropatch/oracle-NEW_ATTEMPT --timeout 900
```

For a host-qualified task, the oracle verifies current compiler/CMake/Ninja
hashes against the batch environment and accepts only the exact published
reference patch bytes and SHA-256. Other native candidates return
`NATIVE_CANDIDATE_REQUIRES_DOCKER` before compilation. For Docker-qualified
tasks it uses the exact qualified image ID and permits in-scope production
patches from any framework. The oracle preserves the candidate bytes, native
test results, stage timing and a SHA-256 manifest.

## Scope of the first expansion

The 41 fmt records share the existing project's CMake and native test layout.
This provides a low-cost first expansion path. Generalizing nlohmann/json and
simdjson requires their existing offline-data and generated-header contracts;
older Catch2 tasks additionally require approval-snapshot and toolchain review.
Those tasks retain an explicit pending status in the 129-task index.

Dynamic qualification establishes reproducibility of a repository repair
task. The upstream pool also contains feature additions and ambiguous mixed
changes. Report issue scope separately from qualification: only reviewed bug
fixes contribute to the real-defect benchmark count. Feature tasks may remain
useful as a separately reported software engineering set.

Task preparation exposes the reference patch to preparation code. A
`holdout_candidate` label means no prior model-attempt record was found in the
audited repository summaries. Freeze final task/configuration identities and
record any strategy-development exposure before the first holdout model call.

## Further sources, checked 2026-10-24

`benchmarks/cpp-expansion-sources.json` records source revisions, static counts,
overlap and the next adaptation step. These counts are not qualified tasks.

- [SWE-bench Multilingual](https://www.swebench.com/multilingual.html) contains
  12 C++ tasks, from fmt (11) and nlohmann/json (1). Eight IDs already occur in
  the current Multi-SWE-bench pool. Only fmt-1683, fmt-2457, fmt-3901 and
  json-4237 add distinct IDs; issue/base deduplication and strict qualification
  still remain.
- [SWE-bench-Live/MultiLang](https://huggingface.co/datasets/SWE-bench-Live/MultiLang)
  at revision `3638632e8153a10ca422c1022bed79023084b5c9` has 142 C++ records
  across 43 repositories. None shares an instance ID with the current 129.
  One task, fmt-4490, uses an already adapted repository. Review it first,
  followed by Ninja (1), jsoncpp (2) and OpenCC (11), measuring preparation
  cost before admitting a larger batch. DuckDB (26) and shader-slang (22)
  offer further volume but require a separate cost assessment.

Live records provide evaluation commands, parsers and container image tags.
Their supplied metadata is not evidence of a passing ReproPatch contract:
some records have no P2P tests. Freeze full dataset file hashes, review the
execution scripts, resolve image digests, separate features from bugs, and
rerun baseline/reference and the independent oracle before inclusion.
Confirm that the actual production patch changes C++: a C++ repository or
dataset split can also contain Python, JavaScript or configuration-only repairs.
