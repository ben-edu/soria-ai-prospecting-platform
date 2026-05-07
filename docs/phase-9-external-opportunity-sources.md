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
| **9B** | Import candidates into `SourceRecord`, `Company`, and `Opportunity` | 📅 Planned |
| **9C/9D/9E** | Real connector implementations for each provider | 📅 Planned |

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
