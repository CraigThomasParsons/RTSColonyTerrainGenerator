// Steps for the adjacency-mask contract (slice-02). The Given parses a small terrain
// grid written as slash-separated rows; the When routes through the world's target —
// the SAME sentences answered by the legacy Tiler binary and by MapGen.Cli.
import { Given, When, Then } from "@cucumber/cucumber";
import assert from "node:assert/strict";
import { maskViaLegacy, maskViaNet } from "../support/mask_targets.js";

Given("a {int} by {int} terrain grid with rows {string}", function (width, height, rows) {
  const grid = rows.split("/").flatMap((row) =>
    row.trim().split(",").map((value) => Number.parseInt(value.trim(), 10)));
  assert.equal(grid.length, width * height,
    `grid "${rows}" has ${grid.length} values, expected ${width * height}`);
  this.grid = { width, height, terrain: grid };
});

When("I compute the adjacency mask at {int},{int}", function (cellX, cellY) {
  const compute = this.viaTarget({ net: maskViaNet, legacy: maskViaLegacy });
  this.result = compute(this.grid.width, this.grid.height, cellX, cellY, this.grid.terrain);
  assert.equal(this.result.ok, true, `mask computation failed: ${this.result.error}`);
});

When("I try to compute the adjacency mask at {int},{int}", function (cellX, cellY) {
  this.requireNetTarget("per-cell rejection");
  this.failure = maskViaNet(this.grid.width, this.grid.height, cellX, cellY, this.grid.terrain);
});

Then("the adjacency mask is {int}", function (expected) {
  assert.equal(this.result.mask, expected,
    `expected mask ${expected}, got ${this.result.mask}`);
});

Then("the mask has East and South but not North or West", function () {
  const mask = this.result.mask;
  assert.ok((mask & 2) !== 0 && (mask & 4) !== 0, `expected East|South set in ${mask}`);
  assert.ok((mask & 1) === 0 && (mask & 8) === 0, `expected North|West clear in ${mask}`);
});

Then("the mask has North and South but not East or West", function () {
  const mask = this.result.mask;
  assert.ok((mask & 1) !== 0 && (mask & 4) !== 0, `expected North|South set in ${mask}`);
  assert.ok((mask & 2) === 0 && (mask & 8) === 0, `expected East|West clear in ${mask}`);
});

// "the operation fails because the cell coordinate is outside the cell map" is defined
// once in cell_to_tile.steps.js and shared — it asserts on this.result/this.expansion.
// Keep the two slices' failure objects field-compatible: both use { ok, error }.
