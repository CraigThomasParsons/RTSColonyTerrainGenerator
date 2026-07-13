// Stage-roster questions answered straight from the filesystem — the pipeline's
// source of truth (tools/README.md: "If a file exists, the stage is done").
import { Given, Then } from "@cucumber/cucumber";
import assert from "node:assert/strict";

Given("the MapGenerator stage roster", function () {
  this.roster = this.stageNames();
  assert.ok(this.roster.length > 0, "no stage directories found under MapGenerator/");
});

Then("every stage provides an executable bin lane", function () {
  const missing = this.roster.filter((s) => !this.stageHasLane(s, "bin"));
  assert.deepEqual(missing, [], `stages missing bin/: ${missing.join(", ")}`);
});

Then("the core stages are present:", function (table) {
  const missing = table
    .raw()
    .flat()
    .filter((s) => !this.roster.includes(s));
  assert.deepEqual(missing, [], `core stages missing from roster: ${missing.join(", ")}`);
});
