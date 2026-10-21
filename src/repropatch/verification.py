"""共享的 CTest 身份、结构化观察和独立补丁验收。"""

import hashlib
import json
import math
import re
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta

from .artifacts import EvidenceRef
from .errors import (
    CleanupUnconfirmed,
    ExecutionError,
    InfrastructureError,
    PatchRejected,
    PolicyError,
    SourceChanged,
)
from .process import RAW_OUTPUT_LIMIT, CommandResult
from .task import canonical_json
from .workspace import SourceManifest, Worktree, apply_candidate, source_manifest


class EvidenceInvalid(ValueError):
    """容器返回的发现或测试数据不满足固定 CTest 协议。"""


class DuplicateIdentity(EvidenceInvalid):
    """发现数据可靠地包含重复的选定测试。"""


class UnsupportedLayout(EvidenceInvalid):
    """选定测试要求当前不支持的隐式 fixture 或依赖执行。"""


class StageDeadline(Exception):
    """当前阶段没有可供下一条命令使用的时间。"""


@dataclass
class RunClock:
    wall_seconds: int
    reserve_seconds: int
    started: float = field(default_factory=time.monotonic)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def deadline(self, role):
        return (
            self.started
            + self.wall_seconds
            - 10
            - (0 if role == "independent" else self.reserve_seconds)
        )

    def remaining(self, role):
        return self.deadline(role) - time.monotonic()

    def timeout(self, role, command_cap):
        value = min(command_cap, self.remaining(role))
        if value <= 0:
            raise StageDeadline("STAGE_DEADLINE: 当前阶段预算耗尽")
        return value

    @property
    def deadline_at(self):
        return (self.created_at + timedelta(seconds=self.wall_seconds)).isoformat()


@dataclass
class RunContext:
    task: object
    resources: object
    log: object
    clock: RunClock
    factory: object
    test_backend: bool = False
    evaluations: list = field(default_factory=list)
    image_id: str | None = None
    isolated: bool | None = None

    @property
    def directory(self):
        return self.resources.directory

    def new_worktree(self, name):
        work = Worktree(
            self.task.repository_path,
            self.resources.workspace / name,
            self.task.base_commit,
            retain=True,
        )
        work.__enter__()
        try:
            self.resources.register_worktree(work)
        except BaseException as error:
            try:
                work.close()
            except Exception as cleanup:
                error.add_note(f"新工作树登记失败后的清理错误：{cleanup}")
            raise
        return work


@dataclass
class TestObservation:
    evaluation_role: str
    group: str
    name: str
    command_id: str | None = None
    identity_sha256: str | None = None
    observed_status: str = "not_run"
    ctest_exit_code: int | None = None
    marker_seen: bool | None = None
    result: EvidenceRef | None = None
    diagnostic: str = ""


@dataclass
class EvaluationEvidence:
    evaluation_id: str
    evaluation_role: str
    source_tree_sha256: str
    source_manifest: EvidenceRef
    started_at: str
    finished_at: str | None = None
    configure: CommandResult | None = None
    build: CommandResult | None = None
    discovery: CommandResult | None = None
    inventory: EvidenceRef | None = None
    identities: dict = field(default_factory=dict)
    tests: list[TestObservation] = field(default_factory=list)
    commands: list[CommandResult] = field(default_factory=list)
    cleanup: dict = field(
        default_factory=lambda: {"container_id": None, "confirmed": False, "errors": []}
    )
    issue_code: str | None = None
    diagnostic: str = ""
    snapshot_path: str | None = None
    isolated: bool | None = None
    image_id: str | None = None
    container_name: str | None = None
    evidence: EvidenceRef | None = None

    @property
    def successful(self):
        return (
            self.issue_code is None
            and self.cleanup["confirmed"]
            and all(
                command is not None and command.ok
                for command in (self.configure, self.build, self.discovery)
            )
            and bool(self.tests)
            and all(item.observed_status == "passed" for item in self.tests)
        )

    def to_dict(self):
        result = asdict(self)
        for name in ("configure", "build", "discovery"):
            command = getattr(self, name)
            result[name] = command.to_dict() if command is not None else None
        result["commands"] = [command.to_dict() for command in self.commands]
        result.update(
            phase=self.evaluation_role.replace("_", "-"),
            source_sha256=self.source_tree_sha256,
            cleanup_confirmed=self.cleanup["confirmed"],
            cleanup_error="; ".join(self.cleanup["errors"]) or None,
        )
        return result


@dataclass(frozen=True)
class VerificationResult:
    outcome: str
    reason_code: str
    independent: EvaluationEvidence | None


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceInvalid("JSON 重复键")
        result[key] = value
    return result


def parse_inventory(data, names):
    """仅使用 JSON v1；属性保留类型和列表顺序，只有属性名排序。"""
    try:
        if len(data) >= RAW_OUTPUT_LIMIT:
            raise EvidenceInvalid("inventory 超限")
        text = data.decode("utf-8")
        document = json.loads(
            text,
            object_pairs_hook=_json_object,
            parse_constant=lambda _: (_ for _ in ()).throw(EvidenceInvalid("非有限数值")),
        )
        stack = [(document, 0)]
        while stack:
            value, depth = stack.pop()
            if depth > 32:
                raise EvidenceInvalid("inventory 过深")
            if isinstance(value, dict):
                stack.extend((child, depth + 1) for child in value.values())
            elif isinstance(value, list):
                stack.extend((child, depth + 1) for child in value)
        if (
            not isinstance(document, dict)
            or document.get("kind") != "ctestInfo"
            or document.get("version") != {"major": 1, "minor": 0}
            or any(type(document["version"].get(key)) is not int for key in ("major", "minor"))
            or not isinstance(document.get("tests"), list)
        ):
            raise EvidenceInvalid("不是 CTest JSON v1")
        selected = {}
        for item in document["tests"]:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise EvidenceInvalid("测试身份缺失")
            name = item["name"]
            if name not in names:
                continue
            if name in selected:
                raise DuplicateIdentity("选定测试重名")
            command = item.get("command")
            if (
                not isinstance(command, list)
                or not command
                or any(not isinstance(x, str) or "\0" in x for x in command)
            ):
                raise EvidenceInvalid("选定测试 argv 无效")
            properties = item.get("properties")
            if not isinstance(properties, list):
                raise EvidenceInvalid("测试属性缺失")
            by_name = {}
            for prop in properties:
                if (
                    not isinstance(prop, dict)
                    or set(prop) != {"name", "value"}
                    or not isinstance(prop["name"], str)
                    or prop["name"] in by_name
                ):
                    raise EvidenceInvalid("测试属性无效或重名")
                by_name[prop["name"]] = prop["value"]
            if any(
                by_name.get(key)
                for key in ("FIXTURES_SETUP", "FIXTURES_CLEANUP", "FIXTURES_REQUIRED", "DEPENDS")
            ):
                raise UnsupportedLayout("UNSUPPORTED_TEST_LAYOUT: 不支持自动 fixture 或依赖测试")
            normalized = {
                "name": name,
                "command": command,
                "properties": [{"name": key, "value": by_name[key]} for key in sorted(by_name)],
            }
            selected[name] = {
                "identity": hashlib.sha256(canonical_json(normalized)).hexdigest(),
                "disabled": by_name.get("DISABLED") is True,
            }
        return selected
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, EvidenceInvalid):
            raise
        raise EvidenceInvalid("inventory JSON 损坏") from exc


def literal_selector(name):
    return "^" + re.escape(name) + "$"


def parse_junit(data, name, command):
    """按固定镜像的 CTest JUnit 状态解释，未知格式不产生通过。"""
    try:
        if not data or len(data) >= RAW_OUTPUT_LIMIT:
            raise EvidenceInvalid("JUnit 缺失或超限")
        text = data.decode("utf-8")
        if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise EvidenceInvalid("不接受 DTD 或实体")
        declaration = re.search(r"<\?xml[^>]*encoding\s*=\s*['\"]([^'\"]+)", text, re.I)
        if declaration and declaration.group(1).lower() not in {"utf-8", "utf8"}:
            raise EvidenceInvalid("JUnit 必须是 UTF-8")
        parser = ET.XMLPullParser(("start", "end"))
        depth = count = 0
        for start in range(0, len(text), 4096):
            parser.feed(text[start : start + 4096])
            for event, _ in parser.read_events():
                depth += 1 if event == "start" else -1
                count += event == "start"
                if depth > 32 or count > 10000:
                    raise EvidenceInvalid("JUnit 结构超限")
        parser.close()
        suite = ET.fromstring(text)
        cases = list(suite.iter("testcase"))
        if (
            suite.tag != "testsuite"
            or len(cases) != 1
            or len(suite) != 1
            or cases[0] is not suite[0]
        ):
            raise EvidenceInvalid("必须恰好一个测试结果")
        case = cases[0]
        if set(case.attrib) != {"name", "classname", "time", "status"}:
            raise EvidenceInvalid("未知 testcase 属性")
        if case.get("name") != name or case.get("classname") != name:
            raise EvidenceInvalid("JUnit 用例名不符")
        duration = float(case.attrib["time"])
        if not math.isfinite(duration) or duration < 0:
            raise EvidenceInvalid("测试时长无效")
        children = {}
        for child in case:
            if (
                child.tag
                not in {"failure", "error", "skipped", "properties", "system-out", "system-err"}
                or child.tag in children
            ):
                raise EvidenceInvalid("JUnit 包含未知或重复节点")
            if child.tag != "properties" and len(child):
                raise EvidenceInvalid("不接受嵌套测试状态或输出节点")
            children[child.tag] = child
        failure = children.get("failure")
        skipped = children.get("skipped")
        status = case.get("status")
        expected = {
            "tests": 1,
            "failures": int(failure is not None),
            "skipped": int(skipped is not None),
            "disabled": int(status == "disabled"),
        }
        for key, value in expected.items():
            if suite.get(key) != str(value):
                raise EvidenceInvalid("JUnit 计数与实际结果矛盾")
        if "error" in children or suite.get("errors", "0") != "0":
            raise EvidenceInvalid("非固定 CTest 错误结构")
        if command.status != "exited" or command.output_truncated or command.error:
            raise EvidenceInvalid("CTest 执行证据不完整")
        if status == "run" and failure is None and skipped is None and command.returncode == 0:
            return "passed", ""
        if status == "disabled" and failure is None and skipped is None and command.returncode == 0:
            return "not_run", "Disabled"
        if status == "notrun" and skipped is not None and failure is None:
            message = skipped.get("message", "")
            if (
                not message
                or (message.startswith("SKIP_") and command.returncode != 0)
                or (not message.startswith("SKIP_") and command.returncode != 8)
            ):
                raise EvidenceInvalid("未运行状态与 CTest 返回码矛盾")
            return ("skipped" if message.startswith("SKIP_") else "not_run"), message[:2000]
        if status == "fail" and failure is not None and skipped is None and command.returncode != 0:
            message = failure.get("message", "")
            known = {
                "Failed": "failed",
                "Timeout": "timed_out",
                "SEGFAULT": "crashed",
                "ILLEGAL": "crashed",
                "INTERRUPT": "crashed",
                "NUMERICAL": "crashed",
                "Subprocess aborted": "crashed",
                "BAD_COMMAND": "not_run",
            }
            if message in known:
                return known[message], message
        raise EvidenceInvalid("未知或矛盾的 CTest 状态")
    except (ValueError, TypeError, UnicodeError, KeyError, ET.ParseError) as exc:
        if isinstance(exc, EvidenceInvalid):
            raise
        raise EvidenceInvalid("JUnit 无效") from exc


def _stdout(command, root):
    if command.stdout_log is None or command.stderr_log is None:
        raise InfrastructureError("EVIDENCE_MISSING: 命令没有原始双流引用")
    command.stderr_log.read(root, limit=RAW_OUTPUT_LIMIT)
    return command.stdout_log.read(root, limit=RAW_OUTPUT_LIMIT)


def evaluate_checks(task, workspace, role, run, *, only_f2p=False, baseline=None):
    """配置、构建、发现及逐测试观察共用一次容器，不在这里决定 Run outcome。"""
    run.resources.assert_owned()
    current = workspace.assert_current()
    eid = uuid.uuid4().hex
    phase = role.replace("_", "-")
    source = run.resources.workspace / "snapshots" / f"{len(run.evaluations) + 1:03d}-{phase}"
    workspace.export(
        source,
        on_created=lambda identity: run.resources.register_snapshot(
            source, current, identity=identity
        ),
    )
    manifest = EvidenceRef.save(
        run.directory,
        f"manifests/{eid}.json",
        canonical_json(current.to_dict()) + b"\n",
        budget=run.resources.budget,
    )
    evidence = EvaluationEvidence(
        eid,
        role,
        current.sha256,
        manifest,
        datetime.now(UTC).isoformat(),
        snapshot_path=str(source),
    )
    names = [("F2P", item.name) for item in task.task.tests.fail_to_pass]
    if not only_f2p:
        names += [("P2P", name) for name in task.task.tests.pass_to_pass]
    evidence.tests = [TestObservation(role, group, name) for group, name in names]
    run.evaluations.append(evidence)
    directory = run.directory / "evidence"
    directory.mkdir(mode=0o700, exist_ok=True)
    (directory / eid).mkdir(mode=0o700)
    sandbox = run.factory(source)
    sandbox.audit_log = run.log
    sandbox.audit_payload = {"evaluation_id": eid, "evaluation_role": role}
    if run.test_backend:
        sandbox.log_root = run.directory
        sandbox.audit_budget = run.resources.budget
    sandbox.operation_deadline = run.clock.deadline(role)
    entered = False

    def execute(argv):
        run.resources.assert_owned()
        sandbox.timeout = run.clock.timeout(role, task.task.budget.command_timeout_seconds)
        result = sandbox.run(tuple(argv))
        evidence.commands.append(result)
        if result.status == "cancelled":
            raise KeyboardInterrupt()
        return result

    def complete_command(command):
        return command.status == "exited" and not command.output_truncated and command.error is None

    try:
        run.clock.timeout(role, task.task.budget.command_timeout_seconds)
        with sandbox:
            entered = True
            evidence.isolated = sandbox.isolated
            evidence.image_id = getattr(sandbox, "image_id", None)
            evidence.container_name = getattr(sandbox, "name", None)
            evidence.cleanup["container_id"] = getattr(sandbox, "container_id", None)
            if run.image_id is None:
                run.image_id = evidence.image_id
            elif evidence.image_id != run.image_id:
                raise InfrastructureError("Execution image changed during a run")
            if not run.test_backend and evidence.image_id != task.image_id:
                raise InfrastructureError("IMAGE_CHANGED: 执行镜像与冻结输入不同")
            if run.isolated is None:
                run.isolated = sandbox.isolated
            elif run.isolated != sandbox.isolated:
                raise InfrastructureError("Execution backend changed during a run")
            if not run.test_backend:
                sandbox.timeout = run.clock.timeout(role, task.task.budget.command_timeout_seconds)
                preflight = sandbox.preflight()
                evidence.commands.append(preflight)
                if preflight.status == "cancelled":
                    raise KeyboardInterrupt()
                if not preflight.ok:
                    evidence.issue_code = "IMAGE_TOOLS"
                    return evidence
            for name in ("configure", "build"):
                result = execute(task.task.commands[name])
                setattr(evidence, name, result)
                if not result.ok or not complete_command(result):
                    return evidence
            discovery = execute(("ctest", "--test-dir", "/build", "--show-only=json-v1"))
            evidence.discovery = discovery
            if not discovery.ok or not complete_command(discovery):
                evidence.issue_code = "EVIDENCE_INVALID"
                return evidence
            evidence.inventory = discovery.stdout_log
            try:
                inventory = parse_inventory(
                    _stdout(discovery, run.directory), {name for _, name in names}
                )
            except (UnsupportedLayout, DuplicateIdentity) as exc:
                evidence.issue_code = (
                    "TEST_IDENTITY_CHANGED"
                    if baseline is not None
                    else "UNSUPPORTED_TEST_LAYOUT"
                    if isinstance(exc, UnsupportedLayout)
                    else "EVIDENCE_INVALID"
                )
                evidence.diagnostic = str(exc)
                return evidence
            except EvidenceInvalid as exc:
                evidence.issue_code = "EVIDENCE_INVALID"
                evidence.diagnostic = str(exc)
                return evidence
            evidence.identities = {name: item["identity"] for name, item in inventory.items()}
            for observation in evidence.tests:
                observation.identity_sha256 = evidence.identities.get(observation.name)
            if len(inventory) != len(names):
                evidence.issue_code = "REQUIRED_TEST_NOT_RUN"
                evidence.diagnostic = "选定测试在 inventory 中缺失"
                return evidence
            if baseline is not None and any(
                baseline.identities.get(name) != value
                for name, value in evidence.identities.items()
            ):
                evidence.issue_code = "TEST_IDENTITY_CHANGED"
                return evidence
            prepared = execute(
                (
                    "/bin/sh",
                    "-ec",
                    "test ! -L /build/.repropatch-results && "
                    "mkdir -p -- /build/.repropatch-results",
                )
            )
            if not prepared.ok or not complete_command(prepared):
                evidence.issue_code = "EVIDENCE_INVALID"
                return evidence
            failures = {item.name: item for item in task.task.tests.fail_to_pass}
            for observation in evidence.tests:
                if inventory[observation.name]["disabled"]:
                    observation.diagnostic = "Disabled"
                    continue
                tid = uuid.uuid4().hex
                filename = f"/build/.repropatch-results/{eid}-{tid}.xml"
                template = task.task.commands[
                    "reproduce" if observation.group == "F2P" else "verify"
                ]
                seconds = run.clock.timeout(role, task.task.budget.command_timeout_seconds)
                result = execute(
                    (
                        *template,
                        "-R",
                        literal_selector(observation.name),
                        "--output-junit",
                        filename,
                        "--timeout",
                        f"{seconds:.6f}",
                    )
                )
                observation.command_id = result.command_id
                observation.ctest_exit_code = (
                    result.returncode if result.status == "exited" else None
                )
                if not complete_command(result):
                    observation.observed_status = (
                        "timed_out" if result.status == "timed_out" else "invalid"
                    )
                    observation.diagnostic = result.status
                    break
                read = execute(
                    (
                        "/bin/sh",
                        "-ec",
                        'test -f "$1" && test ! -L "$1" && '
                        'test "$(wc -c < "$1")" -lt 4194304 && cat -- "$1"',
                        "repropatch-read",
                        filename,
                    )
                )
                if not read.ok or not complete_command(read):
                    observation.observed_status = "invalid"
                    observation.diagnostic = "JUnit 读取失败"
                    break
                data = _stdout(read, run.directory)
                observation.result = EvidenceRef.save(
                    run.directory, f"evidence/{eid}/{tid}.xml", data, budget=run.resources.budget
                )
                try:
                    observation.observed_status, observation.diagnostic = parse_junit(
                        data, observation.name, result
                    )
                except EvidenceInvalid as exc:
                    observation.observed_status = "invalid"
                    observation.diagnostic = str(exc)
                    break
                if role == "baseline" and observation.group == "F2P":
                    _stdout(result, run.directory)
                    observation.marker_seen = result.contains(
                        failures[observation.name].output_contains, run.directory
                    )
                if observation.observed_status in {"timed_out", "invalid"}:
                    break
        return evidence
    except StageDeadline as exc:
        evidence.issue_code = "STAGE_DEADLINE"
        evidence.diagnostic = str(exc)
        return evidence
    except ExecutionError as exc:
        evidence.issue_code = (
            "STAGE_DEADLINE" if run.clock.remaining(role) <= 0 else "EVIDENCE_INVALID"
        )
        evidence.diagnostic = str(exc)
        return evidence
    except CleanupUnconfirmed as exc:
        evidence.issue_code = "CLEANUP_UNCONFIRMED"
        evidence.diagnostic = str(exc)
        return evidence
    finally:
        primary = sys.exception()
        for observation in evidence.tests:
            if observation.command_id is None and not observation.diagnostic:
                observation.diagnostic = (
                    evidence.diagnostic or evidence.issue_code or "上游阶段未完成，未执行该测试"
                )
        evidence.finished_at = datetime.now(UTC).isoformat()
        evidence.cleanup["container_id"] = getattr(sandbox, "container_id", None)
        confirmed = getattr(
            sandbox,
            "cleanup_confirmed",
            run.test_backend and entered and not isinstance(primary, CleanupUnconfirmed),
        )
        if (
            not entered
            and not getattr(sandbox, "created", False)
            and evidence.cleanup["container_id"] is None
        ):
            confirmed = True
        evidence.cleanup["confirmed"] = bool(confirmed)
        cleanup_error = getattr(sandbox, "cleanup_error", None)
        if cleanup_error:
            evidence.cleanup["errors"].append(cleanup_error)
        if evidence.issue_code == "CLEANUP_UNCONFIRMED":
            evidence.cleanup["confirmed"] = False
            evidence.cleanup["errors"].append(evidence.diagnostic)
        try:
            workspace.assert_current()
            try:
                observed = source_manifest(source)
            except (OSError, ValueError, PolicyError) as exc:
                raise SourceChanged("SOURCE_CHANGED: 快照读取失败") from exc
            if observed != current:
                raise SourceChanged("SOURCE_CHANGED: 执行后源码快照改变")
            run.resources.finish_evaluation(
                source,
                keep=task.task.retain != "none"
                and (role != "agent_check" or not evidence.successful),
            )
            evidence.evidence = EvidenceRef.save(
                run.directory,
                f"evidence/{eid}/evaluation.json",
                canonical_json(evidence.to_dict()) + b"\n",
                budget=run.resources.budget,
            )
            run.log.emit(
                "cleanup_finished",
                {
                    "evaluation_id": eid,
                    "evaluation_role": role,
                    "evidence": asdict(evidence.evidence),
                    "cleanup": evidence.cleanup,
                },
                emergency=True,
            )
        except Exception as exc:
            if primary is None:
                raise
            primary.add_note(f"评估收尾失败：{exc}")


def baseline_result(task, baseline):
    for name in ("configure", "build"):
        command = getattr(baseline, name)
        if (
            command is not None
            and command.status == "exited"
            and not command.output_truncated
            and command.returncode != 0
            and command.error is None
        ):
            return "ERROR", f"BASELINE_{name.upper()}_FAILED"
    if baseline.issue_code == "UNSUPPORTED_TEST_LAYOUT" or baseline.issue_code == "IMAGE_TOOLS":
        return "ERROR", baseline.issue_code
    if not baseline.cleanup["confirmed"]:
        return "INCONCLUSIVE", "CLEANUP_UNCONFIRMED"
    if any(item.group == "P2P" and item.observed_status == "failed" for item in baseline.tests):
        return "INCONCLUSIVE", "BASELINE_REGRESSION_FAILED"
    expected_names = [item.name for item in task.task.tests.fail_to_pass] + list(
        task.task.tests.pass_to_pass
    )
    if (
        baseline.issue_code
        or any(
            command is None or not command.ok or command.output_truncated
            for command in (baseline.configure, baseline.build, baseline.discovery)
        )
        or baseline.inventory is None
        or set(baseline.identities) != set(expected_names)
        or [item.name for item in baseline.tests] != expected_names
        or len(baseline.tests)
        != len(task.task.tests.fail_to_pass) + len(task.task.tests.pass_to_pass)
        or any(
            item.observed_status not in {"passed", "failed"} or item.result is None
            for item in baseline.tests
        )
    ):
        return "INCONCLUSIVE", "BASELINE_INCOMPLETE"
    failures = {item.name: item for item in task.task.tests.fail_to_pass}
    for observation in baseline.tests:
        if observation.group == "F2P":
            if observation.observed_status == "passed":
                return "NOT_REPRODUCED", "F2P_PASSED"
            if (
                observation.ctest_exit_code != failures[observation.name].expected_exit_code
                or not observation.marker_seen
            ):
                return "NOT_REPRODUCED", "FAILURE_SIGNATURE_MISMATCH"
    return None, "BASELINE_PASSED"


def candidate_result(evidence):
    if evidence.issue_code in {"TEST_IDENTITY_CHANGED", "REQUIRED_TEST_NOT_RUN"}:
        return "REJECTED", evidence.issue_code
    for name in ("configure", "build"):
        command = getattr(evidence, name)
        if (
            command is not None
            and command.status == "exited"
            and not command.output_truncated
            and command.returncode != 0
            and command.error is None
        ):
            return "REJECTED", f"CANDIDATE_{name.upper()}_FAILED"
    for observation in evidence.tests:
        if observation.observed_status in {"failed", "crashed"}:
            return "REJECTED", "F2P_FAILED" if observation.group == "F2P" else "REGRESSION_FAILED"
        if observation.observed_status in {"skipped", "not_run"} and (
            observation.result is not None or observation.diagnostic == "Disabled"
        ):
            return "REJECTED", "REQUIRED_TEST_NOT_RUN"
    if (
        any(item.status == "timed_out" for item in evidence.commands)
        or any(item.observed_status == "timed_out" for item in evidence.tests)
        or evidence.issue_code == "STAGE_DEADLINE"
    ):
        return "INCONCLUSIVE", "VERIFICATION_TIMEOUT"
    if any(item.status in {"output_limit", "oom_killed"} for item in evidence.commands):
        return "INCONCLUSIVE", "RESOURCE_TERMINATION"
    if not evidence.cleanup["confirmed"]:
        return "INCONCLUSIVE", "CLEANUP_UNCONFIRMED"
    if evidence.successful:
        return "ACCEPTED", "VERIFICATION_PASSED"
    return "INCONCLUSIVE", "EVIDENCE_INVALID"


def validate_evidence(evidence, root):
    manifest = SourceManifest.from_dict(
        json.loads(evidence.source_manifest.read(root, limit=256 * 1024 * 1024))
    )
    if manifest.sha256 != evidence.source_tree_sha256:
        raise InfrastructureError("ARTIFACT_CORRUPT: 评估源码摘要不符")
    if evidence.inventory is not None:
        evidence.inventory.read(root, limit=RAW_OUTPUT_LIMIT)
    for command in evidence.commands:
        if command.stdout_log is not None:
            command.stdout_log.read(root, limit=RAW_OUTPUT_LIMIT)
        if command.stderr_log is not None:
            command.stderr_log.read(root, limit=RAW_OUTPUT_LIMIT)
    for observation in evidence.tests:
        if observation.result is not None:
            observation.result.read(root, limit=RAW_OUTPUT_LIMIT)


def verify_candidate(task, baseline, candidate, run):
    if baseline_result(task, baseline)[0] is not None:
        raise InfrastructureError("BASELINE_NOT_ELIGIBLE: 独立验收缺少完整基线")
    validate_evidence(baseline, run.directory)
    try:
        run.clock.timeout("independent", task.task.budget.command_timeout_seconds)
        target = run.new_worktree("validation")
        original = SourceManifest.from_dict(
            json.loads(baseline.source_manifest.read(run.directory, limit=256 * 1024 * 1024))
        )
        apply_candidate(
            target, candidate, run.directory, original, task.editable_files, task.protected_files
        )
        evidence = evaluate_checks(task, target, "independent", run, baseline=baseline)
        candidate.load(run.directory)
        validate_evidence(evidence, run.directory)
        outcome, reason = candidate_result(evidence)
        return VerificationResult(outcome, reason, evidence)
    except PatchRejected as exc:
        return VerificationResult("REJECTED", str(exc).split(":", 1)[0], None)
    except StageDeadline:
        return VerificationResult("INCONCLUSIVE", "VERIFICATION_TIMEOUT", None)
