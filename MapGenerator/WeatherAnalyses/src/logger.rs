//! JSONL logging for MapGenerator pipeline compatibility.
//!
//! Writes structured logs to `logs/jobs/{job_id}/weather.log.jsonl`
//! in the same format as Tiler, so mapgenctl TUI can display them.

use serde::Serialize;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

/// A structured log entry matching the Tiler's JSONL format.
#[derive(Serialize)]
struct LogEntry<'a> {
    ts: u64,
    stage: &'a str,
    job_id: &'a str,
    level: &'a str,
    event: &'a str,
    msg: &'a str,
}

/// Stage logger that writes JSONL entries to a per-job log file.
pub struct StageLogger {
    job_id: String,
    stage: String,
    log_path: PathBuf,
}

impl StageLogger {
    /// Create a new logger for the given job ID.
    ///
    /// Log file path: {MAPGEN_LOG_ROOT}/jobs/{job_id}/weather.log.jsonl
    pub fn new(job_id: &str) -> anyhow::Result<Self> {
        let log_root = std::env::var("MAPGEN_LOG_ROOT")
            .unwrap_or_else(|_| "./logs".to_string());
        
        let job_dir = PathBuf::from(&log_root).join("jobs").join(job_id);
        fs::create_dir_all(&job_dir)?;
        
        let log_path = job_dir.join("weather.log.jsonl");
        
        Ok(Self {
            job_id: job_id.to_string(),
            stage: "weather".to_string(),
            log_path,
        })
    }

    /// Log an INFO level message.
    pub fn info(&self, event: &str, msg: &str) {
        self.write("INFO", event, msg);
    }

    /// Log a WARN level message.
    #[allow(dead_code)]
    pub fn warn(&self, event: &str, msg: &str) {
        self.write("WARN", event, msg);
    }

    /// Log an ERROR level message.
    #[allow(dead_code)]
    pub fn error(&self, event: &str, msg: &str) {
        self.write("ERROR", event, msg);
    }

    fn write(&self, level: &str, event: &str, msg: &str) {
        let ts = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_millis() as u64)
            .unwrap_or(0);

        let entry = LogEntry {
            ts,
            stage: &self.stage,
            job_id: &self.job_id,
            level,
            event,
            msg,
        };

        if let Ok(json) = serde_json::to_string(&entry) {
            if let Ok(mut file) = OpenOptions::new()
                .create(true)
                .append(true)
                .open(&self.log_path)
            {
                let _ = writeln!(file, "{}", json);
            }
        }
    }
}
