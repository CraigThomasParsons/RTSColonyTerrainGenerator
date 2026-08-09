import { useEffect, useRef } from "react";

import type { MapPreview } from "~/shared/api/contract.ts";
import { createPreviewSurface } from "../lib/previewSurface.ts";

import styles from "./MapPreviewPanel.module.css";

/**
 * The map, drawn. React owns the canvas element's lifetime; the engine owns everything
 * painted onto it, so this component is a mount point and nothing else.
 */
export interface MapPreviewPanelProps {
  preview: MapPreview | null;
}

export function MapPreviewPanel({ preview }: MapPreviewPanelProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !preview) {
      return;
    }

    const surface = createPreviewSurface(canvas, preview);
    return () => surface.destroy();
  }, [preview]);

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
    </div>
  );
}
