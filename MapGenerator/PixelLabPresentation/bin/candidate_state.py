#!/usr/bin/env python3
"""Explicit candidate lifecycle states for the PixelLab candidate lane (#52).

Issue #49 requires that a generated image can never quietly become the active
presentation. This module is the single place that says which candidate states
exist, which transitions are legal, and — most importantly — which transitions
automation is forbidden to perform.

The rule that motivates the whole module: automated validation may move a
candidate to `rejected`, but only an explicit local operator action may move a
candidate to `human-approved`.
"""

from __future__ import annotations


# --------------------------------------------------------------------------
# States
# --------------------------------------------------------------------------

# A candidate exists in the run plan but nothing has been written for it yet.
STATE_PLANNED = "planned"

# The request was built entirely offline. No socket was opened and no credit
# was spent. This is the default terminal state of an offline run.
STATE_DRY_RUN = "dry-run"

# A generation was submitted and accepted remotely but has not been collected.
STATE_PROCESSING = "processing"

# An image exists locally and passed every automated structural check.
STATE_GENERATED = "generated"

# The candidate failed automated validation or an operator rejected it. A
# rejected candidate can never become the active preview.
STATE_REJECTED = "rejected"

# An operator explicitly approved the candidate, on the record, with evidence.
STATE_HUMAN_APPROVED = "human-approved"

ALL_STATES = (
    STATE_PLANNED,
    STATE_DRY_RUN,
    STATE_PROCESSING,
    STATE_GENERATED,
    STATE_REJECTED,
    STATE_HUMAN_APPROVED,
)

# Only an operator decision may produce these states. Automation that reaches
# for one of them is a defect, not a policy choice, so it raises.
OPERATOR_ONLY_STATES = frozenset({STATE_HUMAN_APPROVED})

# Actor kinds recorded on every transition so that the evidence trail names who
# caused a state change rather than only what changed.
ACTOR_KIND_AUTOMATION = "automation"
ACTOR_KIND_OPERATOR = "operator"
ALL_ACTOR_KINDS = (ACTOR_KIND_AUTOMATION, ACTOR_KIND_OPERATOR)

# Legal successor states. Rejection is reachable from every non-terminal state
# because failing closed must always be available.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    STATE_PLANNED: frozenset({STATE_DRY_RUN, STATE_PROCESSING, STATE_GENERATED, STATE_REJECTED}),
    STATE_DRY_RUN: frozenset({STATE_PROCESSING, STATE_GENERATED, STATE_REJECTED}),
    STATE_PROCESSING: frozenset({STATE_GENERATED, STATE_REJECTED}),
    STATE_GENERATED: frozenset({STATE_HUMAN_APPROVED, STATE_REJECTED}),
    # A decision may be revisited by a later explicit operator decision, but
    # never by automation; that restriction is enforced by actor kind below.
    STATE_REJECTED: frozenset({STATE_HUMAN_APPROVED}),
    STATE_HUMAN_APPROVED: frozenset({STATE_REJECTED}),
}


class CandidateStateError(ValueError):
    """Represent an illegal or unauthorized candidate state transition."""


def require_known_state(state: str) -> str:
    """
    Description:
        Reject any state value that is not part of the declared lifecycle.
    Required State:
        None.
    Usage:
        Call when reading a state back from a persisted manifest or record.
    Parameters:
        state (str): Candidate state value to check.
    Returns:
        str: The validated state value.
    Other I/O:
        - none
    """
    # Guard early: an unknown state read from disk means the artifact was
    # written by something that does not share this contract.
    if state not in ALL_STATES:
        raise CandidateStateError(f"unknown candidate state {state!r}; expected one of {list(ALL_STATES)}")
    return state


def require_known_actor_kind(actor_kind: str) -> str:
    """
    Description:
        Reject any actor kind outside the declared automation/operator pair.
    Required State:
        None.
    Usage:
        Call at the top of every transition request.
    Parameters:
        actor_kind (str): Who is requesting the transition.
    Returns:
        str: The validated actor kind.
    Other I/O:
        - none
    """
    if actor_kind not in ALL_ACTOR_KINDS:
        raise CandidateStateError(
            f"unknown actor kind {actor_kind!r}; expected one of {list(ALL_ACTOR_KINDS)}"
        )
    return actor_kind


def require_transition(current_state: str, next_state: str, actor_kind: str) -> str:
    """
    Description:
        Authorize one candidate state change, or refuse it with a reason.
    Required State:
        Both states belong to this lifecycle and the actor kind is declared.
    Usage:
        Call before writing any state to a manifest or approval record.
    Parameters:
        current_state (str): State recorded before the change.
        next_state (str): Requested new state.
        actor_kind (str): ACTOR_KIND_AUTOMATION or ACTOR_KIND_OPERATOR.
    Returns:
        str: The authorized next state.
    Other I/O:
        - none
    """
    require_known_state(current_state)
    require_known_state(next_state)
    require_known_actor_kind(actor_kind)

    # This is the safety property issue #49 asks for: no automated path, however
    # convincing its validation looked, may mark a candidate human-approved.
    if actor_kind == ACTOR_KIND_AUTOMATION and next_state in OPERATOR_ONLY_STATES:
        raise CandidateStateError(
            f"automation may not set state {next_state!r}; approval requires an explicit "
            "local operator action recorded with actor, time, and reason"
        )

    if next_state not in ALLOWED_TRANSITIONS[current_state]:
        raise CandidateStateError(
            f"illegal candidate transition {current_state!r} -> {next_state!r}"
        )
    return next_state
