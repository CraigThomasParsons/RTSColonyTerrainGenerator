// The pseudo-persona pattern: act as a named persona from support/personas.js.
// Personas are all strategy 'local' for now — no sign-in, the persona simply takes
// the controls of the checkout. When Screenplay lands, this becomes actorCalled(name).
import { Given, Then } from "@cucumber/cucumber";
import assert from "node:assert/strict";
import { persona } from "../support/personas.js";

Given("the persona {string} is at the controls", function (name) {
  this.currentPersona = persona(name);
});

Then("the acting persona has role {string}", function (role) {
  assert.ok(this.currentPersona, "no persona is at the controls");
  assert.equal(
    this.currentPersona.role,
    role,
    `expected the acting persona to have role "${role}", got "${this.currentPersona.role}"`,
  );
});
