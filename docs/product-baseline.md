# Product Baseline — SORIA AI Prospecting Platform

## Purpose

Automate and structure SORIA's prospecting process while maintaining full human control over external communications.

## Scope (Bootstrap Phase)

- [x] FastAPI backend skeleton
- [x] Database models (13 tables)
- [x] Enums for all classification fields
- [x] Alembic migrations
- [x] Basic CRUD API endpoints
- [x] Seed data script
- [x] Dockerfile
- [x] Documentation

## Planned (Future Phases)

- LLM-based opportunity scoring and qualification
- AI message generation with human validation
- External data enrichment (Hunter, Dropcontact)
- Company website scraping and analysis
- LinkedIn opportunity discovery
- France Travail / job board integration
- Email sending with tracking
- OpenProject work package sync
- Academy/Moodle API integration
- Dashboard and reporting
- Kubernetes deployment

## Core Rules

1. No uncontrolled automated messages — human must approve every external communication
2. All contact collection must be logged for compliance
3. Opt-out requests must be respected immediately
4. Email verification before first contact
