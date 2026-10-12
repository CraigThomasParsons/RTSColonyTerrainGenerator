# MapGen.Api

The HTTP transport shell over `MapGen.Application` (ADR
[0004](../../docs/adr/0004-ampb-integration-boundary.md)). It adds **no domain
behaviour**: every endpoint dispatches an existing CQRS request through Mediator
(ADR 0005) and maps the result onto a status code.

The endpoint shapes are fixed by the Wire Contract in
[docs/plans/map-gui-prototype.md](../../docs/plans/map-gui-prototype.md). That
section is the contract; this project — and the OpenAPI document it serves —
merely describe it.

## Running it

```bash
dotnet run --project src/MapGen.Api      # http://127.0.0.1:5187/api/v1
```

**Internal by construction.** Kestrel binds `127.0.0.1` only (`appsettings.json`)
and CORS allows exactly the Vite dev origins. There is no auth, which is safe
*only* because nothing off-host can reach it. In Phase 2 the Laravel BFF (Backend For Frontend) becomes
the only caller and holds the internal service token.

The OpenAPI document (`/openapi/v1.json`) is served in Development only.

## PixelLab presentation jobs

Map Studio uses `/api/v1/pixellab/*` to run the repository-owned candidate
orchestrator. The browser sends a completed world-job ID, never an input path or
an API token. The server resolves the golden `.worldpayload`, stores durable job
state beneath `.runtime/pixellab/`, and starts Python with an argument list and
`UseShellExecute=false`.

Generation defaults to `offline`, a zero-network dry-run. Live execution is
refused unless the request selects `live` and sets both explicit confirmations;
the token remains a server environment variable. Candidate images are available
for comparison after structural validation, but the map renderer activates one
only after an operator records an approval with their name and reason. Start-zone
and resource overlays remain authoritative and are always painted above it.

The API integration suite replaces the process executor with a fake transport.
It covers success, cache hit, failure, retry, approval, image collection, and
secret non-disclosure without contacting PixelLab or spending credits.

Development configuration also enables that fake transport for interactive Map
Studio testing. Its readiness banner says `development-fake` and reports fake
credits so it cannot be confused with an account balance. Set
`MapGen:PixelLab:UseFakeTransport=false` to exercise the real adapter; do not do
that merely to test the UI.

## What backs the world endpoints

`MapGen.Application` has no generation handler — its whole surface is the two
tile-resolution commands. So `POST /worlds` and friends **replay the golden-job
fixtures** under `tests/fixtures/golden/`, narrating stages against the clock and
projecting the replayed artifacts into a `MapDocument` and a `MapPreview`. The
fixtures are read-only; nothing here writes to them.

Which fixture a job replays is chosen from its seed, so the same seed always
yields the same map. `MapGen:WorldGeneration:StageDuration` controls how long each
narrated stage dwells (300 ms by default; zero means a job succeeds immediately).

The two `/tiles/*` endpoints are the only ones backed by real verified domain
code, and they wrap `ResolveTileRegionCommand` / `ComputeAdjacencyMaskCommand`
unchanged.

## Tests

```bash
just test-api        # dotnet test tests/MapGen.Api.Tests
```

They host this exact application in-process and assert the raw JSON — the wire is
the contract, and the client's hand-written TypeScript types are mirrored against
these assertions.
