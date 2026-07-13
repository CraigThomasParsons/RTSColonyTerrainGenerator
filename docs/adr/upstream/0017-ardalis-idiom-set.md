<!-- Vendored verbatim from The-Pulse docs/adr/0017-ardalis-idiom-set.md (local checkout ~/Code/The-Pulse), fetched 2026-07-13. Do not edit here; propose changes upstream and re-vendor. -->
# Adopt the Ardalis idiom set: Result, FastEndpoints, Vogen, SmartEnum, GuardClauses

**Status:** Accepted (2026-07-03). Applies to the .NET rewrite (`net/`). Rides on ADR-0016 (the .NET 10
foundation), which must land first. Constrained throughout by ADR-0013 (the dual-backend parity
harness): during the migration the Express oracle is the wire truth.

Having aligned the base types and runtime with the Ardalis Clean Architecture template (ADR-0016), we
adopt the template's remaining code idioms. The governing rule the owner set: **when an Ardalis idiom
would change the HTTP wire contract, we intend to adopt it — but the change is deferred and recorded,
not taken mid-migration**, because the parity harness pins our observable behavior to the Express
oracle down to error-body shape (the `{message, code}` 400s matched exactly in slice #293). So idioms
split into *internal/representation* (taken now, verified byte-identical) and *wire-shape* (recorded as
debt, flipped once at cutover).

## Decision

### 1. `Ardalis.Result` internally; the wire stays oracle-faithful (deferred debt)

Command/query handlers return `Result<T>` / `Result` instead of bespoke records
(`LoginResult(bool Succeeded, string? FailureMessage, …)` and friends are deleted). This is
wire-invisible: the endpoint maps the `Result` to the response.

**We do NOT adopt `Ardalis.Result.AspNetCore`'s `.ToMinimalApiResult()`/`.ToActionResult()`
translation yet** — it emits RFC 7807 `ProblemDetails` (`{ type, title, status, errors:{…} }`), which
diverges from the oracle's `{message, code}` and would break the parity gate and the live React client.

> **Deferred debt (must be tracked).** A post-cutover ADR flips the wire to ProblemDetails, re-baselines
> every error-path parity golden to the .NET contract, and migrates the React SPA's error handling — in
> one coordinated change, once .NET is the contract-defining backend. Until then endpoints hand-map
> `Result` → `{message, code}`/`{message}`. File the follow-up so this does not evaporate.

### 2. FastEndpoints as the HTTP layer

Minimal-API handlers are rewritten as FastEndpoints REPR classes (`Endpoint<TRequest, TResponse>`) that
dispatch to `IMediator.Send`. Consequences:

- **Validation moves to FastEndpoints `Validator<TRequest>` classes** (FluentValidation under the hood);
  the Mediator `ValidationBehavior` and the `ValidationExceptionHandler` are retired.
- FastEndpoints' default validation-failure envelope (`{ statusCode, message, errors:{…} }`) is
  **overridden to stay `{message, code}`-faithful** — the same deferred-debt bucket as §1; the faithful
  override is removed when the wire flips at cutover.
- **`FastEndpoints.Swagger` + `Scalar`** provide the OpenAPI spec and reference UI (`net/` currently
  generates none).

### 3. Vogen for strongly-typed ids and single-value value objects

- Strongly-typed ids (`OperatorId`, `UserId`, …) and single-value VOs (`EmailAddress`, `TenantSlug`,
  `OperatorName`) become Vogen `readonly partial struct` types (`[ValueObject<Guid>]` /
  `[ValueObject<string>]`) with generated validation and EF/STJ converters. These replace the ADR-0015
  hand-written typed-id converters and satisfy `EntityBase<TId> where TId : struct` cleanly (structs
  use `EntityBase<TId>`; where the two-parameter form is needed, `EntityBase<T, TId>`).
- **Multi-field VOs decompose:** `PersonName` (first + last) is not a single primitive, so `FirstName`
  and `LastName` become Vogen `[ValueObject<string>]` types and `PersonName` becomes a thin EF
  **complex type** grouping them (it is already a two-column complex mapping per ADR-0015). **No value
  object is left on a hand-base.**
- **Parity guard:** Vogen's System.Text.Json converter must serialize the raw underlying primitive
  (Guid/string), so ids and VOs stay byte-identical on the wire. Verified by the comparator per
  endpoint before merge.

### 4. `Ardalis.SmartEnum` for all domain enums

Every domain enum (`PersonType`, `EmploymentStatus`, `TenantModuleStatus`, role labels, …) becomes a
`SmartEnum`, structurally eliminating the zero-default bug class (the `enum-0 SystemOwner → silent
EMPLOYEE` defect: a value-`0` member colliding with a DB column default).

- **Parity guard (critical):** the EF value converter maps to the member **Name** and the STJ converter
  (`Ardalis.SmartEnum.SystemTextJson`) emits the **exact** string the oracle stores/returns (e.g.
  `"EMPLOYEE"`). Both the persisted column and the JSON must be byte-identical to the oracle — a silent
  parity break if mis-wired, so each converted enum is comparator-checked against the oracle before
  merge.

### 5. `Ardalis.GuardClauses` in smart constructors

Hand-written `if (…) throw new ArgumentException(…)` in aggregate factory methods and Vogen `Validate`
bodies is replaced with `Guard.Against.*`. Internal only; no wire or parity impact.

### 6. Test-stack and dev-ergonomics extras

- **Test stack:** `xunit` 2.x → **`xunit.v3`**, `Moq` → **`NSubstitute`**, add **`Shouldly`**; add
  **`Ardalis.HttpClientTestExtensions`** for the integration-test `HttpClient` calls.
- **Dev ergonomics:** `NimblePros.Metronome` and `Ardalis.ListStartupServices` (both additive,
  dev-only; OpenTelemetry remains the production timing/telemetry source).

## Considered options

- **`Result.AspNetCore` / ProblemDetails on the wire now (rejected during migration).** Canonical
  Ardalis, but breaks the parity gate and the React client; deferred to a coordinated post-cutover flip
  (§1) rather than abandoned.
- **Defer FastEndpoints and bundle it with the wire-flip ADR (rejected by owner).** Would avoid
  churning the HTTP layer twice and fighting FE's default error envelope under the faithful-wire
  constraint; the owner chose to adopt FE now and carry the faithful override as interim debt.
- **Keep raw C# enums, fix defaults by hand (rejected).** Leaves the zero-default trap latent in every
  un-migrated enum; SmartEnum removes the class structurally.
- **Keep class-based value-object ids via `EntityBase<T, TId>` (rejected).** Avoids Vogen but keeps the
  id boilerplate the owner wants gone and diverges from the Vogen id story the base types are shaped
  for.

## Consequences

- A large, mostly mechanical refactor across every context; sequence it **after** the ADR-0016 net10 +
  kernel slice, per idiom, each gated by the parity comparator (`just parity-smoke`) and the arch
  tests. Representation-touching idioms (Vogen STJ, SmartEnum EF/STJ) are the parity-sensitive ones and
  are verified byte-identical before merge.
- **A deferred-debt register is created and tracked** — the wire flip to ProblemDetails (§1) and the
  removal of the FastEndpoints faithful-error override (§2) both land in one post-cutover ADR that also
  re-baselines error-path goldens and migrates the React client. This is the price of "Ardalis idiom
  wins" being honored as a *direction* while the oracle remains the wire truth.
- `Ardalis.Result` and `Ardalis.GuardClauses` join `Ardalis.Specification` as the sanctioned Ardalis
  packages; `Vogen`, `Ardalis.SmartEnum`(`.SystemTextJson`), `FastEndpoints`(`.Swagger`), `Scalar`,
  and the test-stack packages are added to `Directory.Packages.props`.
- Lineage: ADR-0013 (parity harness — the governing constraint), ADR-0015 (repository/converters this
  revises), ADR-0016 (net10 + owned kernel — the foundation). Indexed in `net/AGENTS.md`.
