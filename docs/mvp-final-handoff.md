# MVP Final Handoff — SORIA AI Prospecting Platform

**Phase:** 11F — Final MVP Closure / Handoff
**Date:** 2026-05-10
**Status:** ✅ MVP Completed and Demonstrable

---

## What SORIA Is

SORIA is an AI-augmented prospecting platform that helps training and workforce development organizations discover, evaluate, and engage with potential business opportunities. It provides:

- **External opportunity discovery** — Search job boards and freelance marketplaces for potential prospects
- **Controlled import with provenance** — Bring candidates into SORIA with full audit trail
- **Human-driven review workflow** — Operators evaluate imported opportunities before any action
- **AI-assisted draft generation** — Generate message drafts with human validation built in
- **Compliance traceability** — Every action logged for audit

SORIA is not an automated outreach system. It is a **human-in-the-loop** tool where every external communication requires explicit operator approval.

---

## MVP Scope Completed

The MVP implements a complete end-to-end workflow from external opportunity discovery through to compliance-tracked manual send:

| Capability | Status |
|-----------|--------|
| FastAPI backend skeleton with database models (13 tables) | ✅ Complete |
| CRUD API endpoints for all core entities | ✅ Complete |
| External opportunity discovery (mock mode) | ✅ Complete |
| Three external provider abstractions (France Travail, Adzuna UK, Freelancer) | ✅ Complete |
| Real API connector architecture (gated, not active by default) | ✅ Complete |
| Candidate import with deduplication and provenance | ✅ Complete |
| Imported opportunity review workflow (`imported_pending_review`) | ✅ Complete |
| AI-assisted message draft generation (`mock_ai`) | ✅ Complete |
| Human review workflow (submit → approve/reject → mark sent) | ✅ Complete |
| Follow-up scheduling (7-day auto follow-up) | ✅ Complete |
| Compliance event traceability | ✅ Complete |
| Cockpit frontend for all workflows | ✅ Complete |
| Seed data and test scripts | ✅ Complete |
| Dockerfile and container build | ✅ Complete |
| MVP user guide | ✅ Complete |
| Production deployment (Kubernetes) | ✅ Complete |

### End-to-End Workflow

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

---

## Production Runtime Status

| Aspect | Status |
|--------|--------|
| **Frontend (Cockpit)** | Deployed and accessible |
| **Backend (FastAPI)** | Deployed and responding |
| **Database (PostgreSQL)** | Online, migrated, seeded |
| **External sources mode** | `mock` (safe default) |
| **AI provider** | `mock_ai` (deterministic, no external AI API) |
| **Real API credentials** | Not configured in production environment |
| **CI/CD (Jenkins)** | Pipeline healthy, last build ✅ |
| **Container registry (Harbor)** | Images pushed and tagged |
| **Kubernetes (K3S)** | Pods running, no restarts |

> **Critical fact:** Production runs entirely in mock mode. Real API connectors for France Travail, Adzuna UK, and Freelancer are implemented but inactive. Switching to live mode requires setting `EXTERNAL_SOURCES_MODE=live` and provisioning valid API credentials per provider.

---

## Validated End-to-End Scenario

The full MVP workflow was validated against production on 2026-05-10. The following scenario was executed and verified:

| Step | Action | Result |
|------|--------|--------|
| 1 | External source search via Cockpit | ✅ Results returned |
| 2 | Import candidate from search results | ✅ SourceRecord + Company + Opportunity created |
| 3 | Verify `imported_pending_review` status | ✅ Opportunity visible with warning badge |
| 4 | Human review → set to `interesting` | ✅ Status updated |
| 5 | AI Draft Preview (read-only) | ✅ Dialog rendered without data creation |
| 6 | Generate AI Draft | ✅ MessageDraft + `message_generated` compliance event |
| 7 | Submit for Review | ✅ Draft status → `needs_review` |
| 8 | Approve Draft | ✅ Draft status → `approved`, compliance event `message_approved` |
| 9 | Mark Sent Manually | ✅ Draft status → `sent_manually`, compliance event `message_sent`, follow-up scheduled |
| 10 | Verify `follow_up_needed` | ✅ Opportunity status synced |

All validation passed without errors, regressions, or unexpected behavior.

---

## Human Validation and Safety Principle

SORIA's design is governed by a strict **human-in-the-loop** principle:

1. **No automated external messages** — Every external communication requires explicit human approval. There is no code path that sends an email, API message, or any external communication automatically.

2. **No automatic email integration** — The platform does not connect to any email provider (SMTP, SendGrid, Mailgun, etc.). "Mark Sent Manually" is a record-keeping action only.

3. **Mock mode by default** — External source and AI providers are configured to safe mock defaults. Real APIs require explicit operator action to enable.

4. **All imports are logged** — Every external candidate import creates a SourceRecord with full provenance data for audit.

5. **Imported opportunities require review** — External imports land in `imported_pending_review` status and must be manually advanced by a human operator.

---

## Demo Data Intentionally Kept

One controlled demo scenario is intentionally retained in production:

| Entity | Identifier |
|--------|-----------|
| **Opportunity** | `d7921f56-5521-4e53-b773-4b320e4c8fb9` |
| **MessageDraft** | `f4549033-b432-4fe8-bf50-e80228472290` |
| **SourceRecord external_id** | `phase11c-scenario-20260510T080857Z` |

This data serves as:
- A live demonstration of the complete workflow
- Reference data for operator training
- Validation that the full pipeline endures deployments

No additional test data has been created beyond this controlled scenario.

---

## How to Demonstrate the Product

### Prerequisites

- Access to the SORIA Cockpit URL
- Valid operator credentials

### Demonstration Walkthrough (15-20 minutes)

1. **External search** (2 min)
   - Navigate to External Sources resource
   - Select a provider (e.g., France Travail)
   - Search for "DevOps"
   - Review mock results

2. **Import candidate** (1 min)
   - Click Import on a candidate
   - Verify success response with SourceRecord, Company, Opportunity links

3. **Review imported opportunity** (2 min)
   - Navigate to Opportunities
   - Filter by status `imported_pending_review`
   - Open the imported opportunity
   - Note the warning badge and provenance information

4. **Mark as interesting** (1 min)
   - Edit the opportunity
   - Set status to `interesting`

5. **AI draft preview** (1 min)
   - Click AI Draft Preview
   - Show the read-only dialog

6. **Generate AI draft** (1 min)
   - Click Generate AI Draft
   - Verify compliance event created

7. **Submit for review** (1 min)
   - Open Message Drafts
   - Open the generated draft
   - Click Submit for Review

8. **Approve draft** (1 min)
   - Click Approve
   - Verify compliance event `message_approved`

9. **Mark as sent manually** (1 min)
   - Click Mark Sent Manually
   - Verify compliance event `message_sent`
   - Verify opportunity status → `follow_up_needed`

10. **Compliance audit** (2 min)
    - View Compliance Events
    - Verify all three events: `message_generated`, `message_approved`, `message_sent`

Alternatively, the **MVP User Guide** (`docs/mvp-user-guide.md`) provides detailed step-by-step instructions with screenshots.

---

## Known Limitations

| Area | Limitation |
|------|-----------|
| **External sources** | Running in mock mode — real API credentials not enabled in production |
| **AI drafts** | Using `mock_ai` deterministic provider — no real OpenAI/Claude integration |
| **Email sending** | No email integration — all sends are recorded manually |
| **Demo data** | One controlled demo scenario persists in the production database |
| **External enrichment** | No Hunter.io, Dropcontact, or website scraping |
| **Opportunity scoring** | Basic scoring only — no LLM-based qualification |
| **LinkedIn discovery** | Not implemented |
| **Dashboard/reporting** | Not implemented |
| **OpenProject sync** | Not implemented |

---

## Backlog / Next Possible Improvements

The following improvements are candidates for future phases:

### Short-term (incremental)

- **Real AI provider integration** (OpenAI/Claude) — Replace `mock_ai` with real LLM-based draft generation
- **LLM-based opportunity scoring** — Use AI to qualify and score imported opportunities
- **External data enrichment** (Hunter.io, Dropcontact) — Enrich company and contact data
- **Company website scraping** — Automate company research from imported URLs

### Medium-term

- **Email sending with tracking** — Integrate with an email provider for actual send capability
- **LinkedIn opportunity discovery** — Add LinkedIn as an external source
- **Dashboard and reporting** — KPIs, pipeline visualization, activity metrics
- **OpenProject work package sync** — Create work packages from opportunities

### Longer-term

- **Academy/Moodle API integration** — Extend to training/academy sector
- **Automated follow-up reminders** — Proactive notifications for pending follow-ups
- **Multi-user roles and permissions** — Granular access control
- **Advanced analytics** — Pipeline analytics, conversion tracking, forecasting

---

## Final Statement

> **The SORIA AI Prospecting Platform MVP is completed and demonstrable.**
>
> The platform implements a complete, validated end-to-end workflow from external opportunity discovery through human review, AI-assisted draft generation, approval, and compliance-tracked manual send. All core capabilities are deployed in production, tested, and operational.
>
> Real API connectors for France Travail, Adzuna UK, and Freelancer are implemented but gated behind configuration — they are not active in production without explicit operator action. The platform runs in safe mock mode by default.
>
> The human-in-the-loop principle is enforced by design: no code path can send automated external messages. Every action in the workflow is logged for compliance.
>
> **Phase 11F represents the final closure milestone for the SORIA MVP bootstrap.**

---

## Post-MVP Update — Phase 12B (2026-05-12)

Phase 12B added a read-only **French Freelance Source Catalog** — a reference directory of five French freelance platforms (Free-Work, Codeur.com, LeHibou, Malt, Comet) displayed in the Cockpit. These are informational entries only: they are not searchable, importable, scrapable, or messageable from within SORIA.

See [Phase 12B documentation](phase-12b-french-freelance-source-catalog.md) for full details.

---

## Post-MVP Update — Phase 12C (2026-05-12)

Phase 12C added two new real external source providers — **Adzuna France** (`adzuna_fr`) and **Adzuna Germany** (`adzuna_de`). These are fully registered, searchable, importable providers sharing the existing `AdzunaUKAPIClient` with a per-country code parameter. They reuse the same `ADZUNA_UK_APP_ID` / `ADZUNA_UK_APP_KEY` credentials. No migration, no model change, and no frontend work was needed.

For full details, including the architecture decision (multiple providers sharing a single client), provider-vs-catalog distinction, endpoint behavior, safety governance, production validation, and test coverage, see the dedicated document:

► [Phase 12C — Adzuna FR/DE Providers](phase-12c-adzuna-fr-de-providers.md)

---

## Reference Documents

| Document | Description |
|----------|-------------|
| [Product Baseline](product-baseline.md) | Product scope, roadmap, core rules |
| [MVP User Guide](mvp-user-guide.md) | Step-by-step operator instructions |
| [Phase 9 — External Sources](phase-9-external-opportunity-sources.md) | External source architecture and implementation |
| [Phase 10 — Real External API Foundation](phase-10-real-external-api-foundation.md) | Real API connector architecture |
| [Phase 12B — French Freelance Source Catalog](phase-12b-french-freelance-source-catalog.md) | French freelance platform reference directory |
| [Phase 12C — Adzuna FR/DE Providers](phase-12c-adzuna-fr-de-providers.md) | Adzuna France and Germany real external source providers |
