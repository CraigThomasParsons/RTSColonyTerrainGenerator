#!/usr/bin/env python3
"""
Gitea CLI helper for the RTSColonyTerrainGenerator workflow.

Wraps the Gitea REST API so AI agents and developers never have to
hand-craft HTTP calls or remember endpoint paths.  Every operation that
is possible via the API is exposed as a subcommand here.

Project board column management is intentionally absent: Gitea 1.26.2
has no REST API for moving cards between columns.  Drag cards manually:
  http://192.168.2.48:3000/craigpars/RTSColonyTerrainGenerator/projects

Token resolution order:
  1. GITEA_TOKEN environment variable
  2. ~/.config/pulse/gitea_token  (preferred — never committed; shared
     with the other repos on the same Gitea instance)

Usage:
  python3 scripts/tools/gitea.py create-issue "Title" "Body"
  python3 scripts/tools/gitea.py find-issue "Sprint 2"
  python3 scripts/tools/gitea.py comment <issue-number> "<message>"
  python3 scripts/tools/gitea.py close <issue-number>
  python3 scripts/tools/gitea.py reopen <issue-number>
  python3 scripts/tools/gitea.py pr <branch> "<title>" ["<body>"]
  python3 scripts/tools/gitea.py pr-view <number>
  python3 scripts/tools/gitea.py pr-reviews <number>
  python3 scripts/tools/gitea.py pr-ready <number> "<title>" "<body>" GATES_VALIDATED
  python3 scripts/tools/gitea.py sprint-status
"""

import os
import sys
import json
import requests
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

GITEA_URL   = "http://192.168.2.48:3000"
OWNER       = "craigpars"
REPO        = "RTSColonyTerrainGenerator"

# PRs always target main in this repo.
BASE_BRANCH = "main"

TOKEN_FILE = Path.home() / ".config" / "pulse" / "gitea_token"


def load_api_token() -> str:
    """
    Resolve the Gitea API token from the environment or from the secure file.

    The environment variable takes precedence so CI runners can inject a token
    without touching the filesystem.  The file path is preferred for local dev
    because it survives shell restarts without re-exporting.

    Exits with a clear message rather than returning an empty string so callers
    never silently send unauthenticated requests.
    """
    env_token = os.environ.get("GITEA_TOKEN", "").strip()
    if env_token:
        return env_token

    if TOKEN_FILE.exists():
        file_token = TOKEN_FILE.read_text().strip()
        if file_token:
            return file_token

    sys.exit(
        "No Gitea token found.\n"
        f"  Option 1: export GITEA_TOKEN=<your-token>\n"
        f"  Option 2: echo '<your-token>' > {TOKEN_FILE}  (then chmod 600)"
    )


TOKEN    = load_api_token()
HEADERS  = {"Authorization": f"token {TOKEN}", "Content-Type": "application/json"}
API_BASE = f"{GITEA_URL}/api/v1"


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def make_request(method: str, path: str, **kwargs) -> dict | list:
    """
    Execute an authenticated HTTP request against the Gitea API.

    Exits on any non-2xx response rather than returning partial data, because
    callers have no sensible fallback when the API rejects a write operation.
    """
    response = requests.request(method, f"{API_BASE}{path}", headers=HEADERS, **kwargs)

    if response.status_code not in (200, 201):
        print(f"✗ {method} {path} → HTTP {response.status_code}")
        print(response.text[:400])
        sys.exit(1)

    return response.json()


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_find_issue(title_fragment: str) -> None:
    """
    Search open issues for any whose title contains the given substring.

    Paginates through all open issues so no sprint card is missed even on
    a large repo.  Prints matching issues to stdout.
    """
    page = 1
    while True:
        issues = make_request(
            "GET",
            f"/repos/{OWNER}/{REPO}/issues",
            params={"type": "issues", "state": "open", "limit": 50, "page": page},
        )

        for issue in issues:
            if title_fragment.lower() in issue["title"].lower():
                print(f"#{issue['number']}  {issue['title']}")

        if len(issues) < 50:
            break
        page += 1


def cmd_create_issue(title: str, body: str) -> None:
    """Create one repository issue and print its durable URL."""
    result = make_request(
        "POST",
        f"/repos/{OWNER}/{REPO}/issues",
        json={"title": title, "body": body},
    )
    print(f"✓ Issue #{result['number']} created: {result['html_url']}")


def cmd_comment(issue_number: str, message: str) -> None:
    """
    Append a comment to a Gitea issue.

    Used throughout the sprint workflow to leave an audit trail: sprint start,
    end of deliverable, and sprint-close messages all go through here.
    """
    make_request(
        "POST",
        f"/repos/{OWNER}/{REPO}/issues/{issue_number}/comments",
        json={"body": message},
    )
    print(f"✓ Comment added to #{issue_number}")


def cmd_close(issue_number: str) -> None:
    """
    Close a Gitea issue by patching its state to 'closed'.

    Closing the issue also advances the milestone progress bar, giving Craig
    a visual indicator of phase completion.
    """
    make_request(
        "PATCH",
        f"/repos/{OWNER}/{REPO}/issues/{issue_number}",
        json={"state": "closed"},
    )
    print(f"✓ Issue #{issue_number} closed")


def cmd_reopen(issue_number: str) -> None:
    """
    Reopen a previously closed issue.

    Used when a deliverable is rolled back or a regression is discovered.
    """
    make_request(
        "PATCH",
        f"/repos/{OWNER}/{REPO}/issues/{issue_number}",
        json={"state": "open"},
    )
    print(f"✓ Issue #{issue_number} reopened")


def cmd_open_pull_request(branch: str, title: str, body: str = "") -> str:
    """
    Open a pull request from the given branch into main.

    Returns the PR URL so it can be included in the sprint-end handoff report.
    """
    if not body:
        body = (
            "See the plan in `docs/plan/` and the specs in `specs/` for context.\n\n"
            "Opened by AI agent."
        )

    result = make_request(
        "POST",
        f"/repos/{OWNER}/{REPO}/pulls",
        json={"head": branch, "base": BASE_BRANCH, "title": title, "body": body},
    )

    pr_url = f"{GITEA_URL}/{OWNER}/{REPO}/pulls/{result['number']}"
    print(f"✓ PR #{result['number']} opened: {pr_url}")
    return pr_url


def cmd_view_pull_request(number: str) -> None:
    """Print concise review and merge metadata for one pull request."""
    result = make_request("GET", f"/repos/{OWNER}/{REPO}/pulls/{number}")
    fields = {
        "number": result.get("number"),
        "title": result.get("title"),
        "state": result.get("state"),
        "draft": result.get("draft"),
        "mergeable": result.get("mergeable"),
        "merged": result.get("merged"),
        "base": result.get("base", {}).get("ref"),
        "head": result.get("head", {}).get("ref"),
        "headSha": result.get("head", {}).get("sha"),
        "url": result.get("html_url"),
    }
    print(json.dumps(fields, indent=2, sort_keys=True))


def cmd_pull_request_reviews(number: str) -> None:
    """Print reviews and aggregate commit status for one pull request."""
    pull = make_request("GET", f"/repos/{OWNER}/{REPO}/pulls/{number}")
    reviews = make_request("GET", f"/repos/{OWNER}/{REPO}/pulls/{number}/reviews")
    head_sha = pull.get("head", {}).get("sha")
    status = make_request("GET", f"/repos/{OWNER}/{REPO}/commits/{head_sha}/status")
    summary = {
        "number": pull.get("number"),
        "headSha": head_sha,
        "reviewCount": len(reviews),
        "reviews": [
            {
                "id": review.get("id"),
                "state": review.get("state"),
                "reviewer": review.get("user", {}).get("login"),
                "submitted": review.get("submitted_at"),
            }
            for review in reviews
        ],
        "commitStatus": status.get("state"),
        "statusCount": status.get("total_count", 0),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def cmd_mark_pull_request_ready(
    number: str, title: str, body: str, confirmation: str
) -> None:
    """Remove Gitea draft state after evidence gates have been validated."""
    if confirmation != "GATES_VALIDATED":
        sys.exit("pr-ready requires the exact confirmation GATES_VALIDATED")
    current = make_request("GET", f"/repos/{OWNER}/{REPO}/pulls/{number}")
    if current.get("merged") or current.get("state") != "open":
        sys.exit(f"PR #{number} is not an open, unmerged pull request")
    result = make_request(
        "PATCH",
        f"/repos/{OWNER}/{REPO}/pulls/{number}",
        json={"title": title, "body": body, "draft": False},
    )
    if result.get("draft"):
        sys.exit(f"Gitea left PR #{number} in draft state")
    print(f"✓ PR #{number} marked ready: {result['html_url']}")


def cmd_sprint_status() -> None:
    """
    Print a progress bar for every milestone (phase) in the project.

    Milestones map 1:1 to the phases of the terrain-generator plan.
    """
    milestones = make_request("GET", f"/repos/{OWNER}/{REPO}/milestones")

    for milestone in milestones:
        open_count   = milestone.get("open_issues", 0)
        closed_count = milestone.get("closed_issues", 0)
        total        = open_count + closed_count
        progress_bar = "█" * closed_count + "░" * open_count
        print(f"{milestone['title']:<42} [{progress_bar}] {closed_count}/{total}")


# ── Command dispatch ──────────────────────────────────────────────────────────

COMMANDS: dict = {
    "create-issue":  (cmd_create_issue,             2, 2),
    "find-issue":    (cmd_find_issue,         1, 1),
    "comment":       (cmd_comment,            2, 2),
    "close":         (cmd_close,              1, 1),
    "reopen":        (cmd_reopen,             1, 1),
    "pr":            (cmd_open_pull_request,  2, 3),
    "pr-view":       (cmd_view_pull_request,        1, 1),
    "pr-reviews":    (cmd_pull_request_reviews,     1, 1),
    "pr-ready":      (cmd_mark_pull_request_ready,  4, 4),
    "sprint-status": (cmd_sprint_status,      0, 0),
}


def main() -> None:
    """
    Parse argv and dispatch to the appropriate command function.

    Prints the module docstring as help when no command is given.
    """
    args = sys.argv[1:]

    if not args or args[0] not in COMMANDS:
        print(__doc__)
        sys.exit(0)

    command_name = args[0]
    command_fn, min_args, max_args = COMMANDS[command_name]
    command_args = args[1:]

    if not (min_args <= len(command_args) <= max_args):
        print(
            f"Usage error: '{command_name}' expects {min_args}–{max_args} "
            f"arguments, got {len(command_args)}"
        )
        sys.exit(1)

    command_fn(*command_args)


if __name__ == "__main__":
    main()
