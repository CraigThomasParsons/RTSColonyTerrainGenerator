import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { GenerateWorldForm } from "./GenerateWorldForm.tsx";
import { IDLE_SNAPSHOT } from "~/entities/world";

/**
 * The seam under test is what a person can do with the form and what request that produces.
 * The tracker is a prop, so this slice is tested without a server, a timer, or a canvas.
 */
describe("GenerateWorldForm", () => {
  it("submits the cell dimensions in the contract's own field names", async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn();

    render(<GenerateWorldForm snapshot={IDLE_SNAPSHOT} onGenerate={onGenerate} />);

    await user.clear(screen.getByLabelText(/map width in cells/i));
    await user.type(screen.getByLabelText(/map width in cells/i), "32");
    await user.clear(screen.getByLabelText(/map height in cells/i));
    await user.type(screen.getByLabelText(/map height in cells/i), "48");
    await user.type(screen.getByLabelText(/name/i), "Default Forest");
    await user.click(screen.getByRole("button", { name: /generate/i }));

    expect(onGenerate).toHaveBeenCalledWith({
      map_width_in_cells: 32,
      map_height_in_cells: 48,
      name: "Default Forest",
    });
  });

  it("omits an empty seed so the server picks one and echoes it back", async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn();

    render(<GenerateWorldForm snapshot={IDLE_SNAPSHOT} onGenerate={onGenerate} />);
    await user.click(screen.getByRole("button", { name: /generate/i }));

    expect(onGenerate).toHaveBeenCalledWith({
      map_width_in_cells: 64,
      map_height_in_cells: 64,
    });
  });

  it("passes a seed through as typed, without rounding it into a JS number", async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn();

    render(<GenerateWorldForm snapshot={IDLE_SNAPSHOT} onGenerate={onGenerate} />);
    await user.type(screen.getByLabelText(/seed/i), "9007199254740993");
    await user.click(screen.getByRole("button", { name: /generate/i }));

    expect(onGenerate).toHaveBeenCalledWith(
      expect.objectContaining({ seed: "9007199254740993" }),
    );
  });

  it("narrates the stage and percentage while a job is running", () => {
    render(
      <GenerateWorldForm
        snapshot={{
          phase: "polling",
          jobId: "43860dcf",
          status: {
            job_id: "43860dcf",
            status: "running",
            stage: "Tiler",
            pct: 37,
            seed: "1234567890",
            map_width_in_cells: 64,
            map_height_in_cells: 64,
            submitted_at_utc: "2026-01-28T00:42:24Z",
            completed_at_utc: null,
            error: null,
          },
          preview: null,
          error: null,
        }}
        onGenerate={vi.fn()}
      />,
    );

    // The stage is an opaque display string: shown, never branched on.
    expect(screen.getByText(/Tiler/)).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "37");
    expect(screen.getByRole("button", { name: /generating/i })).toBeDisabled();
  });

  it("shows the server's failure text verbatim", () => {
    render(
      <GenerateWorldForm
        snapshot={{
          phase: "failed",
          jobId: null,
          status: null,
          preview: null,
          error: "Map width in cells must be greater than zero.",
        }}
        onGenerate={vi.fn()}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Map width in cells must be greater than zero.",
    );
  });
});
