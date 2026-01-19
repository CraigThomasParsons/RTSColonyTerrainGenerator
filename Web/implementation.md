# Web Dashboard Implementation Plan

This document outlines the implementation strategy for a read-only web dashboard for BandcampSync, utilizing an LCARS-inspired design. The dashboard observes system state through filesystem and systemd monitoring without persistent storage.

## Overview

The dashboard provides real-time visibility into:
- Systemd service status
- Job queue status (files in Sync/inbox/)
- Application logs (Sync/logs/)
- System reconciliation triggers

## Architecture Summary

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Backend | Python Flask | Lightweight, matches repo language |
| Frontend | Vanilla HTML/CSS/JS | No build dependencies, static assets |
| Communication | HTTP polling (3s interval) | Simple, stateless |
| Data Source | Filesystem & systemd | No database dependency |

## Directory Structure

Web Dashboard Implementation Plan
Goal Description
Build a visual, read-only web dashboard for "BandcampSync". The dashboard will observe the state of the system by reading the filesystem (Sync/inbox, Sync/logs) and systemd status, without using databases or hidden state. It will use an LCARS-inspired design.

## Architecture
 - Backend: Python (Flask). Easy to deploy, matches existing repo language availability.
 - Constraint Check: "Small local web server".
 - Frontend: Vanilla HTML/CSS/JS. No build steps, no frameworks.
 - Constraint Check: "Static frontend + JSON endpoints".
 - Communication: Polling (every 3s).
 - Data Source: Direct filesystem reads.
## Features
 - Systemd Service Status: Show current states of relevant services.
 - Job Queue Status: Show counts and details of jobs in Sync/inbox/.
 - Application Logs: Tail logs from Sync/logs/.

Proposed Changes:  
Top-Level Directory
Create Web/ with:

server/ (Python code)
 - ui/ (HTML/CSS/JS assets - served by Flask as static)

docs/ (Documentation)
README.md
Backend (Web/server/)

[NEW] app.py:

# Serve ../ui/index.html as root.
- GET /api/status: Aggregated system status (systemd service states).
- GET /api/queue: Counts and details of jobs in Sync/inbox/*.
- GET /api/logs: Tail of Sync/logs/*.log.
