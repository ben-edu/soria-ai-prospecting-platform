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
- [x] AI-assisted message draft generation with human validation (mock_ai provider, provider abstraction, prompt builder, diagnostics, Cockpit UX, human review workflow)
- [x] External opportunity sources foundation (Phase 9A — mock-only, france_travail, adzuna_uk, freelancer)
- [x] External candidate controlled import (Phase 9B — SourceRecord, Company, Opportunity, duplicate prevention, provenance tracking)
- [x] Real external API connector architecture (Phase 10 — configuration foundation, France Travail connector, live gating, Adzuna UK connector, Freelancer connector, mock-mode safety preserved)
- [x] Imported opportunity review workflow (Phase 11A — imported_pending_review status, Cockpit visibility, status filtering)
- [x] Imported opportunity review UX (Phase 11B — human-readable status labels, warning badge in list, status choices reordered for review workflow)

## Planned (Future Phases)

- Real external AI provider integration (OpenAI/Claude)
- LLM-based opportunity scoring and qualification
- External data enrichment (Hunter, Dropcontact)
- Company website scraping and analysis
- LinkedIn opportunity discovery
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
