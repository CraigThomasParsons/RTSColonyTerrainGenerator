# Trade & Connectivity Simulation — Context

## Purpose

This module simulates historical and ongoing trade connectivity between all civilized settlements in the generated world.

The "Trader" is **not a real NPC**, unit, or agent.  
It is an abstract, analytical construct used to validate:

- World traversability
- Economic connectivity
- Infrastructure necessity
- Geographic plausibility

If a trader *could not* reach a settlement, then the world is considered **incomplete**.

This module runs **after WorldFeatures** and **before any gameplay-specific systems**.

---

## Core Design Philosophy

- The world must be **honest**
- Geography comes first
- Civilization adapts to terrain — not the reverse
- Infrastructure exists because it is *needed*, not because it was placed arbitrarily

WorldFeatures produces only **natural features**:
- Forests
- Rivers
- Mountains
- Marshes
- Cliffs
- Natural passes

This module answers:
> “Can civilization actually function in this world?”

---

## The Trader Concept (Abstract)

The Trader represents:

- A hypothetical ancient trade network
- A civilization-agnostic actor
- A neutral economic force

Assumptions:
- The trader will attempt to visit **every settlement**
- The trader does not avoid danger — only impassable terrain
- The trader does not fight
- The trader seeks the *cheapest viable path*

If the trader cannot reach a settlement:
- The world must adapt
- Infrastructure must emerge
- Or the settlement must be reclassified as isolated

---

## Determinism

The simulation must be:
- Fully deterministic
- Seed-driven
- Reproducible

Given the same world seed and inputs, trade connectivity results must be identical.

---

## Non-Goals

This module does NOT:
- Spawn units
- Simulate time
- Create economies
- Assign prices
- Invent settlements
- Modify terrain arbitrarily

It only **analyzes**, **validates**, and **requests change**.

---

## Output Philosophy

The output is **authoritative**.

Downstream systems (AI, economy, quests, lore, gameplay) must trust it.

If a settlement is marked unreachable:
- Trade systems must respect that
- Gameplay systems must reflect isolation
