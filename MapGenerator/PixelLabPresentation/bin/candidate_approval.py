#!/usr/bin/env python3
"""Explicit local operator approval and rejection of candidates (#52).

Nothing in the automated pipeline may approve a candidate. Approval is a human
act, and this module is the only place that can record it. Every decision it
writes names the actor, the moment, and the reason, and carries the evidence
the decision was made against: the validation report hash, the candidate image
hash, and the immutable control-input hashes.

Decisions are appended rather than replaced. Superseding an earlier decision is
allowed — people change their minds after looking again — but erasing the fact
that an earlier decision existed is not, because the audit trail is the point.

Source and control artifacts are never written here. Only files inside the
candidate's own directory are created or replaced, always atomically.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import candidate_state
import candidate_validation
import pixellab_modules


visual_contract = pixellab_modules.load_visual_contract()
pixellab_client = pixellab_modules.load_pixellab_client()

canonical_json_bytes = visual_contract.canonical_json_bytes
sha256_bytes = visual_contract.sha256_bytes

CONTRACT_VERSION = visual_contract.CONTRACT_VERSION
APPROVAL_VERSION = "1"
APPROVAL_RECORD_NAME = "approval.json"

# The two decisions an operator may record. Both are explicit; there is no
# implicit or default decision, and absence of a record means "undecided".
DECISION_APPROVE = candidate_state.STATE_HUMAN_APPROVED
DECISION_REJECT = candidate_state.STATE_REJECTED
ALL_DECISIONS = (DECISION_APPROVE, DECISION_REJECT)


class CandidateApprovalError(ValueError):
    """Represent a decision that must not be recorded as requested."""


def utc_now() -> datetime:
    """
    Description:
        Read the wall clock as a timezone-aware UTC moment.
    Required State:
        None.
    Usage:
        Default clock for decisions; tests inject a fixed clock instead.
    Parameters:
        none
    Returns:
        datetime: Current time in UTC.
    Other I/O:
        - reads the system clock
    """
    return datetime.now(timezone.utc)


def format_decision_timestamp(moment: datetime) -> str:
    """
    Description:
        Render a decision moment as a stable ISO 8601 UTC string.
    Required State:
        The moment must be timezone-aware so the record is unambiguous.
    Usage:
        Call once per recorded decision.
    Parameters:
        moment (datetime): Moment the decision was made.
    Returns:
        str: ISO 8601 timestamp ending in "Z".
    Other I/O:
        - none
    """
    # A naive datetime would make the audit trail ambiguous across machines,
    # so it is refused rather than assumed to be local time.
    if moment.tzinfo is None:
        raise CandidateApprovalError("decision timestamps must be timezone-aware")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_approval_record(candidate_directory: Path) -> dict[str, Any] | None:
    """
    Description:
        Read the decision history for one candidate, if any decision exists.
    Required State:
        The candidate directory exists.
    Usage:
        Call before recording a decision and whenever reporting candidate state.
    Parameters:
        candidate_directory (Path): Directory owning one candidate.
    Returns:
        dict[str, Any] | None: Parsed approval record, or None when undecided.
    Other I/O:
        - files: reads approval.json when present
    """
    record_path = candidate_directory / APPROVAL_RECORD_NAME
    if not record_path.is_file():
        return None
    try:
        record = json.loads(record_path.read_bytes())
    except json.JSONDecodeError as error:
        raise CandidateApprovalError(f"approval record is not valid JSON: {error}") from None
    if not isinstance(record, dict):
        raise CandidateApprovalError(f"approval record must be a JSON object: {record_path}")
    return record


def resolve_current_state(candidate_directory: Path, validation_report: dict[str, Any]) -> str:
    """
    Description:
        Determine the candidate's present lifecycle state from its artifacts.
    Required State:
        The validation report describes this candidate's current files.
    Usage:
        Call before authorizing any transition.
    Parameters:
        candidate_directory (Path): Directory owning one candidate.
        validation_report (dict[str, Any]): Fresh report for this candidate.
    Returns:
        str: The candidate's current state.
    Other I/O:
        - files: reads approval.json when present
    """
    # An operator decision, once recorded, outranks the automated reading:
    # automation describes the artifacts, a human decides what they mean.
    existing_record = read_approval_record(candidate_directory)
    if existing_record is not None:
        return candidate_state.require_known_state(existing_record.get("currentState", ""))
    return candidate_state.require_known_state(validation_report["resultingState"])


def require_decision_inputs(decision: str, actor: str, reason: str) -> None:
    """
    Description:
        Require a named actor and a stated reason for every decision.
    Required State:
        None.
    Usage:
        Call before doing any work for a decision request.
    Parameters:
        decision (str): DECISION_APPROVE or DECISION_REJECT.
        actor (str): Human who is making the decision.
        reason (str): Why the decision was made.
    Returns:
        None: Completes when the request is well formed.
    Other I/O:
        - none
    """
    if decision not in ALL_DECISIONS:
        raise CandidateApprovalError(
            f"unknown decision {decision!r}; expected one of {list(ALL_DECISIONS)}"
        )
    # An unattributed or unexplained decision is not evidence of anything, so
    # both fields are mandatory rather than merely encouraged.
    if not actor.strip():
        raise CandidateApprovalError("a decision requires a non-empty actor")
    if not reason.strip():
        raise CandidateApprovalError("a decision requires a non-empty reason")


def record_decision(
    controls_directory: Path,
    candidate_directory: Path,
    run_plan: dict[str, Any],
    candidate_index: int,
    decision: str,
    actor: str,
    reason: str,
    clock_function: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    """
    Description:
        Record one explicit operator decision with its evidence, atomically.
    Required State:
        The controls directory is intact and the candidate belongs to the plan.
    Usage:
        Called only by the operator-facing approve and reject commands.
    Parameters:
        controls_directory (Path): Read-only issue #50 artifact directory.
        candidate_directory (Path): Directory owning one candidate.
        run_plan (dict[str, Any]): Plan the candidate belongs to.
        candidate_index (int): Candidate ordinal being decided.
        decision (str): DECISION_APPROVE or DECISION_REJECT.
        actor (str): Human recording the decision.
        reason (str): Stated justification for the decision.
        clock_function (Callable[[], datetime]): Injected clock.
    Returns:
        dict[str, Any]: The approval record that was written.
    Other I/O:
        - files: reads controls and candidate artifacts; writes approval.json
          and validation.json inside the candidate directory only
    """
    require_decision_inputs(decision, actor, reason)

    # Validation is re-run at decision time rather than trusted from an earlier
    # report, so a candidate edited since generation cannot be approved.
    validation_report = candidate_validation.validate_candidate(
        controls_directory, candidate_directory, run_plan, candidate_index
    )
    candidate_validation.write_validation_report(candidate_directory, validation_report)

    if decision == DECISION_APPROVE:
        if bool(run_plan.get("explorationOnly")):
            raise CandidateApprovalError(
                "candidates from an exploration-only dimension override can never be approved "
                "(Gitea #55); regenerate the controls once dimensions agree"
            )
        if not validation_report["eligibleForApproval"]:
            raise CandidateApprovalError(
                "candidate is not eligible for approval; failing checks: "
                f"{validation_report['failures']}"
            )

    current_state = resolve_current_state(candidate_directory, validation_report)
    # The transition is authorized as an operator action. The same call with an
    # automation actor kind would be refused for an approval, which is what
    # keeps automated validation from ever approving anything.
    candidate_state.require_transition(current_state, decision, candidate_state.ACTOR_KIND_OPERATOR)

    control_artifacts = pixellab_client.load_control_artifacts(controls_directory)
    validation_report_path = candidate_directory / candidate_validation.VALIDATION_REPORT_NAME
    manifest = candidate_validation.read_candidate_manifest(candidate_directory)

    evidence = {
        "validationReportSha256": sha256_bytes(validation_report_path.read_bytes()),
        "candidateImageSha256": validation_report["evidence"].get("candidateImage", {}).get("sha256"),
        "controlInputs": dict(control_artifacts.source_manifest.get("inputs", {})),
        "requestCacheKey": manifest.get("request", {}).get("requestCacheKey"),
        "planId": run_plan.get("planId"),
        "sourceSha256": run_plan.get("source", {}).get("sha256"),
        "protectedLandmarks": validation_report["evidence"].get("protectedLandmarks"),
    }

    existing_record = read_approval_record(candidate_directory)
    previous_decisions = list(existing_record.get("decisions", [])) if existing_record else []
    new_decision = {
        "sequence": len(previous_decisions) + 1,
        "decision": decision,
        "actor": actor.strip(),
        "actorKind": candidate_state.ACTOR_KIND_OPERATOR,
        "recordedAt": format_decision_timestamp(clock_function()),
        "reason": reason.strip(),
        "previousState": current_state,
        "evidence": evidence,
    }

    record = {
        "contractVersion": CONTRACT_VERSION,
        "approvalVersion": APPROVAL_VERSION,
        "planId": run_plan.get("planId"),
        "candidateIndex": candidate_index,
        "seed": validation_report["seed"],
        "currentState": decision,
        # History is append-only: an earlier decision is superseded, never
        # deleted, so the record always explains how the candidate got here.
        "decisions": previous_decisions + [new_decision],
    }
    pixellab_client.write_file_atomically(
        candidate_directory / APPROVAL_RECORD_NAME, canonical_json_bytes(record)
    )
    return record
