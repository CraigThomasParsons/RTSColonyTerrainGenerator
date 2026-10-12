import { useId, useState, type FormEvent } from "react";

import type { WorldJobSnapshot } from "~/entities/world";
import type { GenerateWorldRequest } from "~/shared/api/contract.ts";

import styles from "./GenerateWorldForm.module.css";

/**
 * Submitting a generation job, and narrating the one that is running.
 *
 * The form is a controlled dumb component: it takes a snapshot and an action, so the feature
 * carries no knowledge of polling or transport. `stage` is shown but never branched on — it
 * is legacy-pipeline vocabulary that will change as the .NET conversion proceeds.
 */
export interface GenerateWorldFormProps {
  snapshot: WorldJobSnapshot;
  onGenerate: (request: GenerateWorldRequest) => void;
}

const DEFAULT_CELLS = 64;

export function GenerateWorldForm({ snapshot, onGenerate }: GenerateWorldFormProps) {
  const ids = {
    width: useId(),
    height: useId(),
    seed: useId(),
    name: useId(),
  };

  const [width, setWidth] = useState(String(DEFAULT_CELLS));
  const [height, setHeight] = useState(String(DEFAULT_CELLS));
  const [seed, setSeed] = useState("");
  const [name, setName] = useState("");

  const busy = snapshot.phase === "submitting" || snapshot.phase === "polling";

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const request: GenerateWorldRequest = {
      map_width_in_cells: Number(width),
      map_height_in_cells: Number(height),
    };

    // Omitted rather than empty: the server picks a seed and echoes it back, and the seed
    // is passed on as typed so an int64 beyond 2^53 survives the round trip.
    if (seed.trim() !== "") {
      request.seed = seed.trim();
    }
    if (name.trim() !== "") {
      request.name = name.trim();
    }

    onGenerate(request);
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <h2 className={styles.heading}>Generate a world</h2>

      <div className={styles.pair}>
        <label className={styles.field} htmlFor={ids.width}>
          <span>Map width in cells</span>
          <input
            id={ids.width}
            type="number"
            min={1}
            value={width}
            onChange={(event) => setWidth(event.target.value)}
          />
        </label>

        <label className={styles.field} htmlFor={ids.height}>
          <span>Map height in cells</span>
          <input
            id={ids.height}
            type="number"
            min={1}
            value={height}
            onChange={(event) => setHeight(event.target.value)}
          />
        </label>
      </div>

      <label className={styles.field} htmlFor={ids.seed}>
        <span>Seed</span>
        <input
          id={ids.seed}
          inputMode="numeric"
          placeholder="left empty, the server picks one"
          value={seed}
          onChange={(event) => setSeed(event.target.value)}
        />
      </label>

      <label className={styles.field} htmlFor={ids.name}>
        <span>Name</span>
        <input
          id={ids.name}
          placeholder="Default Forest"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </label>

      <button className={styles.submit} type="submit" disabled={busy}>
        {busy ? "Generating…" : "Generate"}
      </button>

      {snapshot.status && <JobProgress snapshot={snapshot} />}

      {snapshot.error && (
        <p className={styles.error} role="alert">
          {snapshot.error}
        </p>
      )}
    </form>
  );
}

function JobProgress({ snapshot }: { snapshot: WorldJobSnapshot }) {
  const status = snapshot.status;
  if (!status) {
    return null;
  }

  return (
    <dl className={styles.progress}>
      <div className={styles.progressRow}>
        <dt>Stage</dt>
        {/* Null while queued — the Status row already says so; restating it here read as
            a stage named "queued", which is not in the stage vocabulary. */}
        <dd>{status.stage ?? "—"}</dd>
      </div>
      <div className={styles.progressRow}>
        <dt>Status</dt>
        <dd>{status.status}</dd>
      </div>
      <div className={styles.progressRow}>
        <dt>Seed</dt>
        <dd className={styles.mono}>{status.seed}</dd>
      </div>
      <div
        className={styles.bar}
        role="progressbar"
        aria-label="Generation progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={status.pct}
      >
        <span className={styles.barFill} style={{ width: `${status.pct}%` }} />
      </div>
    </dl>
  );
}
