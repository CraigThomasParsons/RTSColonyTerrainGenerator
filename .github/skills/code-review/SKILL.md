---
name: code-review
description: Review a release pull request targeting main (or any commit range) for real defects — correctness bugs, security problems, broken contracts, and things that should not ship. Use when asked to review a PR, review a release, review a mirror, check what is about to land on main, or do a code review. Produces a ship/hold verdict and a short, ranked list of verified findings, each with a concrete failure scenario.
---

# Code review

You are reviewing a change set that is about to land on `main`. In this repository
`main` is the release branch on GitHub. Day-to-day work happens on another forge, and
the history is mirrored here. A release PR therefore usually bundles **many already
merged feature PRs**. Your job is to catch what those individual reviews missed, and
especially what only shows up when the changes are combined.

The goal is **a few true findings, not many plausible ones**. One real bug with a
reproducible failure is worth more than twenty style remarks. If the change is clean,
say so. An empty findings list is a valid result.

## 1. Establish scope

Work out exactly what is being reviewed before reading any code.

1. Find the base and head. For a PR, the base is the PR's base branch (normally
   `main`) and the head is the PR branch. Without a PR, use the range the user gives
   you. If they give none, use the last release tag up to `HEAD`
   (`git describe --tags --abbrev=0`).
2. If you have a terminal, list what is in the range:
   - `git log --oneline --no-merges <base>..<head>` for commits
   - `git log --oneline --merges <base>..<head>` for the bundled PRs
   - `git diff --stat <base>...<head>` for the size and shape of the change
3. Group the changes by the issue or PR they came from (commit subjects usually
   carry `#NN` or a `feature/NN-…` branch name). Review by group, not file by file in
   alphabetical order.
4. Triage by risk. Spend most of your effort on:
   - domain logic, algorithms, and anything with invariants
   - persistence, schemas, serialization formats, and migrations
   - auth, secrets, input handling, shell/process execution, and file paths
   - concurrency, retries, locking, and resource cleanup
   - public APIs and contracts consumed by other repos or services
   - CI/workflow files and build or deploy scripts

   Skim, but do not skip, docs, tests, and generated files. Note anything you did
   not review.

## 2. Load the repository's own rules

Before judging the code, read whatever of these exist. They define what "correct"
means here and override generic best practice:

- `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`,
  `.github/instructions/*.instructions.md`
- `CONTEXT.md` (domain vocabulary) and `docs/adr/` (decisions already made; do not
  re-litigate them)
- style guides under `docs/style/` or similar
- the spec or issue a change group came from (for example `docs/specs/<slice>/`), so
  you can check that the code does what was asked

Treat explicit "must not" rules in those files as review criteria. Typical examples
are not weakening specs or tests to make them pass, not editing fixtures without
explanation, and not moving domain rules into handlers or adapters. A violation of
one of them is a finding even if the code otherwise works.

## 3. Review passes

Do these in order. Stop adding findings from later passes once you have the
important ones.

### Pass A: correctness (highest priority)

For each risky hunk, read the surrounding function and at least one caller. A diff
alone hides most bugs. Look for:

- wrong conditions, inverted checks, off-by-one errors, wrong operator or units
- unhandled `null`/empty/missing cases on paths that are actually reachable
- errors swallowed, logged and ignored, or turned into success
- state mutated before validation, or partial writes left behind on failure
- non-determinism where determinism is required (clocks, global RNG, unordered
  iteration, floating point compared for equality)
- resources not disposed or closed, tasks or processes not awaited, races on shared
  state
- a changed function signature or behaviour whose callers were not all updated
- tests that cannot fail: asserting on the mock, or missing the assertion entirely

### Pass B: release-bundle hazards (specific to mirrored releases)

These are the issues individual PR reviews cannot see:

- **Cross-PR interaction.** Two PRs are each fine but conflict together: both change
  the same contract, one renames what the other starts using, or both add a
  migration with the same number.
- **Merge damage.** Look for conflict markers (`<<<<<<<`, `>>>>>>>`), duplicated
  blocks, a fix from one PR silently undone by a later merge, or code that only
  compiles because of something deleted elsewhere.
- **Accidental inclusions.** `.env` files or credentials, tokens, private keys,
  absolute home-directory paths, internal IPs or hostnames, logs, scratch or
  worktree directories, agent lock or state files, large binaries, `node_modules`,
  virtualenvs, and debug output or `TODO: remove` code. On a public GitHub mirror,
  **any secret is a blocking finding**, even if it is "only local".
- **Ops impact.** New required env vars or config keys, schema or data migrations,
  changed ports or paths, and new external dependencies. Each must be either handled
  or called out, because whoever deploys the release needs to know.
- **Dependency changes.** A manifest changed without its lockfile, or the reverse;
  new packages that are unmaintained, typosquat-looking, or broader than needed.
- **Workflow files** under `.github/workflows/`: `pull_request_target` with a
  checkout of PR code, secrets exposed to untrusted input, unpinned third-party
  actions, or `${{ github.event.* }}` interpolated directly into `run:`.

### Pass C: security

Injection (SQL, shell, path traversal, template), missing authorization on new
endpoints, unsafe deserialization, SSRF from user-controlled URLs, secrets in logs.
Only report what is reachable from an input someone other than the developer
controls.

### Pass D: spec and contract fidelity

Does each change group do what its issue or spec asked? Check for missing acceptance
criteria, behaviour that was changed without updating its spec, test, or fixture, and
specs, assertions, or scenarios that were weakened or deleted rather than fixed.

### Pass E: cleanup (optional, low priority)

Report only clear wins: duplicated logic that already has a helper in the repo, dead
code introduced by this change, or an obviously quadratic loop on a hot path. Skip
anything a formatter or linter would catch, and skip taste.

## 4. Verify before you report

Every candidate finding must survive this check. Drop it if it does not.

1. **Concrete failure scenario.** Can you state specific inputs or state that lead to
   a wrong result, crash, leak, or exposure? "This could be a problem" is not a
   finding.
2. **Reachability.** Did you confirm the path is actually reachable? Check callers,
   guards upstream, and types that already rule the case out.
3. **Not already handled.** Search for the validation, test, or fallback elsewhere
   before claiming it is missing.
4. **Not intentional.** Check the ADRs, comments, and commit messages. A documented
   decision is not a bug, though you may note it if it is now clearly wrong.

Mark each surviving finding **Confirmed** (you traced it end to end) or **Plausible**
(strong evidence, one link unverified). Do not report anything weaker.

## 5. Report

Use this format. Keep it short: the reader will act on it, not study it.

```markdown
## Verdict: Ship | Ship after fixes | Hold

<one or two sentences: what this release contains and the overall risk>

## Findings

### 1. <short claim> — Blocking | Should fix | Minor · Confirmed | Plausible
`path/to/file.ext:LINE`
**What breaks:** <concrete inputs/state → wrong outcome>
**Fix:** <the smallest change that fixes it>

### 2. …

## Deploy notes
<new env vars, migrations, config, or dependency changes the deployer must know about; "None" if none>

## Not reviewed
<files or areas skipped or only skimmed, and why>
```

Rules for the report:

- Rank findings by severity, most severe first. **Blocking** means do not merge:
  data loss, security exposure, leaked secret, broken build, or broken core path.
  **Should fix** means a real bug with limited blast radius. **Minor** means correct
  but worth changing.
- Default to at most 10 findings. If there are more real ones, say how many you
  left out.
- Cite `file:line` against the head revision for every finding.
- No praise sections, no restating the diff, no generic advice ("consider adding
  more tests"). If you recommend a test, name the case it should cover.
- If you are posting inline PR comments, post one comment per finding on its line,
  and put the verdict and deploy notes in the summary comment.
