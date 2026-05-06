# Go Coding Style & Commenting Conventions (Project-Aligned)

This document defines the required Go coding style for all MapGenerator and
Heightmap-related Go code.

The goals are clarity, explicitness, and long-term maintainability. Favor
boring, readable code over cleverness.

---

## Core Philosophy

- Code must be understandable months later without external context.
- Readability beats brevity; avoid terse or clever constructs.
- Descriptive names everywhere; avoid abbreviations.
- Fail fast, guard early, and be explicit about errors.
- Keep modules focused: one clear responsibility per package/file.

---

## Standards Compliance

- **gofmt is mandatory**; never hand-format.
- **Static analysis**: run `go vet` and `golangci-lint` where available.
- Use the standard library whenever practical; avoid unnecessary deps.

---

## Naming Conventions (LOCKED)

- Exported: `PascalCase`. Unexported: `camelCase`.
- Receivers and locals must be **>= 3 characters** and descriptive (project rule).
- Avoid abbreviations unless they are domain terms (e.g., `URL`, `API`).
- Functions/methods are verb-based and explicit: `enqueueHeightmapJob`,
  `startWatcherLoop`, `publishJobUpdate`.
- Constants: `ALL_CAPS_WITH_UNDERSCORES` for configuration values; otherwise
  prefer typed `const` with meaningful names.

Good:

```go
pipelineRootDirectory := resolvePipelineRoot()
heightmapInboxPath := filepath.Join(pipelineRootDirectory, "Heightmap/inbox")
```

Bad:

```go
pr := resolvePipelineRoot()
inbox := filepath.Join(pr, "Heightmap/inbox")
```

---

## File & Package Structure

- One responsibility per package; avoid mixed concerns.
- Keep files short and focused on a single concept.
- API handlers should do one thing: validate, execute, respond.

---

## Commenting Rules (CRITICAL)

- Target: a meaningful comment every 3–5 logical statements.
- Comments explain **why** more than **what**. Avoid narrating syntax.
- Document guard clauses: why the early exit exists.
- Use block comments to describe package/file intent and boundaries.
- Keep examples current; delete stale comments.

Examples:

```go
// Reject empty bodies to avoid writing malformed jobs to disk.
if strings.TrimSpace(bodyText) == "" {
    http.Error(responseWriter, "empty body", http.StatusBadRequest)
    return
}
```

```go
// EventHub broadcasts job state changes to SSE clients.
// It favors availability over delivery guarantees; slow clients may drop events.
type EventHub struct { ... }
```

---

## Error Handling

- Fail fast with guard clauses; avoid deep nesting.
- Always wrap returned errors with context: `fmt.Errorf("enqueue job: %w", err)`.
- Never ignore errors; handle explicitly.
- Prefer clear HTTP error responses over silent failures.

---

## JSON & I/O

- Always set `Content-Type` explicitly.
- Use `json.Decoder`/`Encoder` with proper error checks.
- Avoid partial reads; prefer `io.ReadAll` only for bounded bodies.
- Validate external input before use.

---

## Concurrency

- Protect shared state with mutexes; prefer `sync.RWMutex` for read-heavy paths.
- Channels must be buffered when used for fan-out; avoid unbounded blocking.
- Document goroutines: what they watch, how they stop, and which channel closes them.

---

## Guard Clauses

- Place validations at the top of functions.
- Comment each guard with intent.
- Return early to keep happy path shallow.

---

## Formatting Rules

- `gofmt` controls whitespace; do not hand-tune alignment.
- One statement per line; no inline `if` bodies.
- Blank lines separate logical sections.

---

## Forbidden Practices

- 🚫 Variables shorter than 3 characters (project rule).
- 🚫 Abbreviated or unclear names.
- 🚫 Deeply nested conditionals when guard clauses suffice.
- 🚫 Silent error ignoring (`_ = ...`).
- 🚫 Clever one-liners that obscure intent.
- 🚫 Mixing unrelated concerns in a single function.

---

## Canonical Example

```go
// enqueueHeightmapJob accepts a JSON payload and writes a job file into the
// heightmap inbox. It does not run the engine or wait for results.
func enqueueHeightmapJob(responseWriter http.ResponseWriter, request *http.Request) {
    // Reject empty bodies to prevent invalid jobs from being queued.
    bodyBytes, readError := io.ReadAll(request.Body)
    if readError != nil {
        http.Error(responseWriter, "unable to read body", http.StatusBadRequest)
        return
    }

    trimmedBody := strings.TrimSpace(string(bodyBytes))
    if trimmedBody == "" {
        http.Error(responseWriter, "empty body", http.StatusBadRequest)
        return
    }

    var enqueueRequest EnqueueRequest
    decodeError := json.Unmarshal(bodyBytes, &enqueueRequest)
    if decodeError != nil {
        http.Error(responseWriter, "invalid JSON payload", http.StatusBadRequest)
        return
    }

    jobIdentifier := generateJobIdentifier()
    jobFilePath := filepath.Join(heightmapInboxDirectory, jobIdentifier+".json")

    writeError := writeJobFile(jobFilePath, enqueueRequest, jobIdentifier)
    if writeError != nil {
        http.Error(responseWriter, "failed to write job", http.StatusInternalServerError)
        return
    }

    responseWriter.Header().Set("Content-Type", "application/json")
    json.NewEncoder(responseWriter).Encode(map[string]string{
        "job_id": jobIdentifier,
    })
}
```

---

Final rule: if a future reader must guess intent, the code is wrong. Clarity is the priority.
