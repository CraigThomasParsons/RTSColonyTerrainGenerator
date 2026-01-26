use std::fs;
use std::path::PathBuf;
use std::process::{Command, ExitCode};

use wcar::WcarError;

//
// Entry point for the Stratagus headless runner.
//
// This program:
// - Validates input map path
// - Launches Stratagus with the harness script
// - Parses stdout markers for PASS/FAIL
// - Exits with deterministic status
//
fn main() -> ExitCode {
    match run() {
        Ok(_) => ExitCode::SUCCESS,
        Err(err) => {
            eprintln!("HARNESS:FAIL:UNKNOWN:{}", err);
            ExitCode::from(1)
        }
    }
}

fn run() -> Result<(), WcarError> {
    let args = parse_args();
    if !args.map_path.exists() {
        return Err(WcarError::InvalidFormat("Map file not found".to_string()));
    }

    fs::create_dir_all(&args.out_dir).map_err(WcarError::Io)?;

    let stratagus_bin = args
        .stratagus_bin
        .clone()
        .unwrap_or_else(|| PathBuf::from("stratagus"));

    let harness_script = args
        .harness_script
        .clone()
        .unwrap_or_else(|| PathBuf::from("harness.lua"));

    let mut command = Command::new(stratagus_bin);
    command
        .arg("--headless")
        .arg("--lua")
        .arg(harness_script)
        .env("MAP_PATH", &args.map_path)
        .env("HARNESS_TICKS", args.ticks.to_string())
        .env("HARNESS_SEED", args.seed.to_string())
        .env("HARNESS_OUT_DIR", &args.out_dir);

    let output = command.output().map_err(WcarError::Io)?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    fs::write(args.out_dir.join("stratagus_stdout.log"), &stdout).map_err(WcarError::Io)?;
    fs::write(args.out_dir.join("stratagus_stderr.log"), &stderr).map_err(WcarError::Io)?;

    if stdout.contains("HARNESS:PASS") {
        return Ok(());
    }

    if let Some(line) = stdout.lines().find(|line| line.contains("HARNESS:FAIL")) {
        return Err(WcarError::InvalidFormat(line.to_string()));
    }

    Err(WcarError::InvalidFormat("Harness did not report PASS".to_string()))
}

//
// CLI arguments.
//
struct Args {
    map_path: PathBuf,
    ticks: u32,
    seed: u64,
    out_dir: PathBuf,
    stratagus_bin: Option<PathBuf>,
    harness_script: Option<PathBuf>,
}

fn parse_args() -> Args {
    let mut map_path = None;
    let mut ticks = None;
    let mut seed = None;
    let mut out_dir = None;
    let mut stratagus_bin = None;
    let mut harness_script = None;

    let mut iter = std::env::args().skip(1);
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--map" => map_path = iter.next().map(PathBuf::from),
            "--ticks" => ticks = iter.next().and_then(|v| v.parse().ok()),
            "--seed" => seed = iter.next().and_then(|v| v.parse().ok()),
            "--out-dir" => out_dir = iter.next().map(PathBuf::from),
            "--stratagus-bin" => stratagus_bin = iter.next().map(PathBuf::from),
            "--harness-script" => harness_script = iter.next().map(PathBuf::from),
            _ => {}
        }
    }

    Args {
        map_path: map_path.expect("--map is required"),
        ticks: ticks.unwrap_or(5000),
        seed: seed.unwrap_or(0),
        out_dir: out_dir.unwrap_or_else(|| PathBuf::from(".")),
        stratagus_bin,
        harness_script,
    }
}
