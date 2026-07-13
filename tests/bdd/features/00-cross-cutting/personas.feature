@slice-00-cross-cutting
Feature: Personas
  The behaviour suite acts as a named cast of personas, defined once in
  tests/bdd/support/personas.js and referenced by friendly name. All personas are
  local (they act through the repository checkout); the planned Screenplay evolution
  turns each into a Serenity/JS Actor with pipeline-native abilities.

  Scenario: The Operator takes the controls
    Given the persona "Operator" is at the controls
    Then the acting persona has role "OPERATOR"

  Scenario: The Level Designer takes the controls
    Given the persona "Level Designer" is at the controls
    Then the acting persona has role "LEVEL_DESIGNER"
