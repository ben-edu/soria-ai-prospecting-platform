# Phase 12C — Adzuna France and Germany Providers

**Date:** 2026-05-12
**Status:** ✅ Merged, deployed, validated in production

---

## Objective

Extend the Adzuna external source provider to support France and Germany, giving SORIA operators the ability to search job listings from two additional European countries without requiring separate API integrations. This adds two new registered providers — `adzuna_fr` and `adzuna_de` — that share the existing `AdzunaUKAPIClient` with a per-country code parameter.

Phase 12C does **not** require:
- A database migration
- A database model change
- New frontend components (auto-discovered by Cockpit via `GET /api/v1/external-sources/providers`)
- New secret management (reuses existing ADZUNA_UK credentials)

---

## Why These Are Real External Source Providers

Adzuna France and Adzuna Germany are registered in `PROVIDER_REGISTRY` as real external source providers, distinct from the manual Source Catalog entries from Phase 12B. This means they are:

| Capability | Adzuna FR/DE | Phase 12B Catalog Entries |
|------------|-------------|--------------------------|
| Registered in `PROVIDER_REGISTRY` | ✅ Yes | ❌ No |
| Searchable via `GET /search` | ✅ Yes | ❌ No |
| Importable via `POST /import-candidate` | ✅ Yes | ❌ No |
| Creates `SourceRecord`, `Company`, `Opportunity` | ✅ Yes | ❌ No |
| Real API connector exists | ✅ Yes (shared `AdzunaUKAPIClient`) | ❌ No |
| `supports_real_api` | ✅ `True` | ❌ `false` |
| Land in `imported_pending_review` on import | ✅ Yes | N/A |
| Human review required before action | ✅ Yes (governance enforced by workflow) | ✅ Yes (by rule) |
| Purpose | Automated/assisted sourcing via SORIA | Manual reference directory |

### Provider Registry (after Phase 12C)

```
PROVIDER_REGISTRY (5 providers)
├── france_travail  — real, searchable, importable
├── adzuna_uk      — real, searchable, importable (existing)
├── adzuna_fr      — real, searchable, importable (new)
├── adzuna_de      — real, searchable, importable (new)
└── freelancer     — real, searchable, importable
```

### Source Catalog (Phase 12B, separate)

```
Source Catalog (read-only, not registered as providers)
├── free_work   ─┐
├── codeur       ├── Manual reference only
├── lehibou      ├── No search, no import
├── malt         ├── No real API
└── comet       ─┘
```

The catalog entries are **informational only** — they exist to tell operators *where* to look for French freelance opportunities manually, outside SORIA. The Adzuna providers are **fully functional data pipelines** — operators can search, browse, import, and review candidates entirely within the SORIA workflow.

---

## Architecture Decision: Multiple Providers, Shared Client

### Why not add a `country` parameter to the public API?

The external source architecture is provider-based: each provider is a registered class with its own metadata (label, country, language, diagnostics). The public API was designed around provider name routing (`/external-sources/{provider}/search`). Adding a `country` query parameter to the Adzuna UK endpoint would:

1. Break the uniform provider abstraction — other providers (France Travail, Freelancer) don't have country parameters
2. Require special-case routing logic in the API layer
3. Make diagnostics and provider discovery less transparent — a single provider entry would need to report multiple countries
4. Complicate the Cockpit UI auto-discovery, which relies on one provider = one search endpoint

### Chosen approach: multiple provider classes sharing a single client

Instead of creating separate API client modules per country, Phase 12C:

1. **Extends `AdzunaUKAPIClient`** with an optional `country_code` parameter (default `"gb"`) in `adzuna_uk_client.py`
2. **Creates two new mock provider classes** (`AdzunaFrMockProvider`, `AdzunaDeMockProvider`) in `external_sources.py`, both registered in `PROVIDER_REGISTRY`
3. **Shares credentials** — both new providers use the same `_credential_fields = ["ADZUNA_UK_APP_ID", "ADZUNA_UK_APP_KEY"]` as `AdzunaUkMockProvider`
4. **Routes live mode** through the same `AdzunaUKAPIClient` but instantiated with `country_code="fr"` or `country_code="de"`

```
Live-mode routing (EXTERNAL_SOURCES_MODE != "mock"):

AdzunaUkMockProvider.search()
  → AdzunaUKAPIClient(settings, country_code="gb").search_jobs()

AdzunaFrMockProvider.search()
  → AdzunaUKAPIClient(settings, country_code="fr").search_jobs()

AdzunaDeMockProvider.search()
  → AdzunaUKAPIClient(settings, country_code="de").search_jobs()
```

### Credential sharing

All three Adzuna providers (UK, France, Germany) use the same `ADZUNA_UK_APP_ID` and `ADZUNA_UK_APP_KEY` environment variables. This is possible because Adzuna issues a single set of API credentials that work across all country subdomains (`api.adzuna.com/v1/api/jobs/gb`, `api.adzuna.com/v1/api/jobs/fr`, `api.adzuna.com/v1/api/jobs/de`).

- **No new env vars were added** — the existing `ADZUNA_UK_APP_ID` and `ADZUNA_UK_APP_KEY` are reused
- **No `.env.example` changes** — existing documentation already covers these variables
- **Diagnostics accurately reflect** — if credentials are configured, all three Adzuna providers report `credentials_configured=true` and can route to live mode

### Backward compatibility

- `AdzunaUKAPIClient()` with no arguments defaults to `country_code="gb"` — existing Phase 10E code is unchanged
- `AdzunaUkMockProvider` is unchanged — same provider name, same class, same behavior
- All existing tests pass without modification

---

## Backend Endpoint Behavior

### Provider discovery

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/external-sources/providers` | Returns all 5 registered providers including `adzuna_fr` and `adzuna_de` |

Response diagnostics for the new providers:

```json
{
  "provider": "adzuna_fr",
  "label": "Adzuna France",
  "country": "FR",
  "source_kind": "job",
  "language": "fr",
  "supports_real_api": true,
  "credentials_configured": false,
  "safe_status": "mock",
  "safe_message": "Mock mode active. Real API credentials not configured."
}
```

```json
{
  "provider": "adzuna_de",
  "label": "Adzuna Germany",
  "country": "DE",
  "source_kind": "job",
  "language": "de",
  "supports_real_api": true,
  "credentials_configured": false,
  "safe_status": "mock",
  "safe_message": "Mock mode active. Real API credentials not configured."
}
```

### Single-provider search

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/external-sources/adzuna_fr/search?query=devops&limit=3` | Search Adzuna France — returns FR/fr candidates |
| `GET` | `/api/v1/external-sources/adzuna_de/search?query=devops&limit=3` | Search Adzuna Germany — returns DE/de candidates |

In mock mode (the default), each provider returns deterministic mock candidates with correct country/language/provider metadata:

- `adzuna_fr` returns 4 mock candidates with `country="FR"`, `language="fr"`, `provider="adzuna_fr"`
- `adzuna_de` returns 4 mock candidates with `country="DE"`, `language="de"`, `provider="adzuna_de"`

### Combined search

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/external-sources/search?providers=adzuna_uk,adzuna_fr,adzuna_de&query=devops` | Search across all three Adzuna countries simultaneously |

### Import

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/external-sources/import-candidate` | Import a candidate from any provider including `adzuna_fr` and `adzuna_de` |

Import creates:
- `SourceRecord` with `source_type=SourceType.other`, `source_name="adzuna_fr"` or `"adzuna_de"`
- `Company` with appropriate country
- `Opportunity` with status `imported_pending_review`

Duplicate detection works identically to other providers — importing the same `(provider, external_id)` pair twice is rejected.

---

## Safety & Governance

Phase 12C inherits all the safety guarantees of the existing external source architecture:

| Rule | How Enforced |
|------|-------------|
| No scraping | Adzuna API is the only data source — no HTML scraping, no undocumented endpoints |
| No automatic messaging | The import pipeline creates opportunities in `imported_pending_review` status. No code path sends automated external messages. |
| No migration needed | No database schema changes were required — new providers reuse existing models (SourceRecord, Company, Opportunity) |
| No database model change | Same tables, same columns, same enums — only new provider class code |
| Human review required | Imported opportunities land in `imported_pending_review`. Human operator must explicitly advance them. |
| Mock mode by default | `EXTERNAL_SOURCES_MODE=mock` — no live API calls without explicit operator action |
| No new credentials | Reuses existing `ADZUNA_UK_APP_ID` / `ADZUNA_UK_APP_KEY` — no additional secrets to manage |
| Credential sharing is safe | All three providers share credentials; live mode requires all credentials configured for any of them to go live |

### Why credential sharing is acceptable

Adzuna's API does not issue per-country credentials. The same `app_id` + `app_key` pair works across all country subdomains (`/gb/`, `/fr/`, `/de/`). There is no security or operational risk in sharing — it's how the upstream API is designed. If a future Adzuna country required separate credentials, a new env var would be added and the `_credential_fields` list updated per-provider.

---

## Production Validation

Phase 12C was validated in production after deployment through Jenkins:

| Check | Endpoint | Result |
|-------|----------|--------|
| Provider discovery | `GET /api/v1/external-sources/providers` | ✅ Returns `adzuna_fr` and `adzuna_de` (5 providers total) |
| Search Adzuna France | `GET /api/v1/external-sources/adzuna_fr/search?query=devops&limit=3` | ✅ Returns FR/fr candidates |
| Search Adzuna Germany | `GET /api/v1/external-sources/adzuna_de/search?query=devops&limit=3` | ✅ Returns DE/de candidates |
| Cockpit UI | React Admin auto-discovery from `/providers` | ✅ Both new providers visible and searchable |
| Existing providers | France Travail, Adzuna UK, Freelancer | ✅ Unchanged |

No production incidents, no regressions, no database changes.

---

## Test Coverage

**File:** `backend/tests/test_phase12c.py`

| Test Class | Coverage |
|------------|----------|
| `TestDefaultCountry` | `AdzunaUKAPIClient` default `country_code` is `"gb"`, URL contains `/jobs/gb`, GB/en/adzuna_uk metadata |
| `TestCrossCountryURL` | FR: `/jobs/fr` URL, FR/fr/adzuna_fr metadata. DE: `/jobs/de` URL, DE/de/adzuna_de metadata. Verified via mocked HTTP transport. |
| `TestNormalizedCandidates` | Mock provider returns candidates with correct country/language/provider for both FR and DE |
| `TestProviderRegistration` | `adzuna_fr` and `adzuna_de` present in `PROVIDER_REGISTRY` (total 5). Correct provider attributes (label, country, language, source_kind, supports_real_api, credential_fields). |
| `TestProvidersEndpoint` | `GET /providers` includes both new providers with correct info. Adzuna UK still present. Total 5. |
| `TestMockSearch` | FR search returns `adzuna_fr`/FR/fr data. DE search returns `adzuna_de`/DE/de data. Location filtering works. Limit works. Each has 3+ candidates. |
| `TestCombinedSearch` | Combined search across adzuna_uk+fr+de returns all three. Combined search across all 5 providers returns all 5. Live-mode combined search works. |
| `TestNoDatabaseMutation` | Search endpoints for fr, de, and combined do not create SourceRecord, Company, or Opportunity. |
| `TestImportCandidate` | Import FR candidate creates records correctly with `imported_pending_review` and `SourceType.other`. Import DE candidate works identically. Duplicate detection works for both. |
| `TestExistingProvidersUnchanged` | France Travail and Freelancer mock search still works. Diagnostics unchanged for existing providers. |

---

## Key Files

| File | Role |
|------|------|
| `backend/app/services/external_sources.py` | `AdzunaFrMockProvider` and `AdzunaDeMockProvider` classes (lines 636–910), registered in `PROVIDER_REGISTRY` |
| `backend/app/services/adzuna_uk_client.py` | `AdzunaUKAPIClient` extended with `country_code` parameter, `_COUNTRY_CONFIG` mapping, template-based URL building |
| `backend/tests/test_phase12c.py` | Full test coverage for Phase 12C |

---

## Future Possible Extensions

### Additional Adzuna countries

Adzuna operates in 16 countries. Adding more follows the same pattern:

1. Add country entry to `_COUNTRY_CONFIG` in `adzuna_uk_client.py` (country, language, provider_name)
2. Create a new mock provider class in `external_sources.py` registered as `adzuna_XX`
3. Verify the Adzuna API supports the target country code (`api.adzuna.com/v1/api/jobs/{code}`)

**Prerequisite:** Each new country must be verified against the live Adzuna API first — not all advertised countries may have sufficient job listing coverage.

### UI grouping by country

The Cockpit currently auto-discovers providers and displays them as separate entries. A future improvement could group Adzuna providers by family (e.g., "Adzuna" dropdown with UK/France/Germany sub-entries) similar to how the Source Catalog groups platforms by country. This is a pure frontend concern — no API changes needed.

### Documentation of credential sharing

If additional Adzuna countries are added, credential sharing clarity becomes more important. The per-provider diagnostics already handle this correctly (all Adzuna providers share the same `_credential_fields`), but future documentation should explicitly list which providers share which credentials.

---

## Phase Plan

| Phase | Description | Status |
|-------|-------------|--------|
| **12B** | French freelance source catalog (read-only reference directory) | ✅ Done |
| **12C** | Adzuna France and Germany real external source providers | ✅ **Done** |
