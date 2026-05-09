# Phase 9 — External Opportunity Sources

## Purpose

Phase 9 adds the ability to discover and import external opportunities from public job boards and freelance marketplaces. This enables SORIA operators to find potential prospects beyond manual entry.

## Supported Planned Sources

| Provider | Country | Source Kind | Description |
|----------|---------|-------------|-------------|
| **France Travail** (`france_travail`) | FR | `job` | French job board (ex-Pôle emploi) — DevOps, cloud, training roles |
| **Adzuna UK** (`adzuna_uk`) | GB | `job` | UK job aggregation — DevOps, cloud, cybersecurity roles |
| **Freelancer.com** (`freelancer`) | GLOBAL | `freelance_project` | Global freelance marketplace — project-based opportunities |

## Phase Plan

| Phase | Description | Status |
|-------|-------------|--------|
| **9A** | Mock-only foundation. Deterministic providers. Read-only search endpoints. No real API calls. No credentials. | ✅ Done |
| **9B** | Import candidates into `SourceRecord`, `Company`, and `Opportunity` | ✅ Done |
| **9C** | Cockpit external source search and import UX | ✅ Done |
| **9D** | SourceRecord / Import Provenance UX | ✅ Done |
| **10A** | Real external API configuration foundation | ✅ Done (see phase-10 docs) |
| **10B** | France Travail real connector skeleton | ✅ Done (see phase-10 docs) |
| **10C** | Wire real France Travail search behind EXTERNAL_SOURCES_MODE | ✅ Done (see phase-10 docs) |
| **10D** | Phase 10 closure documentation | ✅ Done (see phase-10 docs) |
| **11A** | Imported Opportunity Review Workflow — imported opportunities get `imported_pending_review` status, visible in Cockpit, filterable by status. Duplicate imports preserve existing status. | ✅ Done |
| **11B** | Imported Opportunity Review UX — status labels render human-readable text in list/show views, `imported_pending_review` highlighted with warning badge in list, status filter choices reordered to group review workflow path (`imported_pending_review` → `interesting` → `not_relevant` → `draft_needed`). | ✅ Done |

---

## Phase 9A — Mock-Only Foundation

### Architecture

Each external source is modelled as a **provider class** registered in a global provider registry (`backend/app/services/external_sources.py`). The registry pattern mirrors the existing AI provider abstraction.

```
ExternalSourceProvider (base class)
├── FranceTravailMockProvider   — france_travail
├── AdzunaUkMockProvider        — adzuna_uk
└── FreelancerMockProvider      — freelancer
```

### Service Functions

All in `backend/app/services/external_sources.py`:

- `list_external_source_providers()` — return info for every registered provider
- `get_external_source_provider(name)` — resolve a provider by name (raises `ValueError` if unknown)
- `search_external_opportunities(name, query, location, limit)` — search a single provider
- `search_multiple_external_sources(providers, query, location, limit)` — search multiple providers

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/external-sources/providers` | List all providers with diagnostics |
| `GET` | `/api/v1/external-sources/search` | Combined search across multiple providers |
| `GET` | `/api/v1/external-sources/{provider}/search` | Search a single provider |

### Constraints

- **No real external API calls** — all providers are deterministic mocks
- **No API keys, secrets, or credentials**
- **No database mutations** — all endpoints are read-only
- **No automated outreach or email sending**
- `query` parameter is required and must not be blank
- `limit` parameter must be between 1 and 50

### Mock Provider Behavior

- **FranceTravailMockProvider**: Returns 6 French job candidates (DevOps, cloud architect, trainer, security engineer, Kubernetes admin, digital learning PM). Location filter matches against the candidate's city. Language is `fr`. Contract types include CDI and CDD.
- **AdzunaUkMockProvider**: Returns 6 UK job candidates (DevOps engineer, cloud architect, cyber security analyst, senior DevOps, cloud security engineer, IT trainer). Location filter matches against city. Language is `en`. Contract types include `permanent` and `contract`.
- **FreelancerMockProvider**: Returns 6 freelance project candidates (Kubernetes setup, AWS automation, security audit, CI/CD pipeline, training material, platform consulting). All include `budget_min`, `budget_max`, and `budget_currency`. Location filter checks both `location` and `country`.

All candidates include `raw_payload` containing the full source data dict.

### Human Validation

Human validation remains mandatory for all imported candidates (Phase 9B+). No automated actions are taken on discovered opportunities.

### Key Files

- `backend/app/schemas/external_source.py` — Pydantic schemas
- `backend/app/services/external_sources.py` — Provider registry, mock providers, service functions
- `backend/app/api/v1/endpoints/external_sources.py` — API endpoints
- `backend/tests/test_phase9a.py` — Phase 9A tests

---

## Phase 9B — Controlled Import

### Purpose

Add the ability to import one external opportunity candidate into SORIA internal data (SourceRecord, Company, Opportunity) with proper deduplication and provenance tracking.

### Architecture

```
ExternalOpportunityCandidate
       │
       ▼
import_external_candidate(candidate, db)
       │
       ├── Provider validation (must be in PROVIDER_REGISTRY)
       ├── Deduplication (SourceRecord.source_name + external_id)
       ├── Company lookup/create (by name + country)
       ├── Opportunity create (with provenance notes)
       └── SourceRecord create (with raw_payload + processing_notes)
```

### Endpoint

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/external-sources/import-candidate` | Import one candidate into SourceRecord, Company, and Opportunity |

**Request body**: `ExternalOpportunityCandidate` schema
**Response**: `ImportExternalCandidateResponse` with:
- `source_record`, `company`, `opportunity` — serialized records
- `created_source_record`, `created_company`, `created_opportunity` — boolean flags
- `duplicate_detected` — boolean
- `message` — human-readable result summary

### SourceRecord Provenance

Each import creates a `SourceRecord` with:
- `source_type` = `SourceType.france_travail` for france_travail provider, `SourceType.other` otherwise
- `source_name` = provider name (e.g. "france_travail", "adzuna_uk")
- `external_id` = candidate's external ID
- `raw_payload` = full candidate payload as JSON
- `imported_at` = UTC timestamp of import
- `processed` = `True`
- `processing_notes` mentions created/reused Company and Opportunity IDs

### Company Reuse/Create

- If `candidate.company_name` is present: look up existing `Company` by exact name + country match
- If found: reuse (no new Company created)
- If not found: create a new `Company` with `status=new`
- If `company_name` is missing: create a fallback `"Unknown External Company - {provider}"`

### Opportunity Create

- `title` = candidate title
- `description` = candidate description
- `source` = `SourceType.france_travail` only for france_travail provider, otherwise `SourceType.other`
- `source_url` / `source_published_at` / `location` passed through
- `language` = candidate language or default (`"fr"` for france_travail, `"en"` otherwise)
- `status` = `new`, `priority` = `medium`
- `opportunity_type` = `devops_cloud` if DevOps/cloud keywords found, otherwise `other`
- `notes` includes provenance: provider, external_id, source_kind, country, contract_type, remote_type, budget

### Duplicate Prevention

- Deduplication key: `(SourceRecord.source_name, SourceRecord.external_id)`
- If an existing `SourceRecord` with matching key and `processed=True` exists:
  - Look for an `Opportunity` whose notes contain `provider=<name>` and `external_id=<id>`
  - If found: return existing records, mark `duplicate_detected=True`, create nothing new
  - If not found: create Opportunity but reuse existing SourceRecord
- If no SourceRecord exists: perform full fresh import

### Constraints (Phase 9B)

- **No real external API calls** — operates only on provided candidate data
- **No outreach / no drafts / no follow-ups / no compliance events**
- Only creates: SourceRecord, Company, Opportunity
- Unknown provider returns HTTP 400
- Invalid/blank required fields return validation error

### Key Files

- `backend/app/schemas/external_source.py` — `ImportExternalCandidateResponse`
- `backend/app/services/external_sources.py` — `import_external_candidate()` service function
- `backend/app/api/v1/endpoints/external_sources.py` — `POST /import-candidate` endpoint
- `backend/tests/test_phase9b.py` — Phase 9B tests (31 tests)

---

## Phase 9D — SourceRecord / Import Provenance UX

### Purpose

Make SourceRecord import provenance visible in the SORIA Cockpit. Adds a read-only API and a Cockpit resource for browsing and inspecting import records.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/source-records` | List source records (paginated, filterable) |
| `GET` | `/api/v1/source-records/{id}` | Get a single source record |

**List filters:** `skip`, `limit`, `source_name`, `source_type`, `external_id`, `processed`, `search`

**Search matches against:** `source_name`, `external_id`, `source_url`, `processing_notes`

### Schema — SourceRecordRead

Exposes all model fields plus two computed fields derived from `processing_notes`:

| Field | Source |
|-------|--------|
| `id`, `source_type`, `source_name`, `source_url`, `external_id` | Direct model fields |
| `raw_payload` | Direct model field (JSON) |
| `imported_at`, `processed`, `processing_notes` | Direct model fields |
| `created_at`, `updated_at` | Base model timestamps |
| `linked_company_id` | Extracted from `processing_notes` via pattern `"Company <uuid> ("` |
| `linked_opportunity_id` | Extracted from `processing_notes` via pattern `"Opportunity <uuid> ("` |

If parsing fails, linked IDs return `null`.

### Constraints

- **Read-only** — no POST, PATCH, or DELETE endpoints
- **No database mutations** — endpoints only query SourceRecord table
- **No side effects** — endpoints do not create MessageDraft, FollowUp, or ComplianceEvent

### Cockpit Resource

- Resource name: `source-records`
- **List** with filters: search, source_name, source_type, external_id, processed
- **Show** displays all fields, raw_payload as formatted JSON, linked_company_id/opportunity_id with navigation buttons
- Alert banner explaining read-only provenance semantics

### Key Files

- `backend/app/schemas/source_record.py` — `SourceRecordRead`, `SourceRecordListResponse`
- `backend/app/api/v1/endpoints/source_records.py` — read-only REST endpoints
- `frontend/cockpit/src/resources/sourceRecords/SourceRecordList.tsx` — list view
- `frontend/cockpit/src/resources/sourceRecords/SourceRecordShow.tsx` — show view
- `frontend/cockpit/src/App.tsx` — resource registration
- `backend/tests/test_phase9d.py` — Phase 9D tests (21 tests)

---

## Phase 11A — Imported Opportunity Review Workflow

### Purpose

Imported external opportunities must be clearly identifiable as items waiting for human review before outreach or draft usage. This is an MVP stabilization step — not a new connector phase.

### Changes

- **New `OpportunityStatus.imported_pending_review`** enum value added to `backend/app/core/enums.py`
- **`_create_opportunity()`** in `backend/app/services/external_sources.py` now sets status to `imported_pending_review` instead of `new`
- **Duplicate imports** preserve the existing opportunity status (not overwritten)
- **Scoring** does not auto-advance `imported_pending_review` opportunities (only `new` status is auto-advanced to `scored`)
- **Status filtering** works via the existing `GET /api/v1/opportunities?status=imported_pending_review` API
- **Cockpit UX** updated: `imported_pending_review` appears in all status choice lists (list, create, edit)

### Review Workflow

```
Import → status=imported_pending_review
              │
              ▼
       Human reviews opportunity
              │
              ├── Change status to "interesting" → proceed with scoring/draft
              ├── Change status to "not_relevant" → discard
              └── Keep as "imported_pending_review" → revisit later
```

### Key Design Decisions

- No database migration required — the new enum value is stored as a string in the existing `opportunities.status` column
- No new database columns or tables
- `EXTERNAL_SOURCES_MODE=mock` remains the safe default
- Adzuna UK and Freelancer live connectors are NOT activated
- Real external API calls are NOT activated by default

### Key Files

- `backend/app/core/enums.py` — `OpportunityStatus.imported_pending_review`
- `backend/app/services/external_sources.py` — `_create_opportunity()` uses `imported_pending_review`
- `frontend/cockpit/src/resources/opportunities/OpportunityList.tsx` — status filter includes new value
- `frontend/cockpit/src/resources/opportunities/OpportunityEdit.tsx` — status choices include new value
- `frontend/cockpit/src/resources/opportunities/OpportunityCreate.tsx` — status choices include new value
- `backend/tests/test_phase11a.py` — Phase 11A tests (new import, duplicate preservation, search read-only, Phase 9B/10C safety)
