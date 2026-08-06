import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { MapPreview } from "~/shared/api/contract.ts";
import { createPreviewSurface, PREVIEW_TILE_PIXELS } from "./previewSurface.ts";

/**
 * The seam under test is the surface's public API — create, redraw, destroy — and what it
 * asks of the canvas. The camera and viewport come from the self-hosted
 * `capybara_2d_engine` (`CameraViewportController`), so these assertions are really about
 * whether this client hands the engine a world it can frame: backing store sized from the
 * world extent and the device pixel ratio, drawing done through the camera transform.
 *
 * jsdom ships no canvas backend, so `getContext` is stubbed with a recorder. That is the
 * point of the test — the pixels are the browser's business; the wiring is ours.
 */
const PREVIEW: MapPreview = {
  version: 1,
  job_id: "43860dcf-6469-42a7-9843-4e33abeacfac",
  width: 4,
  height: 4,
  terrain_palette: ["deep_water", "water", "dirt", "grass"],
  terrain: [
    0, 1, 1, 0, //
    1, 2, 2, 1, //
    1, 2, 3, 1, //
    0, 1, 1, 0,
  ],
  start_zones: [{ id: "start_1", x: 2, y: 2 }],
  resource_clusters: [],
};

interface Recorder {
  fillRects: Array<{ x: number; y: number; w: number; h: number }>;
  transforms: number[][];
  clears: number;
}

const canvasWithRecorder = (): { canvas: HTMLCanvasElement; recorder: Recorder } => {
  const recorder: Recorder = { fillRects: [], transforms: [], clears: 0 };
  const canvas = document.createElement("canvas");

  const ctx = {
    fillStyle: "",
    strokeStyle: "",
    lineWidth: 1,
    setTransform: (...args: number[]) => recorder.transforms.push(args),
    clearRect: () => {
      recorder.clears += 1;
    },
    fillRect: (x: number, y: number, w: number, h: number) =>
      recorder.fillRects.push({ x, y, w, h }),
    beginPath: () => {},
    arc: () => {},
    fill: () => {},
    stroke: () => {},
    save: () => {},
    restore: () => {},
    translate: () => {},
    scale: () => {},
  };

  vi.spyOn(canvas, "getContext").mockReturnValue(ctx as unknown as CanvasRenderingContext2D);
  document.body.append(canvas);
  return { canvas, recorder };
};

beforeEach(() => {
  // `CameraViewportController.resize()` asks the engine's touch-device question.
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  vi.stubGlobal("devicePixelRatio", 1);
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.replaceChildren();
});

describe("createPreviewSurface", () => {
  it("sizes the canvas backing store from the world extent and paints the terrain", () => {
    const { canvas, recorder } = canvasWithRecorder();

    const surface = createPreviewSurface(canvas, PREVIEW);

    const worldPixels = PREVIEW.width * PREVIEW_TILE_PIXELS;
    expect(canvas.width).toBe(worldPixels);
    expect(canvas.height).toBe(worldPixels);

    const tiles = recorder.fillRects.filter((rect) => rect.w === PREVIEW_TILE_PIXELS);
    expect(tiles).toHaveLength(PREVIEW.width * PREVIEW.height);

    surface.destroy();
  });

  it("draws through the camera transform rather than straight onto the canvas", () => {
    // The camera is the engine's; the preview must go through it, or panning and
    // device-pixel scaling would be this widget reimplementing what is already vendored.
    const { canvas, recorder } = canvasWithRecorder();

    const surface = createPreviewSurface(canvas, PREVIEW);

    expect(recorder.transforms.length).toBeGreaterThan(0);
    expect(recorder.clears).toBeGreaterThan(0);

    surface.destroy();
  });

  it("repaints when asked to redraw, and stops repainting once destroyed", () => {
    const { canvas, recorder } = canvasWithRecorder();

    const surface = createPreviewSurface(canvas, PREVIEW);
    const afterMount = recorder.clears;

    surface.redraw();
    expect(recorder.clears).toBe(afterMount + 1);

    surface.destroy();
    window.dispatchEvent(new Event("resize"));
    expect(recorder.clears).toBe(afterMount + 1);
  });

  it("repaints on a window resize while alive, because the engine reframes the viewport", () => {
    const { canvas, recorder } = canvasWithRecorder();

    const surface = createPreviewSurface(canvas, PREVIEW);
    const afterMount = recorder.clears;

    window.dispatchEvent(new Event("resize"));
    expect(recorder.clears).toBeGreaterThan(afterMount);

    surface.destroy();
  });
});
