// Steps for the cell-to-tile contract (slice-01). The Given/When pair routes through
// the world's target — the SAME sentences are answered by the legacy Tiler binary on
// the legacy profile and by MapGen.Cli on the net profile.
import { Given, When, Then } from "@cucumber/cucumber";
import assert from "node:assert/strict";
import { expandViaLegacy, expandViaNet } from "../support/expansion_targets.js";

Given("a cell map that is {int} cells wide and {int} cells high", function (width, height) {
  this.cellMap = { width, height };
});

When("I expand the cell at {int},{int}", function (cellX, cellY) {
  const expand = this.viaTarget({ net: expandViaNet, legacy: expandViaLegacy });
  this.expansion = expand(this.cellMap.width, this.cellMap.height, cellX, cellY);
  assert.equal(this.expansion.ok, true, `expansion failed: ${this.expansion.error}`);
});

When("I try to expand the cell at {int},{int}", function (cellX, cellY) {
  this.requireNetTarget("per-cell rejection");
  this.failure = expandViaNet(this.cellMap.width, this.cellMap.height, cellX, cellY);
});

Then("the tile region contains exactly {int} coordinates", function (count) {
  assert.equal(this.expansion.tiles.length, count,
    `expected ${count} tiles, got: ${JSON.stringify(this.expansion.tiles)}`);
});

Then("the tile region contains {int},{int}", function (tileX, tileY) {
  const found = this.expansion.tiles.some((tile) => tile.x === tileX && tile.y === tileY);
  assert.ok(found, `tile (${tileX},${tileY}) not in region: ${JSON.stringify(this.expansion.tiles)}`);
});

Then("every tile coordinate is inside a tile map that is {int} tiles wide and {int} tiles high", function (mapWidth, mapHeight) {
  assert.equal(this.expansion.tileMap.width, mapWidth, "tile map width");
  assert.equal(this.expansion.tileMap.height, mapHeight, "tile map height");
  const outside = this.expansion.tiles.filter(
    (tile) => tile.x >= mapWidth || tile.y >= mapHeight || tile.x < 0 || tile.y < 0);
  assert.deepEqual(outside, [], `tiles outside ${mapWidth}×${mapHeight}: ${JSON.stringify(outside)}`);
});

// Shared rejection step for every slice's @net-only rejection scenario. Each slice's
// "I try to …" step stores its failure outcome in this.failure as { ok, error }.
Then("the operation fails because the cell coordinate is outside the cell map", function () {
  assert.equal(this.failure.ok, false, "expected the operation to fail");
  assert.match(this.failure.error, /outside the cell map/);
});
