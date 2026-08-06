# Night Crew integration design

Status: Discovery and decision-making

Gitea planning issue: `#25` — `http://192.168.2.48:3000/craigpars/RTSColonyTerrainGenerator/issues/25`

This is the living design record for bringing TheNightCrew into
RTSColonyTerrainGenerator and connecting it to the repository's planning,
implementation, verification, review, and delivery machinery. Decisions are recorded
here as they are resolved; implementation remains out of scope until the design is
agreed and decomposed into Gitea issues with acceptance criteria.

## Intended outcome

The Night Crew system delivers an approved MapGen Slice through this path:

```text
Gitea issue with acceptance criteria + repository Markdown planning
        ↓
Beads dependency and readiness planning
        ↓
TheNightCrew offers eligible work; a MapGen Night-Crew Worker claims it
        ↓
isolated branch and worktree
        ↓
LaunchKit tmux pipeline
TDD → simplify → architecture → code review
        ↓
MapGen verification gates
BDD legacy/net + Dafny + .NET + functional tests
        ↓
canonical Gitea pull request
        ↓
unmergeable GitHub draft review mirror
        ↓
Copilot review → bounded remediation → full retest → repeat until converged
        ↓
merge at the agreed authority gate
        ↓
close and reconcile the issue and Bead; notify with acceptance evidence and links
```

## Planning contract

Every implementation Slice begins as both a Gitea issue and durable Markdown inside
this repository. The issue carries explicit, testable acceptance criteria and links to
the repository document. The document contains enough behavioural and architectural
context for a fresh worker to act without relying on chat history.

Each Slice also has exactly one top-level Bead. The records divide authority as
follows:

- The Gitea Issue owns approved scope, acceptance criteria, human-visible status, and
  pull-request linkage.
- The Planning Document owns durable requirements, design, and verification context.
- The Bead owns dependency relationships and machine-readable readiness.
- The NightCrew Job owns only the runtime claim, progress, and execution outcome.

The Gitea Issue, Planning Document, and Bead link to one another and identify the same
Slice. A worker may not execute a Bead that lacks either link. If work must be split or
new work is discovered, the new Slice receives all three records before it can become
eligible. See ADR 0008.

## Eligibility and approval

Dependency readiness and human authorization are separate gates. `bd ready` answers
whether a Bead is unblocked; it does not authorize execution. `status: planned`
answers whether planning is complete; it also does not authorize execution.

Only Craig applying `night-crew: approved` to the canonical Gitea Issue authorizes
the Night Crew system to execute a Slice. A Slice is eligible only when all of these
conditions hold:

- the Gitea Issue is open and has both `status: planned` and
  `night-crew: approved`;
- the issue contains explicit acceptance criteria and links its Planning Document;
- the linked Planning Document exists in the repository;
- the top-level Bead points back to that issue and document and reports ready;
- no conflicting NightCrew claim exists; and
- every source needed to verify those facts is available and agrees.

Any missing, unavailable, or contradictory evidence fails closed. Workers and agents
must never apply the approval label themselves.

### Gitea approval queue

Gitea is the first approval interface and remains the authority:

- [Awaiting approval](http://192.168.2.48:3000/craigpars/RTSColonyTerrainGenerator/issues?type=all&state=open&labels=89,-98)
  shows planned issues without `night-crew: approved`.
- [Approved and waiting](http://192.168.2.48:3000/craigpars/RTSColonyTerrainGenerator/issues?type=all&state=open&labels=89,98)
  shows planned issues that Craig has authorized but no Worker has claimed.

From the awaiting list, Craig can open an issue and inspect its acceptance criteria
and Planning Document, or select one or more issue checkboxes and use **Label** to
apply `night-crew: approved`. The issue then leaves the awaiting list and enters the
approved list. Removing the label revokes approval before claim.

TheNightCrew may later show the same candidates and provide a convenience approval
button, but that button must write the Gitea label and must not store an independent
approval decision.

## Resolved boundary

TheNightCrew's source and product ownership move into this repository, but its role
does not expand today. TheNightCrew coordinates availability, claims, and progress. A
separate MapGen Night-Crew Worker owns worktrees, coding-agent execution, tests,
reviews, remediation, and delivery effects. "Night Crew system" names the combination.

Turning TheNightCrew itself into the executable pipeline is a future option, not part
of this integration. See ADR 0007.

## Existing machinery to reuse

- TheNightCrew already provides a durable Laravel job board, Worker identities,
  atomic claims, Gitea fences, an API, and a live dashboard.
- LaunchKit provides the sentinel-gated tmux pipeline and deterministic worker-state
  classification.
- RTSColonyTerrainGenerator provides Gitea issue lifecycle scripts, isolated branch
  conventions, the dual-reference BDD lane, Dafny verification, .NET tests, and
  Gitea-to-GitHub draft review mirrors.
- AMPB provides proven reviewer, structured review-marker, remediation-loop, agent
  adapter, and notification patterns that can be ported deliberately.
- The Daedalus design describes much of the repository-side worker loop and will be
  reconciled with this design rather than implemented as a competing orchestrator.

## Known integration gaps

- The current Beads client cannot authenticate to the configured Dolt server.
- This checkout has only a GitHub `origin`; the lifecycle scripts require a canonical
  Gitea remote and a separate GitHub mirror remote.
- TheNightCrew coordinator source still lives in its standalone repository.
- The MapGen Night-Crew Worker and its contract with TheNightCrew do not yet exist.
- AMPB's review and remediation machinery has not been extracted or adapted to the
  MapGen verification contract.
- GitHub draft mirrors exist, but requesting Copilot review, ingesting its findings,
  and reconciling them back to the canonical Gitea PR are not yet one bounded loop.
- Merge authority, failure escalation, retry ceilings, and notification destinations
  remain to be decided.

## Design decisions still to resolve

The grilling sequence will resolve these remaining dependencies in order: eligibility
and approval; isolation and claim recovery; phase and verification contracts; review
convergence; merge authority; completion and notification semantics; migration shape;
and end-to-end canary criteria.
