import { useCallback, useState } from "react";

/**
 * How the preview paints its grid layers: AMPB's tiles, or flat colour for debugging
 * generation. Client-only. It is never part of any payload.
 */
export type PreviewRenderMode = "tiled" | "flat";

export const RENDER_MODE_STORAGE_KEY = "mapgen.preview.renderMode";

const DEFAULT_RENDER_MODE: PreviewRenderMode = "tiled";

/**
 * The render mode, kept in `sessionStorage` so it survives new generations and remounts
 * within a session, and resets with the tab. Storage that throws (private mode, quota)
 * costs only the persistence, never the toggle.
 */
export function usePreviewRenderMode(): [PreviewRenderMode, (mode: PreviewRenderMode) => void] {
  const [mode, setModeState] = useState<PreviewRenderMode>(readStoredMode);

  const setMode = useCallback((next: PreviewRenderMode) => {
    setModeState(next);
    try {
      window.sessionStorage.setItem(RENDER_MODE_STORAGE_KEY, next);
    } catch {
      // Persistence is a convenience; the in-memory state above is the source of truth.
    }
  }, []);

  return [mode, setMode];
}

function readStoredMode(): PreviewRenderMode {
  try {
    const stored = window.sessionStorage.getItem(RENDER_MODE_STORAGE_KEY);
    if (stored === "tiled" || stored === "flat") return stored;
  } catch {
    // Unreadable storage behaves like an empty one.
  }
  return DEFAULT_RENDER_MODE;
}
