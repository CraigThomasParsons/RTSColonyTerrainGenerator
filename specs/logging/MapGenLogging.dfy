/**
 * MapGenerator Logging Contract
 * =============================
 *
 * PURPOSE
 * -------
 * This module defines the *canonical* structure and validity rules
 * for all log events emitted by MapGenerator pipeline stages.
 *
 * This is NOT a logging framework.
 * This file does NOT:
 *   - Write logs to disk
 *   - Format log output
 *   - Decide where logs are stored
 *   - Perform I/O of any kind
 *
 * Instead, it defines:
 *   - What a log event *is*
 *   - What makes a log event *valid*
 *   - What all pipeline stages must agree on
 *
 * Think of this file as:
 *   "The constitution of logging for MapGenerator"
 *
 * WHY THIS EXISTS
 * ---------------
 * In a multi-language pipeline (Rust, C#, PHP, Kotlin, etc.),
 * behavior diverges easily and silently.
 *
 * This contract prevents:
 *   - Missing fields
 *   - Ambiguous log formats
 *   - Inconsistent semantics between stages
 *   - Downstream tooling breakage
 *
 * If this file verifies, every language can safely rely on it.
 */

module {:extern "MapGen.Logging"} MapGenLogging {

  /**
   * Log severity levels.
   *
   * DESIGN NOTE:
   * ------------
   * We intentionally keep this small and conventional.
   * Exotic or highly granular log levels tend to fragment
   * tooling and make aggregation harder.
   */
  datatype LogLevel =
    | Trace
    | Debug
    | Info
    | Warn
    | Error


  /**
   * Canonical log event structure.
   *
   * DESIGN PRINCIPLES:
   * ------------------
   * - Flat structure (easy JSON serialization)
   * - No optional core fields (avoid ambiguity)
   * - Language-agnostic types
   *
   * FIELD NOTES:
   * ------------
   * ts:
   *   Intended to represent Unix timestamp in milliseconds (UTC).
   *   We use `int` instead of `int64` because Dafny integers are
   *   mathematical and unbounded; concrete bit-width is a
   *   *language-level concern*, not a spec concern.
   *
   * kv:
   *   Key/value pairs are restricted to string-to-string.
   *   This avoids cross-language serialization pitfalls and
   *   keeps logs trivially indexable.
   */
  datatype LogEvent = LogEvent(
    //This is intended to represent Unix milliseconds.
    ts: int,

    // Pipeline stage emitting the log.
    stage: string,

    // Unique job identifier (UUID format), so we can grep logs by job.
    job_id: string,

    // Log severity level.
    level: LogLevel,

    // Event name, e.g., "heightmap_generation_started".
    event: string,

    // Human-readable message.
    msg: string,

    // Additional key/value metadata.
    kv: map<string, string>
  )

  /**
   * Determines whether a string is non-empty.
   *
   * WHY THIS EXISTS:
   * ----------------
   * We name this explicitly instead of inlining `|s| > 0`
   * everywhere to make intent obvious at call sites.
   *
   * This mirrors the philosophy:
   *   "Readable predicates > clever expressions"
   */
  predicate NonEmpty(s: string)
  {
    |s| > 0
  }

  /**
   * Performs a minimal sanity check for UUID-like strings.
   *
   * DESIGN NOTE:
   * ------------
   * This is *not* a full UUID validation.
   * We intentionally avoid regex-heavy or version-specific
   * checks to keep the contract:
   *
   *   - Portable
   *   - Language-agnostic
   *   - Cheap to satisfy
   *
   * Downstream systems may enforce stricter validation
   * if they choose.
   */
  predicate LooksLikeUuid(s: string)
  {
    |s| == 36 &&
    s[8]  == '-' &&
    s[13] == '-' &&
    s[18] == '-' &&
    s[23] == '-'
  }


  /**
   * Determines whether a log event is safe to emit.
   *
   * THIS IS THE CORE CONTRACT.
   *
   * If `Valid(e)` holds, downstream systems may assume:
   *   - Required fields exist
   *   - Strings are meaningful
   *   - Identifiers are structurally sane
   *
   * FAILURE MODE:
   * -------------
   * Code that attempts to emit invalid log events
   * will fail verification or compilation.
   *
   * This replaces:
   *   - Runtime guessing
   *   - Defensive parsing everywhere
   *   - Tribal knowledge
   */
  predicate Valid(e: LogEvent)
  {
    e.ts >= 0 &&
    NonEmpty(e.stage) &&
    LooksLikeUuid(e.job_id) &&
    NonEmpty(e.event) &&
    NonEmpty(e.msg)
  }


  /**
   * Enforces the logging contract.
   *
   * WHY THIS METHOD EXISTS:
   * -----------------------
   * This method has no runtime behavior.
   * Its sole purpose is to *force callers* to prove
   * that the log event satisfies the contract.
   *
   * Think of this as a guard clause that runs at
   * verification time instead of runtime.
   */
  class LogContract {

    static method RequireValid(e: LogEvent)
      requires Valid(e)
    {
      // Intentionally empty.
      //
      // If this method can be called,
      // the proof obligation has already succeeded.
    }


    /**
     * Determines whether an event name follows project conventions.
     *
     * CONVENTION:
     * -----------
     * - lowercase
     * - snake_case
     * - alphanumeric with underscores
     *
     * DESIGN NOTE:
     * ------------
     * We keep this separate from `Valid(e)` so that
     * naming conventions can evolve without invalidating
     * historical logs.
     */
    static function IsReasonableEventName(name: string): bool
    {
      NonEmpty(name) &&
      (forall i :: 0 <= i < |name| ==>
        (name[i] >= 'a' && name[i] <= 'z') ||
        (name[i] >= '0' && name[i] <= '9') ||
        name[i] == '_')
    }
  }
}
