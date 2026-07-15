// Steps for the cell-to-tile contract (slice-01). The Given/When pair routes through
// the world's target — the SAME sentences are answered by the legacy Tiler binary on
// the legacy profile and by MapGen.Cli on the net profile.
import { Given, When, Then } from "@cucumber/cucumber";
import assert from "node:assert/strict";
import { expandViaLegacy, expandViaNet } from "../support/expansion_targets.js";

Given("a cell map that is {int} cells wide and {int} cells high", function (width, height) {
  this.cellMap = { width, height };
});

When("I expand the cell at {int},{int}", function (x, y) {
  const expand = this.target === "net" ? expandViaNet : expandViaLegacy;
  this.expansion = expand(this.cellMap.width, this.cellMap.height, x, y);
  assert.equal(this.expansion.ok, true, `expansion failed: ${this.expansion.error}`);
});

When("I try to expand the cell at {int},{int}", function (x, y) {
  this.requireNetTarget("per-cell rejection");
  this.expansion = expandViaNet(this.cellMap.width, this.cellMap.height, x, y);
});

Then("the tile region contains exactly {int} coordinates", function (count) {
  assert.equal(this.expansion.tiles.length, count,
    `expected ${count} tiles, got: ${JSON.stringify(this.expansion.tiles)}`);
});

Then("the tile region contains {int},{int}", function (x, y) {
  const found = this.expansion.tiles.some((t) => t.x === x && t.y === y);
  assert.ok(found, `tile (${x},${y}) not in region: ${JSON.stringify(this.expansion.tiles)}`);
});

Then("every tile coordinate is inside a tile map that is {int} tiles wide and {int} tiles high", function (w, h) {
  assert.equal(this.expansion.tileMap.width, w, "tile map width");
  assert.equal(this.expansion.tileMap.height, h, "tile map height");
  const outside = this.expansion.tiles.filter((t) => t.x >= w || t.y >= h || t.x < 0 || t.y < 0);
  assert.deepEqual(outside, [], `tiles outside ${w}×${h}: ${JSON.stringify(outside)}`);
});

Then("the operation fails because the cell coordinate is outside the cell map", function () {
  assert.equal(this.expansion.ok, false, "expected the expansion to fail");
  assert.match(this.expansion.error, /outside the cell map/);
});
