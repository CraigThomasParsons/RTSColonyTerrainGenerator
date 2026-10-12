import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { MapPreview } from "~/shared/api/contract.ts";
import {
  FOREST_SOURCE_TILE_SIZE,
  FOREST_TERRAIN_TILES,
  FOREST_TREE_AUTOTILE,
  type Tileset,
} from "../lib/forestTileset.ts";
import { RENDER_MODE_STORAGE_KEY } from "../model/renderMode.ts";
import { MapPreviewPanel } from "./MapPreviewPanel.tsx";

const PREVIEW: MapPreview = {
  version: 2,
  job_id: "43860dcf-6469-42a7-9843-4e33abeacfac",
  width: 2,
  height: 2,
  terrain_palette: ["water", "grass"],
  terrain: [0, 1, 1, 0],
  trees: [],
  start_zones: [],
  resource_clusters: [],
};

const NEXT_PREVIEW: MapPreview = { ...PREVIEW, job_id: "a6d1d3f5-0d3f-4f7e-b0a5-6bd8b0c7c0aa" };

const STUB_TILESET: Tileset = {
  image: {} as CanvasImageSource,
  sourceTileSize: FOREST_SOURCE_TILE_SIZE,
  tree: FOREST_TREE_AUTOTILE,
  terrain: FOREST_TERRAIN_TILES,
};

/** Counts what the most recent frames painted: sheet blits versus flat fills. */
const paintRecorder = () => {
  const painted = { blits: 0, fills: 0 };
  const ctx = {
    fillStyle: "",
    strokeStyle: "",
    lineWidth: 1,
    imageSmoothingEnabled: true,
    setTransform: () => {},
    clearRect: () => {
      painted.blits = 0;
      painted.fills = 0;
    },
    drawImage: (...args: unknown[]) => {
      if (args.length === 9) painted.blits += 1;
    },
    fillRect: () => {
      painted.fills += 1;
    },
    beginPath: () => {},
    arc: () => {},
    fill: () => {},
    stroke: () => {},
  };
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
    ctx as unknown as CanvasRenderingContext2D,
  );
  return painted;
};

const toggle = () => screen.getByRole("button", { name: /game tiles/i });

beforeEach(() => {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

describe("MapPreviewPanel", () => {
  it("says what it is waiting for when no map has been generated yet", () => {
    render(<MapPreviewPanel preview={null} loadTileset={() => Promise.resolve(STUB_TILESET)} />);

    expect(screen.getByText(/no map yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("renders the preview as a labelled canvas once a map arrives", () => {
    // jsdom has no canvas backend; the surface must survive that rather than throw.
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);

    render(<MapPreviewPanel preview={PREVIEW} loadTileset={() => Promise.resolve(STUB_TILESET)} />);

    // The grid size is read off the preview, never inferred from the request: 64x64 cells
    // do not imply a 64x64 document (ADR 0004's resolution mapping is still open).
    const canvas = screen.getByRole("img", { name: /2 x 2/i });
    expect(canvas.tagName).toBe("CANVAS");
  });
});

describe("MapPreviewPanel render mode", () => {
  it("draws game tiles by default, from the injected loader", async () => {
    const painted = paintRecorder();
    const loadTileset = vi.fn(() => Promise.resolve(STUB_TILESET));

    render(<MapPreviewPanel preview={PREVIEW} loadTileset={loadTileset} />);

    expect(toggle()).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(painted.blits).toBe(4));
    expect(painted.fills).toBe(0);
    expect(loadTileset).toHaveBeenCalledTimes(1);
  });

  it("switches to flat colour and back", async () => {
    const painted = paintRecorder();
    const user = userEvent.setup();

    render(<MapPreviewPanel preview={PREVIEW} loadTileset={() => Promise.resolve(STUB_TILESET)} />);
    await waitFor(() => expect(painted.blits).toBe(4));

    await user.click(toggle());
    expect(toggle()).toHaveAttribute("aria-pressed", "false");
    expect(painted.blits).toBe(0);
    expect(painted.fills).toBe(4);

    await user.click(toggle());
    expect(toggle()).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(painted.blits).toBe(4));
  });

  it("keeps the chosen mode across new generations and remounts within the session", async () => {
    const painted = paintRecorder();
    const user = userEvent.setup();
    const loadTileset = () => Promise.resolve(STUB_TILESET);

    const { rerender, unmount } = render(<MapPreviewPanel preview={PREVIEW} loadTileset={loadTileset} />);
    await user.click(toggle());

    // A new generation arrives: same panel, new preview.
    rerender(<MapPreviewPanel preview={NEXT_PREVIEW} loadTileset={loadTileset} />);
    expect(toggle()).toHaveAttribute("aria-pressed", "false");
    expect(painted.fills).toBe(4);

    // The page is torn down and rebuilt within the same session.
    unmount();
    render(<MapPreviewPanel preview={PREVIEW} loadTileset={loadTileset} />);
    expect(toggle()).toHaveAttribute("aria-pressed", "false");
    expect(window.sessionStorage.getItem(RENDER_MODE_STORAGE_KEY)).toBe("flat");
  });

  it("does not load the tileset at all while flat colour is chosen", () => {
    paintRecorder();
    window.sessionStorage.setItem(RENDER_MODE_STORAGE_KEY, "flat");
    const loadTileset = vi.fn(() => Promise.resolve(STUB_TILESET));

    render(<MapPreviewPanel preview={PREVIEW} loadTileset={loadTileset} />);

    expect(loadTileset).not.toHaveBeenCalled();
  });

  it("falls back to flat colour, and says so, when the tileset fails to load", async () => {
    const painted = paintRecorder();

    render(
      <MapPreviewPanel
        preview={PREVIEW}
        loadTileset={() => Promise.reject(new Error("404"))}
      />,
    );

    expect(await screen.findByRole("status")).toHaveTextContent(/flat colour/i);
    expect(painted.blits).toBe(0);
    expect(painted.fills).toBe(4);
  });

  it("drops a load that finishes after the user switched to flat colour", async () => {
    const painted = paintRecorder();
    const user = userEvent.setup();
    let finish: (tileset: Tileset) => void = () => {};
    const pending = new Promise<Tileset>((resolve) => {
      finish = resolve;
    });

    render(<MapPreviewPanel preview={PREVIEW} loadTileset={() => pending} />);
    await user.click(toggle());
    await act(async () => {
      finish(STUB_TILESET);
      await pending;
    });

    expect(painted.blits).toBe(0);
    expect(painted.fills).toBe(4);
  });
});
