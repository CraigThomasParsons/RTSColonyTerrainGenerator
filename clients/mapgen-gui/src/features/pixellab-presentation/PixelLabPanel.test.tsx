import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PixelLabJob } from "~/shared/api/contract.ts";
import type { MapGenClient } from "~/shared/api/mapgenClient.ts";
import { PixelLabPanel } from "./PixelLabPanel.tsx";

const job = (state: "generated" | "human-approved" = "generated"): PixelLabJob => ({
  job_id: "presentation-1", world_job_id: "world-1", status: "succeeded", stage: "awaiting-approval", pct: 100,
  mode: "offline", candidate_budget: 0, submissions: 0, cache_hits: 1,
  submitted_at_utc: "2026-08-09T12:00:00Z", completed_at_utc: "2026-08-09T12:00:01Z", error: null,
  candidates: [{ candidate_index: 0, seed: 1, state, structurally_valid: true,
    eligible_for_approval: true, cache_hit: true, failures: [], image_url: "/pixellab/jobs/presentation-1/candidates/0/image" }],
});

describe("PixelLabPanel", () => {
  it("generates through the fake client, reports cache/balance state, and activates only after approval", async () => {
    const user = userEvent.setup();
    const onApprovedImage = vi.fn();
    const client = {
      getPixelLabReadiness: vi.fn().mockResolvedValue({ available: true, live_configured: false, mode: "offline", balance: null, balance_currency: null, message: "Fake transport ready." }),
      refreshPixelLabBalance: vi.fn(),
      submitPixelLabJob: vi.fn().mockResolvedValue(job()),
      decidePixelLabCandidate: vi.fn().mockResolvedValue(job("human-approved")),
      getPixelLabJob: vi.fn(), retryPixelLabJob: vi.fn(),
      resolveApiUrl: (path: string) => `http://api.test${path}`,
    } as unknown as MapGenClient;
    render(<PixelLabPanel client={client} worldJobId="world-1" worldReady pollIntervalMs={10} onApprovedImage={onApprovedImage} />);
    expect(await screen.findByText(/fake transport ready/i)).toBeInTheDocument();
    expect(screen.getByText(/balance unavailable/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /generate candidates offline/i }));
    expect(await screen.findByAltText(/candidate 1/i)).toBeInTheDocument();
    expect(screen.getAllByText(/cache hit/i)).toHaveLength(2);
    expect(onApprovedImage).toHaveBeenLastCalledWith(null);
    await user.click(screen.getByRole("button", { name: /^approve$/i }));
    await waitFor(() => expect(onApprovedImage).toHaveBeenLastCalledWith(
      "http://api.test/pixellab/jobs/presentation-1/candidates/0/image"));
  });
});
