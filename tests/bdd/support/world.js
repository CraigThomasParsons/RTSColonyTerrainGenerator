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
   * The profile seam: hand in one adapter per target, get back the one for the active
   * profile. Step files never mention profile names — the world owns dispatch.
   *   const expand = this.viaTarget({ net: expandViaNet, legacy: expandViaLegacy });
   */
  viaTarget(adapters) {
    const adapter = adapters[this.target];
    if (!adapter) {
      throw new Error(
        `No adapter for target "${this.target}" — got: ${Object.keys(adapters).join(", ")}. ` +
          `If this step is net-only, tag its scenario @net-only and guard with requireNetTarget.`,
      );
    }
    return adapter;
  }

  /**
   * Guard for @net-only steps: they exist only on the new implementation's boundary
   * (documented asymmetries, e.g. per-cell rejection). Profiles exclude the tag for
   * the legacy target; this guard makes a mis-tagged scenario fail loudly instead of
   * silently exercising the wrong backend.
   */
  requireNetTarget(capability) {
    if (this.target !== "net") {
      throw new Error(
        `"${capability}" is @net-only — it has no legacy equivalent. ` +
          `Run it under the net profile (npm run bdd:net).`,
      );
    }
  }
}

setWorldConstructor(MapGenWorld);
