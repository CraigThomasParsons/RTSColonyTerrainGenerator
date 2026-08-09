#!/usr/bin/env python3
"""
Dirty-state classifier for the agent parking policy.

What it does:
    Inspects the working tree and classifies it into one of five categories,
    then maps each category to an allowed action.

    Categories:
        clean           — no changes; proceed safely.
        staged-only     — files are staged but not committed; STOP.
        unstaged-only   — tracked files modified but not staged; auto-checkpoint.
        mixed           — both staged and unstaged changes present; STOP.
        untracked-only  — untracked non-ignored files exist; STOP and list.

    Policies:
        proceed         — working tree is clean; no action needed before parking.
        checkpoint      — unstaged changes only; safe to auto-commit before pushing.
        stop-staged     — staged changes present; a human must review and commit.
        stop-untracked  — untracked files present; add to .gitignore before parking.

    Never use `git add -A`. The checkpoint path always commits only tracked modified
    files. Files that must never be committed:
        .env, *.env.*, token files, bin/, obj/, node_modules/, logs/.

Why it was created:
    Ported from ThePulseProject Sprint #46 (Agent Parking Policy) — Phase 1.
    Feeds park_gitea_issue.py so the park command always knows whether it is
    safe to auto-commit.

How to use (as a library):
    from parking_policy import classify_working_tree, POLICY_PROCEED

    result = classify_working_tree()
    if result['policy'] != POLICY_PROCEED:
        print(result['message'])
        sys.exit(1)

How to run standalone:
    python3 scripts/tools/parking_policy.py
    python3 scripts/tools/parking_policy.py --json
"""

import json
import subprocess
import sys
from pathlib import Path

# ── Policy constants ───────────────────────────────────────────────────────────

POLICY_PROCEED = "proceed"
POLICY_CHECKPOINT = "checkpoint"
POLICY_STOP_STAGED = "stop-staged"
POLICY_STOP_UNTRACKED = "stop-untracked"

# Categories produced by the classifier.
CATEGORY_CLEAN = "clean"
CATEGORY_STAGED_ONLY = "staged-only"
CATEGORY_UNSTAGED_ONLY = "unstaged-only"
CATEGORY_MIXED = "mixed"
CATEGORY_UNTRACKED_ONLY = "untracked-only"

# Files that the auto-checkpoint must never include.  Adapted from the Pulse
# original (a Laravel/Node app) to this .NET repo: vendor/ and public/build/
# are replaced with bin/ and obj/ build outputs, plus the logs/ directory.
NEVER_COMMIT_PATTERNS = [
    ".env",
    ".env.",
    "_token",
    "gitea_token",
    "bin/",
    "obj/",
    "node_modules/",
    "logs/",
]


# ── Git helpers ────────────────────────────────────────────────────────────────


def run_git(args: list[str]) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def porcelain_lines() -> list[str]:
    """Return non-empty lines from `git status --porcelain=v1`."""
    code, output, _ = run_git(["status", "--porcelain=v1", "--untracked-files=normal"])
    if code != 0:
        return []
    return [line for line in output.splitlines() if len(line) >= 2]


def tracked_modified_files() -> list[str]:
    """
    Return paths of tracked files with unstaged modifications.

    These are safe candidates for the checkpoint commit — they are already
    tracked so no unintended file enters the repository.
    """
    code, output, _ = run_git(["diff", "--name-only"])
    if code != 0:
        return []
    return [path for path in output.splitlines() if path]


# ── Classifier ────────────────────────────────────────────────────────────────


def classify_working_tree() -> dict:
    """
    Inspect the working tree and return a classification result dict.

    Return schema:
        category    str   — one of the CATEGORY_* constants.
        policy      str   — one of the POLICY_* constants.
        staged      list  — paths with staged changes.
        unstaged    list  — tracked paths with unstaged changes.
        untracked   list  — untracked, non-ignored paths.
        message     str   — human-readable explanation for the policy decision.
    """
    lines = porcelain_lines()

    staged: list[str] = []
    unstaged: list[str] = []
    untracked: list[str] = []

    for line in lines:
        index_status = line[0]
        worktree_status = line[1]
        path = line[3:].strip()

        if line[:2] == "??":
            untracked.append(path)
        else:
            if index_status not in (" ", "?"):
                staged.append(path)
            if worktree_status not in (" ", "?"):
                unstaged.append(path)

    return _apply_policy(staged, unstaged, untracked)


def _apply_policy(staged: list[str], unstaged: list[str], untracked: list[str]) -> dict:
    """Map the three file lists to a category and policy."""
    has_staged = len(staged) > 0
    has_unstaged = len(unstaged) > 0
    has_untracked = len(untracked) > 0

    # Staged changes always require a human decision — stop unconditionally.
    if has_staged and has_unstaged:
        return {
            "category": CATEGORY_MIXED,
            "policy": POLICY_STOP_STAGED,
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "message": (
                "Mixed dirty state: both staged and unstaged changes detected.\n"
                "Review staged changes and either commit or unstage them before parking."
            ),
        }

    if has_staged:
        return {
            "category": CATEGORY_STAGED_ONLY,
            "policy": POLICY_STOP_STAGED,
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "message": (
                f"{len(staged)} staged file(s) detected.\n"
                "Commit or unstage these changes before parking — the agent never completes "
                "an in-progress commit on your behalf."
            ),
        }

    # Untracked files that are not ignored must be resolved by the developer.
    if has_untracked:
        return {
            "category": CATEGORY_UNTRACKED_ONLY,
            "policy": POLICY_STOP_UNTRACKED,
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "message": (
                f"{len(untracked)} untracked file(s) detected:\n"
                + "\n".join(f"  {path}" for path in untracked)
                + "\nAdd them to .gitignore or stage them before parking."
            ),
        }

    # Unstaged tracked modifications are the auto-checkpoint case.
    if has_unstaged:
        return {
            "category": CATEGORY_UNSTAGED_ONLY,
            "policy": POLICY_CHECKPOINT,
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "message": (
                f"{len(unstaged)} modified tracked file(s). "
                "Auto-checkpoint will stage and commit them before parking."
            ),
        }

    return {
        "category": CATEGORY_CLEAN,
        "policy": POLICY_PROCEED,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "message": "Working tree is clean. Safe to park.",
    }


def filter_safe_files(paths: list[str]) -> tuple[list[str], list[str]]:
    """
    Split a file list into safe-to-commit and blocked paths.

    Returns (safe, blocked). Blocked paths match NEVER_COMMIT_PATTERNS.
    """
    safe: list[str] = []
    blocked: list[str] = []

    for path in paths:
        path_lower = path.lower()
        is_blocked = any(pattern in path_lower for pattern in NEVER_COMMIT_PATTERNS)
        if is_blocked:
            blocked.append(path)
        else:
            safe.append(path)

    return safe, blocked


# ── Standalone entry point ─────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Classify the working tree dirty state.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    result = classify_working_tree()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        icon = "✓" if result["policy"] == POLICY_PROCEED else "✗"
        print(f"Parking Policy — {icon} {result['category'].upper()} ({result['policy']})")
        print(f"  {result['message']}")

    if result["policy"] not in (POLICY_PROCEED, POLICY_CHECKPOINT):
        sys.exit(1)


if __name__ == "__main__":
    main()
