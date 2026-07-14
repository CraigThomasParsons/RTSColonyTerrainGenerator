#!/usr/bin/env python3
"""
Agent Feature Branch — start a Gitea issue safely.

What it does:
    Ports the start_issue runbook from ThePulseProject to this repository.
    Runs all pre-flight checks before mutating anything, then creates the
    feature branch, writes the lock file, updates the Gitea label, and posts
    the [Agent Start] comment.

    Pre-flight (read-only):
        1. Verify working tree is clean.
        2. Check the lock file — reject if a different issue is active.
        3. Fetch issue metadata — must be open and planned.
        4. Confirm no other issue is in-progress.

    Mutations (only after all pre-flights pass):
        5. git checkout {BASE_BRANCH} && git pull origin {BASE_BRANCH}
        6. git checkout -b feature/<issue>-<slug>
        7. Write ~/.config/pulse/locks/RTSColonyTerrainGenerator.json
        8. Set Gitea label to "status: in-progress"
        9. Post [Agent Start] comment

Why it was created:
    Ported from ThePulseProject Sprint #47 (Agent Feature Branch) — makes it
    safe for an AI agent to start any planned Gitea issue without human-guided
    branch setup.

How to run:
    python3 scripts/tools/start_gitea_issue.py <issue-number> [--agent <name>] [--dry-run]

    Examples:
        python3 scripts/tools/start_gitea_issue.py 47
        python3 scripts/tools/start_gitea_issue.py 47 --agent claude
        python3 scripts/tools/start_gitea_issue.py 47 --dry-run
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import timezone
from typing import NoReturn

# ── Configuration ─────────────────────────────────────────────────────────────

REPO_SLUG = "RTSColonyTerrainGenerator"
GITEA_URL = "http://192.168.2.48:3000"
GITEA_OWNER = "craigpars"
GITEA_REPO = "RTSColonyTerrainGenerator"
BASE_BRANCH = "main"
GITEA_REMOTE = "origin"

TOKEN_FILE = Path.home() / ".config" / "pulse" / "gitea_token"
WORKER_ID_FILE = Path.home() / ".config" / "pulse" / "worker_id"
LOCKS_DIR = Path.home() / ".config" / "pulse" / "locks"
LOCK_FILE = LOCKS_DIR / f"{REPO_SLUG}.json"

# Label names in this Gitea repository.  Unlike ThePulseProject, label IDs are
# not hard-coded: they are resolved by name at runtime because every repo on
# the instance carries its own label IDs.
LABEL_PLANNED = "status: planned"
LABEL_IN_PROGRESS = "status: in-progress"


# ── Token / worker helpers ─────────────────────────────────────────────────────


def load_token() -> str:
    """Resolve the Gitea API token from env or file."""
    env_token = os.environ.get("GITEA_TOKEN", "").strip()
    if env_token:
        return env_token

    if TOKEN_FILE.exists():
        file_token = TOKEN_FILE.read_text().strip()
        if file_token:
            return file_token

    die(
        "No Gitea token found.\n"
        f"  Option 1: export GITEA_TOKEN=<your-token>\n"
        f"  Option 2: echo '<token>' > {TOKEN_FILE}"
    )


def resolve_worker_id(agent_name: str | None) -> str:
    """
    Build the worker_id string.

    Uses ~/.config/pulse/worker_id when present, otherwise falls back to
    the machine hostname so the lock file is always human-readable.
    """
    if WORKER_ID_FILE.exists():
        machine = WORKER_ID_FILE.read_text().strip()
    else:
        machine = os.uname().nodename

    if agent_name:
        return f"{agent_name}-{machine}"

    return machine


# ── Subprocess helpers ─────────────────────────────────────────────────────────


def run_git(args: list[str]) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def gitea_request(method: str, path: str, token: str, **kwargs) -> dict | list:
    """
    Make an authenticated Gitea API request.

    Imports requests lazily so the pre-flight check stage can report a
    useful error rather than an ImportError when the library is missing.
    """
    try:
        import requests as req
    except ImportError:
        die("The 'requests' library is required: pip install requests")

    headers = {"Authorization": f"token {token}", "Content-Type": "application/json"}
    response = req.request(method, f"{GITEA_URL}/api/v1{path}", headers=headers, **kwargs)

    if response.status_code not in (200, 201, 204):
        die(f"Gitea API error {response.status_code} on {method} {path}:\n{response.text[:400]}")

    if response.status_code == 204 or not response.text.strip():
        return {}

    return response.json()


def resolve_label_id(label_name: str, token: str) -> int | None:
    """
    Look up a label ID by name in this repository.

    Returns None when the label does not exist so callers can decide whether
    a missing label is fatal (in-progress) or ignorable (planned).
    """
    labels = gitea_request(
        "GET",
        f"/repos/{GITEA_OWNER}/{GITEA_REPO}/labels",
        token,
        params={"limit": 50},
    )
    for label in labels:
        if label.get("name") == label_name:
            return label["id"]
    return None


# ── Error helpers ──────────────────────────────────────────────────────────────


def die(message: str) -> NoReturn:
    """
    Print an error message and exit with a non-zero code.

    :param message: Human-readable failure reason for the operator.

    :return: Never returns because the process exits with a non-zero status.
    """
    print(f"✗  {message}", file=sys.stderr)
    sys.exit(1)


def info(message: str, dry_run: bool = False) -> None:
    """Print a status line. Prefixes with [DRY RUN] when applicable."""
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"{prefix}{message}")


# ── Slug builder ───────────────────────────────────────────────────────────────


def build_branch_slug(issue_number: int, issue_title: str) -> str:
    """
    Derive a lowercase-hyphenated slug from the issue number and title.

    The issue number is prepended so branches sort predictably and the
    associated issue is always traceable from the branch name alone.
    """
    # Strip non-alphanumeric characters and collapse spaces to hyphens.
    cleaned = re.sub(r"[^a-z0-9 ]", "", issue_title.lower())
    words = cleaned.split()

    # Keep enough words to be readable but not so many the branch name overflows.
    slug_words = words[:6]
    slug = "-".join(slug_words)

    return f"{issue_number}-{slug}"


# ── Pre-flight checks (read-only) ──────────────────────────────────────────────


def preflight_clean_tree() -> None:
    """Step 1 — Reject if the working tree has any modifications."""
    code, status_output, _ = run_git(["status", "--porcelain=v1"])
    if status_output:
        die(
            "Working tree is not clean. Stash or commit changes before starting.\n"
            + status_output
        )
    info("  ✓ Working tree is clean")


def preflight_lock_file(issue_number: int) -> None:
    """
    Step 2 — Reject if the lock file references a different active issue.

    A lock for the same issue is fine: this may be a resume after a crash.
    A missing lock is fine: this is a fresh start.
    """
    if not LOCK_FILE.exists():
        info("  ✓ No existing lock file")
        return

    try:
        lock_data = json.loads(LOCK_FILE.read_text())
    except (json.JSONDecodeError, OSError) as parse_error:
        die(f"Lock file is unreadable: {parse_error}")

    locked_issue = lock_data.get("issue_number")

    if locked_issue != issue_number:
        die(
            f"Another issue is already locked: #{locked_issue} "
            f"(worker: {lock_data.get('worker_id', 'unknown')}).\n"
            "Release that lock before starting a new issue."
        )

    info(f"  ✓ Lock file matches issue #{issue_number} — resuming is safe")


def preflight_issue_metadata(issue_number: int, token: str) -> dict:
    """
    Step 3 — Fetch the issue from Gitea and validate state and labels.

    Returns the issue dict so later steps can use its title and body.
    """
    issue = gitea_request("GET", f"/repos/{GITEA_OWNER}/{GITEA_REPO}/issues/{issue_number}", token)

    if issue.get("state") != "open":
        die(f"Issue #{issue_number} is not open (state: {issue.get('state')}). Cannot start.")

    label_names = [label["name"] for label in issue.get("labels", [])]
    current_status = next((name for name in label_names if name.startswith("status:")), None)

    if current_status not in (None, LABEL_PLANNED):
        die(
            f"Issue #{issue_number} has label '{current_status}'. "
            f"Only '{LABEL_PLANNED}' (or no status label) is safe to start."
        )

    info(f"  ✓ Issue #{issue_number}: \"{issue['title']}\" — open, {current_status or 'no status label'}")
    return issue


def preflight_no_other_active(issue_number: int) -> None:
    """
    Step 4 — Confirm the lock file (if any) refers only to this issue.

    This duplicates step 2's check deliberately: the runbook requires it
    as a second confirmation that no other work is active before mutations begin.
    """
    if not LOCK_FILE.exists():
        info("  ✓ No active lock — safe to proceed")
        return

    lock_data = json.loads(LOCK_FILE.read_text())
    if lock_data.get("issue_number") != issue_number:
        die(
            f"Lock file still references issue #{lock_data.get('issue_number')}. "
            "This should have been caught in step 2 — aborting."
        )

    info("  ✓ No conflicting active issue")


# ── Mutations ─────────────────────────────────────────────────────────────────


def step_switch_to_base_branch(dry_run: bool) -> None:
    """Step 5 — Checkout the base branch and pull from Gitea."""
    info(f"  → git checkout {BASE_BRANCH}", dry_run)
    if dry_run:
        return

    code, _, stderr = run_git(["checkout", BASE_BRANCH])
    if code != 0:
        die(f"Could not switch to {BASE_BRANCH}: {stderr}")

    info(f"  → git pull {GITEA_REMOTE} {BASE_BRANCH}", dry_run)
    code, _, stderr = run_git(["pull", GITEA_REMOTE, BASE_BRANCH])
    if code != 0:
        die(f"Could not pull {BASE_BRANCH} from {GITEA_REMOTE}: {stderr}")

    info(f"  ✓ On {BASE_BRANCH}, up to date")


def step_create_branch(branch_name: str, dry_run: bool) -> None:
    """Step 6 — Create the feature branch from the base branch."""
    info(f"  → git checkout -b {branch_name}", dry_run)
    if dry_run:
        return

    code, _, stderr = run_git(["checkout", "-b", branch_name])
    if code != 0:
        die(f"Could not create branch '{branch_name}': {stderr}")

    info(f"  ✓ Branch '{branch_name}' created")


def step_write_lock_file(
    issue_number: int,
    branch_name: str,
    worker_id: str,
    agent_name: str | None,
    dry_run: bool,
) -> None:
    """Step 7 — Write the lock file to ~/.config/pulse/locks/."""
    now_iso = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lock_data: dict = {
        "version": 1,
        "repo_slug": REPO_SLUG,
        "issue_number": issue_number,
        "branch": branch_name,
        "worker_id": worker_id,
        "claimed_at": now_iso,
        "heartbeat_at": now_iso,
    }

    if agent_name:
        lock_data["agent"] = agent_name

    info(f"  → Write lock file: {LOCK_FILE}", dry_run)
    if dry_run:
        info(f"     {json.dumps(lock_data, indent=4)}", dry_run)
        return

    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(json.dumps(lock_data, indent=2))
    info(f"  ✓ Lock file written")


def step_set_label_in_progress(issue_number: int, token: str, dry_run: bool) -> None:
    """Step 8 — Replace the 'status: planned' label with 'status: in-progress'."""
    info(f"  → Set Gitea label: {LABEL_IN_PROGRESS} on #{issue_number}", dry_run)
    if dry_run:
        return

    in_progress_id = resolve_label_id(LABEL_IN_PROGRESS, token)
    if in_progress_id is None:
        die(
            f"Label '{LABEL_IN_PROGRESS}' does not exist in "
            f"{GITEA_OWNER}/{GITEA_REPO}. Create the status labels first."
        )

    planned_id = resolve_label_id(LABEL_PLANNED, token)

    # Remove the planned label first (ignore errors — it may already be absent).
    if planned_id is not None:
        try:
            import requests as req
            headers = {"Authorization": f"token {token}"}
            req.request(
                "DELETE",
                f"{GITEA_URL}/api/v1/repos/{GITEA_OWNER}/{GITEA_REPO}/issues/{issue_number}/labels/{planned_id}",
                headers=headers,
            )
        except Exception:
            pass

    gitea_request(
        "POST",
        f"/repos/{GITEA_OWNER}/{GITEA_REPO}/issues/{issue_number}/labels",
        token,
        json={"labels": [in_progress_id]},
    )
    info(f"  ✓ Label set to {LABEL_IN_PROGRESS}")


def step_post_start_comment(
    issue_number: int,
    branch_name: str,
    worker_id: str,
    agent_name: str | None,
    token: str,
    dry_run: bool,
) -> None:
    """Step 9 — Post the [Agent Start] comment."""
    now_iso = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "[Agent Start]",
        f"Worker: {worker_id}",
        f"Branch: {branch_name}",
        f"Issue: #{issue_number}",
    ]

    if agent_name:
        lines.append(f"Agent: {agent_name}")

    lines.append(f"Started: {now_iso}")

    comment_body = "\n".join(lines)
    info(f"  → Post [Agent Start] comment on #{issue_number}", dry_run)

    if dry_run:
        info(comment_body, dry_run)
        return

    gitea_request(
        "POST",
        f"/repos/{GITEA_OWNER}/{GITEA_REPO}/issues/{issue_number}/comments",
        token,
        json={"body": comment_body},
    )
    info("  ✓ Start comment posted")


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start a Gitea issue: pre-flight checks then branch creation."
    )
    parser.add_argument("issue", type=int, help="Gitea issue number to start")
    parser.add_argument("--agent", metavar="NAME", help="Agent name (e.g. claude, codex)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print every action without mutating any state",
    )
    args = parser.parse_args()

    issue_number: int = args.issue
    agent_name: str | None = args.agent
    dry_run: bool = args.dry_run

    token = load_token()
    worker_id = resolve_worker_id(agent_name)

    # ── Pre-flight (read-only) ─────────────────────────────────────────────────
    print(f"\n=== Pre-flight checks for issue #{issue_number} ===")

    preflight_clean_tree()
    preflight_lock_file(issue_number)
    issue = preflight_issue_metadata(issue_number, token)
    preflight_no_other_active(issue_number)

    # Derive the branch name after fetching the issue title.
    slug = build_branch_slug(issue_number, issue["title"])
    branch_name = f"feature/{slug}"

    print(f"\n  Branch will be: {branch_name}")
    print(f"  Worker ID     : {worker_id}")

    # ── Mutations ─────────────────────────────────────────────────────────────
    print(f"\n=== Starting issue #{issue_number} {'[DRY RUN]' if dry_run else ''} ===")

    step_switch_to_base_branch(dry_run)
    step_create_branch(branch_name, dry_run)
    step_write_lock_file(issue_number, branch_name, worker_id, agent_name, dry_run)
    step_set_label_in_progress(issue_number, token, dry_run)
    step_post_start_comment(issue_number, branch_name, worker_id, agent_name, token, dry_run)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}✓ Issue #{issue_number} started on branch '{branch_name}'")


if __name__ == "__main__":
    main()
