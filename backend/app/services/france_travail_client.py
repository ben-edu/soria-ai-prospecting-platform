"""France Travail (ex-Pôle emploi) API client — real connector skeleton.

Phase 10B — Safe connector skeleton.

This module provides a real France Travail API connector that is NOT
used in normal runtime (EXTERNAL_SOURCES_MODE=mock by default).
It is prepared for future activation with strict safety checks.

Usage (future, when EXTERNAL_SOURCES_MODE != "mock"):
    from app.services.france_travail_client import FranceTravailAPIClient
    client = FranceTravailAPIClient(settings)
    if client.validate_configuration():
        results = client.search_offers("devops", location="Paris", limit=10)
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import Settings
from app.schemas.external_source import ExternalOpportunityCandidate

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class FranceTravailClientError(Exception):
    """Base exception for France Travail client errors."""


class FranceTravailConfigurationError(FranceTravailClientError):
    """Raised when required configuration is missing or invalid."""


class FranceTravailAuthenticationError(FranceTravailClientError):
    """Raised when OAuth2 authentication with France Travail API fails."""


class FranceTravailAPIError(FranceTravailClientError):
    """Raised when the France Travail API returns an error response."""


# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

_FT_TOKEN_URL_DEFAULT = (
    "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token?realm=partenaire"
)
_FT_API_BASE_URL_DEFAULT = "https://api.pole-emploi.fr/partenaire/offresdemploi/v2"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class FranceTravailAPIClient:
    """Real France Travail API client skeleton.

    Provides methods for configuration validation, request building,
    response normalization, and offer search.

    The HTTP transport is injectable for testability. No real HTTP calls
    are made unless explicitly enabled and configured.

    Parameters
    ----------
    settings
        Application settings instance (optional). If not provided,
        configuration will use defaults and is_ready() will return False.
    http_client
        Optional httpx.Client for HTTP transport injection.
        If not provided, one will be created when search_offers is called.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self._settings = settings
        self._http_client = http_client

        if settings is not None:
            self.token_url = settings.FRANCE_TRAVAIL_TOKEN_URL or _FT_TOKEN_URL_DEFAULT
            self.api_base_url = (
                settings.FRANCE_TRAVAIL_API_BASE_URL or _FT_API_BASE_URL_DEFAULT
            )
            self.client_id = settings.FRANCE_TRAVAIL_CLIENT_ID
            self.client_secret = settings.FRANCE_TRAVAIL_CLIENT_SECRET
            self.timeout = settings.EXTERNAL_SOURCE_HTTP_TIMEOUT_SECONDS
        else:
            self.token_url = _FT_TOKEN_URL_DEFAULT
            self.api_base_url = _FT_API_BASE_URL_DEFAULT
            self.client_id = None
            self.client_secret = None
            self.timeout = 10

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        """Return True if all required configuration is present."""
        return bool(self.client_id and self.client_secret)

    def validate_configuration(self) -> bool:
        """Validate that required configuration is present.

        Returns
        -------
        True if all required config is present.

        Raises
        ------
        FranceTravailConfigurationError
            If required config is missing.
        """
        if not self.client_id:
            raise FranceTravailConfigurationError(
                "FRANCE_TRAVAIL_CLIENT_ID is not configured."
            )
        if not self.client_secret:
            raise FranceTravailConfigurationError(
                "FRANCE_TRAVAIL_CLIENT_SECRET is not configured."
            )
        return True

    # ------------------------------------------------------------------
    # Request builders
    # ------------------------------------------------------------------

    def build_token_request_payload(self) -> dict:
        """Build the OAuth2 client credentials token request payload.

        Returns
        -------
        Dict with grant_type, client_id, client_secret, and scope.

        Note
        ----
        This method returns the payload dict only — secrets are not
        logged or included in any error messages by this method.
        """
        return {
            "grant_type": "client_credentials",
            "client_id": self.client_id or "",
            "client_secret": self.client_secret or "",
            "scope": "api_offresdemploi_v2 o2dsoffre",
        }

    def build_search_params(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        """Build search query parameters for the France Travail API.

        Maps SORIA search parameters to France Travail API fields:
        - query -> motsCles (keywords)
        - location -> lieuTravail.libelle (workplace label)
        - limit -> nombreOffres (results count, capped to 1-50)

        Parameters
        ----------
        query
            Free-text search query (maps to motsCles).
        location
            Optional location filter (maps to lieuTravail.libelle).
        limit
            Maximum number of results (maps to nombreOffres, capped at 1-50).

        Returns
        -------
        Dict of query parameters for the France Travail search endpoint.
        """
        params: dict = {
            "motsCles": query.strip(),
            "nombreOffres": min(max(1, limit), 50),
        }
        if location and location.strip():
            params["lieuTravail.libelle"] = location.strip()
        return params

    # ------------------------------------------------------------------
    # Response normalization
    # ------------------------------------------------------------------

    def normalize_offer(self, raw_offer: dict) -> ExternalOpportunityCandidate:
        """Normalize a raw France Travail API offer into ExternalOpportunityCandidate.

        Maps France Travail API field names to SORIA's internal schema:
        - id -> external_id
        - intitule -> title
        - entreprise.nom -> company_name
        - description -> description
        - lieuTravail.libelle -> location
        - typeContrat -> contract_type
        - dateCreation -> source_published_at
        - origineOffre.urlOrigine -> source_url

        Parameters
        ----------
        raw_offer
            Raw offer dict from the France Travail API.

        Returns
        -------
        Normalized ExternalOpportunityCandidate.
        """
        external_id = raw_offer.get("id") or ""

        # Title
        title = raw_offer.get("intitule") or ""

        # Company name from nested object
        entreprise = raw_offer.get("entreprise") or {}
        company_name = entreprise.get("nom") if isinstance(entreprise, dict) else None

        # Description
        description = raw_offer.get("description")

        # Location from nested object
        lieu_travail = raw_offer.get("lieuTravail") or {}
        location = lieu_travail.get("libelle") if isinstance(lieu_travail, dict) else None

        # Contract type (prefer typeContratLibelle if typeContrat is missing)
        contract_type = raw_offer.get("typeContrat")
        if not contract_type:
            contract_type = raw_offer.get("typeContratLibelle")

        # Source URL from nested object
        origine_offre = raw_offer.get("origineOffre") or {}
        source_url = (
            origine_offre.get("urlOrigine") if isinstance(origine_offre, dict) else None
        )

        # Published date
        source_published_at = None
        date_str = raw_offer.get("dateCreation")
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

        # Tags from available metadata
        tags: list[str] = []
        if contract_type:
            tags.append(contract_type.lower())
        duree = raw_offer.get("dureeTravailLibelle")
        if duree:
            tags.append(duree.lower())

        return ExternalOpportunityCandidate(
            provider="france_travail",
            external_id=external_id,
            source_kind="job",
            title=title,
            company_name=company_name,
            description=description,
            location=location,
            country="FR",
            language="fr",
            source_url=source_url,
            source_published_at=source_published_at,
            contract_type=contract_type,
            tags=tags,
            raw_payload=raw_offer.copy() if isinstance(raw_offer, dict) else {},
        )

    # ------------------------------------------------------------------
    # Search (requires HTTP transport)
    # ------------------------------------------------------------------

    def search_offers(
        self,
        query: str,
        location: Optional[str] = None,
        limit: int = 10,
        http_client: Optional[httpx.Client] = None,
    ) -> list[ExternalOpportunityCandidate]:
        """Search offers via the France Travail API.

        Requires valid configuration (client_id and client_secret).
        The HTTP transport can be injected via *http_client* parameter
        or via the constructor for testability.

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
        FranceTravailConfigurationError
            If required configuration is missing.
        FranceTravailAuthenticationError
            If token acquisition fails.
        FranceTravailAPIError
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
            # Step 1 — Acquire access token (OAuth2 client credentials)
            token_payload = self.build_token_request_payload()
            token_resp = client.post(self.token_url, data=token_payload)
            if token_resp.status_code != 200:
                raise FranceTravailAuthenticationError(
                    f"Token acquisition failed with status {token_resp.status_code}."
                )

            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise FranceTravailAuthenticationError(
                    "No access_token in token response."
                )

            # Step 2 — Search offers
            search_params = self.build_search_params(query, location, limit)
            search_url = f"{self.api_base_url.rstrip('/')}/offres/search"

            search_resp = client.get(
                search_url,
                params=search_params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if search_resp.status_code != 200:
                raise FranceTravailAPIError(
                    f"Search failed with status {search_resp.status_code}: "
                    f"{search_resp.text}"
                )

            search_data = search_resp.json()
            raw_results = search_data.get("resultats", [])

            return [self.normalize_offer(offer) for offer in raw_results]

        finally:
            if must_close:
                client.close()
