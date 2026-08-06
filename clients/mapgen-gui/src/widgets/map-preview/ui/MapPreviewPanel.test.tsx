import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import type { MapPreview } from "~/shared/api/contract.ts";
import { MapPreviewPanel } from "./MapPreviewPanel.tsx";

const PREVIEW: MapPreview = {
  version: 1,
  job_id: "43860dcf-6469-42a7-9843-4e33abeacfac",
  width: 2,
  height: 2,
  terrain_palette: ["water", "grass"],
  terrain: [0, 1, 1, 0],
  start_zones: [],
  resource_clusters: [],
};

beforeEach(() => {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  // jsdom has no canvas backend; the surface must survive that rather than throw.
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("MapPreviewPanel", () => {
  it("says what it is waiting for when no map has been generated yet", () => {
    render(<MapPreviewPanel preview={null} />);

    expect(screen.getByText(/no map yet/i)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("renders the preview as a labelled canvas once a map arrives", () => {
    render(<MapPreviewPanel preview={PREVIEW} />);

    // The grid size is read off the preview, never inferred from the request: 64x64 cells
    // do not imply a 64x64 document (ADR 0004's resolution mapping is still open).
    const canvas = screen.getByRole("img", { name: /2 x 2/i });
    expect(canvas.tagName).toBe("CANVAS");
  });
});
