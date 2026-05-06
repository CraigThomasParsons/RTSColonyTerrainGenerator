# Stratagus Headless Harness Contract
## Version 0.1

This document defines the contract between the WCAR toolchain and the
Stratagus / Stargus RTS engine when running in headless (non-UI) mode for
validation and simulation.

This harness exists to validate generated worlds by executing them inside
a real RTS engine.

---

## 1. Purpose

The harness provides:

- Deterministic, headless execution
- Machine-readable success/failure signals
- Minimal but reliable validation of generated maps
- A stable interface for future autonomous testing

This harness is intentionally simple.

---

## 2. Invocation Model

The harness is invoked by an external runner (e.g. `wcar_run_stratagus`)
which launches the Stratagus engine with a known Lua scenario script.

The harness must support:

- Headless execution
- Loading a specific map file
- Running for a bounded simulation window
- Exiting cleanly with status

---

## 3. Required Inputs

The following values MUST be provided to the harness via engine arguments
or environment variables:

- MAP_PATH  
  Path to the map file to load (SCM / SCX / CHK)

- HARNESS_TICKS  
  Number of simulation ticks to execute

- HARNESS_SEED  
  Deterministic seed value (best-effort)

- HARNESS_OUT_DIR  
  Directory for logs and artifacts

---

## 4. Required Outputs

### 4.1 Log Markers

The harness MUST emit structured log markers to stdout or engine logs.

#### Success
HARNESS:PASS

#### Failure
HARNESS:FAIL:<CODE>:<MESSAGE>

Where `<CODE>` is a short, stable identifier.

#### Metrics
HARNESS:METRIC:<key>=<value>

Examples:
HARNESS:METRIC:ticks_executed=5000  
HARNESS:METRIC:units_alive=12

---

## 5. Failure Codes

The harness may emit the following failure codes:

- MAP_LOAD_FAILED
- INVALID_TERRAIN
- INVALID_START_POSITIONS
- RUNTIME_ERROR
- TIMEOUT
- UNKNOWN

Failure codes must remain stable across versions.

---

## 6. Validation Rules (v0.1)

The harness MUST validate:

- Map loads successfully
- Terrain data is valid
- Required player start positions exist
- No fatal Lua or runtime errors occur
- Simulation loop completes requested ticks

The harness MUST NOT attempt deep gameplay correctness in v0.1.

---

## 7. Simulation Loop

The harness must:

1. Load the map
2. Perform basic validation
3. Run the simulation for HARNESS_TICKS
4. Emit metrics
5. Exit cleanly

---

## 8. Determinism Policy

Determinism is best-effort in v0.1.

The harness must:
- Accept a seed
- Record the seed
- Avoid time-based randomness

Perfect determinism is not required in v0.1.

---

## 9. Versioning

This document defines v0.1 of the harness contract.

Future versions may:
- Add metrics
- Add stricter validation
- Add snapshot or state export

Existing markers and failure codes MUST remain backward-compatible.

---

## 10. Philosophy

This harness is not a test suite.
It is not a gameplay validator.

It is a world sanity check executed inside a real RTS engine.

If the engine cannot load or run the world, the world is invalid.
