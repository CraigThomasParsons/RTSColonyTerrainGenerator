---
name: code-review
description: Review a release pull request into main on the GitHub mirror. Use when reviewing any pull request in this repository. Findings are reported for a human to carry back to Gitea; GitHub is a review surface, not where fixes are made.
---

# Release code review

## What you are reviewing

This GitHub repository is a **mirror**. Development happens in Gitea: issues,
branches, pull requests and merges all live there. After work lands in Gitea it
is mirrored here, and a pull request into `main` is opened so the release can be
reviewed. Every pull request you see targets `main` and usually spans several
already-merged Gitea changes.

Consequences for how you review:

- **Do not suggest committing fixes to this pull request** and do not offer
  suggested-change blocks as the way to resolve a finding. The mirror is
  overwritten on the next sync. Describe the problem so a person can file it as
  a Gitea issue.
- Review the **release as a whole**: how the changes fit together, what they
  leave half-finished, and what reaches `main` that should not.
- Commits in the range were already reviewed individually in Gitea. Look for
  what per-change review misses: interactions between changes, drift from the
  documented design, and things left behind.

## Read the repository's own rules first

Before judging the diff, read whichever of these exist and treat them as the
standard to review against. They override the general checks below.

1. `AGENTS.md` (and any nested `AGENTS.md` near changed files)
2. `CONTEXT.md` or `CONTEXT-MAP.md`: the domain glossary
3. `docs/adr/`: accepted architecture decisions
4. `.github/copilot-instructions.md` and `.github/instructions/*.instructions.md`
5. Contract or schema directories the changes touch (OpenAPI, JSON Schema,
   Gherkin features, domain contracts)

If a change contradicts an ADR, a glossary term, or an `AGENTS.md` rule, that
is a finding even if the code works. Cite the document and the line or section.

## What to look for, in priority order

1. **Correctness.** Logic errors, unhandled failure paths, race conditions,
   off-by-one errors, wrong time zone or unit handling, broken idempotency, state
   changes published before they are committed.
2. **Security and trust boundaries.** Secrets, tokens, `.env` files or
   credentials in the diff; missing authentication or authorization on new
   routes or handlers; unvalidated input crossing a boundary; secrets reaching
   browser-visible code; webhook or signature checks that can be bypassed.
3. **Data and migrations.** Destructive or irreversible migrations, missing
   indexes or constraints that code relies on, schema changes with no matching
   code or contract change, and the reverse.
4. **Contract drift.** Endpoints, events, payloads or CLI behaviour that changed
   without the contract, fixtures, mocks or client handoff docs changing to
   match.
5. **Tests.** New behaviour with no test, tests that cannot fail, tests that
   depend on wall-clock time or ordering, and skipped or deleted tests.
6. **Release hygiene.** Debug output, commented-out code, TODOs that hide
   unfinished work, generated or build artefacts, local paths, worktree or
   scratch directories, large binaries, and files that look committed by
   accident.
7. **Design drift.** Domain rules leaking into controllers, handlers or
   adapters; names that contradict the glossary; new dependencies the docs do
   not justify.

Skip pure style and formatting unless the repository's own rules require it.
Formatters and linters already handle those.

## How to report

Report findings most-severe first. For each one, give:

- **Severity:** `blocker` (must not ship), `major` (should be fixed before the
  next release), or `minor` (worth an issue).
- **Location:** `path/to/file:line`.
- **Problem:** one or two sentences on what is wrong.
- **Scenario:** the concrete input or state that triggers it and what goes
  wrong.
- **Rule broken** when it applies: the ADR, glossary term or `AGENTS.md` line.

Write each finding so it can be pasted into a Gitea issue with no other
context. Only report something you can tie to specific lines. If you are
unsure, say so and explain what would confirm it. Do not pad the review: if
the release is clean, say so in one sentence.

End with a short summary covering how many findings at each severity, and
whether anything should stop this release from being promoted.
