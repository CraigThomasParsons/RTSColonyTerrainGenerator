use anyhow::{Context, Result};
use serde::Serialize;
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

/// LogEvent matches the Dafny contract shape.
///
/// PURPOSE:
/// - Emit language-agnostic structured logs (JSONL)
/// - Keep fields stable across stages and languages
///
/// DESIGN NOTE:
/// We intentionally keep kv as string->string for portability.
/// This avoids cross-language "number vs string" mismatches and parsing ambiguity.
#[derive(Debug, Serialize)]
pub struct LogEvent {
    pub ts: i64,
    pub stage: String,
    pub job_id: String,
    pub level: String,
    pub event: String,
    pub msg: String,
    pub kv: HashMap<String, String>,
}

/// Minimal stage logger for filesystem-driven pipelines.
///
/// PURPOSE:
/// - Resolve log path from MAPGEN_LOG_ROOT
/// - Append one JSON object per line (JSONL)
///
/// NON-GOALS:
/// - log rotation
/// - buffering/async complexity
/// - centralized aggregation
pub struct StageLogger {
    stage: String,
    job_id: String,
    log_path: PathBuf,
}

impl StageLogger {
    pub fn new(job_id: impl Into<String>, stage: impl Into<String>) -> Result<Self> {
        let job_id = job_id.into();
        let stage = stage.into();

        // Guard clause: without a job id we cannot derive a stable log location.
        if job_id.trim().is_empty() {
            anyhow::bail!("job_id must be non-empty");
        }

        // Guard clause: stage must be stable and non-empty for predictable filenames.
        if stage.trim().is_empty() {
            anyhow::bail!("stage must be non-empty");
        }

        let log_path = resolve_log_path(&job_id, &stage)?;
        Ok(Self { stage, job_id, log_path })
    }

    pub fn log_path(&self) -> &Path {
        &self.log_path
    }

    pub fn info(&self, event: &str, msg: &str, kv: HashMap<String, String>) -> Result<()> {
        self.write("Info", event, msg, kv)
    }

    pub fn warn(&self, event: &str, msg: &str, kv: HashMap<String, String>) -> Result<()> {
        self.write("Warn", event, msg, kv)
    }

    pub fn error(&self, event: &str, msg: &str, kv: HashMap<String, String>) -> Result<()> {
        self.write("Error", event, msg, kv)
    }

    fn write(&self, level: &str, event: &str, msg: &str, kv: HashMap<String, String>) -> Result<()> {
        // Guard clause: stable event names are critical for tooling.
        if event.trim().is_empty() {
            anyhow::bail!("event must be non-empty");
        }

        // Guard clause: message must be meaningful for humans reading tail output.
        if msg.trim().is_empty() {
            anyhow::bail!("msg must be non-empty");
        }

        let ts = chrono_utc_millis();

        let record = LogEvent {
            ts,
            stage: self.stage.clone(),
            job_id: self.job_id.clone(),
            level: level.to_string(),
            event: event.to_string(),
            msg: msg.to_string(),
            kv,
        };

        append_json_line(&self.log_path, &record)
    }
}

fn resolve_log_path(job_id: &str, stage: &str) -> Result<PathBuf> {
    // Design choice: stage code does NOT parse .env.
    // It consumes inherited environment variables.
    let log_root = env::var("MAPGEN_LOG_ROOT").unwrap_or_else(|_| "./logs".to_string());

    let mut dir = PathBuf::from(log_root);
    dir.push("jobs");
    dir.push(job_id);

    fs::create_dir_all(&dir).with_context(|| format!("create log dir {:?}", dir))?;

    let mut file = dir;
    file.push(format!("{stage}.log.jsonl"));
    Ok(file)
}

fn append_json_line(path: &Path, value: &impl Serialize) -> Result<()> {
    let line = serde_json::to_string(value).context("serialize log event as json")?;

    // Design choice: append-only file writes are crash-tolerant and tail-friendly.
    use std::io::Write;
    let mut f = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .with_context(|| format!("open log file {:?}", path))?;

    writeln!(f, "{line}").context("append jsonl line")?;
    Ok(())
}

fn chrono_utc_millis() -> i64 {
    // Avoid pulling in a heavier time crate if you already have one.
    // If your project already uses chrono, swap this to chrono::Utc::now().
    use std::time::{SystemTime, UNIX_EPOCH};
    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default();
    (now.as_millis() as i64).max(0)
}
