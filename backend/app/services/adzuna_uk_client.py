"""Adzuna UK API client — real connector for UK job aggregation.

Phase 10E — Adzuna UK Real Connector.

This module provides a real Adzuna UK API connector that is NOT
used in normal runtime (EXTERNAL_SOURCES_MODE=mock by default).
It follows the same pattern as the France Travail connector (Phase 10B/10C).

The Adzuna API uses app_id + app_key as query parameters on every request
(no OAuth2 token acquisition).

Usage (future, when EXTERNAL_SOURCES_MODE != "mock"):
    from app.services.adzuna_uk_client import AdzunaUKAPIClient
    client = AdzunaUKAPIClient(settings)
    if client.validate_configuration():
        results = client.search_jobs("devops", location="London", limit=10)
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import Settings
from app.schemas.external_source import ExternalOpportunityCandidate

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class AdzunaUKClientError(Exception):
    """Base exception for Adzuna UK client errors."""


class AdzunaUKConfigurationError(AdzunaUKClientError):
    """Raised when required configuration is missing or invalid."""


class AdzunaUKAPIError(AdzunaUKClientError):
    """Raised when the Adzuna UK API returns an error response."""


# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

_ADZUNA_UK_API_BASE_URL_DEFAULT = "https://api.adzuna.com/v1/api/jobs/gb"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class AdzunaUKAPIClient:
    """Real Adzuna UK API client connector.

    Provides methods for configuration validation, request building,
    response normalization, and job search.

    The HTTP transport is injectable for testability. No real HTTP calls
    are made unless explicitly enabled and configured.

    Adzuna UK uses app_id + app_key as query parameters (no OAuth2).

    Parameters
    ----------
    settings
        Application settings instance (optional). If not provided,
        configuration will use defaults and is_ready() will return False.
    http_client
        Optional httpx.Client for HTTP transport injection.
        If not provided, one will be created when search_jobs is called.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self._settings = settings
        self._http_client = http_client

        if settings is not None:
            self.app_id = settings.ADZUNA_UK_APP_ID
            self.app_key = settings.ADZUNA_UK_APP_KEY
            self.api_base_url = (
                settings.ADZUNA_UK_API_BASE_URL or _ADZUNA_UK_API_BASE_URL_DEFAULT
            )
            self.timeout = settings.EXTERNAL_SOURCE_HTTP_TIMEOUT_SECONDS
        else:
            self.app_id = None
            self.app_key = None
            self.api_base_url = _ADZUNA_UK_API_BASE_URL_DEFAULT
            self.timeout = 10

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        """Return True if all required configuration is present."""
        return bool(self.app_id and self.app_key)

    def validate_configuration(self) -> bool:
        """Validate that required configuration is present.

        Returns
        -------
        True if all required config is present.

        Raises
        ------
        AdzunaUKConfigurationError
            If required config is missing.
        """
        if not self.app_id:
            raise AdzunaUKConfigurationError(
                "ADZUNA_UK_APP_ID is not configured."
            )
        if not self.app_key:
            raise AdzunaUKConfigurationError(
                "ADZUNA_UK_APP_KEY is not configured."
            )
        return True

    # ------------------------------------------------------------------
    # Request builders
    # ------------------------------------------------------------------

    def build_search_params(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        """Build search query parameters for the Adzuna UK API.

        Maps SORIA search parameters to Adzuna UK API fields:
        - query -> what (keywords)
        - location -> where (location)
        - limit -> results_per_page (results count, capped to 1-50)
        Parameters
        ----------
        query
            Free-text search query (maps to q).
        location
            Optional location filter (maps to where).
        limit
            Maximum number of results (maps to results_per_page, capped at 1-50).

        Returns
        -------
        Dict of query parameters for the Adzuna UK search endpoint.
        """
        params: dict = {
            "app_id": self.app_id or "",
            "app_key": self.app_key or "",
            "what": query.strip(),
            "results_per_page": min(max(1, limit), 50),
            "content-type": "application/json",
        }
        if location and location.strip():
            params["where"] = location.strip()
        return params

    # ------------------------------------------------------------------
    # Response normalization
    # ------------------------------------------------------------------

    def normalize_job(self, raw_job: dict) -> ExternalOpportunityCandidate:
        """Normalize a raw Adzuna UK API job into ExternalOpportunityCandidate.

        Maps Adzuna API field names to SORIA's internal schema:
        - id -> external_id
        - title -> title
        - company.display_name -> company_name
        - location.display_name -> location
        - description -> description
        - created -> source_published_at
        - redirect_url -> source_url
        - contract_type -> contract_type
        - salary_min -> budget_min
        - salary_max -> budget_max
        - salary_currency -> budget_currency
        - category.label -> tags

        Parameters
        ----------
        raw_job
            Raw job dict from the Adzuna UK API.

        Returns
        -------
        Normalized ExternalOpportunityCandidate.
        """
        external_id = str(raw_job.get("id") or "")

        # Title
        title = raw_job.get("title") or ""

        # Company name from nested object
        company = raw_job.get("company") or {}
        company_name = (
            company.get("display_name") if isinstance(company, dict) else None
        )

        # Description
        description = raw_job.get("description")

        # Location from nested object
        location_data = raw_job.get("location") or {}
        location = (
            location_data.get("display_name")
            if isinstance(location_data, dict)
            else None
        )

        # Contract type
        contract_type = raw_job.get("contract_type")

        # Source URL
        source_url = raw_job.get("redirect_url")

        # Published date
        source_published_at = None
        date_str = raw_job.get("created")
        if date_str:
            try:
                source_published_at = datetime.fromisoformat(
                    date_str.replace("Z", "+00:00")
                )
                if source_published_at.tzinfo is None:
                    source_published_at = source_published_at.replace(
                        tzinfo=timezone.utc
                    )
            except (ValueError, TypeError):
                source_published_at = None

        # Budget
        budget_min = raw_job.get("salary_min")
        budget_max = raw_job.get("salary_max")
        budget_currency = raw_job.get("salary_currency")

        # Tags from category + contract type
        tags: list[str] = []
        category = raw_job.get("category") or {}
        if isinstance(category, dict):
            cat_label = category.get("label")
            if cat_label:
                tags.append(cat_label.lower())
        if contract_type:
            tags.append(contract_type.lower())

        # Remote type — Adzuna doesn't have a dedicated remote field,
        # but we can infer from description or leave as None
        remote_type = None

        return ExternalOpportunityCandidate(
            provider="adzuna_uk",
            external_id=external_id,
            source_kind="job",
            title=title,
            company_name=company_name,
            description=description,
            location=location,
            country="GB",
            language="en",
            source_url=source_url,
            source_published_at=source_published_at,
            contract_type=contract_type,
            remote_type=remote_type,
            budget_min=budget_min,
            budget_max=budget_max,
            budget_currency=budget_currency,
            tags=tags,
            raw_payload=raw_job.copy() if isinstance(raw_job, dict) else {},
        )

    # ------------------------------------------------------------------
    # Search (requires HTTP transport)
    # ------------------------------------------------------------------

    def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
        http_client: Optional[httpx.Client] = None,
    ) -> list[ExternalOpportunityCandidate]:
        """Search jobs via the Adzuna UK API.

        Requires valid configuration (app_id and app_key).
        The HTTP transport can be injected via *http_client* parameter
        or via the constructor for testability.

        Adzuna API is simpler than France Travail — it uses query parameters
        for authentication (app_id + app_key) on every request, with no
        OAuth2 token acquisition step.

        Parameters
        ----------
        query
            Free-text search query.
        location
            Optional location filter.
        limit
            Maximum number of results (1-50).
        http_client
            Optional httpx.Client for HTTP transport injection.
            Falls back to self._http_client if not provided.

        Returns
        -------
        List of normalized opportunity candidates.

        Raises
        ------
        AdzunaUKConfigurationError
            If required configuration is missing.
        AdzunaUKAPIError
            If the search API returns an error.
        """
        # Validate configuration first (raises if missing)
        self.validate_configuration()

        client = http_client or self._http_client
        must_close = False
        if client is None:
            client = httpx.Client(timeout=self.timeout)
            must_close = True

        try:
            # Build search URL — Adzuna uses /{category}/search/{page}
            # Default category is blank (all), page 1
            search_params = self.build_search_params(query, location, limit)
            search_url = f"{self.api_base_url.rstrip('/')}/search/1"

            search_resp = client.get(search_url, params=search_params)
            if search_resp.status_code != 200:
                raise AdzunaUKAPIError(
                    f"Search failed with status {search_resp.status_code}: "
                    f"{search_resp.text}"
                )

            search_data = search_resp.json()
            raw_results = search_data.get("results", [])

            return [self.normalize_job(job) for job in raw_results]

        finally:
            if must_close:
                client.close()
