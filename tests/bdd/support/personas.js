/**
 * Personas — the named cast the behaviour suite acts as.
 *
 * A lightweight, pre-Screenplay "persona" pattern (inherited from ThePulseProject
 * PulseClient/tests/bdd/support/personas.js): personas live here as data and are referenced
 * by friendly name in .feature files (e.g. `Given the persona "Operator" is at the controls`),
 * so a scenario reads in the ubiquitous language while the persona's substance stays in one
 * place. The planned evolution is Serenity/JS Screenplay: each persona becomes an Actor whose
 * Abilities are pipeline-native (RunAStage, InspectArtifacts) rather than HTTP, and Serenity's
 * reporter narrates runs as living documentation.
 *
 * `strategy`:
 *   'local' — no provisioning needed; the persona acts through the repository checkout
 *             (submitting jobs, reading lanes and artifacts). All personas are local until
 *             the pipeline grows authenticated surfaces.
 */
export const PERSONAS = {
  "Operator": {
    role: "OPERATOR",
    strategy: "local",
    about:
      "Runs the pipeline day to day — submits jobs, watches inbox/outbox lanes, " +
      "chases failed artifacts, reads job logs.",
  },
  "Level Designer": {
    role: "LEVEL_DESIGNER",
    strategy: "local",
    about:
      "Consumes the finished world — cares that the final map document is playable and, " +
      "eventually, that it imports cleanly into AgileMedievalPeasantBoard.",
  },
};

/** Resolve a persona by its friendly name, with a helpful error listing the known cast. */
export function persona(name) {
  const p = PERSONAS[name];
  if (!p) {
    const known = Object.keys(PERSONAS).map((n) => `"${n}"`).join(", ");
    throw new Error(`Unknown persona "${name}". Known personas: ${known}.`);
  }
  return { name, ...p };
}
