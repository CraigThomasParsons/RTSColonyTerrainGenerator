#!/usr/bin/env python3
"""
Agent End Issue — safely conclude work on a Gitea issue.

What it does:
    Phase 1 — Inspection and verification notes:
        - Runs `git diff --stat HEAD` and captures the changed file list.
        - Requires verification notes (via --notes or --notes-file).
        - Refuses to proceed if no notes are provided.

    Phase 2 — Push the feature branch:
        - Pushes to the `origin` remote, which is the canonical Gitea remote.
        - If the push fails: restore the lock file, keep the in-progress label, exit non-zero.
        - Confirms the branch is visible on the remote with `git ls-remote`.

    Phase 3 — PR creation (when --open-pr is passed):
        - Opens a PR to `main` via the Gitea API.
        - PR title format: feat(<sprint-key>): <issue-title>.
        - Posts the PR link to the Gitea issue as a follow-up comment.

    Phase 4 — Gitea comment and lock release:
        - Updates the lock heartbeat one last time.
        - Posts `[Agent End]` comment with branch, PR URL, notes.
        - Removes the lock file.
        - Removes the `status: in-progress` label; adds `status: complete` if
          a PR was opened, or leaves `status: planned` otherwise.

    Mutation order is push → PR → comment → lock removal so that a failure
    at any step leaves the issue in a recoverable state.

Why it was created:
    Ported from ThePulseProject Sprint #49 (Agent End Issue) — the closing
    step of the agent automation sequence: Claim → Branch → Park → End.

How to run:
    python3 scripts/tools/end_gitea_issue.py --notes "Tests: dotnet test green. just quality clean."
    python3 scripts/tools/end_gitea_issue.py --notes-file docs/handoff.md --open-pr
    python3 scripts/tools/end_gitea_issue.py --dry-run --notes "Dry run test."
"""

import argparse
import datetime
import json
import os
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
GITEA_REMOTE = "origin"
BASE_BRANCH = "main"

TOKEN_FILE = Path.home() / ".config" / "pulse" / "gitea_token"
LOCK_FILE = Path.home() / ".config" / "pulse" / "locks" / f"{REPO_SLUG}.json"

# Label names in this Gitea repository.  IDs are resolved by name at runtime
# because every repo on the instance carries its own label IDs.
LABEL_PLANNED = "status: planned"
LABEL_IN_PROGRESS = "status: in-progress"
LABEL_COMPLETE = "status: complete"


# ── Token helper ───────────────────────────────────────────────────────────────


def load_token() -> str:
    """Resolve the Gitea API token from env or file."""
    env_token = os.environ.get("GITEA_TOKEN", "").strip()
    if env_token:
        return env_token

    if TOKEN_FILE.exists():
        file_token = TOKEN_FILE.read_text().strip()
        if file_token:
            return file_token

    die("No Gitea token found. Set GITEA_TOKEN or write it to " + str(TOKEN_FILE))


# ── Git helpers ────────────────────────────────────────────────────────────────


def run_git(args: list[str]) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(["git"] + args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def current_branch() -> str:
    """Return the current git branch name."""
    code, branch, _ = run_git(["branch", "--show-current"])
    if code != 0 or not branch:
        die("Could not determine current branch.")
    return branch


def changed_files_stat() -> str:
    """Return `git diff --stat HEAD` output, or empty string if tree is clean."""
    code, output, _ = run_git(["diff", "--stat", "HEAD"])
    if code != 0:
        return ""
    return output


# ── Gitea API helpers ──────────────────────────────────────────────────────────


def gitea_request(method: str, path: str, token: str, **kwargs) -> dict | list:
    """Make an authenticated Gitea API request."""
    try:
        import requests as req
    except ImportError:
        die("The 'requests' library is required: pip install requests")

    headers = {"Authorization": f"token {token}", "Content-Type": "application/json"}
    response = req.request(
        method, f"{GITEA_URL}/api/v1{path}", headers=headers, timeout=10, **kwargs
    )

    if response.status_code not in (200, 201, 204):
        die(f"Gitea API {method} {path} → HTTP {response.status_code}:\n{response.text[:300]}")

    if response.status_code == 204 or not response.text.strip():
        return {}

    return response.json()


def resolve_label_id(label_name: str, token: str) -> int | None:
    """Look up a label ID by name in this repository. Returns None if absent."""
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


def post_comment(issue_number: int, body: str, token: str) -> None:
    """Post a comment to the Gitea issue."""
    gitea_request(
        "POST",
        f"/repos/{GITEA_OWNER}/{GITEA_REPO}/issues/{issue_number}/comments",
        token,
        json={"body": body},
    )


def set_label(issue_number: int, label_id: int, token: str) -> None:
    """Add a label to the Gitea issue."""
    gitea_request(
        "POST",
        f"/repos/{GITEA_OWNER}/{GITEA_REPO}/issues/{issue_number}/labels",
        token,
        json={"labels": [label_id]},
    )


def remove_label(issue_number: int, label_id: int, token: str) -> None:
    """Remove a label from the Gitea issue (ignores 404)."""
    try:
        import requests as req
    except ImportError:
        return

    headers = {"Authorization": f"token {token}"}
    req.delete(
        f"{GITEA_URL}/api/v1/repos/{GITEA_OWNER}/{GITEA_REPO}/issues/{issue_number}/labels/{label_id}",
        headers=headers,
        timeout=10,
    )


# ── Error / info helpers ───────────────────────────────────────────────────────


def die(message: str) -> NoReturn:
    """
    Print an error and exit non-zero.

    :param message: Human-readable failure reason for the operator.

    :return: Never returns because the process exits with a non-zero status.
    """
    print(f"✗  {message}", file=sys.stderr)
    sys.exit(1)


def info(message: str, dry_run: bool = False) -> None:
    """Print a status line."""
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"{prefix}{message}")


# ── Lock file helpers ──────────────────────────────────────────────────────────


def read_lock_file() -> dict:
    """Read and return the active lock file. Dies if absent."""
    if not LOCK_FILE.exists():
        die(
            "No lock file found. There is no active issue claim to end.\n"
            f"Expected: {LOCK_FILE}"
        )
    try:
        return json.loads(LOCK_FILE.read_text())
    except (json.JSONDecodeError, OSError) as error:
        die(f"Lock file is unreadable: {error}")


def restore_lock_file(lock_data: dict) -> None:
    """Write lock data back to disk (used when a later step fails)."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(json.dumps(lock_data, indent=2))


# ── Phase 1: Inspection and verification notes ─────────────────────────────────


def collect_diff_stat() -> str:
    """Run git diff --stat HEAD and return the output."""
    stat = changed_files_stat()
    if stat:
        info(f"  ✓ Changed files:\n{stat}")
    else:
        info("  ✓ No uncommitted diff (working tree is clean relative to HEAD)")
    return stat


def require_verification_notes(notes_arg: str | None, notes_file_arg: str | None) -> str:
    """
    Return the verification notes string.

    Priority: --notes-file > --notes. Dies if neither is provided or both are empty.
    """
    if notes_file_arg:
        notes_path = Path(notes_file_arg)
        if not notes_path.exists():
            die(f"Notes file not found: {notes_file_arg}")
        notes = notes_path.read_text().strip()
        if not notes:
            die(f"Notes file is empty: {notes_file_arg}")
        info(f"  ✓ Verification notes loaded from {notes_file_arg} ({len(notes)} chars)")
        return notes

    if notes_arg and notes_arg.strip():
        info(f"  ✓ Verification notes: {notes_arg.strip()}")
        return notes_arg.strip()

    die(
        "Verification notes are required. Provide them with:\n"
        "  --notes \"Tests: dotnet test green. just quality clean.\"\n"
        "  --notes-file path/to/notes.md\n"
        "An empty handoff is worse than a stopped run."
    )


# ── Phase 2: Push branch ───────────────────────────────────────────────────────


def push_branch(branch: str, lock_data: dict, dry_run: bool) -> None:
    """
    Push the branch to the canonical Gitea remote.

    Restores the lock file and exits non-zero if the push fails.
    """
    info(f"  → git push {GITEA_REMOTE} {branch}", dry_run)
    if dry_run:
        return

    code, _, stderr = run_git(["push", GITEA_REMOTE, branch])
    if code != 0:
        restore_lock_file(lock_data)
        die(
            f"Push failed: {stderr}\n"
            "Lock file has been restored. Resolve the push error before ending the issue."
        )
    info("  ✓ Branch pushed")

    # Confirm the branch is visible on the remote.
    code, remote_refs, _ = run_git(["ls-remote", "--heads", GITEA_REMOTE, branch])
    if code == 0 and remote_refs:
        info(f"  ✓ Remote branch confirmed visible")
    else:
        info("  ⚠ Could not confirm remote branch visibility (ls-remote returned nothing)")


# ── Phase 3: PR creation ───────────────────────────────────────────────────────


def open_pull_request(
    issue_number: int,
    branch: str,
    issue_title: str,
    sprint_key: str | None,
    token: str,
    dry_run: bool,
) -> str | None:
    """
    Open a PR to main and return the PR URL.

    Returns None when dry-running.
    """
    scope = sprint_key if sprint_key else str(issue_number)
    pr_title = f"feat({scope}): {issue_title}"

    # Truncate to 70 chars as per the project convention.
    if len(pr_title) > 70:
        pr_title = pr_title[:67] + "..."

    info(f"  → Open PR: \"{pr_title}\"", dry_run)
    if dry_run:
        return None

    result = gitea_request(
        "POST",
        f"/repos/{GITEA_OWNER}/{GITEA_REPO}/pulls",
        token,
        json={
            "head": branch,
            "base": BASE_BRANCH,
            "title": pr_title,
            "body": (
                f"Closes #{issue_number}.\n\n"
                "See the plan in `docs/plan/` and the specs in `specs/` for context.\n\n"
                "Opened by agent automation."
            ),
        },
    )

    pr_url = f"{GITEA_URL}/{GITEA_OWNER}/{GITEA_REPO}/pulls/{result['number']}"
    info(f"  ✓ PR #{result['number']} opened: {pr_url}")
    return pr_url


def post_pr_link_comment(issue_number: int, pr_url: str, token: str, dry_run: bool) -> None:
    """Post the PR link as a comment on the issue."""
    body = f"Pull request opened: {pr_url}"
    info(f"  → Post PR link comment on #{issue_number}", dry_run)
    if dry_run:
        return
    post_comment(issue_number, body, token)
    info("  ✓ PR link comment posted")


# ── Phase 4: End comment and lock release ─────────────────────────────────────


def update_lock_heartbeat_final(dry_run: bool) -> None:
    """Write the final heartbeat timestamp to the lock file before removal."""
    now_iso = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    info(f"  → Update lock heartbeat_at: {now_iso}", dry_run)
    if dry_run:
        return
    lock_data = json.loads(LOCK_FILE.read_text())
    lock_data["heartbeat_at"] = now_iso
    LOCK_FILE.write_text(json.dumps(lock_data, indent=2))


def post_end_comment(
    issue_number: int,
    branch: str,
    pr_url: str | None,
    diff_stat: str,
    notes: str,
    token: str,
    dry_run: bool,
) -> None:
    """Post the [Agent End] comment to the Gitea issue."""
    now_iso = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "[Agent End]",
        f"Branch: {branch}",
    ]

    if pr_url:
        lines.append(f"PR: {pr_url}")

    if diff_stat:
        # Include a compact diff summary — first line of stat output.
        stat_summary = diff_stat.splitlines()[-1] if diff_stat.splitlines() else ""
        if stat_summary:
            lines.append(f"Tests: {stat_summary}")

    lines.append(f"Handoff: {notes[:300]}")
    lines.append(f"At: {now_iso}")

    comment_body = "\n".join(lines)
    info(f"  → Post [Agent End] comment on #{issue_number}", dry_run)

    if dry_run:
        info(comment_body, dry_run)
        return

    post_comment(issue_number, comment_body, token)
    info("  ✓ End comment posted")


def release_lock(dry_run: bool) -> None:
    """Delete the lock file."""
    info(f"  → Remove lock file: {LOCK_FILE}", dry_run)
    if dry_run:
        return
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
        info("  ✓ Lock file removed")
    else:
        info("  ✓ Lock file already absent")


def update_labels(
    issue_number: int,
    pr_was_opened: bool,
    token: str,
    dry_run: bool,
) -> None:
    """Remove in-progress label; add complete (if PR opened) or leave as planned."""
    final_label_name = LABEL_COMPLETE if pr_was_opened else LABEL_PLANNED

    info(f"  → Remove label: {LABEL_IN_PROGRESS}", dry_run)
    info(f"  → Add label: {final_label_name}", dry_run)

    if dry_run:
        return

    in_progress_id = resolve_label_id(LABEL_IN_PROGRESS, token)
    final_label_id = resolve_label_id(final_label_name, token)

    if in_progress_id is not None:
        remove_label(issue_number, in_progress_id, token)

    if final_label_id is None:
        info(f"  ⚠ Label '{final_label_name}' does not exist in this repo — skipped")
        return

    set_label(issue_number, final_label_id, token)
    info(f"  ✓ Labels updated: → {final_label_name}")


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="End a Gitea issue: push, optional PR, end comment, lock release."
    )
    parser.add_argument(
        "--notes",
        metavar="TEXT",
        help="Verification notes (tests run, known gaps, next steps)",
    )
    parser.add_argument(
        "--notes-file",
        metavar="PATH",
        dest="notes_file",
        help="Path to a file containing verification notes",
    )
    parser.add_argument(
        "--open-pr",
        action="store_true",
        dest="open_pr",
        help="Open a PR to main after pushing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print every planned action without mutating state",
    )
    args = parser.parse_args()

    dry_run: bool = args.dry_run

    token = load_token()
    lock_data = read_lock_file()
    issue_number: int = lock_data["issue_number"]
    branch: str = lock_data["branch"]

    # Fetch the issue title for the PR heading.
    issue_title = _fetch_issue_title(issue_number, token)
    sprint_key = _infer_sprint_key(issue_title)

    info(f"\n=== Ending issue #{issue_number} on branch '{branch}' {'[DRY RUN]' if dry_run else ''} ===")

    # ── Phase 1 ───────────────────────────────────────────────────────────────
    info("\n--- Phase 1: Inspect and verify ---")
    diff_stat = collect_diff_stat()
    notes = require_verification_notes(args.notes, args.notes_file)

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    info("\n--- Phase 2: Push branch ---")
    push_branch(branch, lock_data, dry_run)

    # ── Phase 3 ───────────────────────────────────────────────────────────────
    pr_url: str | None = None

    if args.open_pr:
        info("\n--- Phase 3: Open PR ---")
        pr_url = open_pull_request(issue_number, branch, issue_title, sprint_key, token, dry_run)
        if pr_url:
            post_pr_link_comment(issue_number, pr_url, token, dry_run)

    # ── Phase 4 ───────────────────────────────────────────────────────────────
    info("\n--- Phase 4: End comment and lock release ---")
    update_lock_heartbeat_final(dry_run)
    post_end_comment(issue_number, branch, pr_url, diff_stat, notes, token, dry_run)
    release_lock(dry_run)
    update_labels(issue_number, pr_url is not None, token, dry_run)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}✓ Issue #{issue_number} ended.")
    if pr_url:
        print(f"  PR: {pr_url}")
    print("  Lock released. Issue is ready for Craig to merge and close.")


# ── Internal helpers ───────────────────────────────────────────────────────────


def _fetch_issue_title(issue_number: int, token: str) -> str:
    """Fetch the issue title from Gitea; return a fallback on error."""
    try:
        issue = gitea_request(
            "GET",
            f"/repos/{GITEA_OWNER}/{GITEA_REPO}/issues/{issue_number}",
            token,
        )
        return issue.get("title", f"Issue #{issue_number}")
    except SystemExit:
        return f"Issue #{issue_number}"


def _infer_sprint_key(issue_title: str) -> str | None:
    """Derive a CamelCase sprint key from the issue title for the PR title."""
    if not issue_title:
        return None
    return "".join(word.capitalize() for word in issue_title.split())


if __name__ == "__main__":
    main()
