# Phase 12B — French Freelance Source Catalog

## Objective

Add a read-only reference catalog of French freelance platforms in the SORIA Cockpit. This catalog gives operators a quick directory of where to find French freelance opportunities manually — without integrating any of these platforms as searchable external sources.

## Architecture Decision

These platforms are **NOT** external opportunity providers. They are not registered in `PROVIDER_REGISTRY`, they are not searchable via the opportunity search pipeline, and they are not importable.

Key distinction vs. Phase 9/10 providers (France Travail, Adzuna UK, Freelancer.com):

| Aspect | Phase 9/10 Providers | Phase 12B Catalog Entries |
|--------|---------------------|--------------------------|
| Provider registration | Registered in `PROVIDER_REGISTRY` | Not registered |
| Searchable | Yes (`GET /search`) | No |
| Importable | Yes (`POST /import-candidate`) | No |
| Creates SourceRecord, Company, Opportunity | Yes | No |
| Creates MessageDraft, FollowUp, ComplianceEvent | Yes | No |
| Scraping support | Architecture exists | Scraping blocked |
| Real API connectors | Implemented (gated) | No API integration |
| Purpose | Automated/assisted sourcing | Manual reference directory |

## Safety & Governance Rules

All five catalog entries share the same safety profile:

| Flag | Value | Meaning |
|------|-------|---------|
| `is_manual_source` | `true` | Human-driven, no automation possible |
| `supports_real_api` | `false` | No API connector exists for this platform |
| `requires_credentials` | `false` | No credentials stored in SORIA |
| `human_review_required` | `true` | Human oversight mandatory before any action |
| `importable` | `false` | Cannot be imported into SORIA data model |
| `scraping_allowed` | `false` | No scraping — use official site only |
| `external_message_allowed` | `false` | No automated outreach via SORIA |

## Why These Are Not Importable

- Most French freelance platforms do not offer documented public APIs (Malt has an undocumented GraphQL API; Free-Work, Codeur.com, LeHibou, and Comet have no public API at all)
- These are **sourcing references**, not data pipelines — operators browse them manually and note relevant opportunities outside SORIA
- Importing would require scraping or undocumented API access, which violates the platform's safety rules
- The catalog exists to inform operators about *where* to look, not to automate the looking

## Backend Endpoint

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/external-sources/source-catalog` | Return full source catalog as a list |

The endpoint returns a `list[ExternalSourceCatalogEntry]` with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `provider` | `str` | Unique provider identifier (e.g. `"malt"`, `"free_work"`) |
| `label` | `str` | Human-readable platform name |
| `country` | `str` | ISO country code (`"FR"`) |
| `language` | `str` | Primary language (`"fr"`) |
| `source_kind` | `str` | Category (e.g. `"freelance_profile_marketplace"`) |
| `interaction_mode` | `str` | How users interact with the platform |
| `description` | `str` | Platform description |
| `usage_guide` | `str` | How to use this platform with SORIA |
| `search_url` | `str` | URL to search for opportunities |
| `profile_url` | `str` | URL to view freelancer profiles |
| `recommended_for` | `str` | Suggested use cases |
| `notes` | `str` | Additional notes |
| `is_manual_source` | `bool` | Always `true` |
| `supports_real_api` | `bool` | Always `false` |
| `requires_credentials` | `bool` | Always `false` |
| `human_review_required` | `bool` | Always `true` |
| `importable` | `bool` | Always `false` |
| `scraping_allowed` | `bool` | Always `false` |
| `external_message_allowed` | `bool` | Always `false` |

No database queries, no side effects, no authentication required (read-only).

## Cockpit UI Page

A new **Source Catalog** page is available at the `/source-catalog` route in the Cockpit.

States:
- **Loading** — Shows a spinner with "Loading source catalog..." while fetching
- **Error** — Displays an error alert with the error message and a Retry button
- **Empty** — Shows an informational alert when no entries are available
- **Catalog** — Renders cards for each platform with:
  - Platform name and provider ID
  - Country, language, and source kind chips
  - Safety badges (Manual source, No real API, Not importable, No scraping, Human review required)
  - Description, interaction mode, usage guide, recommended for, and notes
  - External links to search URL and profile URL (open in new tabs)
  - Footer disclaimer alert confirming no external API calls are made

### Key Files

- `backend/app/schemas/external_source.py` — `ExternalSourceCatalogEntry` Pydantic schema
- `backend/app/services/source_catalog.py` — Static catalog definition and `get_source_catalog()`
- `backend/app/api/v1/endpoints/external_sources.py` — `GET /source-catalog` endpoint
- `frontend/cockpit/src/resources/externalSources/SourceCatalog.tsx` — Catalog UI component
- `frontend/cockpit/src/App.tsx` — Route registration (`/source-catalog`)

## Included Platforms

| Provider | Label | Source Kind | Interaction Mode | Notes |
|----------|-------|-------------|------------------|-------|
| `free_work` | Free-Work | Freelance mission board | Searchable job board | IT job board, no public API |
| `codeur` | Codeur.com | Freelance project marketplace | Project marketplace | Dev projects, no public API |
| `lehibou` | LeHibou | Freelance IT matching platform | Account-based matching | Requires account, no public API |
| `malt` | Malt | Freelance profile marketplace | Profile marketplace | Undocumented GraphQL API, manual use recommended |
| `comet` | Comet | Freelance IT matching platform | Curated profile matching | Curated approach — missions proposed by account managers |

## How to Use This Feature (Manual Workflow)

1. Navigate to the **Source Catalog** page in the SORIA Cockpit
2. Browse or filter the listed French freelance platforms
3. Read the **usage guide** and **notes** for each platform
4. Click **Open search URL** to visit the platform in a new tab
5. Manually browse opportunities on the external platform
6. If a relevant opportunity is found, create it manually in SORIA as a standard Opportunity (not via import)

> The source catalog is a **reference directory only**. SORIA does not call any external APIs for these platforms, does not scrape them, and cannot import from them. All sourcing is manual through the provided external links.

## Next Phase: Phase 12C — Adzuna Multi-Country Europe

The next phase extends the Adzuna connector to support multiple European countries beyond the UK. This requires:
- Country-specific API base URL routing (e.g. `https://api.adzuna.com/v1/api/jobs/de` for Germany, `https://api.adzuna.com/v1/api/jobs/fr` for France)
- Per-country credential configuration or shared credentials
- Provider registry updates to expose per-country providers
- Source catalog cross-reference entries for the Adzuna country availability
- Cockpit UI updates for country selection in external source search

## Key Design Decisions

1. **Separate module** — The catalog lives in its own `source_catalog.py` module, not in `external_sources.py`, to avoid coupling with the provider registry and search pipeline.
2. **Static data** — The catalog is a dictionary defined in code, not a database table. No migrations, no DB queries, no caching layer needed.
3. **Shared schema** — `ExternalSourceCatalogEntry` reuses the `external_source.py` schemas module but is a distinct type from `ExternalSourceProviderInfo`.
4. **Route placement** — The endpoint lives under `/api/v1/external-sources/source-catalog` to keep all external-source-related routes together, even though catalog entries are not providers.
