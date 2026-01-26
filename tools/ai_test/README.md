# AI-Driven Pipeline Test Framework

A modular, AI-native testing framework for the MapGenerator pipeline. Provides structured monitoring, semantic diagnostics, and automated stage validation.

## Features

### 🔍 **Semantic Log Monitoring**
- Real-time log parsing with stage awareness
- Automatic issue detection and categorization
- Health score computation based on errors, warnings, and activity
- Stall detection with configurable timeouts per stage

### ✅ **Stage-Aware Validation**
- Pluggable validator system with stage-specific logic
- Artifact presence checking
- Content validation (e.g., heightmap variance, PathFinder route analysis)
- Structured validation results (PASS/FAIL/WARN/SKIP)

### 📊 **Multi-Format Reporting**
- Human-friendly CLI output with live monitoring
- Machine-readable JSON export for automation
- YAML export for readability (requires PyYAML)
- Metrics tracking and trend analysis

### 🎛️ **Flexible Execution Modes**
- Monitor existing pipeline runs
- Start and monitor new runs
- Verify specific stages for completed jobs
- Export reports for archival or CI integration

## Quick Start

### Monitor an Active Pipeline
```bash
# Follow logs with default settings (120s monitoring)
python -m tools.ai_test

# Custom duration and stale threshold
python -m tools.ai_test --duration 300 --stale 20
```

### Start and Monitor a New Pipeline
```bash
# Start a 128x128 map and monitor until WorldPreview
python -m tools.ai_test --run --width 128 --height 128 --until WorldPreview

# With JSON output exported to file
python -m tools.ai_test --run --json-output --export pipeline_report.json
```

### Verify Specific Stages
```bash
# Validate PathFinder output for a completed job
python -m tools.ai_test --verify-stage PathFinder --job-id <uuid>

# Get JSON output for automation
python -m tools.ai_test --verify-stage WorldPreview --job-id <uuid> --json-output
```

## Architecture

### Core Components

#### **StageRegistry** (`registry.py`)
Central configuration for all pipeline stages. Defines:
- Artifact patterns and locations
- Stage dependencies
- Timeout thresholds
- Validation rules

```python
from tools.ai_test.registry import StageRegistry

registry = StageRegistry(repo_root)
stage = registry.get("PathFinder")
artifacts = registry.check_artifacts("PathFinder", job_id)
```

#### **LogSentinel** (`sentinel.py`)
Advanced log monitoring with semantic awareness:
- Parses structured log lines (timestamp, job, stage, level, message)
- Tracks per-stage state (first seen, last seen, error counts)
- Detects known failure patterns
- Computes health scores
- Identifies stalled stages

```python
from tools.ai_test.sentinel import LogSentinel

sentinel = LogSentinel(log_path)
sentinel.start()
entries = sentinel.poll()  # Read new lines
score = sentinel.compute_health_score()
```

#### **Validator System** (`validators.py`)
Pluggable validators for stage-specific checks:

**Base Classes:**
- `Validator`: Abstract base for all validators
- `GenericValidator`: Checks artifact presence only

**Stage-Specific Validators:**
- `HeightmapValidator`: Detects flat maps (low variance)
- `PathFinderValidator`: Analyzes route success rates and connectivity
- `WorldPreviewValidator`: Validates complete artifact set and file sizes

```python
from tools.ai_test.validators import ValidatorFactory

factory = ValidatorFactory(registry)
result = factory.create("PathFinder").validate(job_id)
print(result.status, result.message, result.metrics)
```

#### **Reporter** (`reporter.py`)
Multi-format output generation:
- Live CLI view with health dashboard
- Final reports in CLI/JSON/YAML
- Export to files for archival

```python
from tools.ai_test.reporter import Reporter, OutputFormat

reporter = Reporter(OutputFormat.JSON)
reporter.render_report(pipeline_report)
reporter.export_json(report, Path("output.json"))
```

#### **PipelineController** (`controller.py`)
Manages pipeline execution via `mapgenctl`:
- Starts new jobs
- Monitors process lifecycle
- Graceful termination

## Configuration

### Stage Timeouts

Override default timeouts per stage:

```bash
python -m tools.ai_test --stage-timeout heightmap=180 --stage-timeout tiler=150
```

Default timeouts:
- Heightmap: 120s
- Tiler: 120s
- WeatherAnalyses: 120s
- TreePlanter: 180s
- WorldFeatures: 180s
- PathFinder: 180s
- AncientCivilization: 120s
- WorldPreview: 60s

### Log Path

Specify custom log file:

```bash
python -m tools.ai_test --log /custom/path/to/mapgen.log
```

## Validation System

### Writing Custom Validators

Extend the `Validator` base class:

```python
from tools.ai_test.validators import Validator
from tools.ai_test.reporter import ValidationResult

class MyStageValidator(Validator):
    def validate(self, job_id: str) -> ValidationResult:
        artifacts = self._check_artifacts(job_id)
        
        # Custom validation logic
        stage_def = self.registry.get(self.stage_name)
        output_path = stage_def.artifact_path(
            self.registry.repo_root, job_id, "{job_id}.output"
        )
        
        if not output_path.exists():
            return ValidationResult(
                stage=self.stage_name,
                status="FAIL",
                message="Output file missing",
                artifacts=artifacts,
            )
        
        # Perform content checks
        with open(output_path, 'r') as f:
            data = json.load(f)
            
        metrics = {"records": len(data)}
        
        return ValidationResult(
            stage=self.stage_name,
            status="PASS",
            message=f"Validated {len(data)} records",
            artifacts=artifacts,
            metrics=metrics,
        )
```

Register in `ValidatorFactory`:

```python
self._validators["mystage"] = MyStageValidator
```

## TYS Integration

This framework serves as the "Verify" step in the TYS (Test Your S***t) methodology:

```bash
# After implementing a stage, verify it immediately
python -m tools.ai_test --verify-stage YourStage --job-id <uuid>

# Or run a full pipeline test
python -m tools.ai_test --run --until YourStage --duration 180
```

Expected workflow:
1. **Implement** → Make your code change
2. **Run** → Execute the pipeline
3. **Verify** → Use ai_test to validate outputs
4. **Fix** → Debug if validation fails
5. **Iterate** → Repeat until PASS

## Output Examples

### CLI Live View
```
================================================================================
MapGenerator AI Test Framework — Live Monitor
================================================================================
Job ID: 0ab66106-97fe-4fe4-8133-3ff67fde706e
Health Score: 92/100  |  Elapsed: 45s  |  Remaining: 75s
--------------------------------------------------------------------------------
Log Levels: INFO=234  WARN=2  ERROR=0

Stages Seen:
  • Heightmap: 42 lines
  • Tiler: 89 lines
  • PathFinder: 103 lines

Active Issues:

--------------------------------------------------------------------------------
Recent Log Lines:
  2026-01-24T05:10:43Z [job=0ab...] [stage=pathfinder] INFO Route found
  2026-01-24T05:10:44Z [job=0ab...] [stage=pathfinder] INFO Connectivity OK
================================================================================
```

### JSON Validation Output
```json
{
  "stage": "PathFinder",
  "status": "PASS",
  "message": "Validated 3/3 successful routes",
  "metrics": {
    "total_routes": 3,
    "successful": 3,
    "failed": 0,
    "success_rate": 100.0
  },
  "artifacts": {
    "{job_id}.json": true
  }
}
```

### Final Report (CLI)
```
================================================================================
Pipeline Execution Report
================================================================================
Job ID: 0ab66106-97fe-4fe4-8133-3ff67fde706e
Status: SUCCESS
Duration: 120.5s
Health Score: 87/100
Errors: 0  |  Warnings: 2
--------------------------------------------------------------------------------
Completed Stages:
  ✓ Heightmap
  ✓ Tiler
  ✓ TreePlanter
  ✓ PathFinder

Stage Validations:
  ✓ Heightmap: PASS
     Metrics: {'file_size': 65536}
  ✓ PathFinder: PASS
     → Validated 3/3 successful routes
     Metrics: {'total_routes': 3, 'successful': 3, 'success_rate': 100.0}
================================================================================
```

## Future Enhancements

### Phase 3 Features (Planned)
- **Chaos Monkey**: Inject failures during execution to test recovery
- **Scale Testing**: Parallel job execution with concurrency analysis
- **Regression Detection**: Compare metrics across runs
- **Interactive Mode**: Real-time filtering and drill-down
- **Notification Hooks**: Slack/email alerts on failures

## Dependencies

- Python 3.8+
- Standard library only (PyYAML optional for YAML export)

## Related Files

- Original tool: `tools/pipeline_ai_test/pipeline_ai_test.py`
- Design doc: `tools/pipeline_ai_test/plan.md`
- TYS methodology: `docs/tys.md`
