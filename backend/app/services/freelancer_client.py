"""Freelancer.com API client — real connector for global freelance marketplace.

Phase 10F — Freelancer Real Connector.

This module provides a real Freelancer.com API connector that is NOT
used in normal runtime (EXTERNAL_SOURCES_MODE=mock by default).
It follows the same pattern as the Adzuna UK connector (Phase 10E).

The Freelancer API uses OAuth2 Bearer token authentication
(Authorization header) on every request.

Usage (future, when EXTERNAL_SOURCES_MODE != "mock"):
    from app.services.freelancer_client import FreelancerAPIClient
    client = FreelancerAPIClient(settings)
    if client.validate_configuration():
        results = client.search_projects("devops", limit=10)
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import Settings
from app.schemas.external_source import ExternalOpportunityCandidate

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class FreelancerClientError(Exception):
    """Base exception for Freelancer client errors."""


class FreelancerConfigurationError(FreelancerClientError):
    """Raised when required configuration is missing or invalid."""


class FreelancerAPIError(FreelancerClientError):
    """Raised when the Freelancer API returns an error response."""


# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

_FREELANCER_API_BASE_URL_DEFAULT = "https://www.freelancer.com/api"

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class FreelancerAPIClient:
    """Real Freelancer.com API client connector.

    Provides methods for configuration validation, request building,
    response normalization, and project search.

    The HTTP transport is injectable for testability. No real HTTP calls
    are made unless explicitly enabled and configured.

    Freelancer uses OAuth2 Bearer token authentication.

    Parameters
    ----------
    settings
        Application settings instance (optional). If not provided,
        configuration will use defaults and is_ready() will return False.
    http_client
        Optional httpx.Client for HTTP transport injection.
        If not provided, one will be created when search_projects is called.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self._http_client = http_client

        if settings is not None:
            self.oauth_token = settings.FREELANCER_OAUTH_TOKEN
            self.api_base_url = (
                settings.FREELANCER_API_BASE_URL or _FREELANCER_API_BASE_URL_DEFAULT
            )
            self.timeout = settings.EXTERNAL_SOURCE_HTTP_TIMEOUT_SECONDS
        else:
            self.oauth_token = None
            self.api_base_url = _FREELANCER_API_BASE_URL_DEFAULT
            self.timeout = 10

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        """Return True if all required configuration is present."""
        return bool(self.oauth_token)

    def validate_configuration(self) -> bool:
        """Validate that required configuration is present.

        Returns
        -------
        True if all required config is present.

        Raises
        ------
        FreelancerConfigurationError
            If required config is missing.
        """
        if not self.oauth_token:
            raise FreelancerConfigurationError(
                "FREELANCER_OAUTH_TOKEN is not configured."
            )
        return True

    # ------------------------------------------------------------------
    # Request builders
    # ------------------------------------------------------------------

    def _get_auth_headers(self) -> dict[str, str]:
        """Build Authorization header dict.

        Returns headers dict with Bearer token. The oauth_token is
        guaranteed to be non-None after validate_configuration().
        """
        return {
            "Authorization": f"Bearer {self.oauth_token or ''}",
            "Content-Type": "application/json",
        }

    def build_search_params(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        """Build search query parameters for the Freelancer API.

        Maps SORIA search parameters to Freelancer API fields:
        - query -> query (search keywords)
        - limit -> limit (results count, capped to 1-50)
        - location -> location (optional location filter)

        Parameters
        ----------
        query
            Free-text search query (maps to query).
        location
            Optional location filter (maps to location).
        limit
            Maximum number of results (maps to limit, capped at 1-50).

        Returns
        -------
        Dict of query parameters for the Freelancer search endpoint.
        """
        params: dict = {
            "query": query.strip(),
            "limit": min(max(1, limit), 50),
            "offset": 0,
        }
        if location and location.strip():
            params["location"] = location.strip()
        return params

    # ------------------------------------------------------------------
    # Response normalization
    # ------------------------------------------------------------------

    def normalize_project(
        self, raw_project: dict
    ) -> ExternalOpportunityCandidate:
        """Normalize a raw Freelancer API project into ExternalOpportunityCandidate.

        Maps Freelancer API field names to SORIA's internal schema:
        - id -> external_id
        - title -> title
        - description -> description
        - seo_url -> source_url
        - time_created -> source_published_at
        - budget.minimum -> budget_min
        - budget.maximum -> budget_max
        - currency.code -> budget_currency
        - skills[].name -> tags
        - bid_stats.bid_count -> stored in raw_payload
        - location.country.name -> country

        Parameters
        ----------
        raw_project
            Raw project dict from the Freelancer API.

        Returns
        -------
        Normalized ExternalOpportunityCandidate.
        """
        external_id = str(raw_project.get("id") or "")

        # Title
        title = raw_project.get("title") or ""

        # Description
        description = raw_project.get("description")

        # Owner / company — Freelancer projects don't have a company name
        # in the standard search response; leave as None.
        company_name = None

        # Location and country
        location_data = raw_project.get("location") or {}
        location = None
        country = "GLOBAL"
        if isinstance(location_data, dict):
            country_data = location_data.get("country")
            if isinstance(country_data, dict):
                country = country_data.get("name") or country
            location = location_data.get("name") or location_data.get("address")

        # Source URL
        seo_url = raw_project.get("seo_url")
        source_url = (
            f"https://www.freelancer.com{seo_url}"
            if seo_url and seo_url.startswith("/")
            else seo_url
        )

        # Published date
        source_published_at = None
        date_str = raw_project.get("time_created")
        if date_str:
            try:
                # Freelancer returns "YYYY-MM-DD HH:MM:SS" format
                source_published_at = datetime.fromisoformat(date_str)
                if source_published_at.tzinfo is None:
                    source_published_at = source_published_at.replace(
                        tzinfo=timezone.utc
                    )
            except (ValueError, TypeError):
                source_published_at = None

        # Project type
        project_type = raw_project.get("type")  # "fixed" or "hourly"
        contract_type = (
            "project" if project_type == "fixed" else project_type
        )

        # Budget
        budget = raw_project.get("budget") or {}
        currency_data = raw_project.get("currency") or {}
        if isinstance(budget, dict):
            budget_min = budget.get("minimum")
            budget_max = budget.get("maximum")
        else:
            budget_min = None
            budget_max = None
        budget_currency = currency_data.get("code") if isinstance(currency_data, dict) else None

        # Skills / tags
        tags: list[str] = []
        skills = raw_project.get("skills") or []
        if isinstance(skills, list):
            for skill in skills:
                if isinstance(skill, dict):
                    name = skill.get("name")
                    if name:
                        tags.append(name.lower())

        # Jobs (another source of tags)
        jobs = raw_project.get("jobs") or []
        if isinstance(jobs, list):
            for job in jobs:
                if isinstance(job, dict):
                    name = job.get("name")
                    if name:
                        tags.append(name.lower())

        # Remote type — Freelancer projects are typically remote
        remote_type = "remote"

        # Bid count
        bid_stats = raw_project.get("bid_stats") or {}
        bid_count = (
            bid_stats.get("bid_count") if isinstance(bid_stats, dict) else None
        )

        # Build raw_payload with extra Freelancer-specific data
        raw_payload = raw_project.copy() if isinstance(raw_project, dict) else {}
        if bid_count is not None:
            raw_payload["_bid_count"] = bid_count

        return ExternalOpportunityCandidate(
            provider="freelancer",
            external_id=external_id,
            source_kind="freelance_project",
            title=title,
            company_name=company_name,
            description=description,
            location=location,
            country=country,
            language="en",
            source_url=source_url,
            source_published_at=source_published_at,
            contract_type=contract_type,
            remote_type=remote_type,
            budget_min=budget_min,
            budget_max=budget_max,
            budget_currency=budget_currency,
            tags=tags,
            raw_payload=raw_payload,
        )

    # ------------------------------------------------------------------
    # Search (requires HTTP transport)
    # ------------------------------------------------------------------

    def search_projects(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
        http_client: Optional[httpx.Client] = None,
    ) -> list[ExternalOpportunityCandidate]:
        """Search projects via the Freelancer API.

        Requires valid configuration (oauth_token).
        The HTTP transport can be injected via *http_client* parameter
        or via the constructor for testability.

        Freelancer uses Bearer token authentication via Authorization header,
        similar to OAuth2 but with a long-lived personal access token.

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
        FreelancerConfigurationError
            If required configuration is missing.
        FreelancerAPIError
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
            # Build search URL — Freelancer uses /projects/0.1/projects/active/
            search_params = self.build_search_params(query, location, limit)
            search_url = f"{self.api_base_url.rstrip('/')}/projects/0.1/projects/active/"
            headers = self._get_auth_headers()

            search_resp = client.get(
                search_url, params=search_params, headers=headers
            )
            if search_resp.status_code != 200:
                raise FreelancerAPIError(
                    f"Search failed with status {search_resp.status_code}: "
                    f"{search_resp.text}"
                )

            search_data = search_resp.json()
            result_data = search_data.get("result", {})
            raw_projects = result_data.get("projects", [])

            return [self.normalize_project(proj) for proj in raw_projects]

        finally:
            if must_close:
                client.close()
