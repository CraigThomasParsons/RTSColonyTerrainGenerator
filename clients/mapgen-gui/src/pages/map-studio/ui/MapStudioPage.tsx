import { useWorldJob } from "~/entities/world";
import { GenerateWorldForm } from "~/features/generate-world";
import type { MapGenClient } from "~/shared/api/mapgenClient.ts";
import { MapPreviewPanel } from "~/widgets/map-preview";

import styles from "./MapStudioPage.module.css";

/**
 * The prototype's one page: a control rail over a full-bleed preview stage. Composition only
 * — it holds the world job and hands its snapshot to the feature and the widget, neither of
 * which knows the other exists.
 */
export interface MapStudioPageProps {
  client: MapGenClient;
  pollIntervalMs: number;
}

export function MapStudioPage({ client, pollIntervalMs }: MapStudioPageProps) {
  const { snapshot, generate } = useWorldJob(client, pollIntervalMs);

  return (
    <main className={styles.page}>
      <section className={styles.stage}>
        <MapPreviewPanel preview={snapshot.preview} />
      </section>

      <aside className={styles.rail}>
        <header className={styles.brand}>
          <h1 className={styles.title}>MapGen</h1>
          <p className={styles.subtitle}>
            Local prototype · MapGen.Api · capybara_2d_engine preview
          </p>
        </header>

        <GenerateWorldForm snapshot={snapshot} onGenerate={generate} />

        {snapshot.jobId && (
          <footer className={styles.jobId}>
            job <code>{snapshot.jobId}</code>
          </footer>
        )}
      </aside>
    </main>
  );
}
