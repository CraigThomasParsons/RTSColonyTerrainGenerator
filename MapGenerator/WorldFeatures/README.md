# WorldFeatures

World feature generation service for placing special terrain elements.

## Directory Structure

- `systemd/` - Systemd service configuration files
- `inbox/` - Incoming world feature requests
- `outbox/` - Generated world feature data

## The Problem

  ### There needs to be two available resources.
    -> Trees / Lumber
    -> Mine or Cavern == { Stone | Gold }
        - and maybe some harvestable stone outcroppings.

  ### Second problem: Ridges need an opening to allow the player to reach the next layer.
    - In my intention to take a 3d heightmap to a 2d tilemap some areas are blocked off because
        - The ridges show elevation but also form a circle.
        - I need a natural ramp or to force one.

## Goal
  - Identify PSA (Potential Settlement Areas)
  - Make it playable.

### At first I would like to try to put a ramp where a ramp is most naturally likely to exist.

- We need to use the Weather analysis data and use the tilemap to figure out where we will be breaking the ridge circle.
  - If there are two perfect places to do this, I suggest we do it.

- We need to decide where the best place to put a cavern opening is, because that will likely be the starting point of the player.

## Bonus

- Rivers, this will break my original goal of making the map player however
  - The next stage in the pipeline called "PathFinder" will be building bridges through them.


### Output
 - Keep things in the payload format that the Tree Planter started.

---

## Pipeline Position
```
Heightmap
↓
<id>.heightmap
↓
Tiler
↓
<id>.maptiles
↓
Weather Analysis
↓
<id>.weather
↓
TreePlanter
↓
<Payload>
↓
WorldFeatures
↓
<Payload>
↓
PathFinder ← you are here
```
## What is a payload?

This is still a work in progress but this is what the TreePlanter receives.
- inbox
  - from_heigtmap
    - <id>.heightmap
  - from_tiler
    - <id>.maptiles
  - from_weather
    - <id>.weather
