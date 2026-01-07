use clap::Parser;
use std::path::PathBuf;
use std::process;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(long)]
    input: PathBuf,

    #[arg(long)]
    output: PathBuf,
}

mod heightmap;
mod weather_map;
mod analysis;
mod logger;

use logger::StageLogger;

fn main() {
    let args = Args::parse();

    // Extract job_id from input filename (e.g., "abc123.heightmap" -> "abc123")
    let job_id = args.input
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("unknown");

    // Initialize logger for this job
    let log = match StageLogger::new(job_id) {
        Ok(l) => l,
        Err(e) => {
            eprintln!("Failed to initialize logger: {}", e);
            process::exit(1);
        }
    };

    log.info("stage_start", &format!("Starting weather analysis for job {}", job_id));

    if let Err(e) = run(&args, &log) {
        log.error("stage_failed", &format!("Error: {}", e));
        eprintln!("Error: {}", e);
        process::exit(1);
    }

    log.info("stage_complete", "Weather analysis completed successfully");
}

fn run(args: &Args, log: &StageLogger) -> anyhow::Result<()> {
    // Load heightmap
    log.info("loading_heightmap", &format!("Loading {:?}", args.input));
    let hm = heightmap::Heightmap::load(&args.input)?;
    log.info("heightmap_loaded", &format!("Loaded heightmap: {}x{}", hm.width, hm.height));

    // Perform analysis
    log.info("generating_weather", "Generating weather analysis layers");
    let weather = analysis::generate_weather_map(&hm);

    // Write output
    log.info("saving_output", &format!("Saving weather map to {:?}", args.output));
    weather.save(&args.output)?;
    log.info("output_saved", ".weather file written successfully");
    
    Ok(())
}
