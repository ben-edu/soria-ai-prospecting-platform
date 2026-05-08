# Phase 10A — Real External API Configuration Foundation

## Purpose

Phase 10A adds a safe, observable configuration foundation for future real external API connectors — **without making any real external HTTP calls**. All providers continue to run in mock mode by default.

This phase introduces:

1. Environment/config settings for external source API credentials and mode
2. Per-provider diagnostics fields on the `GET /api/v1/external-sources/providers` endpoint
3. Safe-status indicators that communicate whether a provider is in mock mode, has credentials configured, and whether the real API is enabled

## Design Principles

- **No real API calls** — all providers remain deterministic mocks
- **No secrets in code** — credentials are read from environment variables only
- **Backward compatible** — Phase 9A/9B/10A/10B/10C/11A behavior is unchanged
- **Observable** — every provider exposes its configuration state via the diagnostics endpoint

## Configuration Settings

All settings live in `backend/app/core/config.py` (pydantic-settings `Settings` class) and are read from `.env` or environment variables.

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `EXTERNAL_SOURCES_MODE` | `str` | `"mock"` | Operation mode: `"mock"` or (future) `"live"` |
| `FRANCE_TRAVAIL_CLIENT_ID` | `Optional[str]` | `None` | France Travail API client ID |
| `FRANCE_TRAVAIL_CLIENT_SECRET` | `Optional[str]` | `None` | France Travail API client secret |
| `ADZUNA_APP_ID` | `Optional[str]` | `None` | Adzuna API application ID |
| `ADZUNA_APP_KEY` | `Optional[str]` | `None` | Adzuna API application key |
| `EXTERNAL_SOURCE_HTTP_TIMEOUT_SECONDS` | `int` | `10` | HTTP timeout for real API calls (not used in mock mode) |

### Provider Credential Mapping

| Provider | Required Settings |
|----------|-----------------|
| `france_travail` | `FRANCE_TRAVAIL_CLIENT_ID`, `FRANCE_TRAVAIL_CLIENT_SECRET` |
| `adzuna_uk` | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` |
| `freelancer` | None (no real API planned) |

## Diagnostics Fields

Each provider in `GET /api/v1/external-sources/providers` now includes the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `supports_real_api` | `bool` | Whether a real API connector exists/is planned for this provider |
| `credentials_configured` | `bool` | Whether all required credential env vars have truthy values |
| `real_api_enabled` | `bool` | Whether real API mode is active (mock mode → always `False`) |
| `safe_status` | `str` | One of `"mock"`, `"missing_credentials"`, `"ready"`, `"unsupported"` |
| `safe_message` | `str` | Human-readable explanation of current state |

The top-level response also includes:

| Field | Type | Description |
|-------|------|-------------|
| `mode` | `str` | Value of `EXTERNAL_SOURCES_MODE` setting |
| `mock_only` | `bool` | `True` when all providers are mock (always `True` in Phase 10A) |

### Safe Status Values

| `safe_status` | Meaning | Example `safe_message` |
|---------------|---------|----------------------|
| `"mock"` | Provider is running in mock mode (default) | "Mock mode active. Real API credentials not configured." |
| `"missing_credentials"` | Real API is selected but credentials missing | "Real API selected but credentials not configured." |
| `"ready"` | Real API is configured and active | "Real API configured and ready." |
| `"unsupported"` | No real API implementation for this provider | "Mock mode active. No real API available." |

## Phase 10B — France Travail Real Connector Skeleton

### Purpose

Phase 10B adds a safe, dedicated France Travail API connector module that prepares the code architecture for a future real API integration — **without enabling real HTTP calls in normal runtime**.

This phase introduces:

1. **Dedicated connector module** (`backend/app/services/france_travail_client.py`) with a full `FranceTravailAPIClient` class
2. **Custom exception hierarchy** for controlled failure modes
3. **Testable methods** with injectable HTTP transport
4. **No changes to mock mode behavior** — all providers still run in mock mode by default

### Design Principles

- **No real HTTP calls** — the connector exists but is never invoked during normal runtime
- **No credentials required** — connector can be instantiated without settings; `is_ready()` returns `False` when config is missing
- **Safe failure** — `validate_configuration()` raises controlled exceptions instead of failing at runtime
- **Testable transport** — `search_offers` accepts an injectable `httpx.Client` for test mocking
- **Backward compatible** — Phase 9A/9B/9C/9D/10A behavior is unchanged

### Connector Module

**File:** `backend/app/services/france_travail_client.py`

#### Custom Exceptions

| Exception | Parent | Raised When |
|-----------|--------|-------------|
| `FranceTravailClientError` | `Exception` | Base for all FT client errors |
| `FranceTravailConfigurationError` | `FranceTravailClientError` | Required config (client_id/client_secret) is missing |
| `FranceTravailAuthenticationError` | `FranceTravailClientError` | OAuth2 token acquisition fails |
| `FranceTravailAPIError` | `FranceTravailClientError` | Search API returns an error |

#### FranceTravailAPIClient Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `is_ready()` | `bool` | True if client_id and client_secret are both set |
| `validate_configuration()` | `bool` | Raises `FranceTravailConfigurationError` if config is missing |
| `build_token_request_payload()` | `dict` | Builds OAuth2 client credentials payload (no side effects, no logging) |
| `build_search_params(query, location, limit)` | `dict` | Maps SORIA params to France Travail API fields (`motsCles`, `lieuTravail.libelle`, `nombreOffres`) |
| `normalize_offer(raw_offer)` | `ExternalOpportunityCandidate` | Maps France Travail API response fields to SORIA schema |
| `search_offers(query, location, limit, http_client)` | `list[ExternalOpportunityCandidate]` | Full search flow: validate → token → search → normalize. HTTP transport is injectable via `http_client` parameter. |

#### API Field Mapping (normalize_offer)

| France Travail Field | SORIA Field | Notes |
|---------------------|-------------|-------|
| `id` | `external_id` | |
| `intitule` | `title` | |
| `entreprise.nom` | `company_name` | Nested object |
| `description` | `description` | |
| `lieuTravail.libelle` | `location` | Nested object |
| `typeContrat` | `contract_type` | Falls back to `typeContratLibelle` |
| `dateCreation` | `source_published_at` | ISO 8601 parsed |
| `origineOffre.urlOrigine` | `source_url` | Nested object |

#### Search Parameter Mapping (build_search_params)

| SORIA Parameter | France Travail API Parameter |
|----------------|------------------------------|
| `query` | `motsCles` |
| `location` | `lieuTravail.libelle` |
| `limit` | `nombreOffres` (capped 1-50) |

### Configuration

Two new optional settings added to `backend/app/core/config.py`:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `FRANCE_TRAVAIL_TOKEN_URL` | `Optional[str]` | `None` (→ `https://entreprise.pole-emploi.fr/connexion/oauth2/access_token?realm=partenaire`) | France Travail OAuth2 token endpoint |
| `FRANCE_TRAVAIL_API_BASE_URL` | `Optional[str]` | `None` (→ `https://api.pole-emploi.fr/partenaire/offresdemploi/v2`) | France Travail API base URL |

URLs default to the known France Travail (ex-Pôle emploi) API endpoints when not overridden.

### Safety

- **`search_offers` calls `validate_configuration()` first** — missing credentials raise `FranceTravailConfigurationError` before any HTTP call
- **`search_offers` is never called by default** — the provider system still uses `FranceTravailMockProvider` while `EXTERNAL_SOURCES_MODE=mock`
- **No secrets in error messages** — exception messages reference env var names, not values
- **No real HTTP calls in tests** — the `http_client` parameter allows full mocking

### Tests

**File:** `backend/tests/test_phase10b.py`

| Test Class | Coverage |
|------------|----------|
| `TestConnectorInstantiation` | Connector can be instantiated with/without settings, `is_ready()` reflects credential state |
| `TestValidateConfiguration` | `validate_configuration()` raises safely when config is missing; messages don't expose values |
| `TestBuildTokenRequestPayload` | Token payload builder returns expected dict with no side effects |
| `TestBuildSearchParams` | Search params builder maps query/location/limit to France Travail fields correctly |
| `TestNormalizeOffer` | Full offer, minimal offer, empty dict, missing nested objects, bad dates — all handled gracefully |
| `TestSearchOffersWithMockedTransport` | `search_offers` uses injected HTTP client; errors raise appropriate exceptions |
| `TestMockModeSearchUnchanged` | Single provider search still returns mock data |
| `TestMockModeCombinedSearchUnchanged` | Combined search still works |
| `TestMockModeImportUnchanged` | Import-candidate still works |
| `TestMockModeDiagnosticsUnchanged` | Providers diagnostics still returns all providers with Phase 10A fields |
| `TestMockModeNoDbMutation` | Read-only endpoints do not mutate the database |
| `TestExistingProvidersNotBroken` | Provider registry and external_sources module are not affected |

### Phase 10C — Live-Mode Gating for France Travail

Phase 10C wires the real France Travail search behind `EXTERNAL_SOURCES_MODE` with strict safety checks:
- When `EXTERNAL_SOURCES_MODE != "mock"`, `FranceTravailAPIClient` replaces `FranceTravailMockProvider` for search
- Credentials validation before any live call
- Rate limiting, timeout handling, and circuit breaker
- Audit logging for all real API calls
- **Production remains in `EXTERNAL_SOURCES_MODE=mock` by default** — live calls never execute without explicit operator action

### Key Files (Phase 10C)

- `backend/app/services/external_sources.py` — `_get_provider_for_mode()` dispatch, `FranceTravailProvider` mode-aware wrapper
- `backend/app/services/france_travail_client.py` — `FranceTravailAPIClient.search_offers()` invoked when live
- `backend/tests/test_phase10c.py` — Phase 10C tests (gating smoke test, mock-mode regression, provider diagnostics, read-only, no DB mutation)

## Diagnostics Logic

The `credentials_configured` check requires **all** of a provider's credential fields to have truthy values. If any are `None` or empty, credentials are considered not configured.

`real_api_enabled` is `True` only when **all** of the following are true:
- `supports_real_api` is `True` for the provider
- `credentials_configured` is `True`
- `EXTERNAL_SOURCES_MODE` is not `"mock"`

In Phase 10A, `real_api_enabled` is always `False` because the default mode is `"mock"`.

## Phase Plan

| Phase | Description | Status |
|-------|-------------|--------|
| **9A** | Mock-only foundation | ✅ Done |
| **9B** | Import candidates into SourceRecord, Company, Opportunity | ✅ Done |
| **9C** | Cockpit external source search and import UX | ✅ Done |
| **9D** | SourceRecord / Import Provenance UX | ✅ Done |
| **10A** | Real external API configuration foundation | ✅ **Done** |
| **10B** | France Travail real connector skeleton | ✅ **Done** |
| **10C** | Wire real France Travail search behind EXTERNAL_SOURCES_MODE | ✅ **Done** |
| **10D** | Phase 10 closure documentation | ✅ **Done** |

## Phase 10D — Closure & Backlog

### Closure Statement

Phase 10 is complete for the current MVP boundary. This phase safely introduced the architecture, configuration, and gating for real external API connectors — without changing production behaviour.

| Item | Status |
|------|--------|
| Current production mode | `EXTERNAL_SOURCES_MODE=mock` |
| France Travail live connector | Implemented but gated — requires `EXTERNAL_SOURCES_MODE=live` + valid credentials |
| Adzuna UK live connector | **Not implemented** — moved to backlog |
| Freelancer real connector | **Not implemented** — moved to backlog |

### Next Recommended Work

The next product effort should focus on **import review / user workflow / MVP stabilization** rather than additional connectors:

- Improve the import candidate review UX (batch actions, filtering, sorting)
- Strengthen deduplication and merge workflows
- Add analytics and reporting for imported opportunities
- Stabilise the cockpit experience for daily operator use

Adding new live connectors (Adzuna UK, Freelancer, or others) is deferred until:

1. The current connector architecture has been validated in production-like conditions
2. Operational credential management processes are established
3. A clear business case exists for each additional source

### Backlog

The following items are **not in scope** for the current MVP and are moved to the project backlog:

- **Optional future:** Adzuna UK live connector — real API integration for UK job aggregation
- **Optional future:** France Travail production credential activation — switch from mock to live when credentials and operational readiness are confirmed
- **Optional future:** Stronger import review status — enhanced review workflow with approvals, rejection reasons, bulk actions
- **Optional future:** Duplicate hardening — improved fuzzy matching across SourceRecord, Company, and Opportunity
- **Optional future:** Analytics/reporting — dashboards for import activity, source effectiveness, conversion funnel

### Phase 10 Completion Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Configuration foundation (settings, env vars, diagnostics) | ✅ Done |
| 2 | France Travail connector foundation (`FranceTravailAPIClient`, exceptions, mapping) | ✅ Done |
| 3 | Live gating (`_get_provider_for_mode()`, mode-aware dispatch) | ✅ Done |
| 4 | Production mock safety preserved (`EXTERNAL_SOURCES_MODE=mock` default) | ✅ Done |
| 5 | Runtime validation (provider diagnostics, gating smoke test, search regression, read-only, no DB mutation) | ✅ Done |
| 6 | No real external API calls in production by default | ✅ Done |
| 7 | No secrets committed (credentials read from environment only) | ✅ Done |

## Key Files

- `backend/app/core/config.py` — Settings with external source configuration
- `backend/app/schemas/external_source.py` — `ExternalSourceProviderInfo` with diagnostics fields
- `backend/app/services/external_sources.py` — `BaseExternalSourceProvider` with `supports_real_api`, `_credential_fields`, `check_credentials_configured()`, updated `get_provider_info()`
- `backend/app/services/france_travail_client.py` — France Travail real API connector skeleton (Phase 10B)
- `backend/app/api/v1/endpoints/external_sources.py` — Updated `GET /providers` endpoint
- `backend/.env.example` — Documented optional env vars
- `backend/tests/test_phase10a.py` — Phase 10A tests
- `backend/tests/test_phase10b.py` — Phase 10B tests
