# How an AI Should Add a MapGenerator Stage

You are an AI agent tasked with adding a new stage to the MapGenerator pipeline.

This is a **file-based, systemd-driven, deterministic pipeline**.
Your job is to integrate cleanly, not creatively break structure.

Follow this document exactly unless explicitly instructed otherwise.

---

## 1. Core Rules (Non-Negotiable)

- Every stage is isolated
- Stages communicate ONLY via files
- Bash is the orchestration layer
- systemd automates execution
- Language choice is flexible
- Output must be deterministic
- Playability overrides purity

You may create, destroy, analyze, or modify world data.
You may invent infrastructure if needed.
You may NOT invent new pipeline conventions.

---

## 2. Required Directory Structure

You MUST create the following structure:

StageName/
├── inbox/
├── outbox/
├── archive/
├── failed/
├── debug/
├── bin/
├── docs/
├── systemd/
├── install.sh
└── README.md


Optional directories are allowed, but these are mandatory.

---

## 3. Inbox / Outbox Contract

### Inbox
- Contains input jobs
- Each file = one job
- Files are immutable
- Do NOT write to inbox

### Outbox
- Contains authoritative results
- Only data meant for downstream stages
- No debug artifacts
- No temporary files

If you cannot clearly describe your inbox → outbox contract,
you are not ready to implement the stage.

---

## 4. Processing Model

You MUST implement:

- One job per input file
- Stateless processing
- No shared memory
- No background daemons
- No databases
- No sockets
- No network access

Processing flow:

1. systemd detects a file in inbox
2. systemd triggers a service
3. A bash wrapper runs the job
4. Output written to outbox
5. Input moved to archive or failed

Files ARE the API.

---

## 5. Bash Wrapper (Mandatory)

Regardless of language used, you MUST provide a bash entrypoint.

Typical name:


bin/consume_queue_job.sh


This script is responsible for:
- Validating input
- Invoking the core logic
- Handling errors
- Logging
- Moving files
- Exiting with correct status

Do NOT embed systemd logic in your core code.

---

## 6. Language Usage

Allowed languages include (but are not limited to):

- Bash
- Rust
- Go
- Python
- PHP
- C#
- C / C++

Rules:
- Your language must be callable from bash
- Binaries go in `bin/`
- Source code may live anywhere inside the stage directory
- The pipeline does not care about your language

Bash is the glue.
Everything else is an implementation detail.

---

## 7. systemd Integration (Required)

You MUST provide:

- One `.path` unit watching `inbox/`
- One `.service` unit executing the bash wrapper

Use **user-level systemd**, not system-level.

Your service MUST:
- Be `Type=oneshot`
- Exit cleanly
- Never block

---

## 8. install.sh (Required)

You MUST provide an `install.sh` script.

This script must:
- Create needed directories
- Symlink systemd units
- Reload systemd
- Enable the `.path` unit

Example pattern:

```bash
#!/usr/bin/env bash
set -e

STAGE_DIR=~/Code/RTSColonyTerrainGenerator/MapGenerator/StageName
SYSTEMD_DIR=~/.config/systemd/user

mkdir -p "$SYSTEMD_DIR"

ln -sf "$STAGE_DIR/systemd/stage.service" "$SYSTEMD_DIR/"
ln -sf "$STAGE_DIR/systemd/stage.path" "$SYSTEMD_DIR/"

systemctl --user daemon-reload
systemctl --user enable --now stage.path

You may adapt names, but not behavior. 
```
---

9. Debug Output Rules

- Debug artifacts go ONLY in debug/

- Debug output is human-facing

- Debug output is optional

- Debug output is NOT consumed by automation

- Debug output may be deleted at any time

If automation depends on debug output, you are doing it wrong.

---

10. Failure Handling

On failure:

- Move input file to failed/

- Log the reason

- Do NOT retry automatically unless explicitly designed

Failed jobs are expected and acceptable.
---
11. Documentation Requirements

You MUST write:

docs/context.md

Explain:

- Why this stage exists

- What problem it solves

- Where it fits in the pipeline

README.md

Explain:

- Inputs

- Outputs

- Processing logic

- Failure modes

- Assumptions

Documentation is part of the API.

---

12. Determinism Expectations

Unless explicitly instructed otherwise:

- Same input = same output

- Seeded randomness only

- No clocks

- No entropy

- No external state

If determinism is broken, document it clearly.

---

14. Final Self-Check Before Submission

Before considering the stage complete, verify:

 - Directory structure exists

 - inbox → outbox contract is clear

 - Bash wrapper exists

 - systemd units exist

 - install.sh works

 - Docs are written

 - Stage can be removed without breaking others

If all checks pass, the stage is compliant.

---

### Closing Statement

This system values:

- Clarity over cleverness

- Files over services

- Determinism over magic

- Playability over purity