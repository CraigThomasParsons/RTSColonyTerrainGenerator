#!/usr/bin/env python3
"""
Create (or recreate) ONE sprint's Gitea issue from the sprint map, house style.

Ported from The-Pulse's create_sprint_issue.py (a GitHub `gh`-based variant)
to the Gitea REST API for RTSColonyTerrainGenerator.  The issue-body structure
is preserved exactly: Parent / Sprint Goal / What to build / Acceptance
criteria / Blocked by, with acceptance criteria as `- [ ]` checkboxes.

Sprints whose `existing` field cites an issue number are never edited — the
Sprint Goal + acceptance criteria are posted as a COMMENT on that issue
instead.  Sprints with `existing = None` are created as NEW issues with the
full body, the MILESTONE_TITLE milestone (when set), and the house labels.

A duplicate guard refuses to create a second issue for a sprint whose tracker
(docs/sprint_tasks/sprint-NN-*/AUTO_CONTINUE_TRACKER.md) already cites one;
pass --force to override.

The SPRINTS table below is a template: fill it in from the plan in
`docs/plan/` as sprints are defined for this repository.

How to run:
    # Review one sprint (no Gitea writes):
    python3 scripts/tools/create_sprint_issue.py 1 --dry-run

    # Create/post it:
    python3 scripts/tools/create_sprint_issue.py 1
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

GITEA_URL = "http://192.168.2.48:3000"
OWNER = "craigpars"
REPO = "RTSColonyTerrainGenerator"

# Milestone to attach new sprint issues to, resolved by title at runtime.
# Set to None to create issues without a milestone.
MILESTONE_TITLE: str | None = None

# House labels applied to every new sprint issue, resolved by name at runtime.
# Labels missing from the repo are skipped with a warning.
LABELS = ["ready-for-agent", "status: planned"]

TOKEN_FILE = Path.home() / ".config" / "pulse" / "gitea_token"

# slug per sprint, used for the tracker path reference.
# Fill in as sprints are defined in docs/plan/.
SLUGS = {
    1: "sprint-01-example-terrain-slice",
}

# num, title, existing_issue (None = create new), goal, what, acceptance[], blocked_by[]
#
# TEMPLATE — replace the example row with real sprints from docs/plan/.
# The tuple shape and the generated body sections are the contract; keep them.
SPRINTS = [
    (1, "Example Terrain Slice", None,
     "Replace this with the sprint goal: one sentence describing the observable "
     "outcome when the sprint is done.",
     "Replace this with what to build: the concrete scope across src/, tests/, "
     "specs/, and features/ for this vertical slice of the terrain pipeline.",
     ["`just quality` and `dotnet test` are green.",
      "The new stage/spec is promoted in `specs/dafny-ready.tags`.",
      "Replace with sprint-specific acceptance criteria."],
     []),
]


# ── Token / API helpers ────────────────────────────────────────────────────────


def load_api_token() -> str:
    """Resolve the Gitea API token from the environment or from the secure file."""
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


def gitea_request(method: str, path: str, payload: dict | None = None) -> dict | list:
    """Make an authenticated Gitea API request. Dies on error."""
    try:
        import requests as req
    except ImportError:
        sys.exit("The 'requests' library is required: pip install requests")

    headers = {
        "Authorization": f"token {load_api_token()}",
        "Content-Type": "application/json",
    }
    response = req.request(
        method, f"{GITEA_URL}/api/v1{path}", headers=headers, json=payload, timeout=10
    )

    if response.status_code not in (200, 201):
        print(
            f"✗ {method} {path} → HTTP {response.status_code}:\n{response.text[:400]}",
            file=sys.stderr,
        )
        sys.exit(1)

    return response.json() if response.text.strip() else {}


def milestone_id() -> int | None:
    """Resolve the milestone ID for MILESTONE_TITLE, or None when unset."""
    if MILESTONE_TITLE is None:
        return None
    milestones = gitea_request("GET", f"/repos/{OWNER}/{REPO}/milestones?limit=50")
    for m in milestones:
        if m["title"] == MILESTONE_TITLE:
            return m["id"]
    print(f"✗ Milestone '{MILESTONE_TITLE}' not found.", file=sys.stderr)
    sys.exit(1)


def label_ids() -> list[int]:
    """Resolve the house label names to this repo's label IDs."""
    labels = gitea_request("GET", f"/repos/{OWNER}/{REPO}/labels?limit=50")
    by_name = {label["name"]: label["id"] for label in labels}

    resolved: list[int] = []
    for name in LABELS:
        if name in by_name:
            resolved.append(by_name[name])
        else:
            print(f"  ⚠ Label '{name}' not found in {OWNER}/{REPO} — skipped")
    return resolved


# ── Body builders ──────────────────────────────────────────────────────────────


def new_issue_body(num, goal, what, acceptance, blocked) -> str:
    """Assemble the full body for a NEW sprint issue."""
    lines = [
        "## Parent", "",
        f"RTSColonyTerrainGenerator roadmap. Plan: `docs/plan/`. "
        f"Tracker: `docs/sprint_tasks/{SLUGS[num]}/`.",
        "", "## Sprint Goal", "", goal,
        "", "## What to build", "", what,
        "", "## Acceptance criteria", "",
    ]
    lines += [f"- [ ] {item}" for item in acceptance]
    lines += ["", "## Blocked by", ""]
    lines += [f"- {b}" for b in blocked] if blocked else ["- (none)"]
    return "\n".join(lines)


def comment_body(num, title, goal, acceptance) -> str:
    """Assemble the Sprint-Goal comment for an EXISTING issue."""
    lines = [
        f"### Sprint {num} — {title} (augmentation)",
        f"_Tracked in `docs/plan/`; tracker `docs/sprint_tasks/{SLUGS[num]}/`._",
        "", "**Sprint Goal:** " + goal, "", "**Acceptance criteria:**",
    ]
    lines += [f"- [ ] {item}" for item in acceptance]
    return "\n".join(lines)


def tracker_cited_issue(num: int) -> int | None:
    """Return the issue number this sprint's tracker already cites, if any."""
    root = Path(__file__).resolve().parents[2] / "docs" / "sprint_tasks"
    if not root.exists():
        return None
    for tracker in root.glob(f"sprint-{num:02d}-*/AUTO_CONTINUE_TRACKER.md"):
        match = re.search(r"(?:Gitea|GitHub) Issue:\s*#(\d+)", tracker.read_text(encoding="utf-8"))
        if match:
            return int(match.group(1))
    return None


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sprint", type=int, help="Sprint number from the SPRINTS table")
    parser.add_argument("--dry-run", action="store_true", help="Print the action without writing to Gitea")
    parser.add_argument("--force", action="store_true", help="Create even if the tracker already cites an issue")
    args = parser.parse_args()

    match = next((s for s in SPRINTS if s[0] == args.sprint), None)
    if match is None:
        valid = ", ".join(str(s[0]) for s in SPRINTS)
        print(f"✗ Sprint {args.sprint} is not in the map (valid: {valid}).", file=sys.stderr)
        sys.exit(1)

    num, title, existing, goal, what, acceptance, blocked = match

    # Existing issues: post the Sprint Goal as a comment instead of editing.
    if existing is not None:
        body = comment_body(num, title, goal, acceptance)
        print(f"=== Sprint {num}: COMMENT on existing #{existing} — {title} ===")
        if args.dry_run:
            print(body)
        else:
            gitea_request(
                "POST",
                f"/repos/{OWNER}/{REPO}/issues/{existing}/comments",
                {"body": body},
            )
            print(f"  ✓ Sprint Goal comment posted on #{existing}")
        return

    # New issues: refuse to duplicate an already-created issue unless --force.
    already = tracker_cited_issue(num)
    if already is not None and not args.force and not args.dry_run:
        print(f"✗ Sprint {num} already tracked as #{already} (its tracker cites it). "
              f"Pass --force to create another.", file=sys.stderr)
        sys.exit(1)

    body = new_issue_body(num, goal, what, acceptance, blocked)
    print(f"=== Sprint {num}: CREATE new issue — {title} ===")
    if args.dry_run:
        print(f"title: [Sprint {num}] {title}")
        print(f"labels: {', '.join(LABELS)} | milestone: {MILESTONE_TITLE or '(none)'}")
        print(body)
    else:
        payload: dict = {
            "title": f"[Sprint {num}] {title}",
            "body": body,
            "labels": label_ids(),
        }
        milestone = milestone_id()
        if milestone is not None:
            payload["milestone"] = milestone

        result = gitea_request("POST", f"/repos/{OWNER}/{REPO}/issues", payload)
        issue_url = f"{GITEA_URL}/{OWNER}/{REPO}/issues/{result['number']}"
        print(f"  ✓ #{result['number']} created: {issue_url}")


if __name__ == "__main__":
    main()
