@slice-00-cross-cutting
Feature: Pipeline smoke
  The cheapest possible proof that the harness and the pipeline checkout agree:
  the stage roster is intact and every stage keeps its executable lane. Runs green
  on the legacy profile today; the net profile inherits it because the roster is
  a property of the repository, not of either implementation.

  Scenario: The stage roster is intact
    Given the MapGenerator stage roster
    Then every stage provides an executable bin lane
    And the core stages are present:
      | Heightmap       |
      | Tiler           |
      | WeatherAnalyses |
      | TreePlanter     |
