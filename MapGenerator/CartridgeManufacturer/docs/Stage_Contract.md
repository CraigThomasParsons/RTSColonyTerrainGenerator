# CartridgeManufacturer — Stage Contract

## Purpose

CartridgeManufacturer seals a generated world into a WCAR cartridge and
projects it into a StarCraft-compatible CHK/SCM for engine validation.

## Inputs

- `inbox/` or TreePlanter outbox `.worldpayload` JSON files

## Outputs

- `outbox/<job_id>.wcar` (canonical cartridge)
- `outbox/<job_id>.chk` (raw CHK)
- `outbox/<job_id>.scm` (MPQ archive containing CHK)

## Failure Handling

- Invalid payloads → `failed/`
- Successful payloads → `archive/`
- All failures logged to `logs/jobs/<job_id>/cartridge.log.jsonl`

## Determinism

WCAR is immutable once written. Projection is lossy by design and must be
repeatable for identical inputs.
