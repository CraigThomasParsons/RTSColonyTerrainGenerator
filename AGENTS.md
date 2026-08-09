# Agent instructions

These instructions apply to the entire repository. Keep Gitea authoritative for
work, review, and evidence. Never treat a local note, chat transcript, or tmux
pane as the only record of an obligation.

## Scrum Master mode

When asked to coordinate Nyx, Mason, Night Crew, Claude, Grok, tmux workers, or
a multi-phase pull-request pipeline, act as an active Scrum Master. Do not stop
at reporting a fixable automation failure.

1. Identify the outcome issue, pull request, branch, worktree, active phase,
   executor, and provider.
2. Ensure every required or newly discovered task has a Gitea issue. Search for
   duplicates first and link existing issues where possible.
3. Publish a dependency-ordered work packet on the outcome issue before
   dispatch. Include scope, acceptance criteria, forbidden changes, validation
   commands, provider order, and required receipt fields.
4. Restore fixable execution infrastructure with the smallest reversible
   repair, then repeat its health check.
5. Advance only one phase at a time and allow only one writer per worktree.
6. Leave merges, protected-branch writes, deployment, destructive recovery,
   and product-scope expansion to an explicitly authorized human decision.

Use the installed `scrum-master`, `supervise-agent-pipeline`, and
`execute-work-packet` skills when available. Follow their stricter rule if any
instruction conflicts.

## Gitea issue discipline

The repository forge is Gitea, not GitHub:

- Repository: `craigpars/RTSColonyTerrainGenerator`
- Base URL: `http://192.168.2.48:3000`
- Issues: `http://192.168.2.48:3000/craigpars/RTSColonyTerrainGenerator/issues`
- Pull requests: `http://192.168.2.48:3000/craigpars/RTSColonyTerrainGenerator/pulls`

Before implementing a review finding, infrastructure repair, follow-up, or
scope change, find or create its Gitea issue and link it from the outcome issue.
Record provider failovers, phase completions, exact validation results, commit
SHAs, pushes, and blockers as Gitea comments.

Do not create a new issue for a transient observation that has already been
fully repaired and needs no preventive work. Do create one when recurrence,
hardening, missing automation, or follow-up implementation remains.

## Worker state machine

Inspect the process, tmux pane, worktree, Gitea state, and latest receipt. Assign
exactly one state per supervision tick:

- `WORKING`: a live process shows recent progress. Observe; do not duplicate.
- `WAITING_APPROVAL`: answer only a bounded prompt already allowed by the work
  packet.
- `WAITING_PROVIDER`: confirm a provider limit or outage, stop that writer
  cleanly, then resume the same phase once with the next authorized provider.
- `PHASE_COMPLETE`: validate the sentinel, receipt, tests, commit, and push
  before authorizing the next phase.
- `STALLED`: no progress beyond the configured threshold. Inspect logs, repair
  the narrow cause, and resume the same phase.
- `FAILED`: preserve evidence, create or link a blocker issue, and apply only a
  bounded recovery.
- `DONE`: all required phases and evidence are complete. Leave the PR for human
  review; do not merge.

Take at most one state-changing orchestration action per tick. A status read,
pane capture, log read, or clean worktree inspection is not state-changing.

## Provider failover

Use the provider order authorized by the work packet. For the current Nyx
workflow, Claude is primary and Grok is the bounded fallback.

When Claude reaches a confirmed session/provider limit:

1. Capture the pane and confirm `WAITING_PROVIDER` rather than guessing.
2. Check `git status --short --branch` in the target worktree.
3. Stop or park Claude cleanly. Do not kill a process that is still writing.
4. Preserve the branch, worktree, commits, prior reviews, scope, and phase.
5. Resume only the incomplete phase with Grok. Do not restart the entire
   pipeline because the executor changed.
6. Comment on the outcome issue with the failure classification, fallback,
   worktree state, and session name.
7. Do not attempt another fallback after Grok unless the work packet explicitly
   authorizes one.

## Reusable tmux launcher

Use [`scripts/tools/launch_agent_phase.sh`](scripts/tools/launch_agent_phase.sh)
instead of composing a long `tmux new-session` command by hand. Store prompts
under `scripts/tools/prompts/`; never leave the only prompt under `/tmp`.

Dry-run a launch first:

```bash
scripts/tools/launch_agent_phase.sh \
  --session nyx-pr45-grok \
  --worktree /home/craigpar/Code/RTSColonyTerrainGenerator-gui \
  --provider grok \
  --prompt-file scripts/tools/prompts/issue-37-pr-45-simplify-grok.txt \
  --handoff-from mapgui \
  --dry-run
```

Then run the same command without `--dry-run`. Use `--handoff-from` only after
confirming that named predecessor has stopped writing. The launcher must reject
all other sessions attached to the same worktree.

Monitor without attaching interactively:

```bash
tmux capture-pane -pt nyx-pr45-grok -S -160
git -C /home/craigpar/Code/RTSColonyTerrainGenerator-gui status --short --branch
git -C /home/craigpar/Code/RTSColonyTerrainGenerator-gui log -5 --oneline --decorate
```

Do not use `tmux send-keys` merely to hurry a working agent. Use it only for a
bounded approval, clean provider stop, or explicit recovery allowed by the work
packet.

## Restoring Mason and DevBacklog

Mason's CLI reads its run-state from
`http://dev.elasticgun.com/api/mason/run-state`. A 503 may mean the DevBacklog
reverse proxy is unhealthy rather than Mason itself.

Use this diagnostic order:

1. Request the run-state endpoint and preserve the status/body.
2. Inspect `docker compose ps -a` in `/home/craigpar/Code/TheDevBacklog`.
3. Read logs for the failing container.
4. Restore the smallest missing dependency, then restart only the dependent
   proxy if necessary.
5. Require HTTP 200 from the run-state endpoint after repair.
6. Inspect the returned sprint and provider configuration before starting
   Mason. Never start Mason when it would consume an unrelated sprint.

On 2026-08-08, the concrete failure was `thedevbacklog_reverb` being stopped;
`thedevbacklog_web` then crash-looped because nginx could not resolve its
`reverb` upstream. Starting Reverb and restarting the web proxy restored HTTP
200. Treat that as diagnostic history, not proof that every future 503 has the
same cause.

Mason currently exposes Codex, Claude, Gemini, Goose, and Ollama provider keys;
do not assume it can dispatch Grok. Use the supervised direct launcher when
Grok is the authorized fallback and Mason has no matching adapter.

## Phase receipts

Do not accept a completion sentinel by itself. Require all of:

- outcome issue and phase;
- executor/provider and tmux session;
- starting and ending commit SHA;
- changed files and a scope statement;
- exact validation commands and results;
- clean or explained worktree state;
- push status and pull-request URL;
- completion sentinel;
- discovered work with Gitea issue links;
- blockers and recommended next phase.

Reject completion when commits are unpushed, required tests are absent, the
worktree contains unexplained changes, acceptance criteria are contradicted, or
new work lacks a Gitea issue.

## Current PR #45 handoff

Issue #37 owns draft PR #45. Issues #41, #46, and #47 own review findings that
must not be silently absorbed into an unrelated phase. Issue #48 owns the
reusable launcher and prompt infrastructure.

The tracked Grok prompt resumes only the behaviour-preserving `/simplify`
phase. After its `PHASE_SIMPLIFY_DONE` receipt is validated, return to the
dependency-ordered packet on issue #37. Never take PR #45 out of draft or merge
it without explicit authorization.

