# TYS

0. Plan and document
- Reproduce StarCraft load error for StargusExport .scm.
- Inspect MPQ writer for missing MPQ table encryption.
- Implement proper MPQ hash/block table encryption.
- Regenerate .scm and verify StarCraft can open it.

1. Do the thing
- Updated `build_scm_minimal` to write encrypted MPQ hash/block tables.
- Added `_hash_for_table`, `_encrypt_table`, and `_build_hash_table` helpers.
- Added minimal CHK sections (`STR`, `SPRP`, `OWNR`, `SIDE`, `FORC`, `MASK`).
- Switched MPQ file name to `staredit\scenario.chk`.
- Regenerated StargusExport output for job `43524f28-c279-4158-a272-6923fe303ac4` from TreePlanter `outbox/` worldpayload.
- Confirmed outputs exist in `StargusExport/outbox`: `43524f28-c279-4158-a272-6923fe303ac4.chk` and `.scm` (non-zero size).
- Verified `.scm` MPQ header signature (`MPQ\x1a`) and table offsets are present.
- Files: stargus-exporter

2. Test the thing (automated pipeline)

- Regenerate the SCM with all required CHK sections (including UPRP, MRGN, SWNM, WAV) using the updated exporter in `MapGenerator/StargusExport/stargus-exporter`.
- Use the script `scmDraft/tools/ydotool_open_map_and_capture.sh` to automatically open the exported `.scm` in StarEdit and capture a screenshot.
- The latest screenshot is saved at `scmDraft/diagnostics/star_edit_capture.png`.
- Inspect the screenshot to determine if the map editor successfully loads the exported `.scm` (no error dialogs, map preview visible, etc).
- Repeat this process, updating the exporter and regenerating the SCM as needed, until the map editor can finally load the exported `.scm` without errors.

If all options are exhausted and the map still cannot be loaded, consider investigating Stargus itself for alternative map formats or compatibility workarounds.

3. If it doesn’t work, go back to 0

- If it fails, dump MPQ header/hash table using `mpyq` and adjust MPQ layout.

4. I can help double check the StargusExport
But lets make sure that the generated .scm is valid first, lets make sure we start from the beginning of the pipeline, and verify that the generated .scm is valid and comes from the right stages in the pipeline.