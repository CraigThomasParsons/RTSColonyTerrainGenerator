# artifact_hash

Logical-content hashing for MapGenerator pipeline artifacts. A stage is deterministic
(`docs/Stage_Contract.md`), so the same logical input must yield the same logical output.
This tool hashes an artifact's *logical* content — insensitive to key order and to
non-contractual metadata such as timestamps — so a replacement stage can be checked for
parity against the golden baseline (Gate 7, `docs/adr/0002-dafny-as-verified-model.md`).

## Usage

Run from the repository root.

```bash
# hash one artifact
python -m tools.artifact_hash hash MapGenerator/Tiler/outbox/<job>.maptiles

# hash the same logical map produced under a different job id (strips job_id too)
python -m tools.artifact_hash hash <path> --ignore-identity

# build a full logical-hash manifest for a completed job
python -m tools.artifact_hash manifest <job> --out tests/fixtures/golden/<job>/manifest.json
```

## How the hash is computed

| Artifact kind | Rule |
|---|---|
| Binary (`.heightmap`, `.weather`, `.maptiles`, `.png`, `.chk`, `.scm`) | `sha256:` + hex of raw bytes |
| JSON (`.json`, `.playable.json`) | drop volatile keys → canonical JSON (sorted keys, compact) → sha256 |
| `.worldpayload` directory | hash its `world.json` logically (the viewer shell is ignored) |
| anything else | raw bytes (nothing is silently left unhashed) |

Volatile keys stripped from JSON are listed in `VOLATILE_KEYS` (`hasher.py`) — timestamps,
durations, and absolute paths. `--ignore-identity` additionally strips `job_id`.

The binary rule (`sha256:` + hex) is deliberately trivial so the C# compatibility harness can
reproduce it exactly; that shared definition is what makes cross-language parity trustworthy.

## Tests

```bash
python -m pytest tools/artifact_hash/
```
