import CameraViewportController from "@capybara/core/CameraViewportController.ts";

import type { MapPreview } from "~/shared/api/contract.ts";
import { drawPreview } from "./drawPreview.ts";

/**
 * The map preview as a live surface, framed by the self-hosted `capybara_2d_engine`.
 *
 * The engine's `CameraViewportController` owns the things a hand-rolled canvas gets wrong:
 * backing-store size versus CSS size, device-pixel ratio, integer downscales, and the camera
 * transform. This module hands it a world (the preview's tile grid at
 * `PREVIEW_TILE_PIXELS` per tile) and draws through the camera it maintains.
 *
 * The engine's `GameRuntime` / `GameMap` are deliberately not used: they load capybara.build
 * sprite sheets, mask atlases and audio, and a generated terrain preview has none of those.
 * See `third_party/capybara_2d_engine/PROVENANCE.md`.
 */

/** Pixel size of one preview tile. A 128×128 preview becomes a 1024px world. */
export const PREVIEW_TILE_PIXELS = 8;

export interface PreviewSurface {
  /** Repaint the current preview — after a resize, or when the caller wants a fresh frame. */
  redraw(): void;
  /** Detach listeners. Safe to call twice; the surface never repaints afterwards. */
  destroy(): void;
}

export function createPreviewSurface(
  canvas: HTMLCanvasElement,
  preview: MapPreview,
  approvedBackground?: CanvasImageSource,
  overlays: { showStartZones: boolean; showResources: boolean } = {
    showStartZones: true,
    showResources: true,
  },
): PreviewSurface {
  const worldPixelWidth = preview.width * PREVIEW_TILE_PIXELS;
  const worldPixelHeight = preview.height * PREVIEW_TILE_PIXELS;

  const camera = new CameraViewportController(canvas, {
    // One panel is the whole map: a preview wants the entire world in frame, not a
    // player-sized window onto it.
    panelPixelWidth: worldPixelWidth,
    panelPixelHeight: worldPixelHeight,
    worldPixelWidth,
    worldPixelHeight,
    maxViewportScale: 1,
  });

  let alive = true;

  const redraw = () => {
    if (!alive) {
      return;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }

    const { devicePixelRatio: dpr } = camera.viewport;
    const { x, y, zoom } = camera.camera;

    // The engine keeps gameplay maths in logical pixels and the backing store in device
    // pixels; composing both into one transform is what keeps the two from drifting.
    ctx.setTransform(dpr * zoom, 0, 0, dpr * zoom, x * dpr, y * dpr);
    ctx.clearRect(0, 0, worldPixelWidth, worldPixelHeight);

    drawPreview(ctx, preview, { tileSize: PREVIEW_TILE_PIXELS, approvedBackground, ...overlays });
  };

  const handleResize = () => {
    if (!alive) {
      return;
    }
    camera.resize();
    redraw();
  };

  camera.resize();
  redraw();
  window.addEventListener("resize", handleResize);

  return {
    redraw,
    destroy() {
      alive = false;
      window.removeEventListener("resize", handleResize);
    },
  };
}
