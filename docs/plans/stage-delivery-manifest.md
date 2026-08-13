# Terrain stage delivery manifest v1

The stage manifest is the immutable planning boundary for one complete Terrain
feature or legacy stage. It declares the client, server, shared-contract, and
verification work that must converge before an automatic Gitea stage merge can
be considered. Evaluation is read-only; a `ready` result is evidence for a
later capability-gated merge phase, never permission by itself.

## Manifest contract

```json
{
  "protocol": "terrain.stage-manifest/v1",
  "stageId": "golden-job-preview",
  "goal": "Render one verified Golden Job in the developer workbench.",
  "baseCommit": "1111111111111111111111111111111111111111",
  "integrationBranch": "stage/golden-job-preview",
  "authoritativeBranch": "main",
  "components": [
    {"id": "contract", "side": "contract", "issue": 90, "dependsOn": []},
    {"id": "server", "side": "server", "issue": 91, "dependsOn": ["contract"]},
    {"id": "client", "side": "client", "issue": 92, "dependsOn": ["contract"]},
    {"id": "verification", "side": "verification", "issue": 93, "dependsOn": ["server", "client"]}
  ],
  "coverageExceptions": []
}
```

Every component ID is unique and every dependency names another component in
the same acyclic manifest. The base is a full lowercase Git SHA and the
integration branch begins with `stage/`.

The four delivery sides are mandatory. A side may be omitted only with a
`coverageExceptions` entry containing `side`, `reason`, `approvedBy`, and
`approvedAt`. That record represents an explicit human decision and becomes
part of the manifest digest.

## Receipt contract

Each component produces one `terrain.stage-receipt/v1` JSON document containing
the stage and component identities, issue number, manifest digest, exact result
commit, `passed` result, and at least one command evidence record. Command
evidence contains the command, exit code, and a `sha256:` log digest. Large logs
remain external and immutable.

Different receipts for the same component are contradictory. Evidence bound to
an older manifest is stale. A failed command, abbreviated revision, missing
side, unknown dependency, or dependency cycle fails closed.

## Evaluation

```bash
/usr/bin/python3 scripts/tools/stage_manifest.py evaluate \
  path/to/stage.json path/to/receipts/*.receipt.json
```

The command prints stable `terrain.stage-evaluation/v1` JSON. Its state is one
of `ready`, `incomplete`, `stale`, or `contradictory`. It also reports the next
components whose dependencies have current passing receipts. Exit status is
zero only for `ready`.
