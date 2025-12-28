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

fn main() {
    let args = Args::parse();

    println!("Starting analysis for: {:?}", args.input);

    if let Err(e) = run(&args) {
        eprintln!("Error: {}", e);
        process::exit(1);
    }

    println!("Analysis complete. Output written to: {:?}", args.output);
}

fn run(args: &Args) -> anyhow::Result<()> {
    // Load heightmap
    let hm = heightmap::Heightmap::load(&args.input)?;
    println!("Loaded heightmap: {}x{}", hm.width, hm.height);

    // Perform analysis
    println!("Generating weather analysis...");
    let weather = analysis::generate_weather_map(&hm);

    // Write output
    println!("Saving weather map...");
    weather.save(&args.output)?;
    
    Ok(())
}
