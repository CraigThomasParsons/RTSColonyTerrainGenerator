# Tiler

Tile generation service for breaking terrain into manageable chunks.

## Overview

The Tiler is a **deterministic, batch-processing stage** that converts authoritative heightmap cell data into fully resolved tile maps suitable for direct use by game engines and future procedural tooling (Stitcher, WFC).

**Core Principle:** Pure interpretation — no randomness, no terrain modification, no procedural generation.

## Directory Structure

- `systemd/` - Systemd service configuration files
- `inbox/` - Incoming tiling requests (symlinked to Heightmap outbox)
- `outbox/` - Generated tile files (`.maptiles` binary artifacts)
- `archive/` - Archived processed tiles

## Pipeline Position

