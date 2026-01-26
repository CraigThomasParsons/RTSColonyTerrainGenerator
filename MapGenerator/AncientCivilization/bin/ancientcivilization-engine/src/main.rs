use rand::{Rng, SeedableRng};
use rand_chacha::ChaCha8Rng;
use serde_json::json;
use std::env;
use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

fn iso_timestamp() -> String {
    // Simple ISO8601-like timestamp (UTC) without timezone handling
    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap();
    format!("{}", now.as_secs())
}

fn parse_args() -> (PathBuf, PathBuf, PathBuf) {
    let mut input = None;
    let mut output = None;
    let mut log_dir = None;

    let args: Vec<String> = env::args().collect();
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--input" => {
                if i + 1 < args.len() { input = Some(PathBuf::from(&args[i + 1])); i += 2; } else { break; }
            }
            "--output" => {
                if i + 1 < args.len() { output = Some(PathBuf::from(&args[i + 1])); i += 2; } else { break; }
            }
            "--log-dir" => {
                if i + 1 < args.len() { log_dir = Some(PathBuf::from(&args[i + 1])); i += 2; } else { break; }
            }
            _ => { i += 1; }
        }
    }

    match (input, output, log_dir) {
        (Some(i), Some(o), Some(l)) => (i, o, l),
        _ => {
            eprintln!("Usage: ancientcivilization-engine --input <dir> --output <dir> --log-dir <dir>");
            std::process::exit(1);
        }
    }
}

fn find_one_payload(input_dir: &Path) -> Option<PathBuf> {
    if !input_dir.is_dir() { return None; }
    let mut entries: Vec<PathBuf> = fs::read_dir(input_dir)
        .ok()?
        .filter_map(|e| e.ok().map(|de| de.path()))
        .filter(|p| p.extension().map(|ext| ext == "worldpayload").unwrap_or(false))
        .collect();
    entries.sort();
    entries.into_iter().next()
}

fn job_id_from_filename(path: &Path) -> Option<String> {
    path.file_name()
        .and_then(|os| os.to_str())
        .and_then(|name| name.split('.').next().map(|s| s.to_string()))
}

fn write_json_file(path: &Path, value: serde_json::Value) -> std::io::Result<()> {
    let mut f = File::create(path)?;
    let s = serde_json::to_string_pretty(&value).unwrap();
    f.write_all(s.as_bytes())
}

fn log_line(log_dir: &Path, job_id: &str, message: &str) -> std::io::Result<()> {
    let job_log_dir = log_dir.join(job_id);
    fs::create_dir_all(&job_log_dir)?;
    let log_path = job_log_dir.join("ancientcivilization.log.jsonl");
    let mut f = fs::OpenOptions::new().create(true).append(true).open(&log_path)?;
    let line = json!({
        "ts": iso_timestamp(),
        "stage": "AncientCivilization",
        "job_id": job_id,
        "message": message
    });
    writeln!(f, "{}", line.to_string())
}

fn main() {
    let (input_dir, output_dir, log_dir) = parse_args();

    // Find one payload to process
    let payload = match find_one_payload(&input_dir) {
        Some(p) => p,
        None => {
            eprintln!("No .worldpayload found in {:?}", input_dir);
            return;
        }
    };

    let job_id = match job_id_from_filename(&payload) {
        Some(id) => id,
        None => {
            eprintln!("Failed to extract job_id from {:?}", payload);
            return;
        }
    };

    fs::create_dir_all(&output_dir).ok();
    fs::create_dir_all(&log_dir).ok();

    // Deterministic RNG seeded by job_id hash
    let seed: u64 = {
        let mut h: u64 = 1469598103934665603; // FNV offset basis
        for b in job_id.as_bytes() {
            h ^= *b as u64;
            h = h.wrapping_mul(1099511628211);
        }
        h
    };
    let mut rng = ChaCha8Rng::seed_from_u64(seed);

    // Generate minimal deterministic artifacts
    let settlements = json!([
        {
            "id": "settlement-1",
            "name": "Ancient Hamlet",
            "pos": {"x": rng.gen_range(5..95), "y": rng.gen_range(5..95)},
            "population": 64,
            "era": "bronze"
        }
    ]);

    let ruins = json!([
        {
            "id": "ruin-1",
            "type": "collapsed_temple",
            "pos": {"x": rng.gen_range(0..100), "y": rng.gen_range(0..100)},
            "integrity": 0.42
        }
    ]);

    let ancient_paths = json!([
        {
            "id": "path-1",
            "from": {"x": 10, "y": 10},
            "to": {"x": 90, "y": 90},
            "movement_bonus": 0.1
        }
    ]);

    let reclaimed_resources = json!([
        {
            "id": "cache-1",
            "pos": {"x": rng.gen_range(0..100), "y": rng.gen_range(0..100)},
            "items": [{"name": "grain", "qty": 100}]
        }
    ]);

    let collapse_reason = "none";

    // Write files
    let settlements_path = output_dir.join(format!("{}.settlements.json", job_id));
    let ruins_path = output_dir.join(format!("{}.ruins.json", job_id));
    let paths_path = output_dir.join(format!("{}.ancient_paths.json", job_id));
    let resources_path = output_dir.join(format!("{}.reclaimed_resources.json", job_id));
    let collapse_path = output_dir.join(format!("{}.collapse_reason.txt", job_id));

    write_json_file(&settlements_path, settlements).expect("write settlements");
    write_json_file(&ruins_path, ruins).expect("write ruins");
    write_json_file(&paths_path, ancient_paths).expect("write paths");
    write_json_file(&resources_path, reclaimed_resources).expect("write resources");

    let mut f = File::create(&collapse_path).expect("write collapse reason");
    writeln!(f, "{}", collapse_reason).ok();

    // Log lines
    let _ = log_line(&log_dir, &job_id, "AncientCivilization starting");
    let _ = log_line(&log_dir, &job_id, &format!(
        "Artifacts written: {}, {}, {}, {}, {}",
        settlements_path.display(),
        ruins_path.display(),
        paths_path.display(),
        resources_path.display(),
        collapse_path.display()
    ));
    let _ = log_line(&log_dir, &job_id, "AncientCivilization complete");
}
