# TreePlanter

Tree and vegetation placement service for terrain generation.

## Directory Structure

- `systemd/` - Systemd service configuration files
- `inbox/` - Incoming tree placement requests
- `outbox/` - Completed vegetation placement data
- `archive/` - Archived processed tree placements

The inbox will take both output from the tiler and output from the Weather Analyser.
