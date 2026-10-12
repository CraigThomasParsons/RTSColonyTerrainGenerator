import { useEffect, useMemo, useState } from "react";
import type { MapPreview, PixelLabEvaluationBundle, PixelLabEvaluationScores } from "~/shared/api/contract.ts";
import type { MapGenClient } from "~/shared/api/mapgenClient.ts";
import { MapPreviewPanel } from "~/widgets/map-preview";
import styles from "./EvaluationWorkbench.module.css";

export interface EvaluationWorkbenchProps {
  client: MapGenClient;
  pixelLabJobId: string;
  preview: MapPreview;
}

const DEFAULT_SCORES: PixelLabEvaluationScores = {
  shoreline_fidelity: 3,
  traversability_cues: 3,
  starts_and_resources: 3,
  visual_cohesion: 3,
  gameplay_readability: 3,
};

const SCORE_FIELDS: ReadonlyArray<[keyof PixelLabEvaluationScores, string]> = [
  ["shoreline_fidelity", "Shoreline fidelity"],
  ["traversability_cues", "Roads / traversability"],
  ["starts_and_resources", "Starts and resources"],
  ["visual_cohesion", "Visual cohesion"],
  ["gameplay_readability", "Gameplay readability"],
];

export function EvaluationWorkbench({ client, pixelLabJobId, preview }: EvaluationWorkbenchProps) {
  const [bundle, setBundle] = useState<PixelLabEvaluationBundle | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [showProtected, setShowProtected] = useState(false);
  const [showRoadEvidence, setShowRoadEvidence] = useState(false);
  const [showStarts, setShowStarts] = useState(true);
  const [showResources, setShowResources] = useState(true);
  const [reviewer, setReviewer] = useState("local-operator");
  const [rationale, setRationale] = useState("");
  const [verdict, setVerdict] = useState<"accept" | "reject">("reject");
  const [scores, setScores] = useState(DEFAULT_SCORES);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => setBundle(await client.getPixelLabEvaluation(pixelLabJobId));
  useEffect(() => { void load().catch((error: Error) => setMessage(error.message)); }, [pixelLabJobId]);
  const candidate = useMemo(() => bundle?.candidates.find((item) => item.candidate_index === selectedIndex)
    ?? bundle?.candidates[0] ?? null, [bundle, selectedIndex]);
  const url = (key: string) => candidate?.artifact_urls[key]
    ? client.resolveApiUrl(candidate.artifact_urls[key]) : null;

  const submit = async () => {
    if (!candidate) return;
    setMessage(null);
    try {
      await client.recordPixelLabEvaluation(pixelLabJobId, candidate.candidate_index,
        { reviewer, rationale, verdict, scores });
      await load();
      setMessage("Digest-bound evaluation recorded.");
    } catch (error) { setMessage((error as Error).message); }
  };

  if (!bundle || !candidate) return <section className={styles.workbench}>Loading evaluation evidence…</section>;
  const cost = candidate.cost.status === "observed" ? `${candidate.cost.value} ${candidate.cost.unit}` : "not observed";
  const latency = candidate.latency.status === "observed" ? `${candidate.latency.value} ${candidate.latency.unit}` : "not observed";
  const currentReview = candidate.reviews.find((review) => review.current);

  return <section className={styles.workbench} aria-labelledby="evaluation-heading">
    <header><div><h2 id="evaluation-heading">AI detailing evaluation</h2><p>Presentation evidence only. Gameplay terrain remains authoritative.</p></div>
      <label>Candidate <select aria-label="Evaluation candidate" value={candidate.candidate_index} onChange={(event) => setSelectedIndex(Number(event.target.value))}>
        {bundle.candidates.map((item) => <option key={item.candidate_index} value={item.candidate_index}>{item.candidate_index + 1}</option>)}</select></label></header>
    <div className={styles.toggles}>
      <label><input type="checkbox" checked={showProtected} onChange={(event) => setShowProtected(event.target.checked)} /> Protected areas</label>
      <label><input type="checkbox" checked={showRoadEvidence} onChange={(event) => setShowRoadEvidence(event.target.checked)} /> Road evidence</label>
      <label><input type="checkbox" checked={showStarts} onChange={(event) => setShowStarts(event.target.checked)} /> Start zones</label>
      <label><input type="checkbox" checked={showResources} onChange={(event) => setShowResources(event.target.checked)} /> Resources</label>
    </div>
    <div className={styles.comparison}>
      <figure><MapPreviewPanel preview={preview} showStartZones={showStarts} showResources={showResources} /><figcaption>Deterministic Terrain preview</figcaption></figure>
      <figure className={styles.control}><img src={showProtected || showRoadEvidence ? url("protected_mask") ?? "" : url("semantic_control") ?? ""} alt={showProtected || showRoadEvidence ? "Protected terrain and road evidence" : "Semantic terrain control"} /><figcaption>{showProtected || showRoadEvidence ? "Protected mask (includes road constraints)" : "Semantic control"}</figcaption></figure>
      <figure><MapPreviewPanel preview={preview} approvedBackgroundUrl={url("candidate")} showStartZones={showStarts} showResources={showResources} /><figcaption>Candidate with authoritative overlays</figcaption></figure>
    </div>
    <div className={styles.evidence}><span>provider <strong>{candidate.provider}</strong></span><span>cost <strong>{cost}</strong></span><span>latency <strong>{latency}</strong></span><span>digest <code>{candidate.evidence_digest.slice(0, 12)}</code></span></div>
    {!candidate.eligible_for_evaluation && <p role="alert">This candidate lacks complete, structurally valid evidence and cannot be evaluated.</p>}
    {candidate.validation_failures.length > 0 && <p role="alert">{candidate.validation_failures.join(" ")}</p>}
    <div className={styles.form}>{SCORE_FIELDS.map(([field, label]) => <label key={field}>{label}<input aria-label={label} type="number" min="1" max="5" value={scores[field]} onChange={(event) => setScores({ ...scores, [field]: Number(event.target.value) })} /></label>)}
      <label>Reviewer<input aria-label="Evaluation reviewer" value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></label>
      <label>Verdict<select aria-label="Evaluation verdict" value={verdict} onChange={(event) => setVerdict(event.target.value as "accept" | "reject")}><option value="reject">Reject</option><option value="accept">Accept</option></select></label>
      <label className={styles.rationale}>Rationale<textarea aria-label="Evaluation rationale" value={rationale} onChange={(event) => setRationale(event.target.value)} /></label>
      <button type="button" disabled={!candidate.eligible_for_evaluation || !reviewer.trim() || !rationale.trim()} onClick={() => void submit()}>Record digest-bound evaluation</button>
    </div>
    {currentReview && <p className={styles.current}>Current review: {currentReview.verdict} by {currentReview.reviewer}. Changed evidence requires a fresh review.</p>}
    {message && <p role="status">{message}</p>}
  </section>;
}
