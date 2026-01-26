# AI-Driven Pipeline Test Harness Plan

## Goal

Transform `pipeline_ai_test.py` into a "perfect" AI-native testing framework.
The goal is to enable an AI agent (like me) to:

1. **Trigger** complex pipeline runs.
2. **Observe** execution in real-time with structured feedback.
3. **Diagnose** failures with semantic precision.
4. **Verify** artifacts against the Stage Contract automatically.

## Core Philosophy

* **"Agent-First" Output**: Logs and reports should be structurally parsable (JSON/YAML) but also summarized in natural language for context.
* **Semantic Awareness**: The tool shouldn't just `grep` logs; it should understand the *flow* (e.g., "PathFinder started but stalled because WorldFeatures didn't emit a payload").
* **Active Validation**: Don't just check if files exist. Validate their content (integrity, schema, logic).

## Implementation Plan

### Phase 1: Architecture Refactoring

* **Split the Monolith**: Refactor `pipeline_ai_test.py` into modular classes:
  * `PipelineController`: Manages `mapgenctl` invocation and process lifecycle.
  * `LogSentinel`: Advanced log monitoring with state tracking (not just regex).
  * `StageRegistry`: Dynamic configuration of stages, timeouts, and artifact paths (no more hardcoded dicts).
  * `Reporter`: Generates human (CLI) and machine (JSON) reports.

### Phase 2: Stage-Aware Validators

Implement a plugin system for stage verification.

* `Validator` Interface: `validate(job_id, context) -> ValidationResult`
* **Generic Validator**: Checks `outbox/` for expected files.
* **Specific Validators**:
  * `Heightmap`: Check for non-zero variance (flat map detection).
  * `PathFinder`: Check JSON connectivity report for isolation counts.
  * `InfrastructureBuilder`: Check for invalid mutations (e.g., road on water).

### Phase 3: "AI Mode" & CLI Upgrades

* **Chaos Monkey**: Optional flag to inject failures (e.g., delete an artifact mid-run, `kill -9` a worker) to test system recovery.
* **Scale Testing**: Loop parameter to run N jobs in parallel to test `systemd` concurrency.

## TYS Integration

This tool becomes the "Verify" step in TYS.

* **Command**: `python tools/pipeline_ai_test/main.py --verify-stage PathFinder --job-id <id>`
* **Output**:

    ```json
    {
      "status": "PASS",
      "stage": "PathFinder",
      "metrics": { "routes": 50, "coverage": 100.0 }
    }
    ```

## Execution Steps

1. Refactor `pipeline_ai_test.py` into a package `tools/ai_test/`.
2. Implement `StageRegistry` and migrate hardcoded values.
3. Implement `JSON` reporting.
4. Add `PathFinder` specific validation logic.
