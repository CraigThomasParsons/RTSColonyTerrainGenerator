# CartridgeManufacturer — Context

## Why This Stage Exists

CartridgeManufacturer turns pipeline world payloads into immutable WCAR
cartridges. WCAR is the canonical world artifact for long-term storage
and engine validation.

## Pipeline Position

TreePlanter → CartridgeManufacturer → WCAR/CHK → Stratagus

## Core Rules

- WCAR is written once and never mutated
- CHK is a projection, not a source of truth
- Engine validation is a sanity check, not gameplay testing
