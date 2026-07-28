# Nyx recon — where the existing Hermes instance lives

Written 2026-07-20. Purpose: record what was found while trying to locate the
maintainer's existing **Nyx** Hermes agent, so that duplicating it into a new
instance (**Daedalus**, for personal coding work) does not repeat this search.

Status: **Nyx not yet located directly — blocked on QNAP host access.** Strong
evidence it runs on the QNAP host in Container Station (see below).

## The NAS is two machines, not one

This matters because "SSH into the NAS as craigpars" reaches only the first:

1. **`ubuntu-2404` VM — `192.168.2.48`** (Ubuntu Linux Station, a VM inside QNAP
   Virtualization Station). `craigpars` SSH (key auth, passwordless) works here.
   Runs: Gitea + gitea-postgres (podman), the AMPB app/reverb/queue/scheduler
   containers, PlexSonarBridge, ThePostalService, syncthing/gluetun/qbittorrent,
   the Gitea Actions runners. **Nyx is NOT here** — no matching process, systemd
   unit, podman container, crontab entry, config, or home directory; nothing in
   `.bash_history`.

2. **QNAP host — `nas32a387` / `192.168.2.47`** (the physical NAS; the `.48` VM
   runs on top of it). This is where Container Station lives. SSH here is
   **password-gated** — `craigpars@192.168.2.47` and `admin@192.168.2.47` both
   return `Permission denied (publickey,password,keyboard-interactive)`; the
   agent's key is not authorized and non-interactive login can't supply a
   password. **Nyx almost certainly runs here** (a Hermes daemon as a Container
   Station container), but it could not be confirmed from this session.

The `.48` VM mounts only Plex media shares from `//192.168.2.47/Plex/*` (Movies,
TV, Music, Photos, Comics, Other) plus an empty `Vault` — no Container Station
config is exposed over CIFS, so the container definition can't be read from the
VM either.

## Also ruled out

- Local workstation (`cachyos`, `192.168.2.14`): no Nyx/Hermes/Discord references
  in shell history or `~/Code`. (Grep hits for "hermes" are the unrelated Facebook
  Hermes JS engine inside `package-lock.json`/`vendor` trees.)
- `159.89.50.97` (`elasticgun.prod`, a cloud droplet in `known_hosts`) was not
  checked — Nyx was described as living "on my QNAP NAS server," so the QNAP host
  is the lead, not the droplet. Note it here only so a future session can rule it
  in/out if the QNAP host turns up empty.

## To actually reach Nyx (pick one)

- **Authorize the agent on the QNAP host:** add this account's SSH public key
  (`~/.ssh/id_ed25519.pub` on the workstation) to the QNAP host's
  `authorized_keys` for a shell-capable user, OR provide the password
  interactively. Then: `ssh <user>@192.168.2.47`, and inspect Container Station
  (`docker ps -a` / the Container Station app data path, typically under
  `/share/Container/container-station-data/` or `/share/ZFS*/…`).
- **Or, from the QNAP web UI:** open Container Station, find the Nyx container,
  and read off its image, env vars, mounted volumes, and (if compose-managed) its
  `docker-compose.yml`. That definition is exactly what Daedalus duplicates.

## What "Nyx" is (context)

Per the maintainer: a **Hermes agent** — the Nous Research self-hosted,
self-improving personal-agent daemon (multi-platform messaging incl. Discord,
cron, tools, sub-agent orchestration) — set up for work tasks. **Daedalus** is to
be a second, renamed instance of the same thing, pointed at personal coding work
and driving the worker loop described in [`01-worker-loop-design.md`](01-worker-loop-design.md).
See also the coordinator design this pairs with: AMPB
`docs/plans/the-night-crew.md`.
