# Thoughts

- 2026-01-23
  - Started WorldFeatures Kotlin module with deterministic feature planning.
  - Why: Kotlin provides a typed, testable runtime without touching existing pipeline stages.
  - Added AI testing tool usage as part of the manual validation loop.
  - Why: Real-time log heuristics shorten debugging cycles.

- 2026-01-23
  - Updated TreePlanter JobLocator to select the newest complete job by artifact modification time.
  - Why: Old artifacts remain in outboxes, so picking the lexicographically first file causes repeat processing and stalls new work.
  - Why: Using the max mtime across heightmap, maptiles, and weather makes the job freshness reflect the last-produced artifact.
  - Refactored TreePlanter PHP code to align with php_style.md (Why-heavy comments, descriptive variables).
  - Why: Consistent style and explicit intent reduce regressions when pipelines grow.
  - Installed phpmd/phpmd for TreePlanter and ran it on src and run.php.
  - Why: Static analysis highlights complexity hotspots and naming violations early.
  - Added an AI-style pipeline test helper under tools/pipeline_ai_test.
  - Why: Real-time log heuristics make regressions obvious while iterating on pipeline stages.
  - Expanded AI heuristics with stage timeouts, artifact checks, and log-based triage suggestions.
  - Why: Faster root-cause hints reduce time spent scanning logs manually.
  - Began WorldFeatures Kotlin implementation with deterministic feature planning and unit tests.
  - Why: A typed module reduces error rates and is easier to validate with tests.

- 2026-01-26
  - Validated WCAR parsing rules and added strict HEAD-first and dimension checks.
  - Why: WCAR is a canonical artifact and must fail fast on malformed structure.
  - Cleaned up MapGenerator stages reference with updated inbox/outbox details.
  - Why: The pipeline guide is the top-level operational reference for new stages.
