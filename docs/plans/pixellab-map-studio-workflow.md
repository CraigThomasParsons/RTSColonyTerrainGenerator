# PixelLab Map Studio workflow

Tracks Gitea #53 and its implementation issues #68–#71.

## Flow

1. Generate a world in Map Studio and wait for its existing MapGen job to succeed.
2. Choose one to four candidates and start the offline candidate run.
3. Map Studio polls the server job and shows its stage, percent, cache hits, paid
   submissions, failure, retry action, and balance availability.
4. Compare structurally valid candidate images in the gallery.
5. Enter the local operator name and decision reason, then approve or reject.
6. Only a `human-approved` candidate becomes the presentation background. The
   generated start zones and resource clusters are painted afterward and remain
   authoritative.

## Safety boundaries

- The browser never supplies a filesystem path or receives the PixelLab token.
- Offline is the default and uses a candidate budget of zero.
- Live mode requires two independent confirmations at the API boundary.
- Process execution uses no shell and only repository/server-owned paths.
- Job records and candidate evidence are written below `.runtime/pixellab/` and
  survive API restarts; runtime data is excluded from Git.
- Automated validation cannot activate a candidate. Approval is an explicit,
  recorded human transition.

## Credit-free verification

`PixelLabEndpointTests` injects `FakePixelLabProcessExecutor`, which writes the
same plan, validation, manifest, approval, and PNG shapes the server consumes.
The GUI tests inject the typed client seam. Together they exercise submit, poll,
progress, cache hit, failure, retry, comparison, approval, image retrieval, and
overlay ordering without a credential or external request.

The current golden payloads cannot yet produce real candidates: their declared
64×64 dimensions disagree with their 128×128 tile extents. The offline smoke
test fails closed as designed. Gitea #55 tracks that source-contract correction;
the exploration override is not a workaround because it deliberately produces
controls only and leaves candidates ineligible for approval.
