# Where I Left Off

## Summary
- WCAR toolchain exists under [MapGenerator/CartridgeManufacturer/bin/wcar-tools](MapGenerator/CartridgeManufacturer/bin/wcar-tools):
  - `wcar` crate parses and writes WCAR chunks.
  - `wcar_pack` builds WCAR from world payload JSON.
  - `wcar_export_chk` projects WCAR to CHK/SCM (minimal MPQ).
  - `wcar_run_stratagus` runs the headless Stratagus harness.
- WCAR parsing now enforces HEAD-first, validates WCAR magic/version, and checks TILE/HMAP/BIOM dimensions.
- CartridgeManufacturer stage already wires the pipeline (`consume_cartridge_job.sh`) and calls all tools.
- MapGenerator stage reference doc was cleaned and updated.

## Latest Changes
- Updated WCAR validation rules in [MapGenerator/CartridgeManufacturer/bin/wcar-tools/crates/wcar/src/lib.rs](MapGenerator/CartridgeManufacturer/bin/wcar-tools/crates/wcar/src/lib.rs).
- Rewrote [MapGenerator/stages.md](MapGenerator/stages.md) for clarity and correct inbox/outbox details.
- Added pipeline_ai_test usage to [MapGenerator/CartridgeManufacturer/README.md](MapGenerator/CartridgeManufacturer/README.md).
- Logged work in [Thoughts.md](Thoughts.md).

## TYS Notes
- Ran `cargo build --release` for the WCAR toolchain.
- Next: run the cartridge consumer to verify `.wcar`, `.chk`, `.scm`, and harness logs.

## Next Steps
1. Run `MapGenerator/CartridgeManufacturer/bin/consume_cartridge_job.sh` and confirm:
   - `outbox/<id>.wcar`, `outbox/<id>.chk`, `outbox/<id>.scm`
   - `logs/jobs/<id>/cartridge.log.jsonl` contains `HARNESS:PASS` or a stable failure marker.
2. If Stratagus fails to load maps, verify:
   - Tileset mapping JSON (default_badlands.json)
   - CHK section completeness (DIM/ERA/MTXM)
3. Extend `wcar_pack` to emit HMAP/BIOM/FEAT when available (currently TILE only).
4. Update `pipeline_ai_test` heuristics if new failure modes appear.
