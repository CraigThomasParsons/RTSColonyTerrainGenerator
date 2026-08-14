import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { MapPreview, PixelLabEvaluationBundle } from "~/shared/api/contract.ts";
import type { MapGenClient } from "~/shared/api/mapgenClient.ts";
import { EvaluationWorkbench } from "./EvaluationWorkbench.tsx";

const PREVIEW: MapPreview = {
  version: 2, job_id: "world-1", width: 2, height: 2,
  terrain_palette: ["water", "grass"], terrain: [0, 1, 1, 0], trees: [],
  start_zones: [{ id: "start", x: 1, y: 1 }],
  resource_clusters: [{ id: "wood", type: "wood", x: 0, y: 1, start_id: "start" }],
};

const bundle = (reviewed = false): PixelLabEvaluationBundle => ({
  version: 1, job_id: "presentation-1", world_job_id: "world-1", world_seed: "1",
  candidates: [{
    candidate_index: 0, candidate_seed: 1, state: "human-approved", structurally_valid: true,
    eligible_for_evaluation: true, evidence_digest: "a".repeat(64),
    artifact_digests: { candidate: "b".repeat(64) },
    artifact_urls: {
      semantic_control: "/semantic.png", protected_mask: "/protected.png",
      candidate: "/candidate.png", validation: "/validation.json", provenance: "/manifest.json",
    },
    provider: "development-fake",
    cost: { status: "not-observed", value: null, unit: null },
    latency: { status: "not-observed", value: null, unit: null }, validation_failures: [],
    reviews: reviewed ? [{
      reviewer: "Craig", rationale: "Compared all evidence.", verdict: "accept",
      scores: { shoreline_fidelity: 5, traversability_cues: 4, starts_and_resources: 5, visual_cohesion: 4, gameplay_readability: 5 },
      recorded_at_utc: "2026-08-14T12:00:00Z", bound_evidence_digest: "a".repeat(64), current: true,
    }] : [],
  }],
});

beforeEach(() => {
  vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} }));
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("EvaluationWorkbench", () => {
  it("compares controls, discloses missing evidence, and records a digest-bound review", async () => {
    const user = userEvent.setup();
    const getEvaluation = vi.fn().mockResolvedValueOnce(bundle()).mockResolvedValueOnce(bundle(true));
    const recordEvaluation = vi.fn().mockResolvedValue(bundle(true).candidates[0]);
    const client = {
      getPixelLabEvaluation: getEvaluation,
      recordPixelLabEvaluation: recordEvaluation,
      resolveApiUrl: (path: string) => `http://api.test${path}`,
    } as unknown as MapGenClient;
    render(<EvaluationWorkbench client={client} pixelLabJobId="presentation-1" preview={PREVIEW} />);

    expect(await screen.findByText(/cost/i)).toBeInTheDocument();
    expect(screen.getAllByText(/not observed/i)).toHaveLength(2);
    expect(screen.getByAltText("Semantic terrain control")).toHaveAttribute("src", "http://api.test/semantic.png");
    await user.click(screen.getByLabelText("Protected areas"));
    expect(screen.getByAltText("Protected terrain and road evidence")).toHaveAttribute("src", "http://api.test/protected.png");
    await user.clear(screen.getByLabelText("Evaluation reviewer"));
    await user.type(screen.getByLabelText("Evaluation reviewer"), "Craig");
    await user.type(screen.getByLabelText("Evaluation rationale"), "Compared all authoritative overlays.");
    await user.selectOptions(screen.getByLabelText("Evaluation verdict"), "accept");
    await user.click(screen.getByRole("button", { name: /record digest-bound evaluation/i }));

    await waitFor(() => expect(recordEvaluation).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/current review: accept by craig/i)).toBeInTheDocument();
    expect(screen.getByText(/changed evidence requires a fresh review/i)).toBeInTheDocument();
  });
});
