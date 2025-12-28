# TreePlanter

Tree and vegetation placement service for terrain generation.

## Directory Structure

- `systemd/` - Systemd service configuration files
- `inbox/` - Incoming tree placement requests
- `outbox/` - Completed vegetation placement data
- `archive/` - Archived processed tree placements

1. The inbox will take both output from the tiler and output from the Weather Analyser and plant trees on tiles.
   - This job will not start until they have a <id>.heightmap a <id>.maptiles, a <id>.weather file. (all with the same id)
2. The output of Weather Analysis will be the first to package the tiler and the heightmap and the analyses together and put it in the outbox.
3. I need the A.I. to be creative and figure ouit a way to determine where trees can go based off of the weather analyses
   and tiles and place trees in the maptiles file before packaging all three outputs in the payload and sending it off into the outbox.
