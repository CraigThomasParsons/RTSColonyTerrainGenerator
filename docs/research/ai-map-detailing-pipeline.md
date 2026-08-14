# AI-Assisted Map Detailing for RTSColonyTerrainGenerator

**Research date:** 2026-08-10  
**Status:** Architecture research and proposed experiment; no live generation authorized

## Research question

Can a deterministic RTS map be used as structural conditioning for an AI image
generator that adds visual richness without changing gameplay geometry, after
which authoritative units, markers, and other overlays are rendered above the
generated background?

The short answer is **yes**. No turnkey system found in this review implements
that exact end-to-end contract, but several projects independently validate its
main architectural choices.

## Closest existing work

### Blizzard: Zenith

Blizzard's internal **Zenith** pipeline is the closest match. It converts
procedural 3D geometry into several conditioning layers and uses a multi-encoder
diffusion pipeline to produce stylized top-down line art, shadows, and
highlights. Its controls include depth, normals, and detail information while
walkable structure remains grounded in procedural geometry.

RTSColonyTerrainGenerator starts from an authoritative 2D tile model rather
than a 3D scene, but the separation is the same:

```text
authoritative geometry -> control layers -> generated presentation layers
```

Source: [Zenith: Diffusion Model-Driven Map Generation, GDC 2026](https://schedule.gdconf.com/session/zenith-diffusion-model-driven-map-generation/914450)

### Map Mosaic

**Map Mosaic** is an open-source tool that combines procedural heightmaps and
colour mapping with an image-generation stage to produce a polished map. It is
probably the closest publicly accessible product implementation. Its apparent
one-shot image-generation design is less structurally strict than the protected
mask and authoritative-overlay design proposed here.

Source: [Map Mosaic](https://keystoneintelligence.itch.io/mapmosaic) and its
[source repository](https://github.com/keystoneintelligence/mapmosaic)

### Earthbender

**Earthbender** uses a multi-channel semantic drawing to guide a custom
ControlNet. Separate channels identify mountains, lakes, roads, rivers, and
structural edges. The output is a heightmap rather than an RTS background, but
the control architecture maps directly onto terrain, topology, protected-area,
and decoration channels.

Source: [Earthbender project and paper](https://danial-barazandeh.github.io/Earthbender/)

### SPADE/GauGAN

SPADE established semantic-layout-to-image synthesis: labelled regions remain
meaningful while the generator supplies texture and visual detail. It is a
foundational precedent for treating the procedural map as a semantic contract
rather than merely a low-resolution image.

Source: [SPADE/GauGAN](https://nvlabs.github.io/SPADE/)

### GANcraft

GANcraft accepts a semantically labelled Minecraft block world and renders a
more detailed world while retaining its layout. It is a much heavier 3D neural
rendering system, but it is conceptually close to enriching a structured game
world without asking the model to invent the world itself.

Source: [GANcraft](https://nvlabs.github.io/GANcraft/)

### Broader game-development research

The survey *Level generation and style enhancement -- deep learning for game
development* identifies semantic-map-to-image translation, super-resolution,
style transfer, and texture synthesis as complementary tools for enriching
game maps.

Source: [Migdał, Olechno, and Podgórski (2021)](https://arxiv.org/abs/2107.07397)

Semantic procedural rendering predates diffusion models. Work on woodcut maps,
for example, rendered different patterns according to semantic geographical
labels. This supports keeping semantic ownership in the map model even when the
presentation implementation changes.

Source: [Semantics-guided procedural rendering for woodcut maps](https://www.microsoft.com/en-us/research/publication/semantics-guided-procedural-rendering-for-woodcut-maps/)

## Where Tile Upscaler fits

[Tile Upscaler](https://huggingface.co/spaces/gokaygokay/Tile-Upscaler) is useful
as an optional **final refinement stage**, not as the semantic map detailer.

```text
approved detailed map
        -> tiled diffusion / ControlNet refinement
        -> larger, sharper map
```

It conditions overlapping image regions on existing visual content. It may add
bark, grass variation, shoreline texture, and small debris, but it does not
understand terrain semantics, traversability, protected coordinates, or map
contracts. At stronger denoising settings it may invent gameplay-significant
features.

Use it only:

- after candidate approval;
- at conservative denoising strength;
- with overlapping tiles and stable whole-image conditioning;
- before reapplying authoritative overlays;
- followed by structural validation again.

It must not decide where water, cliffs, roads, buildings, or blocking trees
belong.

## What PixelLab can provide

PixelLab is closer to a map detailer than a generic upscaler:

- [Create Map](https://www.pixellab.ai/docs/tools/create-map) accepts an initial
  image, seed, target palette, camera view, and detail controls. Higher tiers
  support canvases up to 400x400.
- [Extend Map v2](https://www.pixellab.ai/docs/tools/extend-map-v2) supports
  selected-region editing, although it is experimental and limited to 180x180.
- The [PixelLab API](https://api.pixellab.ai/v2/docs) exposes Pixflux initial
  image conditioning, reproducible seeds, asynchronous jobs, usage reporting,
  map-object generation, and background polling.
- [Create Tileset](https://www.pixellab.ai/docs/tools/create-tileset) produces
  top-down Wang, dual-grid, and 3x3 tilesets.
- Map-object generation can use part of a map as a style-matching background.

A 128x128 control map is within PixelLab's supported range. A useful first
experiment would enlarge it to 256x256 or 384x384 with nearest-neighbour
sampling before submission so semantic boundaries remain crisp.

The principal limitation is that PixelLab's public API exposes an initial image
and inpainting controls, not the explicit simultaneous semantic, depth, normal,
and edge ControlNet channels used by Zenith and Earthbender. PixelLab is a good
first provider for validating the workflow. A later local Hugging Face or
ComfyUI backend would offer stronger structural control.

## Recommended architecture

```text
Authoritative worldpayload
        |
        +-- semantic terrain control
        +-- protected gameplay mask
        +-- topology/edge control
        +-- optional height/slope control
        +-- decoration-freedom mask
        |
        v
PixelLab or local multi-control candidates
        |
        v
Automated structural validation
        |
        v
Human comparison and approval
        |
        v
Optional Tile Upscaler refinement
        |
        v
Structural revalidation
        |
        v
Approved static background
        |
        v
Authoritative units, markers, bounds, and overlays
```

### Control artifacts

- `semantic-control.png`: exact water, grass, stone, forest, and road regions.
- `protected-mask.png`: spawn areas, navigable corridors, coast boundaries, and
  anything the generated presentation must not obscure.
- `topology-control.png`: shoreline, road, cliff, and other significant edges.
- `height-control.png`: optional inferred elevation and slope information.
- `decoration-mask.png`: areas where the generator may freely add flowers,
  roots, dirt variation, non-blocking foliage, and small stones.
- `visual-brief.json`: biome, season, palette, lighting direction, historical
  style, prohibited features, and permitted decoration vocabulary.

The existing `controls/` handoff is therefore the correct boundary. PixelLab,
Hugging Face, ComfyUI, or another provider should consume that contract rather
than becoming part of the authoritative map generator.

## The structural critic

Generation alone is insufficient. A visually attractive candidate can still be
a dishonest map. Each candidate should be checked by a structural critic:

1. Classify or downsample the candidate back into terrain regions.
2. Compare coastlines, roads, cliffs, and protected regions with the source.
3. Reject candidates whose boundary displacement exceeds a defined tolerance.
4. Measure visual obstruction over spawn points and navigation corridors.
5. Record source hash, control hash, provider, model, seed, prompt, cost, and
   validation scores.
6. Permit human approval only after automated structural gates pass.
7. Repeat validation after any upscaling or refinement stage.

Ordinary perceptual metrics such as SSIM are not sufficient because they do not
reliably measure topology or map usability. Recent cartographic research argues
for semantic and structural metrics specifically because generated maps can be
visually plausible while structurally wrong.

Source: [Map Feature Perception Metric for Map Generation Quality Assessment and Loss Optimization](https://www.mdpi.com/2072-4292/18/6/924)

## Recommended first experiment

Use one existing Golden Job map and remain offline until all integration paths
are proven with a fake provider.

1. Produce three 256x256 inputs:
   - the current visual preview;
   - a semantic colour map;
   - the semantic map with strongly rendered coastline and road edges.
2. Generate three candidates per input with the same visual brief and controlled
   seeds.
3. Score boundary drift and protected-region obstruction.
4. Compare passing candidates in Map Studio and approve one manually.
5. Apply Tile Upscaler to only the approved candidate at two conservative
   strengths.
6. Re-run structural validation.
7. Reapply authoritative overlays and compare the final presentations.

This experiment should answer whether PixelLab's initial-image adherence is
sufficient or whether the next provider needs explicit multi-ControlNet input.
It is small enough to learn from without becoming a model-training project.

## Expected outcome

- PixelLab should be useful for attractive candidate backgrounds and rapid
  experimentation.
- Tile Upscaler should improve local texture but will not replace semantic
  detailing.
- A local multi-control diffusion backend is the likely long-term map detailer.
- Protected masks, structural validation, source provenance, and explicit human
  approval are what turn the technique from a map-art demo into a viable game
  pipeline.

## Authorization boundaries

- No live PixelLab generation or credit spending without explicit approval.
- No redistribution of WC1-derived artwork without an explicit licensing
  decision.
- Generated presentation remains subordinate to the authoritative world model.
- Only human-approved candidates may be rendered beneath authoritative overlays.
