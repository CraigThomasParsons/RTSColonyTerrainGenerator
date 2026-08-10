# Postal Service Integration Proposal for MapGenerator

## Overview

This document outlines the architectural strategy for migrating MapGenerator's rigid, file-copying pipeline to the robust, event-driven RabbitMQ architecture of **ThePostalService**.

By using ThePostalService, we achieve a decoupled, observable DAG (Directed Acyclic Graph) where stages no longer rely on hardcoded relative paths to pass artifacts to downstream consumers.

## 1. Registry Configuration

Each pipeline stage will become a registered "observable" service.
We will create a script `register_stages.sh` inside `MapGenerator/` that generates and drops the following `toml` profiles into `/home/craigpar/Code/ThePostalService/registry/`:

- `mapgen-heightmap.toml`
- `mapgen-weather.toml`
- `mapgen-tiler.toml`
- `mapgen-treeplanter.toml`
- `mapgen-worldfeatures.toml`
- `mapgen-pathfinder.toml`
- ...etc.

Each profile will define `inbox_path` and `outbox_path` pointing strictly to their respective local stage directories.

## 2. Emitting Packages (The Mailbox Flag)

Instead of stages using bash `cp` to inject files into downstream folders, they will construct a self-contained "Package" in their own local outbox.

**Format:**

```text
MapGenerator/{Stage}/outbox/<job_id>/
  ├── <artifacts> (e.g. .heightmap, .weather)
  ├── letter.toml (Defines the recipient)
  └── manifest.toml (Lists the package contents)
```

At the end of a stage's processing bash script, it will:

1. Generate `letter.toml` specifying the downstream `recipient` (e.g., `recipient = "mapgen-weather"`).
2. Generate `manifest.toml` listing the artifacts.
3. Publish a `package_ready` JSON event to RabbitMQ on the `postal.signals` queue using a lightweight AMQP CLI tool or curl.

## 3. Handling DAG Constraints (Fan-Outs & Fan-Ins)

MapGenerator is not a linear pipeline; it features complex fan-outs and fan-ins that must be addressed carefully under ThePostalService's 1-to-1 delivery guarantee.

### Fan-Outs (e.g., Heightmap -> Tiler & WeatherAnalyses & TreePlanter)

Currently, `Heightmap` feeds its output to multiple stages.
Because `letter.toml` defines a single recipient, stages that fan out must create **separate packages** in their outbox for each downstream destination.
For example, the Heightmap stage will create:

- `outbox/<job_id>_tiler/` with `letter.toml` pointing to `mapgen-tiler`
- `outbox/<job_id>_weather/` with `letter.toml` pointing to `mapgen-weather`
- `outbox/<job_id>_planter/` with `letter.toml` pointing to `mapgen-treeplanter`

It will then fire 3 distinct RabbitMQ signals.

*(Alternative: We could upgrade ThePostalService Go Worker to support a `recipients = ["mapgen-tiler", "mapgen-weather"]` array in the letter, causing the worker to duplicate the envelope across multiple inboxes during delivery. This would save local disk I/O).*

### Fan-Ins (e.g., TreePlanter needs Heightmap, Maptiles, Weather)

TreePlanter requires 3 distinct files to execute.
With ThePostalService, these will arrive asynchronously as 3 separate packages drops into the TreePlanter Inbox.
TreePlanter's consumer script (triggered by `systemd.path`) must be refactored to check a "ready state". When it wakes up, it will check if `<id>.heightmap`, `<id>.maptiles`, and `<id>.weather` are **ALL** present. If any are missing, the script simply exits gracefully (or requeues), knowing that a future package delivery will trigger it again. Once all 3 exist, it triggers the engine.

## 4. Execution Flow

1. **Job Start:** A job spec is dropped into Heightmap's inbox. `systemd.path` detects it and executes the engine.
2. **Heightmap Finish:** Heightmap writes its output packages, drops `letter.toml`, and pings RabbitMQ.
3. **ThePostalService Route:** Reads RabbitMQ, looks up the registry, and safely moves the packages into the Tiler, Weather, and TreePlanter inboxes.
4. **Intermediate Stages:** Tiler & Weather wake up via `systemd.path`, process their specific `.heightmap` packages, generate their artifacts, package them for TreePlanter, and ping RabbitMQ.
5. **Synchronization Wait:** TreePlanter wakes up repeatedly as packages drop in, but only executes its core logic once the final dependency arrives.

## 5. Testing & Implementation Guide

When implementing this architectural shift, follow this rigorous testing sequence to ensure no jobs are lost in transit:

1. **Registry Verification:**
   - Run the `register_stages.sh` script.
   - Assert that the `.toml` profiles exist in `ThePostalService/registry/` and that the paths exactly match the filesystem.
2. **RabbitMQ Integrity Test:**
   - Integrate the AMQP broadcast script into a test bash script.
   - Broadcast a mock `package_ready` event and verify it appears in the RabbitMQ Management UI (`http://localhost:15672`).
3. **End-to-End Tracer Move:**
   - Start `ThePostalService` worker (`go run main.go`).
   - Manually construct a mock package directory with a `letter.toml` inside `Heightmap/outbox`.
   - Fire a manual signal via CLI.
   - **Validation:** Verify that ThePostalService worker logs the transport and that the directory physically disappears from the `outbox` and materializes completely in the target `inbox`.
4. **Full Pipeline Run:**
   - Submit a real MapGenerator job spec.
   - Tail the logs of all systemd units concurrently (`journalctl -u "mapgen-*" -f`).
   - Monitor the `postal.signals` exchange.
   - **Validation:** Ensure TreePlanter successfully waits for all 3 dependencies before firing, and validate the final playable payload emerges at `CartridgeManufacturer`.
