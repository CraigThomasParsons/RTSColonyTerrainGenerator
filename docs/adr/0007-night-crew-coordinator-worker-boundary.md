# Keep TheNightCrew separate from MapGen execution

Status: Accepted

TheNightCrew's source and product ownership will move into the
RTSColonyTerrainGenerator repository, but TheNightCrew remains a coordinator: it
owns availability, claims, and progress rather than invoking coding agents. A
separate MapGen Night-Crew Worker owns checkouts, isolated execution, verification,
and delivery actions. This preserves the existing cross-machine coordination model
and keeps repository toolchains out of the coordinator; making TheNightCrew itself
an executable pipeline is explicitly deferred.
