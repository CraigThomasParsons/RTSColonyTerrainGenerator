#!/usr/bin/env python3
"""
Mark one or more Gitea issues as 'status: complete'.

What it does:
    Removes 'status: planned' and 'status: in-progress' labels from each
    specified issue, then adds 'status: complete'.  Safe to run multiple
    times — label removal is idempotent.  Label IDs are resolved by name
    at runtime (unlike the ThePulseProject original, which hard-coded them)
    because every repo on the Gitea instance carries its own label IDs.

Why it was created:
    Allows bulk label correction after sprint merges without opening the
    Gitea browser UI.

How to run:
    python3 scripts/tools/mark_issues_complete.py 1 2
    python3 scripts/tools/mark_issues_complete.py 3 --dry-run
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


GITEA_API = "http://192.168.2.48:3000/api/v1"
GITEA_REPO = "craigpars/RTSColonyTerrainGenerator"
TOKEN_FILE = Path.home() / ".config" / "pulse" / "gitea_token"

LABEL_PLANNED = "status: planned"
LABEL_IN_PROGRESS = "status: in-progress"
LABEL_COMPLETE = "status: complete"


def _token() -> str:
    return TOKEN_FILE.read_text().strip()


def _request(method: str, path: str, body: dict | None = None, dry_run: bool = False) -> int:
    url = f"{GITEA_API}/{path}"
    if dry_run:
        print(f"  [dry-run] {method} {url}")
        return 200
    data = json.dumps(body).encode() if body else None
    headers = {
        "Authorization": f"token {_token()}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def _label_ids() -> dict[str, int]:
    """Fetch the repo's labels and return a name → id map."""
    url = f"{GITEA_API}/repos/{GITEA_REPO}/labels?limit=50"
    headers = {"Authorization": f"token {_token()}"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            labels = json.loads(response.read())
    except urllib.error.HTTPError as error:
        sys.exit(f"Failed to fetch labels: HTTP {error.code}")
    return {label["name"]: label["id"] for label in labels}


def mark_complete(issue_number: int, label_ids: dict[str, int], dry_run: bool = False) -> None:
    print(f"Issue #{issue_number}:")
    for label_name in (LABEL_PLANNED, LABEL_IN_PROGRESS):
        label_id = label_ids.get(label_name)
        if label_id is None:
            print(f"  remove {label_name} → label not found in repo, skipped")
            continue
        status = _request("DELETE", f"repos/{GITEA_REPO}/issues/{issue_number}/labels/{label_id}", dry_run=dry_run)
        print(f"  remove {label_name} → HTTP {status}")

    complete_id = label_ids.get(LABEL_COMPLETE)
    if complete_id is None:
        sys.exit(f"Label '{LABEL_COMPLETE}' not found in {GITEA_REPO}. Create it first.")

    status = _request("POST", f"repos/{GITEA_REPO}/issues/{issue_number}/labels", {"labels": [complete_id]}, dry_run=dry_run)
    print(f"  add complete → HTTP {status}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mark Gitea issues as status: complete.")
    parser.add_argument("issues", nargs="+", type=int, help="Issue numbers to mark complete")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without making API calls")
    args = parser.parse_args()

    label_ids = _label_ids() if not args.dry_run else {}
    if args.dry_run:
        # Dry-run still shows the intended requests; use name placeholders.
        label_ids = {LABEL_PLANNED: 0, LABEL_IN_PROGRESS: 0, LABEL_COMPLETE: 0}

    for issue_number in args.issues:
        mark_complete(issue_number, label_ids, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
