"""API endpoints for external opportunity sources.

Phase 9A — External Opportunity Sources Foundation.
"""

from fastapi import APIRouter, HTTPException, Query

from app.schemas.external_source import (
    ExternalOpportunitySearchResponse,
    ExternalSourceDiagnosticsResponse,
)
from app.services.external_sources import (
    get_enabled_provider_names,
    list_external_source_providers,
    search_external_opportunities,
    search_multiple_external_sources,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# NOTE: /providers and /search MUST be declared before /{provider}/search
# to avoid FastAPI path parameter conflicts.
# ---------------------------------------------------------------------------


@router.get(
    "/providers",
    response_model=ExternalSourceDiagnosticsResponse,
)
def get_providers():
    """List all registered external source providers with diagnostics."""
    providers = list_external_source_providers()
    enabled = get_enabled_provider_names()
    return ExternalSourceDiagnosticsResponse(
        providers=providers,
        enabled_providers=enabled,
        mock_only=True,
        message="Phase 9A — All providers are mocks. "
        "No real external API calls are made. "
        "Credentials are not required.",
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
