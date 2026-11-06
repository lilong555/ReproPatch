"""Checkpointed localization phase and exact model-visible source receipts."""

import hashlib
import json
import math
import re
import time
from dataclasses import asdict

from .artifacts import EvidenceRef
from .errors import InfrastructureError, PolicyError
from .task import canonical_json

SCHEMA = "repropatch.localization.session.v1"
READ_ONLY_TOOLS = frozenset({"list_directory", "read_file", "search_code", "search_files"})
FEEDBACK_LIMIT = 2 * 1024 * 1024


def validate_feedback(value, task, *, source_tree_sha256=None):
    """Freeze an allowlisted public baseline package before any model request."""
    try:
        raw = canonical_json(value)
        if len(raw) > FEEDBACK_LIMIT:
            raise ValueError("feedback package size")
        value = json.loads(raw)
        if (
            not isinstance(value, dict)
            or set(value)
            != {
                "schema",
                "instance_id",
                "prepared_commit",
                "source_tree_sha256",
                "logs",
                "feedback_sha256",
            }
            or value["schema"] != "repropatch.localization-feedback.v1"
            or not isinstance(value["instance_id"], str)
            or value["instance_id"].replace("__", "-").lower() != task.id
            or value["prepared_commit"] != task.revision
            or not isinstance(value["source_tree_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", value["source_tree_sha256"]) is None
            or not isinstance(value["logs"], list)
            or len(value["logs"]) != 3
        ):
            raise ValueError("feedback identity")
        if source_tree_sha256 is not None and value["source_tree_sha256"] != source_tree_sha256:
            raise ValueError("feedback source")
        expected = ("baseline-configure.log", "baseline-build.log", "baseline-ctest.log")
        for entry, name in zip(value["logs"], expected, strict=True):
            if (
                not isinstance(entry, dict)
                or set(entry) != {"name", "sha256", "text"}
                or entry["name"] != name
                or not isinstance(entry["text"], str)
                or hashlib.sha256(entry["text"].encode("utf-8")).hexdigest() != entry["sha256"]
            ):
                raise ValueError("feedback log")
        payload = {key: item for key, item in value.items() if key != "feedback_sha256"}
        if hashlib.sha256(canonical_json(payload)).hexdigest() != value["feedback_sha256"]:
            raise ValueError("feedback checksum")
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
        raise InfrastructureError(
            "LOCALIZATION_FEEDBACK: invalid frozen public observation"
        ) from exc
    return value


class LocalizationSession:
    def __init__(self, harness, workspace, toolbox, context_state):
        self.harness, self.workspace, self.toolbox = harness, workspace, toolbox
        self.context_state = context_state
        contract = {
            "mode": harness.localization_mode,
            "tool_budget": harness.localization_tool_budget,
            "step_budget": harness.localization_step_budget,
        }
        state = context_state.localization_state
        if state:
            if (
                state.get("schema") != SCHEMA
                or state.get("contract") != contract
                or state.get("phase") not in {"localization", "repair"}
                or type(state.get("started_elapsed_seconds")) not in (int, float)
                or not math.isfinite(state["started_elapsed_seconds"])
                or any(
                    type(state.get(key)) is not int or state[key] < 0
                    for key in ("tools_used", "model_steps", "tool_ordinal", "receipt_count")
                )
            ):
                raise InfrastructureError("LOCALIZATION_STATE: checkpoint identity mismatch")
        else:
            state.update(
                schema=SCHEMA,
                contract=contract,
                phase="localization" if contract["tool_budget"] else "repair",
                tools_used=0,
                model_steps=0,
                tool_ordinal=0,
                receipt_count=0,
                exposure_count=0,
                pending_receipts=[],
                baseline_recorded=False,
                source_tree_sha256=workspace.expected_manifest.sha256,
                started_elapsed_seconds=time.monotonic() - harness.context.clock.started,
            )
        self.state = state
        self._inflight = []
        self.engine = None
        if contract["mode"] != "native":
            from .localization import OUTPUT_BYTES, Localization, LocalizationLimits

            response_limit = (
                min(
                    OUTPUT_BYTES,
                    max(16 * 1024, harness.context_policy.tool_output_max_bytes - 2048),
                )
                if harness.context_policy.compaction_enabled
                else OUTPUT_BYTES
            )
            self.engine = Localization(
                toolbox,
                mode=contract["mode"],
                state=state.get("engine"),
                limits=LocalizationLimits(output_bytes=response_limit),
            )
        self._sync()

    @property
    def phase(self):
        return self.state["phase"]

    def _sync(self):
        if self.engine is not None:
            self.state["engine"] = self.engine.to_dict()
        self.context_state.localization_state = self.state
        self.harness.report["localization"] = self.state

    def progress(self):
        return {
            "phase": self.phase,
            "mode": self.state["contract"]["mode"],
            "localization_tool_calls_remaining": max(
                0, self.state["contract"]["tool_budget"] - self.state["tools_used"]
            ),
            "localization_model_steps_remaining": max(
                0, self.state["contract"]["step_budget"] - self.state["model_steps"]
            ),
        }

    def start_model(self):
        if self.phase == "localization":
            self.state["model_steps"] += 1
        self._sync()

    def exhausted(self):
        if self.phase != "localization":
            return None
        if self.state["tools_used"] >= self.state["contract"]["tool_budget"]:
            return "tool_budget"
        if self.state["model_steps"] >= self.state["contract"]["step_budget"]:
            return "model_step_budget"
        return None

    def transition(self, reason):
        if self.phase != "localization":
            return None
        self.state["phase"] = "repair"
        self.state["transition_reason"] = reason
        self.harness.log.emit(
            "localization_phase_finished",
            {
                "schema": SCHEMA,
                "reason": reason,
                "localization_tools_used": self.state["tools_used"],
                "localization_model_steps": self.state["model_steps"],
                "model_step": self.harness.report["model_steps"],
                "tool_calls_used": self.harness.report["tool_calls"],
                "cumulative_usage": self.harness.report["usage"],
                "elapsed_seconds": self.elapsed(),
                "source_tree_sha256": self.workspace.expected_manifest.sha256,
            },
        )
        self._sync()
        return {
            "role": "user",
            "content": (
                "The read-only localization phase is complete. Continue repairing from the "
                "observed source and baseline. Editing and command execution are now available. "
                "The original cumulative request, tool and time budgets remain in force."
            ),
        }

    def before_tool(self, name):
        self.state["tool_ordinal"] += 1
        if self.phase == "localization":
            self.state["tools_used"] += 1
            self._sync()
            if self.workspace.expected_manifest.sha256 != self.state["source_tree_sha256"]:
                raise InfrastructureError("LOCALIZATION_SOURCE_CHANGED: read-only snapshot changed")
            if self.state["tools_used"] > self.state["contract"]["tool_budget"]:
                raise PolicyError("LOCALIZATION_BUDGET: await the repair phase announcement")
            if name not in READ_ONLY_TOOLS:
                raise PolicyError("LOCALIZATION_READ_ONLY: inspect source before the repair phase")

    def elapsed(self):
        return max(
            0.0,
            time.monotonic()
            - self.harness.context.clock.started
            - self.state["started_elapsed_seconds"],
        )

    def prepare_receipt(
        self, name, arguments, text, *, tool_id, provider_call_id=None, source_tree_sha256=None
    ):
        if self.engine is not None:
            self.engine.track_source()
        manifest = self.workspace.expected_manifest
        source = source_tree_sha256 or manifest.sha256
        reference = EvidenceRef.save(
            self.harness.directory,
            f"agent/delivered/{tool_id}.json",
            text.encode("utf-8"),
            budget=self.harness.resources.budget,
        )
        try:
            visible = json.loads(text)
            receipt_format = "json"
        except (ValueError, TypeError):
            visible = {"visible_text": text}
            receipt_format = "folded_text" if "\n[完整工具输出：" in text else "unparsed_text"
        data = visible.get("data", visible) if isinstance(visible, dict) else {}
        paths = set()
        if isinstance(data, dict):
            if isinstance(data.get("path"), str):
                paths.add(data["path"])
            for key in ("matches", "candidates"):
                if isinstance(data.get(key), list):
                    paths.update(
                        item["path"]
                        for item in data[key]
                        if isinstance(item, dict) and isinstance(item.get("path"), str)
                    )
        self.state["receipt_count"] += 1
        report = self.harness.report
        entries = manifest.by_path
        payload = {
            "schema": "repropatch.localization.receipt.v1",
            "phase": self.phase,
            "delivery_status": "prepared",
            "receipt_format": receipt_format,
            "tool_name": name,
            "tool_call_id": tool_id,
            "provider_call_id": provider_call_id,
            "model_step": report["model_steps"],
            "tool_calls_used": report["tool_calls"],
            "tool_ordinal": self.state["tool_ordinal"],
            "localization_tools_used": self.state["tools_used"],
            "cumulative_usage": report["usage"],
            "elapsed_seconds": self.elapsed(),
            "source_tree_sha256": source,
            "source_epoch": self.engine.to_dict()["source_epoch"] if self.engine else None,
            "source_files": {
                path: entries[path].sha256
                for path in sorted(paths)
                if path in self.toolbox.readable and path in entries
            },
            "delivered_ref": asdict(reference),
        }
        self.state["pending_receipts"].append({"payload": payload, "arguments": arguments})
        self.harness.log.emit("localization_receipt_prepared", payload)
        self._sync()

    def submit(self, body, purpose):
        """Match pending receipts against the admitted request's exact input items."""
        self._inflight = []
        if purpose != "repair":
            return
        outputs, baselines = set(), set()
        for item in body.get("input", []):
            if not isinstance(item, dict):
                continue
            if item.get("type") == "function_call_output" and isinstance(item.get("output"), str):
                outputs.add(
                    (item.get("call_id"), hashlib.sha256(item["output"].encode()).hexdigest())
                )
            if item.get("role") == "user" and isinstance(item.get("content"), str):
                try:
                    content = json.loads(item["content"])
                except ValueError:
                    continue
                if isinstance(content, dict):
                    for key in ("baseline", "baseline_observation"):
                        if isinstance(content.get(key), dict):
                            baselines.add(hashlib.sha256(canonical_json(content[key])).hexdigest())
        pending = []
        for receipt in self.state["pending_receipts"]:
            payload = receipt["payload"]
            digest = payload["delivered_ref"]["sha256"]
            present = (
                digest in baselines
                if payload["tool_name"] == "baseline"
                else (payload["provider_call_id"], digest) in outputs
            )
            if present:
                self._inflight.append(receipt)
                pending.append(receipt)
            else:
                self.harness.log.emit(
                    "localization_receipt_omitted",
                    {**payload, "delivery_status": "omitted_before_submission"},
                )
        self.state["pending_receipts"] = pending
        self._submitted_elapsed = self.elapsed()
        self._sync()

    def confirm_response(self):
        """A successful carrier response confirms the model received these bytes."""
        for receipt in self._inflight:
            payload = receipt["payload"]
            ref = EvidenceRef(**payload["delivered_ref"])
            raw = ref.read(self.harness.directory, limit=ref.size_bytes).decode("utf-8")
            try:
                visible = json.loads(raw)
            except ValueError:
                visible = {"visible_text": raw}
            feedback = None
            if self.engine is not None:
                try:
                    feedback = self.engine.observe(
                        payload["tool_name"],
                        receipt["arguments"],
                        visible,
                        receipt_id=payload["tool_call_id"],
                        source_tree_sha256=payload["source_tree_sha256"],
                        source_epoch=payload.get("source_epoch"),
                    )
                except PolicyError as exc:
                    feedback = {"registered": False, "reason": str(exc).split(":", 1)[0]}
            report = self.harness.report
            self.harness.log.emit(
                "localization_exposure",
                {
                    **payload,
                    "schema": "repropatch.localization.exposure.v1",
                    "delivery_status": "confirmed",
                    "produced_model_step": payload["model_step"],
                    "produced_elapsed_seconds": payload["elapsed_seconds"],
                    "carrier_phase": self.phase,
                    "model_step": report["model_steps"],
                    "cumulative_usage": report["usage"],
                    "submitted_elapsed_seconds": self._submitted_elapsed,
                    "elapsed_seconds": self.elapsed(),
                    "feedback_registration": feedback,
                },
            )
            self.state["pending_receipts"].remove(receipt)
            self.state["exposure_count"] += 1
        self._inflight = []
        self._sync()

    def baseline(self, value):
        if self.state["baseline_recorded"]:
            return
        self.prepare_receipt(
            "baseline",
            {},
            canonical_json(value).decode("utf-8"),
            tool_id="baseline",
            source_tree_sha256=value.get("source_tree_sha256"),
        )
        self.state["baseline_recorded"] = True
        self._sync()
