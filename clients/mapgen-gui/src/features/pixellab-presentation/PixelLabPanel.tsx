import { useEffect, useMemo, useState } from "react";
import type { PixelLabCandidate, PixelLabJob, PixelLabReadiness } from "~/shared/api/contract.ts";
import type { MapGenClient } from "~/shared/api/mapgenClient.ts";
import styles from "./PixelLabPanel.module.css";

export interface PixelLabPanelProps {
  client: MapGenClient;
  worldJobId: string | null;
  worldReady: boolean;
  pollIntervalMs: number;
  onApprovedImage: (url: string | null) => void;
}

export function PixelLabPanel({ client, worldJobId, worldReady, pollIntervalMs, onApprovedImage }: PixelLabPanelProps) {
  const [readiness, setReadiness] = useState<PixelLabReadiness | null>(null);
  const [job, setJob] = useState<PixelLabJob | null>(null);
  const [count, setCount] = useState(3);
  const [actor, setActor] = useState("local-operator");
  const [reason, setReason] = useState("Selected in Map Studio after visual comparison.");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { void client.getPixelLabReadiness().then(setReadiness).catch((e: Error) => setError(e.message)); }, [client]);
  useEffect(() => {
    if (!job || (job.status !== "queued" && job.status !== "running")) return;
    const timer = window.setInterval(() => void client.getPixelLabJob(job.job_id).then(setJob).catch((e: Error) => setError(e.message)), pollIntervalMs);
    return () => window.clearInterval(timer);
  }, [client, job, pollIntervalMs]);

  const approved = useMemo(() => job?.candidates.find((candidate) => candidate.state === "human-approved"), [job]);
  useEffect(() => {
    let approvedUrl: string | null = null;
    if (approved?.image_url) approvedUrl = client.resolveApiUrl(approved.image_url);
    onApprovedImage(approvedUrl);
  }, [approved, client, onApprovedImage]);

  const start = async () => {
    if (!worldJobId) return;
    setError(null);
    try {
      setJob(await client.submitPixelLabJob({ world_job_id: worldJobId, candidate_count: count,
        candidate_budget: 0, mode: "offline", enable_live_calls: false, confirm_credit_spend: false }));
    } catch (e) { setError((e as Error).message); }
  };
  const retry = async () => { if (job) setJob(await client.retryPixelLabJob(job.job_id)); };
  const refreshBalance = async () => {
    setError(null);
    try { setReadiness(await client.refreshPixelLabBalance()); }
    catch (e) { setError((e as Error).message); }
  };
  const decide = async (candidate: PixelLabCandidate, decision: "approve" | "reject") => {
    if (!job) return;
    setError(null);
    try { setJob(await client.decidePixelLabCandidate(job.job_id, candidate.candidate_index, decision, { actor, reason })); }
    catch (e) { setError((e as Error).message); }
  };

  let balanceLabel = "balance unavailable";
  if (readiness?.balance != null) balanceLabel = `${readiness.balance} ${readiness.balance_currency ?? ""}`;

  return <section className={styles.panel} aria-labelledby="pixellab-heading">
    <div className={styles.heading}><h2 id="pixellab-heading">PixelLab presentation</h2><span>{balanceLabel}</span></div>
    <button type="button" disabled={!readiness?.live_configured} onClick={() => void refreshBalance()}>Refresh balance (read-only)</button>
    <p className={styles.note}>{readiness?.message ?? "Checking server readiness…"}</p>
    <div className={styles.controls}>
      <label>Candidates <input aria-label="Candidate count" type="number" min="1" max="4" value={count} onChange={(event) => setCount(Number(event.target.value))} /></label>
      <button type="button" disabled={!worldReady || !readiness?.available || job?.status === "running" || job?.status === "queued"} onClick={() => void start()}>Generate candidates offline</button>
    </div>
    {job && <div className={styles.progress} aria-live="polite"><progress value={job.pct} max="100" /><span>{job.stage} · {job.pct}% · {job.cache_hits} cache hit(s) · {job.submissions} paid submission(s)</span></div>}
    {job?.status === "failed" && <div role="alert" className={styles.error}>{job.error}<button type="button" onClick={() => void retry()}>Retry</button></div>}
    {error && <p role="alert" className={styles.error}>{error}</p>}
    {job !== null && job.candidates.length > 0 && <>
      <div className={styles.decisionFields}><input aria-label="Operator name" value={actor} onChange={(event) => setActor(event.target.value)} /><input aria-label="Decision reason" value={reason} onChange={(event) => setReason(event.target.value)} /></div>
      <div className={styles.gallery}>{job.candidates.map((candidate) => <article key={candidate.candidate_index} className={styles.card}>
        {candidate.image_url && <img src={client.resolveApiUrl(candidate.image_url)} alt={`PixelLab candidate ${candidate.candidate_index + 1}`} />}
        {!candidate.image_url && <div className={styles.placeholder}>No image in offline dry-run</div>}
        <strong>Candidate {candidate.candidate_index + 1}</strong><span>{candidate.state}{candidate.cache_hit && " · cache hit"}</span>
        {candidate.failures.length > 0 && <small>{candidate.failures.join(" ")}</small>}
        <div><button type="button" disabled={!candidate.eligible_for_approval || candidate.state === "human-approved"} onClick={() => void decide(candidate, "approve")}>Approve</button><button type="button" disabled={candidate.state === "rejected"} onClick={() => void decide(candidate, "reject")}>Reject</button></div>
      </article>)}</div>
    </>}
  </section>;
}
