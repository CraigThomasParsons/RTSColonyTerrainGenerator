# CartridgeManufacturer — TYS Checklist

## Goal
Produce a WCAR cartridge from a world payload, export CHK/SCM, and validate the map with Stratagus headless harness.

## Inputs
- World payload JSON (`<id>.worldpayload`) from Playable outbox (preferred) or TreePlanter outbox (fallback).

## Outputs
- `outbox/<id>.wcar`
- `outbox/<id>.chk`
- `outbox/<id>.scm`
- `logs/jobs/<id>/cartridge.log.jsonl`

## TYS Checklist
- Build tools: `bin/wcar-tools` release binaries build cleanly.
- Run consumer: `bin/consume_cartridge_job.sh` produces WCAR + CHK + SCM.
- Validate artifacts:
  - `.wcar` exists and is non-empty
  - `.chk` exists and is non-empty
  - `.scm` exists and is non-empty
- Verify harness:
  - `logs/jobs/<id>/cartridge.log.jsonl` contains `stratagus harness pass`
  - If it fails, check `logs/jobs/<id>/stratagus/stratagus_stdout.log`

## Quick Commands
- Build toolchain:
  - `cd MapGenerator/CartridgeManufacturer/bin/wcar-tools && cargo build --release`
- Run stage:
  - `cd MapGenerator/CartridgeManufacturer && bin/consume_cartridge_job.sh`
- Optional monitoring:
  - `tools/pipeline_ai_test/pipeline_ai_test.py --follow-only`
