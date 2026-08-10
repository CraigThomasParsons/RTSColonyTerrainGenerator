#!/usr/bin/env python3
"""Bootstrap this repository onto the self-hosted Gitea forge.

One-time setup implementing the "Gitea primary + GitHub mirror" decision:

  1. create the repo  craigpars/RTSColonyTerrainGenerator  on Gitea (if missing);
  2. create the status labels the issue-lifecycle scripts expect
     (status: planned / status: in-progress / status: complete);
  3. create milestones M1..M9 (milestones = phases, from
     mapgen-spec-driven-planning/04-migration-roadmap.md);
  4. rewire local remotes:  origin -> Gitea (ssh),  github -> GitHub mirror;
  5. push main (and the current branch) to Gitea.

Prints the plan and exits unless --apply is given. Requires a Gitea token with
repo scope at ~/.config/pulse/gitea_token (shared with the other repos on this forge).

After bootstrapping, keep GitHub current with scripts/tools/sync_gitea_to_github.sh.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

GITEA_URL = "http://192.168.2.48:3000"
GITEA_OWNER = "craigpars"
GITEA_REPO = "RTSColonyTerrainGenerator"
GITEA_SSH_REMOTE = f"ssh://git@192.168.2.48:2222/{GITEA_OWNER}/{GITEA_REPO}.git"
GITHUB_REMOTE = "git@github.com:CraigThomasParsons/RTSColonyTerrainGenerator.git"
TOKEN_PATH = Path.home() / ".config" / "pulse" / "gitea_token"

STATUS_LABELS = [
    ("status: planned", "#0075ca", "Specified and ready to start"),
    ("status: in-progress", "#d93f0b", "A worker holds the lock on this issue"),
    ("status: complete", "#0e8a16", "Merged; ledgers updated"),
]

MILESTONES = [
    ("M1 Baseline and golden jobs", "Phase 0 — characterize the legacy pipeline; golden jobs, artifact hashes, one-command runs."),
    ("M2 Specification templates and CI", "Phase 1 — spec packs, C# skeleton, Dafny in CI, quality gates."),
    ("M3 Verified cell-to-tile slice", "Phase 2 — Epic 1: requirement -> BDD -> Dafny verified model -> C# -> compatibility with the legacy Tiler."),
    ("M4 Complete Tile Resolution migration", "Phase 3 — remainder of Tiler behaviour behind the Tile Resolution bounded context."),
    ("M5 Verified pipeline lifecycle", "Phase 4 — explicit, verified job/stage state transitions."),
    ("M6 Heightmap validation boundary", "Phase 5 — C# readers/validators around the Rust Heightmap stage."),
    ("M7 Vegetation contracts", "Phase 6/7 — weather structural invariants and tree-placement policies."),
    ("M8 Traversal built specification-first", "Phase 8 — PathFinder from specs, validity and termination first."),
    ("M9 Operational consolidation", "Phase 9 — C# worker host, deployment, rollback, dashboard."),
]


def read_token() -> str:
    if not TOKEN_PATH.exists():
        sys.exit(f"No Gitea token at {TOKEN_PATH}. Create one in Gitea (repo scope) and save it there.")
    return TOKEN_PATH.read_text().strip()


def api(token: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict | list | None]:
    req = urllib.request.Request(
        f"{GITEA_URL}/api/v1{path}",
        method=method,
        headers={"Authorization": f"token {token}", "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read()
            return resp.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as e:
        return e.code, None


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def remotes() -> dict[str, str]:
    out = subprocess.run(["git", "remote", "-v"], check=True, capture_output=True, text=True).stdout
    found: dict[str, str] = {}
    for line in out.splitlines():
        name, url = line.split()[:2]
        found[name] = url
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="perform the changes (default: print the plan only)")
    args = parser.parse_args()

    current = remotes()
    plan = [
        f"1. POST /user/repos             -> create {GITEA_OWNER}/{GITEA_REPO} (skipped if it exists)",
        f"2. POST /repos/.../labels       -> {', '.join(name for name, _, _ in STATUS_LABELS)}",
        f"3. POST /repos/.../milestones   -> {len(MILESTONES)} phase milestones (M1..M9)",
        f"4. git remote: origin -> {GITEA_SSH_REMOTE}",
        f"                github -> {GITHUB_REMOTE}   (currently: {current})",
        "5. git push origin main && git push origin HEAD",
    ]
    print("Plan:\n  " + "\n  ".join(plan))
    if not args.apply:
        print("\nDry run. Re-run with --apply to execute.")
        return

    token = read_token()

    status, _ = api(token, "GET", f"/repos/{GITEA_OWNER}/{GITEA_REPO}")
    if status == 404:
        status, _ = api(token, "POST", "/user/repos", {
            "name": GITEA_REPO,
            "description": "RTS colony map-generation pipeline — spec-driven conversion to verified C# (CQRS/DDD, Dafny).",
            "private": False,
            "default_branch": "main",
        })
        if status not in (200, 201):
            sys.exit(f"Repo creation failed (HTTP {status}).")
        print(f"Created {GITEA_OWNER}/{GITEA_REPO}.")
    elif status == 200:
        print("Repo already exists on Gitea.")
    else:
        sys.exit(f"Cannot reach Gitea (HTTP {status}) at {GITEA_URL}.")

    _, existing_labels = api(token, "GET", f"/repos/{GITEA_OWNER}/{GITEA_REPO}/labels")
    have = {l["name"] for l in (existing_labels or [])}
    for name, color, description in STATUS_LABELS:
        if name in have:
            print(f"Label exists: {name}")
            continue
        status, _ = api(token, "POST", f"/repos/{GITEA_OWNER}/{GITEA_REPO}/labels",
                        {"name": name, "color": color, "description": description})
        print(f"Label {'created' if status in (200, 201) else 'FAILED'}: {name}")

    _, existing_ms = api(token, "GET", f"/repos/{GITEA_OWNER}/{GITEA_REPO}/milestones?state=all&limit=50")
    have_ms = {m["title"] for m in (existing_ms or [])}
    for title, description in MILESTONES:
        if title in have_ms:
            print(f"Milestone exists: {title}")
            continue
        status, _ = api(token, "POST", f"/repos/{GITEA_OWNER}/{GITEA_REPO}/milestones",
                        {"title": title, "description": description})
        print(f"Milestone {'created' if status in (200, 201) else 'FAILED'}: {title}")

    if current.get("origin") != GITEA_SSH_REMOTE:
        if "github" not in current and current.get("origin", "").startswith(("git@github.com", "https://github.com")):
            git("remote", "rename", "origin", "github")
        elif "origin" in current:
            git("remote", "remove", "origin")
        git("remote", "add", "origin", GITEA_SSH_REMOTE)
        print(f"origin -> {GITEA_SSH_REMOTE}")
    if "github" not in remotes():
        git("remote", "add", "github", GITHUB_REMOTE)
    print(f"Remotes now: {remotes()}")

    subprocess.run(["git", "push", "origin", "main"], check=True)
    subprocess.run(["git", "push", "origin", "HEAD"], check=True)
    print("Pushed main and the current branch to Gitea. Done.")


if __name__ == "__main__":
    main()
