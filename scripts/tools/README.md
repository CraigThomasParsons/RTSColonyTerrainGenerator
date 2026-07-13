# scripts/tools — Gitea issue-lifecycle automation

Ported from ThePulseProject (with one script each from The-Pulse and
AgileMedievalPeasantBoard) and adapted for RTSColonyTerrainGenerator.
These scripts let an AI agent or a developer drive the full issue
lifecycle on the local Gitea forge — claim, branch, checkpoint, finish —
without hand-crafting HTTP calls or branch setup.

## Configuration (shared constants)

Every script carries the same configuration block:

| Constant       | Value                                                                    |
|----------------|--------------------------------------------------------------------------|
| `GITEA_URL`    | `http://192.168.2.48:3000`                                               |
| `GITEA_OWNER`  | `craigpars`                                                              |
| `GITEA_REPO`   | `RTSColonyTerrainGenerator`                                              |
| `BASE_BRANCH`  | `main`                                                                   |
| `GITEA_REMOTE` | `origin` → `ssh://git@192.168.2.48:2222/craigpars/RTSColonyTerrainGenerator.git` |
| GitHub mirror  | remote `github` → `git@github.com:CraigThomasParsons/RTSColonyTerrainGenerator.git` |
| Token file     | `~/.config/pulse/gitea_token`                                            |
| Worker id      | `~/.config/pulse/worker_id`                                              |
| Lock file      | `~/.config/pulse/locks/RTSColonyTerrainGenerator.json`                   |

The `~/.config/pulse/` paths are deliberately shared with the other repos
on the same Gitea instance (ThePulseProject, AgileMedievalPeasantBoard):
one token, one worker id, one lock file per repo slug.

### Token setup

Token resolution order (identical in every script):

1. `GITEA_TOKEN` environment variable (wins — lets CI inject a token)
2. `~/.config/pulse/gitea_token` (preferred for local dev)

```bash
mkdir -p ~/.config/pulse
echo '<your-gitea-token>' > ~/.config/pulse/gitea_token
chmod 600 ~/.config/pulse/gitea_token
```

Generate the token in Gitea under Settings → Applications with
`issue`, `repository`, and `write:repository` scopes.

Optionally set a stable worker id (falls back to the hostname):

```bash
echo 'craig-nas' > ~/.config/pulse/worker_id
```

### Labels

The lifecycle uses three status labels, which must exist in the Gitea repo:

- `status: planned` — triaged and ready for an agent to start
- `status: in-progress` — an agent holds the lock and is working
- `status: complete` — branch pushed and PR opened; awaiting merge

Unlike the ThePulseProject originals (which hard-coded label IDs 75/76/77),
these ports resolve label IDs **by name at runtime**, because label IDs are
per-repository on the Gitea instance.

The Python scripts (except `mark_issues_complete.py`, which uses stdlib
`urllib`) require the `requests` library: `pip install requests`.

## The issue lifecycle

```
 planned ──start──▶ in-progress ──end──▶ complete
                        │  ▲
                      park │
                        ▼  │ (resume = start same issue again)
                     parked (lock intact, branch pushed)
```

1. **Start** — `start_gitea_issue.py <N>` runs read-only pre-flight checks
   (clean tree; lock file absent or already ours; issue open and
   `status: planned`; no other issue in progress), then checks out `main`,
   pulls, creates `feature/<issue>-<slug>`, writes the lock file, flips the
   label to `status: in-progress`, and posts an `[Agent Start]` comment.
2. **Work** — normal development on the feature branch. Verify with
   `just quality` / `dotnet test` before ending.
3. **End** — `end_gitea_issue.py --notes "..." [--open-pr]` captures
   `git diff --stat`, requires verification notes, pushes the branch,
   optionally opens a PR to `main` (title `feat(<key>): <issue title>`),
   posts an `[Agent End]` comment, removes the lock, and sets the final
   label (`status: complete` with a PR, back to `status: planned` without).
4. **Park** (instead of end) — `park_gitea_issue.py [--reason ...]`
   classifies the working tree, auto-checkpoints unstaged tracked changes
   (never `git add -A`; never token/env/build-output paths), pushes, updates
   the lock heartbeat, and posts an `[Agent Checkpoint]` comment. The lock
   stays in place so the same worker can resume later.

Branch naming: `feature/<issue-number>-<first-6-title-words-slug>`.
All lifecycle events leave an audit trail as issue comments
(`[Agent Start]` / `[Agent Checkpoint]` / `[Agent End]`).

## The scripts

### `gitea.py` — general-purpose API CLI

Subcommands: `find-issue <fragment>`, `comment <n> <msg>`, `close <n>`,
`reopen <n>`, `pr <branch> <title> [body]`, `sprint-status` (per-milestone
progress bars — milestones map to plan phases).

```bash
python3 scripts/tools/gitea.py sprint-status
python3 scripts/tools/gitea.py comment 12 "Deployed to staging."
```

### `start_gitea_issue.py` — begin work on a planned issue

```bash
python3 scripts/tools/start_gitea_issue.py 12 --agent claude --dry-run
python3 scripts/tools/start_gitea_issue.py 12 --agent claude
```

Pre-flight is strictly read-only; mutations only begin once every check
passes. `--dry-run` prints every action without touching anything.

### `end_gitea_issue.py` — conclude work

```bash
python3 scripts/tools/end_gitea_issue.py \
    --notes "Tests: dotnet test green. just quality clean." --open-pr
```

Verification notes are mandatory (`--notes` or `--notes-file`) — an empty
handoff is worse than a stopped run. Mutation order is push → PR → comment
→ lock removal, so any failure leaves the issue recoverable (a failed push
restores the lock file).

### `park_gitea_issue.py` + `parking_policy.py` — safe handoff

`parking_policy.py` classifies the tree (clean / unstaged-only /
staged / mixed / untracked) and maps each state to a policy. Staged and
untracked states stop the park — a human must decide. It also holds the
never-commit list, adapted for this repo: `.env*`, `*_token`, `bin/`,
`obj/`, `node_modules/`, `logs/`.

```bash
python3 scripts/tools/parking_policy.py --json   # standalone classifier
python3 scripts/tools/park_gitea_issue.py --reason "blocked on heightmap spec"
```

Auto-checkpoint is on by default; disable with `--no-checkpoint` or
`AGENT_AUTO_CHECKPOINT=false`.

### `check_gitea_state.py` — repo snapshot

Prints milestones with progress bars, labels with IDs/colours, and
open/closed issue counts. Use it to confirm the status labels exist and
to eyeball plan progress.

```bash
python3 scripts/tools/check_gitea_state.py
```

### `mark_issues_complete.py` — bulk label correction

Removes `status: planned` / `status: in-progress` and adds
`status: complete` on each listed issue. Idempotent.

```bash
python3 scripts/tools/mark_issues_complete.py 3 4 7 --dry-run
```

### `create_sprint_issue.py` — create one sprint issue from the map

Ported from The-Pulse's GitHub (`gh`) variant to the Gitea API. Keeps the
same issue-body structure: **Parent / Sprint Goal / What to build /
Acceptance criteria (checkboxes) / Blocked by**, plus the duplicate guard
that refuses to recreate a sprint whose tracker
(`docs/sprint_tasks/sprint-NN-*/AUTO_CONTINUE_TRACKER.md`) already cites an
issue (`--force` overrides).

The `SPRINTS` table ships as a **template with one example row** — the
Pulse original carried 25 sprints of .NET-migration content that does not
apply here. Fill in rows from `docs/plan/` as sprints are defined, and set
`MILESTONE_TITLE` once this repo has phase milestones (it defaults to
`None` = no milestone).

```bash
python3 scripts/tools/create_sprint_issue.py 1 --dry-run
```

### `sync_gitea_to_github.sh` — nightly GitHub mirror

One-way mirror: fetch both remotes with `--prune`, fast-forward `main`
from `origin` (Gitea), push `main` and tags to `github`. Adapted from the
AgileMedievalPeasantBoard original: that repo named Gitea `gitea` and
GitHub `origin` and synced a `develop` branch; here Gitea is `origin`,
GitHub is `github`, and `main` is the only synced branch.

Safety rules (never relaxed): no `push --force`, no `reset --hard`,
dirty worktree → exit 0 without pushing, non-fast-forward → exit 1.

```bash
bash scripts/tools/sync_gitea_to_github.sh
# or via systemd on the NAS:
systemctl --user start rtscolony-github-mirror.service
```

## Conventions inherited from ThePulseProject

- One lock file per repo slug under `~/.config/pulse/locks/`; a single
  in-progress issue per repo at a time.
- Lock schema: `version`, `repo_slug`, `issue_number`, `branch`,
  `worker_id`, `claimed_at`, `heartbeat_at`, optional `agent`.
- Branch naming `feature/<issue>-<slug>`; PRs always target `main`.
- Status labels drive the board; closing issues advances milestone
  progress bars (milestone = phase).
- Every script supports `--dry-run` and prints ✓/✗-prefixed step logs.
- Agents never complete a human's staged commit and never commit
  secrets or build outputs.

## Adaptations from the Pulse originals

- Label IDs resolved by name at runtime instead of hard-coded IDs.
- Verification examples reference `just quality` / `dotnet test`
  (Pulse used PHPUnit/Pint), and the promotion ledger is
  `specs/dafny-ready.tags` (Pulse's was `net-ready.tags`).
- `start_gitea_issue.py --launch` (which chained into Pulse's
  `prompt_generator.py`) was dropped — that generator was not ported.
- PR bodies point at `docs/plan/` and `specs/` instead of Pulse's
  `docs/sprint_tasks/`.
- Never-commit patterns swap Laravel's `vendor/`, `public/build/` for
  .NET's `bin/`, `obj/`, plus `logs/`.
