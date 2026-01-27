# CartridgeManufacturer

CartridgeManufacturer produces WCAR cartridges from world payloads and
exports StarCraft-compatible CHK/SCM projections for validation.

## Inputs
- World payload JSON files (TreePlanter output) in `inbox/` or via PathFinder outbox.

## Outputs
- `outbox/<job_id>.wcar`
- `outbox/<job_id>.chk` (raw CHK)
- `outbox/<job_id>.scm` (MPQ archive containing CHK)
- `logs/jobs/<job_id>/cartridge.log.jsonl`

## Toolchain
- `wcar_pack` builds WCAR from payload JSON
- `wcar_export_chk` produces CHK/SCM from WCAR
- `wcar_run_stratagus` runs the headless harness

## Determinism
- WCAR is immutable once written
- Projection to CHK is lossy and documented

## Running
```bash
cd MapGenerator/CartridgeManufacturer
./install.sh
bin/consume_cartridge_job.sh
```

## TYS Checklist
- Run consumer once
- Verify `outbox/<job_id>.wcar`, `.chk`, `.scm`
- Confirm harness logs contain `HARNESS:PASS` or a structured failure marker
- Run `tools/pipeline_ai_test/pipeline_ai_test.py --follow-only` to verify cartridge artifacts appear
