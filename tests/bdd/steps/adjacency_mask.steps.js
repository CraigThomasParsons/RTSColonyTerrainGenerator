// Steps for the adjacency-mask contract (slice-02). The Given parses a small terrain
// grid written as slash-separated rows; the When routes through the world's target —
// the SAME sentences answered by the legacy Tiler binary and by MapGen.Cli.
import { Given, When, Then } from "@cucumber/cucumber";
import assert from "node:assert/strict";
import { maskViaLegacy, maskViaNet } from "../support/mask_targets.js";

Given("a {int} by {int} terrain grid with rows {string}", function (width, height, rows) {
  const grid = rows.split("/").flatMap((row) =>
    row.trim().split(",").map((v) => Number.parseInt(v.trim(), 10)));
  assert.equal(grid.length, width * height,
    `grid "${rows}" has ${grid.length} values, expected ${width * height}`);
  this.grid = { width, height, terrain: grid };
});

When("I compute the adjacency mask at {int},{int}", function (x, y) {
  const compute = this.target === "net" ? maskViaNet : maskViaLegacy;
  this.result = compute(this.grid.width, this.grid.height, x, y, this.grid.terrain);
  assert.equal(this.result.ok, true, `mask computation failed: ${this.result.error}`);
});

When("I try to compute the adjacency mask at {int},{int}", function (x, y) {
  this.requireNetTarget("per-cell rejection");
  this.failure = maskViaNet(this.grid.width, this.grid.height, x, y, this.grid.terrain);
});

Then("the adjacency mask is {int}", function (expected) {
  assert.equal(this.result.mask, expected,
    `expected mask ${expected}, got ${this.result.mask}`);
});

Then("the mask has East and South but not North or West", function () {
  const m = this.result.mask;
  assert.ok((m & 2) !== 0 && (m & 4) !== 0, `expected East|South set in ${m}`);
  assert.ok((m & 1) === 0 && (m & 8) === 0, `expected North|West clear in ${m}`);
});

Then("the mask has North and South but not East or West", function () {
  const m = this.result.mask;
  assert.ok((m & 1) !== 0 && (m & 4) !== 0, `expected North|South set in ${m}`);
  assert.ok((m & 2) === 0 && (m & 8) === 0, `expected East|West clear in ${m}`);
});

// "the operation fails because the cell coordinate is outside the cell map" is defined
// once in cell_to_tile.steps.js and shared — it asserts on this.result/this.expansion.
// Keep the two slices' failure objects field-compatible: both use { ok, error }.
