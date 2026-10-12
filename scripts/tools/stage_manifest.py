#!/usr/bin/env python3
"""Evaluate immutable evidence for one Terrain full-stack delivery stage.

What it does:
    Reads a versioned stage manifest and its component receipts, then emits a
    deterministic readiness result without changing Git, Gitea, or GitHub.

Why it exists:
    Automated merge phases need a small, fail-closed interface that can prove
    which exact manifest and commits were verified before requesting mutation.

How to use:
    python3 scripts/tools/stage_manifest.py evaluate <manifest> <receipt>...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

MANIFEST_PROTOCOL = "terrain.stage-manifest/v1"
RECEIPT_PROTOCOL = "terrain.stage-receipt/v1"
RESULT_PROTOCOL = "terrain.stage-evaluation/v1"
REQUIRED_SIDES = ("client", "contract", "server", "verification")


def canonical_json(document: dict[str, Any]) -> str:
    """Serialize a document with stable ordering for digest and output use."""
    return json.dumps(document, separators=(",", ":"), sort_keys=True)


def manifest_digest(manifest: dict[str, Any]) -> str:
    """Return the content digest binding receipts to an exact manifest."""
    encoded_manifest = canonical_json(manifest).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded_manifest).hexdigest()


def evaluate_stage(manifest_path: Path, receipt_paths: list[Path]) -> dict[str, Any]:
    """Evaluate whether every declared component has current passing evidence."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = manifest_digest(manifest)
    reasons = _validate_manifest(manifest)

    declared_sides = {
        str(component.get("side", "")) for component in manifest.get("components", [])
    }
    excepted_sides = {
        str(exception.get("side", ""))
        for exception in manifest.get("coverageExceptions", [])
        if _is_approved_exception(exception)
    }
    for required_side in REQUIRED_SIDES:
        if required_side not in declared_sides and required_side not in excepted_sides:
            reasons.append({"code": "missing-coverage", "side": required_side})

    receipts_by_component: dict[str, list[dict[str, Any]]] = {}
    for receipt_path in receipt_paths:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        component_id = str(receipt.get("componentId", ""))
        receipts_by_component.setdefault(component_id, []).append(receipt)

    passed_component_ids: set[str] = set()
    components = manifest.get("components", [])
    for component in components:
        component_id = str(component.get("id", ""))
        matching_receipts = receipts_by_component.get(component_id, [])
        if len(matching_receipts) == 0:
            reasons.append({"code": "missing-receipt", "componentId": component_id})
            continue

        distinct_receipts = {canonical_json(receipt) for receipt in matching_receipts}
        if len(distinct_receipts) > 1:
            reasons.append(
                {"code": "contradictory-receipts", "componentId": component_id}
            )
            continue

        receipt = matching_receipts[0]
        if not _is_valid_receipt(receipt, manifest, component):
            reasons.append({"code": "invalid-receipt", "componentId": component_id})
            continue

        if receipt.get("manifestDigest") != digest:
            reasons.append({"code": "stale-receipt", "componentId": component_id})
            continue

        if receipt.get("result") != "passed":
            reasons.append({"code": "failed-receipt", "componentId": component_id})
            continue

        passed_component_ids.add(component_id)

    state = _classify_state(reasons)
    next_eligible_components = _next_eligible_components(
        components, receipts_by_component, passed_component_ids, state
    )

    return {
        "protocol": RESULT_PROTOCOL,
        "stageId": manifest.get("stageId", ""),
        "manifestDigest": digest,
        "state": state,
        "reasons": reasons,
        "nextEligibleComponents": next_eligible_components,
    }


def _next_eligible_components(
    components: list[dict[str, Any]],
    receipts_by_component: dict[str, list[dict[str, Any]]],
    passed_component_ids: set[str],
    state: str,
) -> list[str]:
    """Return deterministic unstarted components whose dependencies passed."""
    if state in ("contradictory", "stale"):
        return []

    eligible: list[str] = []
    for component in components:
        component_id = str(component.get("id", ""))
        dependencies = set(component.get("dependsOn", []))
        if component_id in receipts_by_component:
            continue
        if dependencies.issubset(passed_component_ids):
            eligible.append(component_id)
    return sorted(eligible)


def _is_approved_exception(exception: dict[str, Any]) -> bool:
    """Require explicit human identity, timestamp, and rationale for exclusions."""
    return all(
        isinstance(exception.get(field), str) and len(exception[field].strip()) > 0
        for field in ("approvedBy", "approvedAt", "reason")
    )


def _validate_manifest(manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Return deterministic contradictions in the stage declaration."""
    reasons: list[dict[str, str]] = []
    if manifest.get("protocol") != MANIFEST_PROTOCOL:
        reasons.append({"code": "invalid-manifest", "field": "protocol"})

    base_commit = str(manifest.get("baseCommit", ""))
    if re.fullmatch(r"[0-9a-f]{40}", base_commit) is None:
        reasons.append({"code": "invalid-manifest", "field": "baseCommit"})

    integration_branch = str(manifest.get("integrationBranch", ""))
    if not integration_branch.startswith("stage/"):
        reasons.append({"code": "invalid-manifest", "field": "integrationBranch"})

    components = manifest.get("components", [])
    component_ids = [str(component.get("id", "")) for component in components]
    known_component_ids = set(component_ids)
    if len(known_component_ids) != len(component_ids) or "" in known_component_ids:
        reasons.append({"code": "invalid-manifest", "field": "components"})

    for component in components:
        component_id = str(component.get("id", ""))
        dependencies = component.get("dependsOn", [])
        if any(dependency not in known_component_ids for dependency in dependencies):
            reasons.append({"code": "unknown-dependency", "componentId": component_id})

    if _has_dependency_cycle(components):
        reasons.append({"code": "dependency-cycle"})

    return reasons


def _has_dependency_cycle(components: list[dict[str, Any]]) -> bool:
    """Detect a cycle without deriving an execution order from invalid input."""
    dependencies_by_component = {
        str(component.get("id", "")): list(component.get("dependsOn", []))
        for component in components
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(component_id: str) -> bool:
        if component_id in visiting:
            return True
        if component_id in visited:
            return False

        visiting.add(component_id)
        for dependency in dependencies_by_component.get(component_id, []):
            if dependency in dependencies_by_component and visit(dependency):
                return True
        visiting.remove(component_id)
        visited.add(component_id)
        return False

    return any(visit(component_id) for component_id in dependencies_by_component)


def _is_valid_receipt(
    receipt: dict[str, Any], manifest: dict[str, Any], component: dict[str, Any]
) -> bool:
    """Validate immutable identity and command evidence for one component."""
    result_commit = str(receipt.get("resultCommit", ""))
    evidence = receipt.get("evidence", [])
    identity_matches = (
        receipt.get("protocol") == RECEIPT_PROTOCOL
        and receipt.get("stageId") == manifest.get("stageId")
        and receipt.get("componentId") == component.get("id")
        and receipt.get("issue") == component.get("issue")
        and re.fullmatch(r"[0-9a-f]{40}", result_commit) is not None
    )
    if not identity_matches or not isinstance(evidence, list) or len(evidence) == 0:
        return False

    for command_evidence in evidence:
        log_digest = str(command_evidence.get("logDigest", ""))
        if command_evidence.get("exitCode") != 0:
            return False
        if re.fullmatch(r"sha256:[0-9a-f]{64}", log_digest) is None:
            return False
    return True


def _classify_state(reasons: list[dict[str, str]]) -> str:
    """Apply fail-closed precedence while keeping incomplete work distinguishable."""
    contradictory_codes = {
        "contradictory-receipts",
        "dependency-cycle",
        "invalid-receipt",
        "invalid-manifest",
        "missing-coverage",
        "unknown-dependency",
    }
    if any(reason["code"] in contradictory_codes for reason in reasons):
        return "contradictory"
    if any(reason["code"] == "stale-receipt" for reason in reasons):
        return "stale"
    if len(reasons) > 0:
        return "incomplete"
    return "ready"


def parse_arguments() -> argparse.Namespace:
    """Parse the intentionally read-only evaluator command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("manifest", type=Path)
    evaluate_parser.add_argument("receipts", nargs="*", type=Path)
    return parser.parse_args()


def main() -> int:
    """Print one deterministic evaluation and signal readiness with exit status."""
    arguments = parse_arguments()
    result = evaluate_stage(arguments.manifest, arguments.receipts)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["state"] == "ready":
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
