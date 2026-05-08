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
- **Backward compatible** — Phase 9A/9B/9C/9D behavior is unchanged
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
| **9E** | Real connector implementations for each provider | 📅 Planned |

## Key Files

- `backend/app/core/config.py` — Settings with external source configuration
- `backend/app/schemas/external_source.py` — `ExternalSourceProviderInfo` with diagnostics fields
- `backend/app/services/external_sources.py` — `BaseExternalSourceProvider` with `supports_real_api`, `_credential_fields`, `check_credentials_configured()`, updated `get_provider_info()`
- `backend/app/api/v1/endpoints/external_sources.py` — Updated `GET /providers` endpoint
- `backend/.env.example` — Documented optional env vars
- `backend/tests/test_phase10a.py` — Phase 10A tests
