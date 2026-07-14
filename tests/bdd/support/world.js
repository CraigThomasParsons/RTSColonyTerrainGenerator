/**
 * MapGenWorld — the per-scenario world for the MapGenerator pipeline.
 *
 * Shape inherited from ThePulseProject's PulseWorld, with pipeline-native abilities in
 * place of HTTP: where Pulse selects a backend by baseUrl, we select by `target`:
 *   'legacy' — the existing filesystem pipeline (stages under MapGenerator/, the baseline)
 *   'net'    — the new C# CQRS implementation (grows as slices are promoted in net-ready.tags)
 *
 * The filesystem is the source of truth (tools/README.md): a stage is done when its
 * artifact appears in its outbox. The world therefore answers questions by reading lanes,
 * never by asking a daemon.
 */
import { setWorldConstructor, World } from "@cucumber/cucumber";
import fs from "node:fs";
import path from "node:path";

const REPO_ROOT = process.cwd();
const STAGES_ROOT = path.join(REPO_ROOT, "MapGenerator");

/** Directories under MapGenerator/ that are not pipeline stages. */
const NON_STAGE_DIRS = new Set(["bin", "systemd"]);

export class MapGenWorld extends World {
  constructor(options) {
    super(options);
    this.target = options.parameters.target ?? "legacy";
    this.repoRoot = REPO_ROOT;
    this.currentPersona = null;
    this.jobId = null;
  }

  /** All stage directories currently registered in the pipeline. */
  stageNames() {
    return fs
      .readdirSync(STAGES_ROOT, { withFileTypes: true })
      .filter((e) => e.isDirectory() && !NON_STAGE_DIRS.has(e.name))
      .map((e) => e.name)
      .sort();
  }

  stagePath(stage, ...segments) {
    return path.join(STAGES_ROOT, stage, ...segments);
  }

  stageHasLane(stage, lane) {
    return fs.existsSync(this.stagePath(stage, lane));
  }

  /**
   * Where a scenario acts against the new implementation, it must fail loudly until the
   * slice is promoted — a silent fallback to the legacy pipeline would fake parity.
   */
  requireNetTarget(capability) {
    if (this.target === "net") {
      throw new Error(
        `The 'net' target does not implement "${capability}" yet. ` +
          `Slices are promoted explicitly via tests/bdd/net-ready.tags.`,
      );
    }
  }
}

setWorldConstructor(MapGenWorld);
