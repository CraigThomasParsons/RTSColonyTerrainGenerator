#!/usr/bin/env python3
"""Bounded, deterministic PixelLab candidate orchestration (Gitea #52).

This is the operator entry point for the candidate lane. It turns one strict
world payload into the issue #50 control artifacts and a small, explicitly
bounded set of issue #51 candidate requests, then validates what came back and
lets a human — and only a human — approve or reject it.

Everything it adds is orchestration. Contract construction stays in
`visual_contract`; token handling, transport, cache, and polling stay in
`pixellab_client`. This module never opens a socket itself and never reads the
PixelLab token.

Defaults are chosen so that the safe thing happens when an operator types the
short command: the mode is offline, the budget is one, and an offline run
provably constructs no transport at all.

Fail-closed rules enforced here:

- A declared/tile dimension mismatch (Gitea #55) may produce controls only. No
  candidate is planned, so none can be submitted or approved.
- A map outside the PixelLab image_size range (Gitea #60) fails before any
  candidate directory is created.
- The submission budget is checked against cache misses before the first
  submission, and cache hits never consume it.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import candidate_approval
import candidate_plan
import candidate_state
import candidate_validation
import pixellab_modules


visual_contract = pixellab_modules.load_visual_contract()
pixellab_client = pixellab_modules.load_pixellab_client()

canonical_json_bytes = visual_contract.canonical_json_bytes
sha256_bytes = visual_contract.sha256_bytes

# Exit codes extend the issue #51 adapter's vocabulary so a wrapper can branch
# on an outcome without parsing text.
EXIT_SUCCESS = pixellab_client.EXIT_SUCCESS
EXIT_CONTRACT_ERROR = pixellab_client.EXIT_CONTRACT_ERROR
EXIT_CONFIGURATION_ERROR = pixellab_client.EXIT_CONFIGURATION_ERROR
EXIT_VALIDATION_REJECTED = 6
EXIT_BUDGET_EXCEEDED = 7


class OrchestrationError(Exception):
    """Base class for orchestration failures reported to an operator."""

    exit_code = EXIT_CONTRACT_ERROR


class BudgetError(OrchestrationError):
    """Represent a run that would exceed the explicit submission budget."""

    exit_code = EXIT_BUDGET_EXCEEDED


class LiveModeError(OrchestrationError):
    """Represent a live run that was not fully and explicitly authorized."""

    exit_code = EXIT_CONFIGURATION_ERROR


# --------------------------------------------------------------------------
# Zero-network evidence
# --------------------------------------------------------------------------


class RefusingTransportFactory:
    """Count and refuse every attempt to build a transport in offline mode."""

    def __init__(self) -> None:
        """
        Description:
            Start a counter that proves an offline run opened no socket.
        Required State:
            None.
        Usage:
            Install as AdapterSettings.transport_factory for every offline run.
        Parameters:
            none
        Returns:
            None: Constructs the factory.
        Other I/O:
            - none
        """
        self.attempts = 0

    def __call__(self):
        """
        Description:
            Refuse to construct a transport and record that it was attempted.
        Required State:
            None.
        Usage:
            Invoked by the adapter only on a code path that would go live.
        Parameters:
            none
        Returns:
            Never returns; always raises.
        Other I/O:
            - none
        """
        # Counting before raising means the evidence survives even when the
        # caller catches the exception.
        self.attempts += 1
        raise LiveModeError(
            "offline mode attempted to construct a network transport; no PixelLab request "
            "may be made outside an explicitly authorized live run"
        )


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------


def default_dry_run_function(adapter_settings: Any) -> dict[str, Any]:
    """
    Description:
        Run one candidate offline through the issue #51 adapter's dry-run mode.
    Required State:
        The adapter settings name intact controls and a separate output directory.
    Usage:
        Default injection point; tests replace it with a counting fake.
    Parameters:
        adapter_settings (Any): pixellab_client.AdapterSettings for one candidate.
    Returns:
        dict[str, Any]: The candidate manifest the adapter published.
    Other I/O:
        - files: writes generation-manifest.json into the candidate directory
    """
    return pixellab_client.run_dry_run_mode(adapter_settings)


def default_submit_function(adapter_settings: Any) -> dict[str, Any]:
    """
    Description:
        Run one candidate through the issue #51 adapter's submit mode.
    Required State:
        The caller already checked the budget and both live opt-ins.
    Usage:
        Default injection point for live runs; tests replace it with a fake.
    Parameters:
        adapter_settings (Any): pixellab_client.AdapterSettings for one candidate.
    Returns:
        dict[str, Any]: The candidate manifest the adapter published.
    Other I/O:
        - files: writes the candidate image, manifest, and cache entry
        - network: at most one generation submission plus bounded polling
    """
    return pixellab_client.run_submit_mode(adapter_settings)


@dataclass
class OrchestrationSettings:
    """Group one orchestrated run, with injectable seams for tests."""

    input_path: Path
    output_root: Path
    cache_directory: Path
    mode: str = candidate_plan.MODE_OFFLINE
    base_seed: int = 1
    candidate_count: int = candidate_plan.DEFAULT_CANDIDATE_COUNT
    explicit_seeds: list[int] | None = None
    candidate_budget: int = candidate_plan.DEFAULT_CANDIDATE_BUDGET
    allow_exploration_dimensions: bool = False
    enable_live_calls: bool = False
    confirm_credit_spend: bool = False
    # The adapter entry points are injected so tests can supply a fake client
    # boundary and assert exactly how many submissions were attempted.
    dry_run_function: Callable[[Any], dict[str, Any]] = default_dry_run_function
    submit_function: Callable[[Any], dict[str, Any]] = default_submit_function

    @property
    def controls_directory(self) -> Path:
        """
        Description:
            Resolve the read-only issue #50 control directory for this run.
        Required State:
            The output root has been chosen.
        Usage:
            Use everywhere controls are read; never write into it after planning.
        Parameters:
            none
        Returns:
            Path: The controls directory inside the run root.
        Other I/O:
            - none
        """
        return self.output_root / candidate_plan.CONTROLS_DIRECTORY_NAME

    def candidate_directory(self, candidate_index: int) -> Path:
        """
        Description:
            Resolve the directory that owns one candidate's artifacts.
        Required State:
            The candidate index belongs to this run's plan.
        Usage:
            Use for execution, validation, and approval alike.
        Parameters:
            candidate_index (int): Candidate ordinal.
        Returns:
            Path: Directory for that candidate.
        Other I/O:
            - none
        """
        return (
            self.output_root
            / candidate_plan.CANDIDATES_DIRECTORY_NAME
            / candidate_plan.candidate_directory_name(candidate_index)
        )


# --------------------------------------------------------------------------
# Planning
# --------------------------------------------------------------------------


def build_controls(settings: OrchestrationSettings) -> dict[str, Any]:
    """
    Description:
        Produce the issue #50 control artifacts for this run's input payload.
    Required State:
        The input path names a readable strict world payload.
    Usage:
        Called by plan and run before anything else happens.
    Parameters:
        settings (OrchestrationSettings): Resolved run settings.
    Returns:
        dict[str, Any]: The generation-manifest template that was written.
    Other I/O:
        - files: reads the payload; writes five artifacts into controls/
    """
    if not settings.input_path.is_file():
        raise OrchestrationError(f"world payload not found: {settings.input_path}")
    # write_contract owns the whole contract, including the Gitea #55 fail-closed
    # rule. This module only decides whether the override was explicitly asked
    # for; it never reinterprets a dimension mismatch itself.
    return visual_contract.write_contract(
        settings.input_path, settings.controls_directory, settings.allow_exploration_dimensions
    )


def require_submittable_map(settings: OrchestrationSettings) -> None:
    """
    Description:
        Fail closed on a map the allowlisted PixelLab endpoint cannot render.
    Required State:
        The controls directory holds a freshly written visual brief.
    Usage:
        Call after building controls and before planning any candidate.
    Parameters:
        settings (OrchestrationSettings): Resolved run settings.
    Returns:
        None: Completes when the map is inside the supported size range.
    Other I/O:
        - files: reads visual-brief.json
    """
    brief = json.loads((settings.controls_directory / pixellab_client.VISUAL_BRIEF_NAME).read_bytes())
    dimensions = brief.get("dimensions", {})
    # Checking here, rather than at submission time, means an unsupported map
    # never creates candidate directories that could later look approvable.
    pixellab_client.require_submittable_image_size(dimensions.get("width"), dimensions.get("height"))


def plan_run(settings: OrchestrationSettings) -> dict[str, Any]:
    """
    Description:
        Build controls and derive the deterministic plan for this run.
    Required State:
        The input payload is readable and the output root is writable.
    Usage:
        Call from the plan command, and as the first step of every run.
    Parameters:
        settings (OrchestrationSettings): Resolved run settings.
    Returns:
        dict[str, Any]: The run plan that was published.
    Other I/O:
        - files: writes controls/ and run-plan.json
    """
    candidate_plan.require_supported_mode(settings.mode)
    controls_manifest = build_controls(settings)
    require_submittable_map(settings)

    source_bytes = settings.input_path.read_bytes()
    run_plan = candidate_plan.build_run_plan(
        source_sha256=sha256_bytes(source_bytes),
        source_file_name=settings.input_path.name,
        controls_manifest=controls_manifest,
        mode=settings.mode,
        base_seed=settings.base_seed,
        candidate_count=settings.candidate_count,
        explicit_seeds=settings.explicit_seeds,
        candidate_budget=settings.candidate_budget,
    )
    candidate_plan.write_run_plan(settings.output_root, run_plan)
    return run_plan


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------


def build_adapter_settings(
    settings: OrchestrationSettings, candidate_index: int, seed: int, transport_factory: Any
):
    """
    Description:
        Build the issue #51 adapter settings for exactly one candidate.
    Required State:
        The candidate belongs to this run's plan.
    Usage:
        Call once per candidate, in both offline and live modes.
    Parameters:
        settings (OrchestrationSettings): Resolved run settings.
        candidate_index (int): Candidate ordinal.
        seed (int): Fixed seed for this candidate.
        transport_factory (Any): Factory the adapter may use for live calls.
    Returns:
        AdapterSettings: Settings for one candidate invocation.
    Other I/O:
        - none
    """
    adapter_settings = pixellab_client.AdapterSettings(
        controls_directory=settings.controls_directory,
        output_directory=settings.candidate_directory(candidate_index),
        cache_directory=settings.cache_directory,
        seed=seed,
        candidate_index=candidate_index,
    )
    adapter_settings.transport_factory = transport_factory
    return adapter_settings


def summarize_cache_state(settings: OrchestrationSettings, run_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Description:
        Decide, offline, which planned candidates would need a paid submission.
    Required State:
        Controls exist; the cache directory may or may not exist yet.
    Usage:
        Call before any submission so the budget is enforced in advance.
    Parameters:
        settings (OrchestrationSettings): Resolved run settings.
        run_plan (dict[str, Any]): Plan being executed.
    Returns:
        list[dict[str, Any]]: One record per candidate with its cache verdict.
    Other I/O:
        - files: reads the controls and the content-addressed cache
    """
    cache_states: list[dict[str, Any]] = []
    for entry in run_plan["candidates"]:
        # A refusing transport factory is installed even for this offline
        # inspection, so a future change that reached the network here would
        # fail loudly instead of quietly spending.
        adapter_settings = build_adapter_settings(
            settings, entry["candidateIndex"], entry["seed"], RefusingTransportFactory()
        )
        _, _, request_cache_key, _ = pixellab_client.prepare_generation(adapter_settings)
        cached_image = pixellab_client.lookup_cached_image(settings.cache_directory, request_cache_key)
        cache_states.append(
            {
                "candidateIndex": entry["candidateIndex"],
                "seed": entry["seed"],
                "requestCacheKey": request_cache_key,
                "cacheHit": cached_image is not None,
            }
        )
    return cache_states


def require_budget(run_plan: dict[str, Any], cache_states: list[dict[str, Any]]) -> int:
    """
    Description:
        Refuse a run whose cache misses would exceed the explicit budget.
    Required State:
        Cache state was computed offline for every planned candidate.
    Usage:
        Call once, before the first submission of a live run.
    Parameters:
        run_plan (dict[str, Any]): Plan being executed.
        cache_states (list[dict[str, Any]]): Per-candidate cache verdicts.
    Returns:
        int: The number of submissions this run is allowed to make.
    Other I/O:
        - none
    """
    budget = run_plan["budget"]["candidateBudget"]
    # Cache hits are free by construction — the adapter returns before building
    # a transport — so they must not consume the operator's spending budget.
    required_submissions = sum(1 for state in cache_states if not state["cacheHit"])
    if required_submissions > budget:
        raise BudgetError(
            f"this run would need {required_submissions} submissions but the explicit candidate "
            f"budget is {budget}; raise --candidate-budget deliberately or reduce --candidates. "
            "Cached candidates do not consume the budget."
        )
    return required_submissions


def require_live_authorization(settings: OrchestrationSettings, run_plan: dict[str, Any]) -> None:
    """
    Description:
        Refuse a live run that is not explicitly and completely authorized.
    Required State:
        The plan was built and its exploration flag is known.
    Usage:
        Call before constructing any live transport.
    Parameters:
        settings (OrchestrationSettings): Resolved run settings.
        run_plan (dict[str, Any]): Plan being executed.
    Returns:
        None: Completes when the live run is authorized.
    Other I/O:
        - none
    """
    if not settings.enable_live_calls:
        raise LiveModeError(
            "live mode requires --enable-live-calls; the default offline mode makes no request"
        )
    if not settings.confirm_credit_spend:
        raise LiveModeError(
            "live mode requires --confirm-credit-spend; it acknowledges that each cache miss "
            "costs exactly one PixelLab generation"
        )
    # Belt and braces: the plan already refuses to contain candidates when the
    # exploration override was used, and a live run refuses the plan outright.
    if bool(run_plan.get("explorationOnly")):
        raise LiveModeError(
            "controls built with the exploration-only dimension override may never be submitted "
            "to PixelLab (Gitea #55)"
        )


def execute_run(settings: OrchestrationSettings) -> dict[str, Any]:
    """
    Description:
        Plan, execute, and validate one bounded batch of candidates.
    Required State:
        The input payload is readable; live mode additionally needs both opt-ins.
    Usage:
        Backs the run command; tests call it directly with injected functions.
    Parameters:
        settings (OrchestrationSettings): Resolved run settings.
    Returns:
        dict[str, Any]: Run summary including per-candidate outcomes.
    Other I/O:
        - files: writes controls/, run-plan.json, and one directory per candidate
        - network: none in offline mode; at most one submission per cache miss
          in an authorized live run
    """
    run_plan = plan_run(settings)

    if bool(run_plan.get("explorationOnly")):
        # Local controls only. Refusing to plan candidates here is what makes
        # "never eligible for live submission or approval" structural rather
        # than a rule someone has to remember.
        return {
            "mode": settings.mode,
            "planId": run_plan["planId"],
            "explorationOnly": True,
            "candidates": [],
            "networkTransportAttempts": 0,
            "submissions": 0,
            "warnings": run_plan["warnings"]
            + ["EXPLORATION ONLY: controls were produced; no candidate was planned (Gitea #55)"],
        }

    cache_states = summarize_cache_state(settings, run_plan)
    planned_submissions = require_budget(run_plan, cache_states)

    offline_transport_factory = RefusingTransportFactory()
    if settings.mode == candidate_plan.MODE_LIVE:
        require_live_authorization(settings, run_plan)

    candidate_summaries: list[dict[str, Any]] = []
    submissions_made = 0

    for entry, cache_state in zip(run_plan["candidates"], cache_states):
        candidate_index = entry["candidateIndex"]
        candidate_directory = settings.candidate_directory(candidate_index)
        candidate_directory.mkdir(parents=True, exist_ok=True)

        if settings.mode == candidate_plan.MODE_OFFLINE:
            adapter_settings = build_adapter_settings(
                settings, candidate_index, entry["seed"], offline_transport_factory
            )
            settings.dry_run_function(adapter_settings)
        else:
            # The live transport is the adapter's own default; this module never
            # builds one and never touches the token.
            adapter_settings = pixellab_client.AdapterSettings(
                controls_directory=settings.controls_directory,
                output_directory=candidate_directory,
                cache_directory=settings.cache_directory,
                seed=entry["seed"],
                candidate_index=candidate_index,
            )
            settings.submit_function(adapter_settings)
            # A cache hit reaches the same call but returns before any transport
            # is constructed, so only a miss counts as a submission.
            if not cache_state["cacheHit"]:
                submissions_made += 1

        report = candidate_validation.validate_candidate(
            settings.controls_directory, candidate_directory, run_plan, candidate_index
        )
        candidate_validation.write_validation_report(candidate_directory, report)
        candidate_summaries.append(
            {
                "candidateIndex": candidate_index,
                "seed": entry["seed"],
                "requestCacheKey": cache_state["requestCacheKey"],
                "cacheHit": cache_state["cacheHit"],
                "state": report["resultingState"],
                "structurallyValid": report["structurallyValid"],
                "eligibleForApproval": report["eligibleForApproval"],
                "failures": report["failures"],
            }
        )

    return {
        "mode": settings.mode,
        "planId": run_plan["planId"],
        "explorationOnly": False,
        "candidates": candidate_summaries,
        "networkTransportAttempts": offline_transport_factory.attempts,
        "plannedSubmissions": planned_submissions,
        "submissions": submissions_made,
        "warnings": run_plan["warnings"],
    }


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def report_status(settings: OrchestrationSettings) -> dict[str, Any]:
    """
    Description:
        Re-validate an existing run and report each candidate's current state.
    Required State:
        The output root holds a run plan produced by a previous invocation.
    Usage:
        Backs the validate command and the operator's pre-approval review.
    Parameters:
        settings (OrchestrationSettings): Settings naming the run directory.
    Returns:
        dict[str, Any]: Per-candidate state, validation outcome, and decisions.
    Other I/O:
        - files: reads the run, writes a refreshed validation.json per candidate
    """
    run_plan = candidate_plan.read_run_plan(settings.output_root)
    candidate_reports: list[dict[str, Any]] = []

    for entry in run_plan["candidates"]:
        candidate_index = entry["candidateIndex"]
        candidate_directory = settings.candidate_directory(candidate_index)
        report = candidate_validation.validate_candidate(
            settings.controls_directory, candidate_directory, run_plan, candidate_index
        )
        candidate_validation.write_validation_report(candidate_directory, report)
        approval_record = candidate_approval.read_approval_record(candidate_directory)
        candidate_reports.append(
            {
                "candidateIndex": candidate_index,
                "seed": entry["seed"],
                # An operator decision, once made, is the candidate's state.
                "state": candidate_approval.resolve_current_state(candidate_directory, report),
                "structurallyValid": report["structurallyValid"],
                "eligibleForApproval": report["eligibleForApproval"],
                "failures": report["failures"],
                "decisionCount": len(approval_record["decisions"]) if approval_record else 0,
            }
        )

    return {
        "planId": run_plan["planId"],
        "explorationOnly": bool(run_plan.get("explorationOnly")),
        "candidates": candidate_reports,
    }


def decide_candidate(
    settings: OrchestrationSettings,
    candidate_index: int,
    decision: str,
    actor: str,
    reason: str,
) -> dict[str, Any]:
    """
    Description:
        Record one explicit operator approval or rejection for a candidate.
    Required State:
        The run directory holds a plan and the named candidate's artifacts.
    Usage:
        Backs the approve and reject commands only.
    Parameters:
        settings (OrchestrationSettings): Settings naming the run directory.
        candidate_index (int): Candidate ordinal being decided.
        decision (str): candidate_approval.DECISION_APPROVE or DECISION_REJECT.
        actor (str): Human recording the decision.
        reason (str): Stated justification.
    Returns:
        dict[str, Any]: The approval record that was written.
    Other I/O:
        - files: writes approval.json and validation.json in the candidate directory
    """
    run_plan = candidate_plan.read_run_plan(settings.output_root)
    return candidate_approval.record_decision(
        controls_directory=settings.controls_directory,
        candidate_directory=settings.candidate_directory(candidate_index),
        run_plan=run_plan,
        candidate_index=candidate_index,
        decision=decision,
        actor=actor,
        reason=reason,
    )


# --------------------------------------------------------------------------
# Command-line interface
# --------------------------------------------------------------------------


def parse_explicit_seeds(seed_text: str | None) -> list[int] | None:
    """
    Description:
        Parse an optional comma-separated list of fixed candidate seeds.
    Required State:
        None.
    Usage:
        Call while translating arguments into settings.
    Parameters:
        seed_text (str | None): Comma-separated seeds, or None.
    Returns:
        list[int] | None: Parsed seeds, or None when seeds are derived.
    Other I/O:
        - none
    """
    if seed_text is None:
        return None
    try:
        return [int(part.strip()) for part in seed_text.split(",") if part.strip()]
    except ValueError as error:
        raise OrchestrationError(f"--seeds must be a comma-separated list of integers: {error}") from None


def build_argument_parser() -> argparse.ArgumentParser:
    """
    Description:
        Define the operator interface for planning, running, and deciding.
    Required State:
        None.
    Usage:
        Called by main and by tests that assert on help output.
    Parameters:
        none
    Returns:
        argparse.ArgumentParser: Configured parser with subcommands.
    Other I/O:
        - none
    """
    parser = argparse.ArgumentParser(
        prog="candidate_orchestrator.py",
        description=(
            "Deterministic, bounded PixelLab candidate orchestration. Defaults to offline "
            "mode, which makes no network request and spends no credits."
        ),
        epilog=(
            f"The PixelLab token is read only by pixellab_client.py, only from "
            f"{pixellab_client.TOKEN_ENVIRONMENT_VARIABLE}, and only during an authorized live "
            "run. This orchestrator never reads, stores, or prints it."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_run_directory_arguments(subparser: argparse.ArgumentParser) -> None:
        """Attach the paths every command needs to locate a run."""
        subparser.add_argument("--output", required=True, type=Path, help="run directory root")
        subparser.add_argument(
            "--cache", type=Path, help="content-addressed cache root shared across runs"
        )

    def add_planning_arguments(subparser: argparse.ArgumentParser) -> None:
        """Attach the arguments that determine a deterministic plan."""
        subparser.add_argument("--input", required=True, type=Path, help="strict JSON worldpayload file")
        subparser.add_argument(
            "--seed", type=int, default=1, help="seed of candidate zero when seeds are derived (default: 1)"
        )
        subparser.add_argument(
            "--candidates",
            type=int,
            default=candidate_plan.DEFAULT_CANDIDATE_COUNT,
            help=f"number of candidates, at most {candidate_plan.MAXIMUM_CANDIDATE_COUNT} "
            f"(default: {candidate_plan.DEFAULT_CANDIDATE_COUNT})",
        )
        subparser.add_argument(
            "--seeds",
            type=str,
            default=None,
            help="explicit comma-separated seeds, one per candidate, instead of derived seeds",
        )
        subparser.add_argument(
            "--candidate-budget",
            type=int,
            default=candidate_plan.DEFAULT_CANDIDATE_BUDGET,
            help=f"maximum paid submissions this run may make; cache hits are free and do not "
            f"consume it (default: {candidate_plan.DEFAULT_CANDIDATE_BUDGET})",
        )
        subparser.add_argument(
            "--mode",
            choices=candidate_plan.ALL_MODES,
            default=candidate_plan.MODE_OFFLINE,
            help="offline builds requests and makes no network call; live may spend credits "
            "(default: offline)",
        )
        subparser.add_argument(
            "--allow-exploration-dimensions",
            action="store_true",
            help="exploration only: accept a declared/tile dimension mismatch (Gitea #55). "
            "Produces controls only; no candidate is planned, submitted, or approvable.",
        )
        subparser.add_argument(
            "--enable-live-calls",
            action="store_true",
            help="required for --mode live; without it no transport is ever constructed",
        )
        subparser.add_argument(
            "--confirm-credit-spend",
            action="store_true",
            help="required in addition to --enable-live-calls; acknowledges that each cache miss "
            "costs exactly one PixelLab generation",
        )

    plan_parser = subparsers.add_parser("plan", help="build controls and publish a deterministic run plan")
    add_run_directory_arguments(plan_parser)
    add_planning_arguments(plan_parser)

    run_parser = subparsers.add_parser("run", help="plan, execute, and validate a bounded candidate batch")
    add_run_directory_arguments(run_parser)
    add_planning_arguments(run_parser)

    validate_parser = subparsers.add_parser(
        "validate", help="re-validate an existing run and report every candidate state"
    )
    add_run_directory_arguments(validate_parser)

    for decision_name, decision_help in (
        ("approve", "record an explicit human approval for one candidate"),
        ("reject", "record an explicit human rejection for one candidate"),
    ):
        decision_parser = subparsers.add_parser(decision_name, help=decision_help)
        add_run_directory_arguments(decision_parser)
        decision_parser.add_argument(
            "--candidate", required=True, type=int, help="candidate index to decide"
        )
        decision_parser.add_argument(
            "--actor", required=True, type=str, help="name of the human recording this decision"
        )
        decision_parser.add_argument(
            "--reason", required=True, type=str, help="why this decision was made"
        )

    return parser


def build_settings(arguments: argparse.Namespace) -> OrchestrationSettings:
    """
    Description:
        Translate parsed arguments into orchestration settings.
    Required State:
        Arguments were parsed successfully.
    Usage:
        Called by main; tests construct OrchestrationSettings directly instead.
    Parameters:
        arguments (argparse.Namespace): Parsed arguments.
    Returns:
        OrchestrationSettings: Settings for this invocation.
    Other I/O:
        - none
    """
    # validate, approve, and reject read an existing run, so the planning
    # arguments are absent for them and sensible defaults stand in.
    output_root = arguments.output
    cache_directory = arguments.cache
    if cache_directory is None:
        cache_directory = output_root / "cache"
    return OrchestrationSettings(
        input_path=getattr(arguments, "input", None) or Path("."),
        output_root=output_root,
        cache_directory=cache_directory,
        mode=getattr(arguments, "mode", candidate_plan.MODE_OFFLINE),
        base_seed=getattr(arguments, "seed", 1),
        candidate_count=getattr(arguments, "candidates", candidate_plan.DEFAULT_CANDIDATE_COUNT),
        explicit_seeds=parse_explicit_seeds(getattr(arguments, "seeds", None)),
        candidate_budget=getattr(arguments, "candidate_budget", candidate_plan.DEFAULT_CANDIDATE_BUDGET),
        allow_exploration_dimensions=getattr(arguments, "allow_exploration_dimensions", False),
        enable_live_calls=getattr(arguments, "enable_live_calls", False),
        confirm_credit_spend=getattr(arguments, "confirm_credit_spend", False),
    )


def main(argv: list[str] | None = None) -> int:
    """
    Description:
        Parse arguments, run one command, and print a canonical JSON summary.
    Required State:
        Python 3.10 or newer and a readable world payload for plan and run.
    Usage:
        Run from the repository root or through a future stage wrapper.
    Parameters:
        argv (list[str] | None): Argument vector, or None to use sys.argv.
    Returns:
        int: Zero on success, or a command-specific non-zero failure code.
    Other I/O:
        - stdout: one canonical JSON summary line
        - stderr: actionable failure messages
    """
    arguments = build_argument_parser().parse_args(argv)
    settings = build_settings(arguments)

    try:
        if arguments.command == "plan":
            run_plan = plan_run(settings)
            summary = {
                "command": "plan",
                "planId": run_plan["planId"],
                "mode": run_plan["mode"],
                "candidateCount": len(run_plan["candidates"]),
                "candidateBudget": run_plan["budget"]["candidateBudget"],
                "explorationOnly": run_plan["explorationOnly"],
                "networkRequests": 0,
            }
        elif arguments.command == "run":
            result = execute_run(settings)
            summary = {
                "command": "run",
                "planId": result["planId"],
                "mode": result["mode"],
                "explorationOnly": result["explorationOnly"],
                "candidates": result["candidates"],
                "submissions": result["submissions"],
                # An offline run reports its own proof: nothing ever asked for
                # a transport, so nothing could have reached the network.
                "networkTransportAttempts": result["networkTransportAttempts"],
            }
        elif arguments.command == "validate":
            status = report_status(settings)
            summary = {"command": "validate", **status}
            # A wrapper must be able to branch on "something failed structurally"
            # without parsing the report, so the exit code carries that verdict.
            if any(not candidate["structurallyValid"] for candidate in status["candidates"]):
                print(json.dumps(summary, sort_keys=True))
                return EXIT_VALIDATION_REJECTED
        else:
            decision = (
                candidate_approval.DECISION_APPROVE
                if arguments.command == "approve"
                else candidate_approval.DECISION_REJECT
            )
            record = decide_candidate(
                settings, arguments.candidate, decision, arguments.actor, arguments.reason
            )
            summary = {
                "command": arguments.command,
                "candidateIndex": record["candidateIndex"],
                "currentState": record["currentState"],
                "decisionCount": len(record["decisions"]),
            }
    except (
        OrchestrationError,
        candidate_plan.CandidatePlanError,
        candidate_validation.CandidateValidationError,
        candidate_approval.CandidateApprovalError,
        candidate_state.CandidateStateError,
        visual_contract.ContractError,
        pixellab_client.PixelLabError,
        OSError,
    ) as error:
        print(f"candidate orchestration failed: {error}", file=sys.stderr)
        return getattr(error, "exit_code", EXIT_CONTRACT_ERROR)

    print(json.dumps(summary, sort_keys=True))
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
