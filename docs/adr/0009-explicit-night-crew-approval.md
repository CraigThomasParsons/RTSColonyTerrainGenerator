# Require explicit, fail-closed Night Crew approval

Status: Accepted

Only Craig's `night-crew: approved` label on the canonical Gitea Issue authorizes an
otherwise-ready Slice for overnight execution. `status: planned`, an unblocked Bead,
or a queued NightCrew Job is insufficient by itself. Approval is browsed and applied
through Gitea's filtered issue list and bulk label action; any future TheNightCrew
view is only a projection that writes the same Gitea label. Intake and claim checks
fail closed when Gitea, Beads, the Planning Document, or their identity links cannot
be verified, because unavailable approval evidence is not approval.
