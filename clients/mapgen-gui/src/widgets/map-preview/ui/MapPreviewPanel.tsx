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
  approvedBackgroundUrl?: string | null;
}

export function MapPreviewPanel({ preview, approvedBackgroundUrl }: MapPreviewPanelProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !preview) {
      return;
    }

    let surface: ReturnType<typeof createPreviewSurface> | undefined;
    let cancelled = false;
    if (!approvedBackgroundUrl) {
      surface = createPreviewSurface(canvas, preview);
    } else {
      const image = new Image();
      image.onload = () => { if (!cancelled) surface = createPreviewSurface(canvas, preview, image); };
      image.onerror = () => { if (!cancelled) surface = createPreviewSurface(canvas, preview); };
      image.src = approvedBackgroundUrl;
    }
    return () => { cancelled = true; surface?.destroy(); };
  }, [preview, approvedBackgroundUrl]);

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
