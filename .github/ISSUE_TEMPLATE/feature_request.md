---
name: Feature Request
about: Suggest an idea or propose a scoped feature for SWM-ICS
title: "[FEATURE] "
labels: ["enhancement"]
assignees: []
---

## Problem Statement
Is your feature request related to a problem or limitation? A clear and concise description of what the problem is. (e.g., "I'm always frustrated when...")

## Proposed Solution / Feature
A clear and concise description of what you want to happen and how it fits into the SWM-ICS architecture.

## Target Component / Layer
- [ ] Backend API / Services
- [ ] Database Schema & Migrations
- [ ] IoT Firmware (ESP32)
- [ ] MQTT Ingestion Pipeline
- [ ] Frontend Operations Dashboard
- [ ] Route Planning & Optimization
- [ ] ML Forecasting & Analytics

## Acceptance Criteria
- [ ] Requirement 1
- [ ] Requirement 2
- [ ] Contract compliance with `docs/integration.md` verified
- [ ] Automated tests included

## Architectural Invariants Check
- Does this maintain REST-only access for browser clients? (Yes/No)
- Does this keep device identity (`device_id`) decoupled from bin identity (`bin_id`)? (Yes/No)
- Are telemetry calculations kept server-authoritative? (Yes/No)

## Alternatives Considered
A clear and concise description of any alternative solutions or features you've considered.

## Additional Context
Add any other context, wireframes, mockups, or API payload designs here.
