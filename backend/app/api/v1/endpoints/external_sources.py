"""API endpoints for external opportunity sources.

Phase 9A — External Opportunity Sources Foundation.
Phase 9B — Import External Candidate into SourceRecord + Company + Opportunity.
Phase 10A — Real External API Configuration Foundation (diagnostics + settings).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_db
from app.core.config import settings as app_settings
from app.schemas.external_source import (
    ExternalOpportunityCandidate,
    ExternalOpportunitySearchResponse,
    ExternalSourceDiagnosticsResponse,
    ImportExternalCandidateResponse,
)
from app.services.external_sources import (
    get_enabled_provider_names,
    import_external_candidate,
    list_external_source_providers,
    search_external_opportunities,
    search_multiple_external_sources,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# NOTE: /providers, /search, and /import-candidate MUST be declared before
# /{provider}/search to avoid FastAPI path parameter conflicts.
# ---------------------------------------------------------------------------


@router.get(
    "/providers",
    response_model=ExternalSourceDiagnosticsResponse,
)
def get_providers():
    """List all registered external source providers with diagnostics.

    Phase 10A adds per-provider diagnostics fields:
    - supports_real_api, credentials_configured, real_api_enabled
    - safe_status, safe_message
    """
    providers = list_external_source_providers(settings=app_settings)
    enabled = get_enabled_provider_names()
    mock_only = all(p.is_mock for p in providers)

    if app_settings.EXTERNAL_SOURCES_MODE == "mock":
        message = (
            f"Mode: mock. All {len(providers)} providers running in mock mode. "
            "No real external API calls are made."
        )
    else:
        message = (
            f"Mode: {app_settings.EXTERNAL_SOURCES_MODE}. "
            f"Real API mode active for {sum(1 for p in providers if p.real_api_enabled)} provider(s)."
        )

    return ExternalSourceDiagnosticsResponse(
        providers=providers,
        enabled_providers=enabled,
        mock_only=mock_only,
        mode=app_settings.EXTERNAL_SOURCES_MODE,
        message=message,
    )


@router.get(
    "/search",
    response_model=ExternalOpportunitySearchResponse,
)
def combined_search(
    providers: str = Query(
        ...,
        description="Comma-separated list of provider names",
    ),
    query: str = Query(
        ...,
        min_length=1,
        description="Free-text search query (required, must not be blank)",
    ),
    location: str = Query(
        None,
        description="Location filter (optional)",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Maximum results per provider (1-50)",
    ),
):
    """Search across multiple external source providers."""
    provider_list = [p.strip() for p in providers.split(",") if p.strip()]

    if not provider_list:
        raise HTTPException(
            status_code=400,
            detail="At least one provider must be specified.",
        )

    try:
        results = search_multiple_external_sources(
            providers=provider_list,
            query=query.strip(),
            location=location.strip() if location else None,
            limit=limit,
            settings=app_settings,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return ExternalOpportunitySearchResponse(
        provider=None,
        query=query.strip(),
        location=location.strip() if location else None,
        total=len(results),
        items=results,
    )


@router.post(
    "/import-candidate",
    response_model=ImportExternalCandidateResponse,
)
def post_import_candidate(
    payload: ExternalOpportunityCandidate,
    db: Session = Depends(get_db),
):
    """Import an external candidate into SourceRecord, Company, and Opportunity."""
    try:
        result = import_external_candidate(candidate=payload, db=db)
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get(
    "/{provider}/search",
    response_model=ExternalOpportunitySearchResponse,
)
def single_provider_search(
    provider: str,
    query: str = Query(
        ...,
        min_length=1,
        description="Free-text search query (required, must not be blank)",
    ),
    location: str = Query(
        None,
        description="Location filter (optional)",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Max results (1-50)",
    ),
):
    """Search a single external source provider for opportunities."""
    try:
        items = search_external_opportunities(
            provider_name=provider,
            query=query.strip(),
            location=location.strip() if location else None,
            limit=limit,
            settings=app_settings,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return ExternalOpportunitySearchResponse(
        provider=provider,
        query=query.strip(),
        location=location.strip() if location else None,
        total=len(items),
        items=items,
    )
