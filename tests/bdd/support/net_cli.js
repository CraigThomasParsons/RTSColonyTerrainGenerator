// Shared driver for the net target: run a MapGen.Cli subcommand, speak its JSON
// protocol (JSON on stdout; failures exit 1 with {"error": ...} still on stdout).
// Every net adapter uses this — the CLI invocation details live only here.
import { execFileSync } from "node:child_process";
import path from "node:path";

const CLI_PROJECT = path.join(process.cwd(), "src", "MapGen.Cli");

/** Run a subcommand; returns { ok: true, ...payload } or { ok: false, error }. */
export function runCliJson(subcommand, args) {
  let stdout;
  try {
    stdout = execFileSync(
      "dotnet",
      ["run", "--project", CLI_PROJECT, "--no-build", "--", subcommand, ...args],
      { encoding: "utf8", timeout: 60_000 },
    );
  } catch (err) {
    const line = String(err.stdout ?? "").trim();
    if (line.length > 0) {
      return { ok: false, error: JSON.parse(line).error };
    }
    throw new Error(`MapGen.Cli failed without JSON output (run 'just build' first?): ${err.message}`);
  }
  return { ok: true, ...JSON.parse(stdout.trim()) };
}
