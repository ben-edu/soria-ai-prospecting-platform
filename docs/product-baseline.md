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

## Planned (Future Phases)

- Real external AI provider integration (OpenAI/Claude)
- LLM-based opportunity scoring and qualification
- External data enrichment (Hunter, Dropcontact)
- Company website scraping and analysis
- LinkedIn opportunity discovery
- Import external candidates into SourceRecord, Company, Opportunity (Phase 9B)
- Real external source connectors (Phase 9C/9D/9E)
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
