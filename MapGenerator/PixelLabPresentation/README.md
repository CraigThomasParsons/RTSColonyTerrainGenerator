# PixelLabPresentation

PixelLabPresentation is an optional, non-authoritative presentation lane. It
turns a JSON `.worldpayload` into deterministic control artifacts that a later
stage may submit to PixelLab. It does not call PixelLab and cannot change map
geometry, traversability, starts, resources, or export data.

This first slice implements Gitea issue #50 under outcome #49.

## Outputs

For an input job `<id>.worldpayload`, `visual_contract.py` writes:

- `visual-brief.json`: versioned visual intent and source summary;
- `semantic-control.png`: one pixel per authoritative map cell;
- `protected-mask.png`: white where visual geometry must be retained;
- `decoration-mask.png`: white where decorative invention is permitted;
- `generation-manifest.template.json`: immutable generation inputs with the
  remote-job fields left unsubmitted.

All JSON is canonical and all PNGs are generated with the Python standard
library. Repeated runs over the same input produce identical bytes.

## Usage

```bash
python3 MapGenerator/PixelLabPresentation/bin/visual_contract.py \
  --input MapGenerator/Playable/outbox/<id>.worldpayload \
  --output MapGenerator/PixelLabPresentation/outbox/<id>
```

Dimension declarations must agree with the addressed tile grid. The temporary
`--dimensions-from-tiles` option exists only to inspect legacy artifacts while
issue #55 is resolved. Artifacts created with that option carry a warning and
must not be submitted to PixelLab or approved for production use.

## Safety boundary

PixelLab outputs are presentation assets. Downstream consumers must render
gameplay and debug overlays from authoritative map data, never infer gameplay
state from an AI-generated image. See
[`docs/adr/0001-pixellab-presentation-only.md`](../../docs/adr/0001-pixellab-presentation-only.md).
