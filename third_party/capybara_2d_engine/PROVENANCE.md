# Provenance — `capybara_2d_engine`

Self-hosted (vendored) copy of the MIT-licensed 2D engine used as the **map preview
renderer** for the Phase 1 prototype GUI (`docs/plans/map-gui-prototype.md`).

| | |
|---|---|
| Upstream | <https://github.com/d-liya/capybara_2d_engine> |
| Commit | `220a56a24664621c1079a35897035c2dfccd1a8f` |
| Vendored on | 2026-08-06 |
| Licence | MIT — see [`LICENSE`](LICENSE), retained verbatim |

## Why vendored rather than depended on

The upstream project is a game **template**, not a published npm package: it has no
`dist/`, no registry entry, and `main` points at a build output that does not exist in
the repository. Self-hosting the source is the only way to consume it, and the slice
plan calls for exactly that ("`capybara_2d_engine` — the MIT-licensed engine we
self-host").

## Modifications

The tree is upstream verbatim except:

- `.git/` removed.
- `AGENTS.md`, `CLAUDE.md`, `.agents/`, `src/core/AGENTS.md`, `src/widgets/AGENTS.md`
  removed. These are agent instructions addressed to contributors of the *upstream*
  template; left in place they would be read as instructions governing work in this
  repository. Removing documentation from an MIT copy is permitted; `LICENSE` stays.

No source file is edited. Upstream is re-pullable by re-cloning at a newer commit and
repeating the two removals above.

## What the client actually uses

`clients/mapgen-gui` consumes the engine's **core camera/viewport and world-space
conventions**, not its asset pipeline:

- `src/core/CameraViewportController.ts` — canvas backing-store sizing, device-pixel
  ratio, CSS scale, and the camera transform the preview draws through.
- `src/utils/common.ts` — the `NORM` (0–1000) normalised world space, `toPixel`, and
  `snapCanvasValue`.

The engine's `GameRuntime` / `GameMap` are deliberately **not** used: they load
capybara.build sprite sheets, mask atlases and audio, none of which a generated terrain
preview has. The preview paints palette-indexed terrain and `.playable.json` markers
into the engine's viewport instead. Should this prototype grow real generated art, that
is the path back to `GameMap`.
