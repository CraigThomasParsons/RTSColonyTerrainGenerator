# WorldCartridge (.wcar)
## WCAR + CHK Integrated Specification — v0.2

---

## 1. Overview

WorldCartridge (WCAR) is a binary, chunk-based container format representing a fully
generated game world as a sealed, portable artifact.

WCAR is the canonical output of the MapGenerator pipeline.

Embedded within WCAR may be one or more executable projections of the world for
specific engines. In v0.2, the first standardized projection is a StarCraft-
compatible CHK map.

WCAR is the source of truth.
CHK is a derived execution view.

---

## 2. Design Principles

- Chunk-based, labeled binary format
- Order-independent chunks (except HEAD)
- Deterministic and reproducible
- Engine-agnostic core
- Engine-compatible projections
- Forward-compatible via extensible chunks

---

## 3. File Structure

A `.wcar` file is a linear sequence of chunks:

```
[HEAD]   required
[SEED]   optional
[PROV]   required
[HMAP]   optional
[TILE]   optional
[BIOM]   optional
[FEAT]   optional
[PATH]   optional
[NAVI]   optional
[CHK0]   optional
[EXT*]   optional
```

Rules:
- HEAD MUST be the first chunk
- PROV MUST be present
- Unknown chunks MUST be skipped safely

---

## 4. Common Chunk Layout

All chunks share a common header:

| Offset | Field  | Type    |
|------:|--------|---------|
| 0     | Tag    | char[4] |
| 4     | Length | u32     |
| 8     | Data   | byte[]  |

- Endianness: little-endian
- Text encoding: UTF-8

---

## 5. HEAD — Cartridge Header

Defines identity, scale, and compatibility.

Payload:

```
char[4] magic            // "WCAR"
u16     major_version    // 0
u16     minor_version    // 2
u128    world_uuid
u64     created_unix_ts
u32     width_tiles
u32     height_tiles
f32     tile_world_size
f32     vertical_scale
u32     declared_chunk_mask
```

---

## 6. SEED — Deterministic Seeds

Stores RNG seeds used by pipeline stages.

Payload:

```
u32 seed_count
repeated:
  char[32] name
  u64      seed_value
```

---

## 7. PROV — Pipeline Provenance

Records how the world was generated.

Payload:

```
u32 entry_count
repeated:
  char[32] stage_name
  char[32] stage_version
  u64      start_ts
  u64      end_ts
  u64      input_hash
  u64      output_hash
```

---

## 8. HMAP — Heightmap

Canonical terrain geometry.

Payload:

```
u32 width
u32 height
f32 min_height
f32 max_height
f32[width * height] height_values
```

---

## 9. TILE — Terrain Types

Logical terrain classification.

Payload:

```
u16 tile_type_count
repeated:
  u16 tile_id
  char[32] tile_name

u16[width * height] tile_map
```

---

## 10. BIOM — Biomes & Climate

Environmental semantics.

Payload:

```
u16 biome_count
repeated:
  u16 biome_id
  char[32] biome_name
  u32 biome_flags

u16[width * height] biome_map
```

---

## 11. FEAT — World Features

Discrete semantic objects (trees, ramps, landmarks, etc.).

Payload:

```
u32 feature_count
repeated:
  u32 feature_id
  u16 feature_type
  u32 x
  u32 y
  f32 elevation
  u32 metadata_len
  byte[metadata_len] metadata
```

Metadata MAY be JSON, CBOR, or binary.

---

## 12. PATH — Roads & Paths

Intended traversal networks.

Payload:

```
u32 path_count
repeated:
  u32 path_id
  u8  path_type
  u32 node_count
  repeated:
    u32 x
    u32 y
```

---

## 13. NAVI — Navigation Hints

High-level AI and simulation hints.

Payload:

```
u32 region_count
repeated:
  u32 region_id
  u32 region_flags
```

---

## 14. CHK0 — Embedded StarCraft Map

Executable StarCraft-compatible projection.

Payload:

```
u32 chk_format_version
u32 chk_length
byte[chk_length] chk_data
```

Rules:
- chk_data MUST be a valid CHK binary
- Dimensions MUST match HEAD
- Treated as opaque by WCAR tools

---

## 15. WCAR → CHK Projection Rules

| WCAR Chunk | CHK Section |
|----------|-------------|
| TILE     | MTXM, ERA   |
| BIOM     | ERA         |
| FEAT     | THG2, UNIT  |
| PATH     | Painted terrain |
| HMAP     | Quantized to tiles |
| NAVI     | Not representable |

Projection is lossy by design.

---

## 16. EXT* — Extensions

Engine- or tool-specific extensions.

Rules:
- Tag must start with 'X'
- Must not be required for validity
- Safe to ignore

---

## 17. Validation Rules

A valid WCAR v0.2 file MUST:
- Start with HEAD
- Contain PROV
- Respect chunk boundaries
- Use declared dimensions consistently

---

## 18. Versioning

- Breaking changes increment major version
- Additive changes increment minor version
- Unknown chunks MUST be skipped

---

## 19. Canonical Interpretation

WCAR is the authoritative world description.
CHK is a derived execution artifact.

WCAR is never generated from CHK.

---

## 20. Summary

WCAR v0.2 defines a durable, inspectable, and executable world cartridge format
capable of driving real RTS engines while preserving semantic intent.
