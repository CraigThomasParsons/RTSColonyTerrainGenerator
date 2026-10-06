import { useEffect, useRef, useState } from "react";

import type { MapPreview } from "~/shared/api/contract.ts";
import { loadForestTileset, type Tileset, type TilesetLoader } from "../lib/forestTileset.ts";
import { createPreviewSurface } from "../lib/previewSurface.ts";
import { usePreviewRenderMode } from "../model/renderMode.ts";

import styles from "./MapPreviewPanel.module.css";

/**
 * The map, drawn. React owns the canvas element's lifetime; the engine owns everything
 * painted onto it. Beyond the mount point, this component owns two things: the tiled /
 * flat-colour toggle, and loading the tileset. A failed load drops to flat colour rather
 * than leaving an empty canvas.
 */
export interface MapPreviewPanelProps {
  preview: MapPreview | null;
  approvedBackgroundUrl?: string | null;
  showStartZones?: boolean;
  showResources?: boolean;
  /**
   * Where the tileset comes from. Injected so tests never load a real image. Pass a stable
   * function: a new identity restarts an in-flight load.
   */
  loadTileset?: TilesetLoader;
}

type TilesetState =
  | { status: "idle" }
  | { status: "ready"; tileset: Tileset }
  | { status: "failed" };

export function MapPreviewPanel({
  preview,
  approvedBackgroundUrl,
  showStartZones = true,
  showResources = true,
  loadTileset = loadForestTileset,
}: MapPreviewPanelProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [renderMode, setRenderMode] = usePreviewRenderMode();
  const [tilesetState, setTilesetState] = useState<TilesetState>({ status: "idle" });

  // Load once, and only once someone actually wants tiles. The state stays "idle" while
  // the load is in flight. Switching to flat colour mid-load drops the result, and
  // switching back starts a fresh load.
  const wantsTiles = renderMode === "tiled";
  useEffect(() => {
    if (!wantsTiles || tilesetState.status !== "idle") {
      return;
    }

    let cancelled = false;
    loadTileset().then(
      (loaded) => {
        if (!cancelled) {
          setTilesetState({ status: "ready", tileset: loaded });
        }
      },
      () => {
        if (!cancelled) {
          setTilesetState({ status: "failed" });
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [wantsTiles, tilesetState.status, loadTileset]);

  let tileset: Tileset | undefined;
  if (wantsTiles && tilesetState.status === "ready") {
    tileset = tilesetState.tileset;
  }

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !preview) {
      return;
    }

    const options = { showStartZones, showResources, tileset };
    let surface: ReturnType<typeof createPreviewSurface> | undefined;
    let cancelled = false;
    if (!approvedBackgroundUrl) {
      surface = createPreviewSurface(canvas, preview, undefined, options);
    } else {
      const image = new Image();
      image.onload = () => { if (!cancelled) surface = createPreviewSurface(canvas, preview, image, options); };
      image.onerror = () => { if (!cancelled) surface = createPreviewSurface(canvas, preview, undefined, options); };
      image.src = approvedBackgroundUrl;
    }
    return () => { cancelled = true; surface?.destroy(); };
  }, [preview, approvedBackgroundUrl, showResources, showStartZones, tileset]);

  if (!preview) {
    return (
      <div className={styles.stage}>
        <p className={styles.empty}>No map yet — generate one to see it here.</p>
      </div>
    );
  }

  return (
    <div className={styles.stage}>
      <canvas
        ref={canvasRef}
        className={styles.canvas}
        role="img"
        // The grid size comes off the preview: the document grid is not the request's cell
        // dimensions, and ADR 0004's resolution-mapping question is not this slice's to answer.
        aria-label={`Generated map preview, ${preview.width} x ${preview.height} tiles`}
      />
      <div className={styles.controls}>
        <button
          type="button"
          className={styles.toggle}
          aria-pressed={wantsTiles}
          onClick={() => {
            if (wantsTiles) {
              setRenderMode("flat");
            } else {
              setRenderMode("tiled");
            }
          }}
        >
          Game tiles
        </button>
        {wantsTiles && tilesetState.status === "failed" && (
          <p role="status" className={styles.notice}>
            Tileset unavailable — showing flat colour.
          </p>
        )}
      </div>
    </div>
  );
}
