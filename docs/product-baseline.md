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

## MVP Completion Status

The MVP minimal viable product workflow is complete and validated in production runtime testing. The following end-to-end flow has been verified:

```
External Source Search
  → Import Candidate
    → imported_pending_review
      → Human Review → interesting
        → AI Draft Preview (read-only)
          → Generate AI Draft
            → Submit for Review
              → Approve
                → Mark Sent Manually
                  → follow_up_needed
                    → Compliance Events: message_generated, message_approved, message_sent
```

| Capability | Status |
|-----------|--------|
| External opportunity discovery (mock) | ✅ Complete |
| Candidate import with deduplication | ✅ Complete |
| Import provenance (SourceRecord) | ✅ Complete |
| Imported opportunity review workflow | ✅ Complete |
| AI-assisted draft generation (mock_ai) | ✅ Complete |
| Human review workflow (submit → approve/reject → mark sent) | ✅ Complete |
| Follow-up scheduling | ✅ Complete |
| Compliance event traceability | ✅ Complete |
| Real API connector architecture (France Travail, Adzuna UK, Freelancer) | ✅ Implemented, gated |
| Real AI provider integration (OpenAI/Claude) | ❌ Not started |

> **Note:** Runtime validation test data is present in the production database and has not been cleaned up.

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
