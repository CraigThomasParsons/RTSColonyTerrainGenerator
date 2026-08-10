/**
 * Lossless carriage of the contract's `int64` fields across `JSON.parse` / `JSON.stringify`.
 *
 * `seed` is an int64 on the wire and the server picks it with
 * `Random.Shared.NextInt64(0, long.MaxValue)`, so it routinely exceeds
 * `Number.MAX_SAFE_INTEGER`. `JSON.parse` would silently round it, and ADR 0004 §4
 * determinism requires the client learn the exact seed it got — a rounded seed resubmitted
 * generates a different map.
 *
 * So: quote the int64 fields before parsing (they become decimal strings in TypeScript) and
 * unquote them after stringifying (they go back onto the wire as JSON numbers). The wire
 * bytes are unchanged; only the in-memory representation differs.
 *
 * Limitation, stated rather than hidden: this is a textual rewrite keyed on the field name
 * at an object-key position, not a full JSON re-tokenisation. A *string value* elsewhere in
 * the document that itself contains the literal text `"seed": 123` would also be rewritten.
 * The documents on this surface are small and machine-generated, and the failure mode is a
 * mangled display string rather than a wrong map, so the trade is deliberate.
 */

const INT64_FIELDS = ["seed"] as const;

const keyed = (field: string, pattern: string) =>
  new RegExp(String.raw`([{,]\s*"${field}"\s*:\s*)${pattern}`, "g");

/** Parse a response body, widening the contract's int64 fields to decimal strings. */
export function parseJsonWithInt64<T>(text: string): T {
  const quoted = INT64_FIELDS.reduce(
    (json, field) => json.replace(keyed(field, String.raw`(-?\d+)`), '$1"$2"'),
    text,
  );
  return JSON.parse(quoted) as T;
}

/** Serialise a request body, narrowing the contract's int64 fields back to JSON numbers. */
export function stringifyJsonWithInt64(value: unknown): string {
  return INT64_FIELDS.reduce(
    (json, field) => json.replace(keyed(field, String.raw`"(-?\d+)"`), "$1$2"),
    JSON.stringify(value),
  );
}
