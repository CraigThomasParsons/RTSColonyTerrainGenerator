#!/usr/bin/env python3
"""Deterministic run plan for bounded PixelLab candidate generation (#52).

A run plan is decided entirely offline, before anything is written and long
before anything could be submitted. It fixes the candidate count, the candidate
index of every candidate, the seed of every candidate, and the directory each
candidate will own. Re-deriving a plan from the same inputs produces the same
bytes, which is what makes an offline re-run reproducible and reviewable.

The plan deliberately carries no clock reading and no environment data, because
either would make identical inputs produce different bytes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# These modules are siblings in bin/. Running a script from bin/ puts that
# directory on sys.path automatically; tests add it explicitly. Nothing here
# mutates sys.path, so importing this module has no hidden side effect.
import pixellab_modules


visual_contract = pixellab_modules.load_visual_contract()

canonical_json_bytes = visual_contract.canonical_json_bytes
sha256_bytes = visual_contract.sha256_bytes

CONTRACT_VERSION = visual_contract.CONTRACT_VERSION
PLAN_VERSION = "1"
RUN_PLAN_NAME = "run-plan.json"
CONTROLS_DIRECTORY_NAME = "controls"
CANDIDATES_DIRECTORY_NAME = "candidates"

# The two modes an operator may ask for. Offline is the default everywhere and
# is the only mode this implementation phase ever exercised.
MODE_OFFLINE = "offline"
MODE_LIVE = "live"
ALL_MODES = (MODE_OFFLINE, MODE_LIVE)

# Bounds exist so that a typo in an operator argument cannot plan a large batch
# of paid generations. They are hard ceilings, not defaults to be tuned upward
# from a config file.
DEFAULT_CANDIDATE_COUNT = 1
MAXIMUM_CANDIDATE_COUNT = 8
DEFAULT_CANDIDATE_BUDGET = 1
MAXIMUM_CANDIDATE_BUDGET = 8


class CandidatePlanError(ValueError):
    """Represent inputs that cannot produce a safe, deterministic run plan."""


def candidate_directory_name(candidate_index: int) -> str:
    """
    Description:
        Build the stable directory name that owns one candidate's artifacts.
    Required State:
        The candidate index is a non-negative integer inside the plan bounds.
    Usage:
        Use for planning, execution, validation, and approval so all four agree.
    Parameters:
        candidate_index (int): Candidate ordinal within the run.
    Returns:
        str: Zero-padded directory name such as "candidate-000".
    Other I/O:
        - none
    """
    # Zero padding keeps lexical ordering equal to numeric ordering, which makes
    # a directory listing readable without sorting logic in every consumer.
    if candidate_index < 0:
        raise CandidatePlanError(f"candidate index must be non-negative; found {candidate_index}")
    return f"candidate-{candidate_index:03d}"


def derive_candidate_seeds(
    base_seed: int, candidate_count: int, explicit_seeds: list[int] | None
) -> list[int]:
    """
    Description:
        Fix one reproducible seed per candidate before anything is generated.
    Required State:
        Counts and seeds are already range-checked by the caller's parser.
    Usage:
        Call once while building a plan; never re-derive during execution.
    Parameters:
        base_seed (int): Seed of candidate zero when seeds are derived.
        candidate_count (int): Number of candidates in the run.
        explicit_seeds (list[int] | None): Operator-supplied seeds, if any.
    Returns:
        list[int]: One seed per candidate, in candidate-index order.
    Other I/O:
        - none
    """
    if candidate_count < 1:
        raise CandidatePlanError(f"candidate count must be at least 1; found {candidate_count}")
    if candidate_count > MAXIMUM_CANDIDATE_COUNT:
        raise CandidatePlanError(
            f"candidate count {candidate_count} exceeds the hard maximum {MAXIMUM_CANDIDATE_COUNT}"
        )

    # Explicit seeds win so that an operator can reproduce one specific historic
    # candidate without recreating the whole batch it came from.
    if explicit_seeds is not None:
        if len(explicit_seeds) != candidate_count:
            raise CandidatePlanError(
                f"{len(explicit_seeds)} explicit seeds were supplied for {candidate_count} candidates"
            )
        if len(set(explicit_seeds)) != len(explicit_seeds):
            raise CandidatePlanError("explicit seeds must be distinct so candidates stay comparable")
        return list(explicit_seeds)

    # The derived form is intentionally the most boring one available: a reader
    # can predict candidate three's seed without running anything.
    return [base_seed + candidate_index for candidate_index in range(candidate_count)]


def require_supported_mode(mode: str) -> str:
    """
    Description:
        Reject any execution mode outside the declared offline/live pair.
    Required State:
        None.
    Usage:
        Call before building a plan and again before executing one.
    Parameters:
        mode (str): Requested execution mode.
    Returns:
        str: The validated mode.
    Other I/O:
        - none
    """
    if mode not in ALL_MODES:
        raise CandidatePlanError(f"unknown mode {mode!r}; expected one of {list(ALL_MODES)}")
    return mode


def require_candidate_budget(candidate_budget: int, candidate_count: int) -> int:
    """
    Description:
        Enforce a small explicit ceiling on how many submissions a run may make.
    Required State:
        The candidate count was already validated.
    Usage:
        Call while building the plan, long before any submission is considered.
    Parameters:
        candidate_budget (int): Maximum number of paid submissions allowed.
        candidate_count (int): Number of candidates in the run.
    Returns:
        int: The validated budget.
    Other I/O:
        - none
    """
    if candidate_budget < 0:
        raise CandidatePlanError(f"candidate budget must be non-negative; found {candidate_budget}")
    if candidate_budget > MAXIMUM_CANDIDATE_BUDGET:
        raise CandidatePlanError(
            f"candidate budget {candidate_budget} exceeds the hard maximum {MAXIMUM_CANDIDATE_BUDGET}"
        )
    # A budget above the candidate count would be meaningless, and allowing it
    # would hide the fact that one candidate is at most one submission.
    if candidate_budget > candidate_count:
        raise CandidatePlanError(
            f"candidate budget {candidate_budget} exceeds the {candidate_count} planned candidates; "
            "one candidate is at most one submission"
        )
    return candidate_budget


def build_run_plan(
    source_sha256: str,
    source_file_name: str,
    controls_manifest: dict[str, Any],
    mode: str,
    base_seed: int,
    candidate_count: int,
    explicit_seeds: list[int] | None,
    candidate_budget: int,
) -> dict[str, Any]:
    """
    Description:
        Derive the complete, deterministic description of one candidate run.
    Required State:
        The controls manifest is the issue #50 template for this exact input.
    Usage:
        Build once per run; persist it before executing any candidate.
    Parameters:
        source_sha256 (str): Hash of the authoritative world payload bytes.
        source_file_name (str): Base name of the world payload file.
        controls_manifest (dict[str, Any]): Issue #50 generation-manifest template.
        mode (str): MODE_OFFLINE or MODE_LIVE.
        base_seed (int): Seed of candidate zero when seeds are derived.
        candidate_count (int): Number of candidates to plan.
        explicit_seeds (list[int] | None): Operator-supplied seeds, if any.
        candidate_budget (int): Maximum number of submissions this run may make.
    Returns:
        dict[str, Any]: Deterministic run plan ready to serialize.
    Other I/O:
        - none
    """
    require_supported_mode(mode)

    control_warnings = list(controls_manifest.get("warnings", []))
    # An exploration-only dimension override (Gitea #55) taints everything
    # downstream, so the plan records it as a first-class property rather than
    # leaving it buried in a warnings list that a consumer might not read.
    exploration_only = any(warning.startswith("EXPLORATION ONLY") for warning in control_warnings)

    if exploration_only:
        # Exploration overrides exist to inspect legacy artifacts locally. They
        # produce controls and nothing else: no candidate may be planned, so no
        # candidate can later be submitted or approved from ambiguous dimensions.
        seeds: list[int] = []
        effective_budget = 0
        candidates: list[dict[str, Any]] = []
    else:
        seeds = derive_candidate_seeds(base_seed, candidate_count, explicit_seeds)
        effective_budget = require_candidate_budget(candidate_budget, candidate_count)
        candidates = [
            {
                "candidateIndex": candidate_index,
                "seed": seeds[candidate_index],
                "directory": f"{CANDIDATES_DIRECTORY_NAME}/{candidate_directory_name(candidate_index)}",
                "state": "planned",
            }
            for candidate_index in range(candidate_count)
        ]

    plan_material = {
        "contractVersion": CONTRACT_VERSION,
        "planVersion": PLAN_VERSION,
        "mode": mode,
        "source": {"sha256": source_sha256, "fileName": source_file_name, "type": "worldpayload-json"},
        "controls": {
            "directory": CONTROLS_DIRECTORY_NAME,
            "endpoint": controls_manifest.get("endpoint"),
            "cacheKey": controls_manifest.get("cacheKey"),
            "inputs": dict(controls_manifest.get("inputs", {})),
        },
        "budget": {
            "candidateBudget": effective_budget,
            "requestedCandidateCount": candidate_count,
            "submissionsPerCandidate": 1,
        },
        "candidates": candidates,
        "explorationOnly": exploration_only,
        "warnings": control_warnings,
    }
    # The plan identifier is a hash of everything above, so two plans with the
    # same identifier are the same plan and must produce the same bytes.
    return {"planId": sha256_bytes(canonical_json_bytes(plan_material)), **plan_material}


def write_run_plan(output_root: Path, run_plan: dict[str, Any]) -> Path:
    """
    Description:
        Publish the run plan atomically so a crash never leaves a partial plan.
    Required State:
        The output root may not exist yet; it is created here.
    Usage:
        Call immediately after building the plan and before executing it.
    Parameters:
        output_root (Path): Run directory that owns controls and candidates.
        run_plan (dict[str, Any]): Plan to persist.
    Returns:
        Path: Path of the published run plan.
    Other I/O:
        - files: writes run-plan.json through a temporary file and rename
    """
    output_root.mkdir(parents=True, exist_ok=True)
    plan_path = output_root / RUN_PLAN_NAME
    temporary_path = output_root / f".{RUN_PLAN_NAME}.tmp"
    temporary_path.write_bytes(canonical_json_bytes(run_plan))
    temporary_path.replace(plan_path)
    return plan_path


def read_run_plan(output_root: Path) -> dict[str, Any]:
    """
    Description:
        Read a previously published run plan and confirm it is still coherent.
    Required State:
        The run directory was produced by a prior plan or run invocation.
    Usage:
        Call from validation and approval, which must not re-derive the plan.
    Parameters:
        output_root (Path): Run directory that owns controls and candidates.
    Returns:
        dict[str, Any]: Parsed run plan.
    Other I/O:
        - files: reads run-plan.json
    """
    plan_path = output_root / RUN_PLAN_NAME
    if not plan_path.is_file():
        raise CandidatePlanError(f"run plan not found: {plan_path}")

    try:
        run_plan = json.loads(plan_path.read_bytes())
    except json.JSONDecodeError as error:
        raise CandidatePlanError(f"run plan is not valid JSON: {error}") from None
    if not isinstance(run_plan, dict):
        raise CandidatePlanError(f"run plan must be a JSON object: {plan_path}")

    # Re-deriving the identifier proves the plan was not hand-edited between
    # generation and approval, which is exactly when tampering would matter.
    recorded_identifier = run_plan.get("planId")
    plan_material = {key: value for key, value in run_plan.items() if key != "planId"}
    if recorded_identifier != sha256_bytes(canonical_json_bytes(plan_material)):
        raise CandidatePlanError(
            f"run plan {plan_path} does not match its recorded planId; it was modified after generation"
        )
    return run_plan


def candidate_entry(run_plan: dict[str, Any], candidate_index: int) -> dict[str, Any]:
    """
    Description:
        Look one candidate up in a plan, refusing an index the plan never had.
    Required State:
        The plan was read through read_run_plan.
    Usage:
        Call from execution, validation, and approval before touching a directory.
    Parameters:
        run_plan (dict[str, Any]): Parsed run plan.
        candidate_index (int): Candidate ordinal to resolve.
    Returns:
        dict[str, Any]: The planned candidate entry.
    Other I/O:
        - none
    """
    for entry in run_plan.get("candidates", []):
        if entry.get("candidateIndex") == candidate_index:
            return entry
    raise CandidatePlanError(
        f"candidate index {candidate_index} is not part of this run plan; "
        "candidates are fixed when the plan is built"
    )
