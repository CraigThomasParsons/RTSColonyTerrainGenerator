# 02 — Canonical remote layout restored

**What to build:** This checkout has both remotes the lifecycle scripts expect — a canonical Gitea `origin` and a GitHub mirror `github` — so `start_gitea_issue.py` / `end_gitea_issue.py` and the Gitea→GitHub draft mirror run without hand-editing.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `git remote` shows a canonical Gitea remote and a distinct GitHub mirror remote per the scripts' contract.
- [ ] A lifecycle script that requires the Gitea remote runs far enough to prove the wiring (dry-run acceptable).
- [ ] The sync/mirror direction is documented so no one force-pushes the wrong way.
