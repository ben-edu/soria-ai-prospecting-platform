"""Jooble API client — real connector for global job aggregation.

Phase 12D — Jooble Real Connector.

This module provides a real Jooble API connector that is NOT
used in normal runtime (EXTERNAL_SOURCES_MODE=mock by default).
It follows the same pattern as the Adzuna UK and Freelancer connectors.

The Jooble API uses an API key embedded in the URL path and a POST
request with a JSON body containing keywords and location.

Usage (future, when EXTERNAL_SOURCES_MODE != "mock"):
    from app.services.jooble_client import JoobleAPIClient
    client = JoobleAPIClient(settings)
    if client.validate_configuration():
        results = client.search_jobs("devops", location="Berlin", limit=10)
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import Settings
from app.schemas.external_source import ExternalOpportunityCandidate

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class JoobleClientError(Exception):
    """Base exception for Jooble client errors."""


class JoobleConfigurationError(JoobleClientError):
    """Raised when required configuration is missing or invalid."""


class JoobleAPIError(JoobleClientError):
    """Raised when the Jooble API returns an error response."""


# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

_JOOBLE_API_BASE_URL_DEFAULT = "https://jooble.org/api"

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class JoobleAPIClient:
    """Real Jooble API client connector.

    Provides methods for configuration validation, request building,
    response normalization, and job search.

    The HTTP transport is injectable for testability. No real HTTP calls
    are made unless explicitly enabled and configured.

    Jooble uses an API key embedded in the URL path (no OAuth2).

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
            self.api_key = settings.JOOBLE_API_KEY
            self.api_base_url = (
                settings.JOOBLE_API_BASE_URL or _JOOBLE_API_BASE_URL_DEFAULT
            )
            self.timeout = settings.EXTERNAL_SOURCE_HTTP_TIMEOUT_SECONDS
        else:
            self.api_key = None
            self.api_base_url = _JOOBLE_API_BASE_URL_DEFAULT
            self.timeout = 10

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        """Return True if all required configuration is present."""
        return bool(self.api_key)

    def validate_configuration(self) -> bool:
        """Validate that required configuration is present.

        Returns
        -------
        True if all required config is present.

        Raises
        ------
        JoobleConfigurationError
            If required config is missing.
        """
        if not self.api_key:
            raise JoobleConfigurationError(
                "JOOBLE_API_KEY is not configured."
            )
        return True

    # ------------------------------------------------------------------
    # Request builders
    # ------------------------------------------------------------------

    def build_search_url(self) -> str:
        """Build the search URL with the API key embedded in the path.

        Jooble uses POST to https://jooble.org/api/{api_key}.

        Returns
        -------
        Full search URL string.
        """
        api_key = self.api_key or ""
        return f"{self.api_base_url.rstrip('/')}/{api_key}"

    def build_search_payload(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        """Build the JSON payload for the Jooble API search request.

        Maps SORIA search parameters to Jooble API fields:
        - query -> keywords (search terms)
        - location -> location (optional)
        - limit -> ResultOnPage (results count, capped to 1-50)

        Parameters
        ----------
        query
            Free-text search query (maps to keywords).
        location
            Optional location filter (maps to location).
        limit
            Maximum number of results (maps to ResultOnPage, capped at 1-50).

        Returns
        -------
        Dict payload for the Jooble search POST body.
        """
        payload: dict = {
            "keywords": query.strip(),
            "ResultOnPage": min(max(1, limit), 50),
        }
        if location and location.strip():
            payload["location"] = location.strip()
        return payload

    # ------------------------------------------------------------------
    # Response normalization
    # ------------------------------------------------------------------

    def normalize_job(self, raw_job: dict) -> ExternalOpportunityCandidate:
        """Normalize a raw Jooble API job into ExternalOpportunityCandidate.

        Maps Jooble API field names to SORIA's internal schema:
        - id -> external_id
        - title -> title
        - company -> company_name
        - location -> location
        - snippet -> description
        - salary -> stored as text in tags/raw_payload (no structured salary)
        - type -> contract_type
        - link -> source_url
        - updated -> source_published_at

        Parameters
        ----------
        raw_job
            Raw job dict from the Jooble API.

        Returns
        -------
        Normalized ExternalOpportunityCandidate.
        """
        external_id = str(raw_job.get("id") or "")

        # Title
        title = raw_job.get("title") or ""

        # Company name
        company_name = raw_job.get("company")

        # Description (snippet)
        description = raw_job.get("snippet")

        # Location
        location = raw_job.get("location")

        # Contract type
        contract_type = raw_job.get("type")

        # Source URL
        source_url = raw_job.get("link")

        # Published date
        source_published_at = None
        date_str = raw_job.get("updated")
        if date_str:
            try:
                # Jooble returns timestamps as Unix milliseconds or ISO strings
                if isinstance(date_str, (int, float)):
                    # Assume Unix timestamp in milliseconds
                    timestamp_s = float(date_str) / 1000.0
                    source_published_at = datetime.fromtimestamp(
                        timestamp_s, tz=timezone.utc
                    )
                else:
                    source_published_at = datetime.fromisoformat(
                        str(date_str).replace("Z", "+00:00")
                    )
                    if source_published_at.tzinfo is None:
                        source_published_at = source_published_at.replace(
                            tzinfo=timezone.utc
                        )
            except (ValueError, TypeError, OSError):
                source_published_at = None

        # Salary — Jooble returns salary as a string (e.g. "$50,000 - $70,000")
        # We store it in tags and raw_payload since it's unstructured
        salary_text = raw_job.get("salary")
        tags: list[str] = []
        if salary_text:
            tags.append(str(salary_text).lower())

        # Remote type — Jooble may include "remote" in location or type
        remote_type = None
        if location and "remote" in location.lower():
            remote_type = "remote"
        if contract_type and "remote" in contract_type.lower():
            remote_type = "remote"

        # Source name from raw source field
        source_name = raw_job.get("source")

        # Build raw_payload without the API key
        raw_payload = raw_job.copy() if isinstance(raw_job, dict) else {}
        # Add extra metadata
        if source_name:
            raw_payload["_source_name"] = source_name

        return ExternalOpportunityCandidate(
            provider="jooble",
            external_id=external_id,
            source_kind="job",
            title=title,
            company_name=company_name,
            description=description,
            location=location,
            country="GLOBAL",
            language="en",
            source_url=source_url,
            source_published_at=source_published_at,
            contract_type=contract_type,
            remote_type=remote_type,
            budget_min=None,
            budget_max=None,
            budget_currency=None,
            tags=tags,
            raw_payload=raw_payload,
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
        """Search jobs via the Jooble API.

        Requires valid configuration (api_key).
        The HTTP transport can be injected via *http_client* parameter
        or via the constructor for testability.

        Jooble uses a POST request with JSON body to a URL containing
        the API key. Unlike France Travail there is no OAuth2 token
        acquisition step, and unlike Adzuna the auth is in the URL path.

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
        JoobleConfigurationError
            If required configuration is missing.
        JoobleAPIError
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
            search_url = self.build_search_url()
            search_payload = self.build_search_payload(query, location, limit)

            search_resp = client.post(search_url, json=search_payload)
            if search_resp.status_code != 200:
                raise JoobleAPIError(
                    f"Search failed with status {search_resp.status_code}: "
                    f"{search_resp.text}"
                )

            search_data = search_resp.json()
            raw_results = search_data.get("jobs", [])

            return [self.normalize_job(job) for job in raw_results]

        finally:
            if must_close:
                client.close()
