#!/usr/bin/env python3
"""
Report the current state of the RTSColonyTerrainGenerator Gitea repository.

Prints a human-readable snapshot of:
  - Milestones (phases) with open/closed issue counts and a progress bar
  - Labels with their IDs and colours
  - Total open and closed issue counts

Use this after bulk issue creation (create_sprint_issue.py) to confirm
everything was created correctly, or at any time to get a quick overview
of plan progress.

Token resolution order (same as scripts/tools/gitea.py):
  1. GITEA_TOKEN environment variable
  2. ~/.config/pulse/gitea_token  (preferred — never committed)

Usage:
  python3 scripts/tools/check_gitea_state.py
"""

import os
import sys
import requests
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

GITEA_URL  = "http://192.168.2.48:3000"
OWNER      = "craigpars"
REPO       = "RTSColonyTerrainGenerator"

# Token file lives outside the repo so it can never be accidentally committed.
TOKEN_FILE = Path.home() / ".config" / "pulse" / "gitea_token"


# ── Token resolution ──────────────────────────────────────────────────────────

def load_api_token() -> str:
    """
    Resolve the Gitea API token from the environment or from the secure token file.

    The environment variable takes precedence so CI runners can inject a token
    without touching the filesystem.  Exits with a clear diagnostic if no token
    is found so the operator knows exactly what to fix.
    """
    # Prefer the environment variable — useful for one-off shells and CI.
    env_token = os.environ.get("GITEA_TOKEN", "").strip()
    if env_token:
        return env_token

    # Fall back to the persistent file-based token for local development.
    if TOKEN_FILE.exists():
        file_token = TOKEN_FILE.read_text().strip()
        if file_token:
            return file_token

    # Neither source yielded a token — fail explicitly rather than sending unauthenticated requests.
    sys.exit(
        "No Gitea token found.\n"
        f"  Option 1: export GITEA_TOKEN=<your-token>\n"
        f"  Option 2: echo '<your-token>' > {TOKEN_FILE}  (then chmod 600)"
    )


# Resolve once at module level so every function shares the same auth headers.
TOKEN    = load_api_token()
HEADERS  = {"Authorization": f"token {TOKEN}"}
API_BASE = f"{GITEA_URL}/api/v1"


# ── API helpers ───────────────────────────────────────────────────────────────

def fetch(endpoint_path: str, **query_params) -> list | dict:
    """
    Execute a GET request against the Gitea API and return the parsed JSON body.

    Does not exit on failure so the script can report partial results if one
    endpoint is unavailable.  The caller is responsible for checking the type
    of the return value before iterating.
    """
    full_url = f"{API_BASE}{endpoint_path}"
    response = requests.get(full_url, headers=HEADERS, params=query_params)

    # Return whatever the API gives us; the caller handles malformed responses.
    return response.json()


def print_section_header(section_title: str) -> None:
    """
    Print a visually distinct section header to make the output easy to scan.

    Consistent formatting here means every section separator looks the same
    regardless of which function produces it.
    """
    print(f"\n{'─' * 50}")
    print(f"  {section_title}")
    print("─" * 50)


# ── Report sections ───────────────────────────────────────────────────────────

def report_milestones() -> None:
    """
    Print all milestones (phases) with a completion progress bar.

    Each milestone maps to one phase of the terrain-generator plan.  The
    progress bar gives a quick visual of how much of each phase has shipped.
    """
    print_section_header("Milestones (Phases)")

    milestone_data = fetch(f"/repos/{OWNER}/{REPO}/milestones", limit=20)

    if not isinstance(milestone_data, list):
        # Unexpected shape — print raw so the operator can diagnose.
        print(f"  Unexpected response: {milestone_data}")
        return

    for milestone in milestone_data:
        open_count   = milestone.get("open_issues", 0)
        closed_count = milestone.get("closed_issues", 0)
        total        = open_count + closed_count

        # Block characters give an at-a-glance view of completion ratio.
        progress_bar = "█" * closed_count + "░" * open_count
        print(f"  [{progress_bar}] {closed_count}/{total}  {milestone['title']}")


def report_labels() -> None:
    """
    Print all labels with their IDs and hex colours.

    This section lets the operator confirm the status labels (planned /
    in-progress / complete) and any phase labels exist with the right IDs.
    """
    print_section_header("Labels")

    label_data = fetch(f"/repos/{OWNER}/{REPO}/labels", limit=20)

    if not isinstance(label_data, list):
        print(f"  Unexpected response: {label_data}")
        return

    for label in label_data:
        # Align columns so the label names are easy to compare visually.
        print(f"  id={label['id']:<4}  color={label['color']}  {label['name']}")


def report_issue_counts() -> None:
    """
    Print total open and closed issue counts.

    A quick sanity check after bulk issue creation that the expected number
    of sprint issues exists.
    """
    print_section_header("Issues")

    open_issues   = fetch(f"/repos/{OWNER}/{REPO}/issues", type="issues", state="open",   limit=50)
    closed_issues = fetch(f"/repos/{OWNER}/{REPO}/issues", type="issues", state="closed", limit=50)

    # Guard against unexpected non-list responses before calling len().
    open_count   = len(open_issues)   if isinstance(open_issues,   list) else "?"
    closed_count = len(closed_issues) if isinstance(closed_issues, list) else "?"

    print(f"  Open:   {open_count}")
    print(f"  Closed: {closed_count}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """
    Run all three report sections in sequence and print a footer with board links.
    """
    report_milestones()
    report_labels()
    report_issue_counts()

    # Print navigation links so the operator can jump straight to the relevant Gitea pages.
    print(f"\n  Issues:     {GITEA_URL}/{OWNER}/{REPO}/issues")
    print(f"  Milestones: {GITEA_URL}/{OWNER}/{REPO}/milestones")
    print(f"  Projects:   {GITEA_URL}/{OWNER}/{REPO}/projects\n")


if __name__ == "__main__":
    main()
