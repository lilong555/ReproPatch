"""Bounded, source-bound repair receipts for a context checkpoint."""

from copy import deepcopy

from .task import canonical_json

CHECK_FIELDS = (
    "phase",
    "tool_id",
    "sequence",
    "source_tree_sha256",
    "source_epoch",
    "ok",
    "passed",
    "exit_code",
    "exit_codes",
    "status",
    "issue_code",
    "evidence",
)
CHANGE_FIELDS = ("path", "before_sha256", "after_sha256", "tool_id", "evidence")
HISTORY_FIELDS = ("phase", "tool_id", "sequence", "source_tree_sha256", "source_epoch", "evidence")


def _sequence(check):
    value = check.get("sequence")
    return value if type(value) is int else -1


def _select(item, fields):
    return {key: deepcopy(item[key]) for key in fields if key in item}


def state_checkpoint(state, *, maximum):
    """Keep source identity and pending work even when receipt details exceed the budget."""
    if not isinstance(state, dict) or type(maximum) is not int or maximum <= 0:
        return None
    source, epoch = state.get("source_tree_sha256"), state.get("source_epoch")
    if not isinstance(source, str) or not source or type(epoch) is not int or epoch < 0:
        return None
    current, historical = {}, {}
    counts = {"current_checks": 0, "historical_checks": 0}
    for check in state.get("checks", []):
        phase = check.get("phase")
        if phase not in {"reproduce", "verify"} and not str(phase).startswith("run_shell:"):
            continue
        is_current = (check.get("source_tree_sha256"), check.get("source_epoch")) == (
            source,
            epoch,
        )
        group = current if is_current else historical
        counts["current_checks" if is_current else "historical_checks"] += 1
        if phase not in group or _sequence(check) >= _sequence(group[phase]):
            group[phase] = check
    selected = [current[phase] for phase in ("reproduce", "verify") if phase in current]
    selected += sorted(
        (check for phase, check in current.items() if phase.startswith("run_shell:")),
        key=lambda check: (check.get("passed") is not True, _sequence(check)),
        reverse=True,
    )[:4]
    old_checks = sorted(historical.values(), key=_sequence, reverse=True)[:4]
    changes = state.get("current_changes", [])
    value = {
        "source_tree_sha256": source,
        "source_epoch": epoch,
        "changes": deepcopy(changes),
        "checks": [{**deepcopy(check), "currency": "current"} for check in selected],
        "omitted_current_checks": len(current) - len(selected),
        "pending_checks": [
            phase
            for phase in ("reproduce", "verify")
            if current.get(phase, {}).get("passed") is not True
        ],
        "historical_check_refs": [
            {**_select(check, HISTORY_FIELDS), "currency": "historical"} for check in old_checks
        ],
        "fallback": False,
        "omitted": {
            "changes": 0,
            "current_checks": counts["current_checks"] - len(selected),
            "historical_checks": counts["historical_checks"] - len(old_checks),
            "check_details": 0,
            "change_details": 0,
        },
    }
    if len(canonical_json(value)) <= maximum:
        return value

    value.update(changes=[], checks=[], historical_check_refs=[], fallback=True)
    value["omitted_current_checks"] = len(current)
    value["omitted"].update(changes=len(changes), **counts)
    if len(canonical_json(value)) > maximum:
        return None

    # Fit whole receipts, never clipped identifiers or evidence hashes. Current checks
    # precede edits and historical references; omitted counts remain exact.
    def append_if_fits(key, item, count_key, *, detail_key=None, unique_current=False):
        value[key].append(item)
        value["omitted"][count_key] -= 1
        if detail_key:
            value["omitted"][detail_key] += 1
        if unique_current:
            value["omitted_current_checks"] -= 1
        if len(canonical_json(value)) <= maximum:
            return True
        value[key].pop()
        value["omitted"][count_key] += 1
        if detail_key:
            value["omitted"][detail_key] -= 1
        if unique_current:
            value["omitted_current_checks"] += 1
        return False

    for check in sorted(selected, key=_sequence, reverse=True):
        has_details = bool(check.keys() - CHECK_FIELDS)
        compact = {
            **_select(check, CHECK_FIELDS),
            "currency": "current",
            **({"details_in_evidence": True} if has_details else {}),
        }
        append_if_fits(
            "checks",
            compact,
            "current_checks",
            detail_key="check_details" if has_details else None,
            unique_current=True,
        )
    for change in reversed(changes):
        compact = _select(change, CHANGE_FIELDS)
        has_details = bool(change.keys() - CHANGE_FIELDS)
        if has_details:
            compact["details_in_evidence"] = True
        append_if_fits(
            "changes", compact, "changes", detail_key="change_details" if has_details else None
        )
    for check in old_checks:
        append_if_fits(
            "historical_check_refs",
            {**_select(check, HISTORY_FIELDS), "currency": "historical"},
            "historical_checks",
        )
    return value
