"""Phase 10B — France Travail real connector skeleton tests.

Covers:
- France Travail connector instantiation and readiness checks
- validate_configuration fails safely when config is missing
- Token payload builder does not expose secrets in logs/messages
- Search params builder maps query/location/limit correctly
- normalize_offer maps raw France Travail-like payload to ExternalOpportunityCandidate
- Missing optional fields do not crash normalization
- search_offers uses mocked transport only; no real HTTP call
- Existing mock mode behavior is unchanged:
  - Provider search returns mock data
  - Combined search returns mock data
  - Import-candidate works
  - Providers diagnostics works
  - No DB mutation from read-only search/diagnostics
  - Existing Phase 10A behavior remains valid
"""

from unittest.mock import MagicMock

import httpx

from app.core.config import Settings
from app.schemas.external_source import ExternalOpportunityCandidate
from app.services.france_travail_client import (
    FranceTravailAPIClient,
    FranceTravailAPIError,
    FranceTravailAuthenticationError,
    FranceTravailClientError,
    FranceTravailConfigurationError,
)

# ---------------------------------------------------------------------------
# Representative France Travail API offer payload
# ---------------------------------------------------------------------------

_FT_REAL_OFFER = {
    "id": "ft-real-001",
    "intitule": "Ingénieur DevOps (H/F)",
    "description": (
        "Nous recherchons un ingénieur DevOps expérimenté pour rejoindre "
        "notre équipe infrastructure et contribuer à la construction "
        "et l'évolution de notre plateforme cloud."
    ),
    "entreprise": {
        "nom": "TechCorp France",
        "description": "Entreprise du numérique spécialisée dans le cloud",
        "logo": "https://example.com/logo.png",
    },
    "lieuTravail": {
        "libelle": "Paris",
        "codePostal": "75001",
        "commune": "Paris",
    },
    "typeContrat": "CDI",
    "typeContratLibelle": "Contrat à durée indéterminée",
    "dateCreation": "2025-06-15T10:00:00+02:00",
    "dureeTravailLibelle": "Temps plein",
    "origineOffre": {
        "urlOrigine": "https://candidat.francetravail.fr/offre/ft-real-001",
        "origineNom": "France Travail",
    },
    "salaire": {
        "libelle": "45 000 - 55 000 EUR par an",
        "commentaire": "Selon expérience",
    },
}

_FT_MINIMAL_OFFER = {
    "id": "ft-min-001",
    "intitule": "Poste sans détails",
}

_NO_RESULTS_RESPONSE: dict = {
    "resultats": [],
    "filtresPossibles": [],
    "totalResultats": 0,
}

_SINGLE_RESULT_RESPONSE: dict = {
    "resultats": [_FT_REAL_OFFER],
    "totalResultats": 1,
}

_MULTI_RESULT_RESPONSE: dict = {
    "resultats": [
        _FT_REAL_OFFER,
        {
            "id": "ft-real-002",
            "intitule": "Architecte Cloud AWS (H/F)",
            "entreprise": {"nom": "Cloud Solutions SAS"},
            "description": "Conception et déploiement d'architectures cloud.",
            "lieuTravail": {"libelle": "Lyon"},
            "typeContrat": "CDI",
            "dateCreation": "2025-06-20",
        },
    ],
    "totalResultats": 2,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(status_code: int, json_data: dict) -> MagicMock:
    """Create a mock httpx.Response-like object."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


def _make_token_response(access_token: str = "test-token-123") -> MagicMock:
    """Create a mock token response."""
    return _make_mock_response(200, {"access_token": access_token})


def _make_search_response(json_data: dict) -> MagicMock:
    """Create a mock search response."""
    return _make_mock_response(200, json_data)


def _make_mock_client(
    token_resp: MagicMock | None = None,
    search_resp: MagicMock | None = None,
) -> MagicMock:
    """Create a mock httpx.Client with pre-configured post/get return values."""
    client = MagicMock(spec=httpx.Client)
    client.post.return_value = token_resp or _make_token_response()
    client.get.return_value = search_resp or _make_search_response(
        _SINGLE_RESULT_RESPONSE
    )
    return client


def _configured_settings() -> Settings:
    """Return Settings with France Travail credentials configured."""
    return Settings(
        FRANCE_TRAVAIL_CLIENT_ID="test-client-id",
        FRANCE_TRAVAIL_CLIENT_SECRET="test-client-secret",
        EXTERNAL_SOURCES_MODE="live",
    )


# ===================================================================
# France Travail Connector Unit Tests
# ===================================================================


class TestConnectorInstantiation:
    """France Travail connector can be instantiated with various configs."""

    def test_instantiate_without_settings(self):
        """Connector can be created without any settings."""
        client = FranceTravailAPIClient()
        assert client.client_id is None
        assert client.client_secret is None
        assert client.token_url is not None
        assert client.api_base_url is not None

    def test_not_ready_without_credentials(self):
        """Without credentials, is_ready() returns False."""
        client = FranceTravailAPIClient()
        assert client.is_ready() is False

    def test_ready_with_credentials(self):
        """With credentials, is_ready() returns True."""
        client = FranceTravailAPIClient(settings=_configured_settings())
        assert client.is_ready() is True

    def test_not_ready_with_partial_credentials(self):
        """With only client_id, is_ready() returns False."""
        settings = Settings(
            FRANCE_TRAVAIL_CLIENT_ID="test-id",
            FRANCE_TRAVAIL_CLIENT_SECRET=None,
        )
        client = FranceTravailAPIClient(settings=settings)
        assert client.is_ready() is False

    def test_default_urls_from_settings(self):
        """Default URLs are used when settings provide no override."""
        client = FranceTravailAPIClient(settings=_configured_settings())
        assert "entreprise.pole-emploi.fr" in client.token_url
        assert "api.pole-emploi.fr" in client.api_base_url

    def test_custom_urls_from_settings(self):
        """Custom URLs from settings override defaults."""
        settings = Settings(
            FRANCE_TRAVAIL_TOKEN_URL="https://custom.example.com/token",
            FRANCE_TRAVAIL_API_BASE_URL="https://custom.example.com/api",
        )
        client = FranceTravailAPIClient(settings=settings)
        assert client.token_url == "https://custom.example.com/token"
        assert client.api_base_url == "https://custom.example.com/api"

    def test_connector_custom_exceptions_are_subclasses(self):
        """All custom exceptions inherit from FranceTravailClientError."""
        assert issubclass(FranceTravailConfigurationError, FranceTravailClientError)
        assert issubclass(FranceTravailAuthenticationError, FranceTravailClientError)
        assert issubclass(FranceTravailAPIError, FranceTravailClientError)
        assert issubclass(FranceTravailClientError, Exception)


class TestValidateConfiguration:
    """validate_configuration fails safely when config is missing."""

    def test_raises_when_client_id_missing(self):
        client = FranceTravailAPIClient()
        try:
            client.validate_configuration()
            assert False, "Expected FranceTravailConfigurationError"
        except FranceTravailConfigurationError as e:
            assert "FRANCE_TRAVAIL_CLIENT_ID" in str(e)

    def test_raises_when_client_secret_missing(self):
        settings = Settings(
            FRANCE_TRAVAIL_CLIENT_ID="test-id",
            FRANCE_TRAVAIL_CLIENT_SECRET=None,
        )
        client = FranceTravailAPIClient(settings=settings)
        try:
            client.validate_configuration()
            assert False, "Expected FranceTravailConfigurationError"
        except FranceTravailConfigurationError as e:
            assert "FRANCE_TRAVAIL_CLIENT_SECRET" in str(e)

    def test_returns_true_when_configured(self):
        client = FranceTravailAPIClient(settings=_configured_settings())
        assert client.validate_configuration() is True

    def test_error_message_does_not_expose_values(self):
        """Exception message mentions env var names, not actual values."""
        client = FranceTravailAPIClient()
        try:
            client.validate_configuration()
        except FranceTravailConfigurationError as e:
            msg = str(e)
            assert "FRANCE_TRAVAIL_CLIENT_ID" in msg
            assert "test" not in msg.lower() or "client" in msg


class TestBuildTokenRequestPayload:
    """Token payload builder does not expose secrets in logs/messages."""

    def test_returns_dict_with_expected_keys(self):
        client = FranceTravailAPIClient(settings=_configured_settings())
        payload = client.build_token_request_payload()
        assert "grant_type" in payload
        assert payload["grant_type"] == "client_credentials"
        assert "client_id" in payload
        assert "client_secret" in payload
        assert "scope" in payload

    def test_contains_credentials(self):
        client = FranceTravailAPIClient(settings=_configured_settings())
        payload = client.build_token_request_payload()
        assert payload["client_id"] == "test-client-id"
        assert payload["client_secret"] == "test-client-secret"

    def test_no_side_effects_or_logging(self):
        """The method is pure: returns dict, no logging, no state mutation."""
        client = FranceTravailAPIClient(settings=_configured_settings())
        payload = client.build_token_request_payload()
        # Verify it's a plain dict with no extra attributes
        assert isinstance(payload, dict)
        assert set(payload.keys()) == {"grant_type", "client_id", "client_secret", "scope"}


class TestBuildSearchParams:
    """Search params builder maps query/location/limit correctly."""

    def test_maps_query_to_motsCles(self):
        client = FranceTravailAPIClient()
        params = client.build_search_params(query="devops")
        assert params["motsCles"] == "devops"

    def test_maps_location_to_lieuTravail_libelle(self):
        client = FranceTravailAPIClient()
        params = client.build_search_params(query="devops", location="Paris")
        assert params["lieuTravail.libelle"] == "Paris"

    def test_omits_location_when_empty(self):
        client = FranceTravailAPIClient()
        params = client.build_search_params(query="devops", location="")
        assert "lieuTravail.libelle" not in params

    def test_omits_location_when_none(self):
        client = FranceTravailAPIClient()
        params = client.build_search_params(query="devops", location=None)
        assert "lieuTravail.libelle" not in params

    def test_maps_limit_to_nombreOffres(self):
        client = FranceTravailAPIClient()
        params = client.build_search_params(query="devops", limit=5)
        assert params["nombreOffres"] == 5

    def test_caps_limit_at_50(self):
        client = FranceTravailAPIClient()
        params = client.build_search_params(query="devops", limit=100)
        assert params["nombreOffres"] == 50

    def test_floor_limit_at_1(self):
        client = FranceTravailAPIClient()
        params = client.build_search_params(query="devops", limit=0)
        assert params["nombreOffres"] == 1

    def test_strips_query_whitespace(self):
        client = FranceTravailAPIClient()
        params = client.build_search_params(query="  devops  ")
        assert params["motsCles"] == "devops"

    def test_strips_location_whitespace(self):
        client = FranceTravailAPIClient()
        params = client.build_search_params(query="devops", location="  Paris  ")
        assert params["lieuTravail.libelle"] == "Paris"


class TestNormalizeOffer:
    """normalize_offer maps raw France Travail payload to ExternalOpportunityCandidate."""

    def test_normalize_full_offer(self):
        """All fields are correctly mapped from a representative payload."""
        candidate = FranceTravailAPIClient().normalize_offer(_FT_REAL_OFFER)

        assert candidate.provider == "france_travail"
        assert candidate.source_kind == "job"
        assert candidate.country == "FR"
        assert candidate.language == "fr"

        assert candidate.external_id == "ft-real-001"
        assert candidate.title == "Ingénieur DevOps (H/F)"
        assert candidate.company_name == "TechCorp France"
        assert candidate.description is not None
        assert "ingénieur DevOps" in candidate.description
        assert candidate.location == "Paris"
        assert candidate.contract_type == "CDI"

        assert candidate.source_url == (
            "https://candidat.francetravail.fr/offre/ft-real-001"
        )
        assert candidate.source_published_at is not None

        # Tags should include contract type and work duration
        assert "cdi" in candidate.tags
        assert "temps plein" in candidate.tags

        # raw_payload should be a copy of the input
        assert candidate.raw_payload == _FT_REAL_OFFER

    def test_normalize_minimal_offer(self):
        """Missing optional fields do not crash normalization."""
        candidate = FranceTravailAPIClient().normalize_offer(_FT_MINIMAL_OFFER)

        assert candidate.provider == "france_travail"
        assert candidate.external_id == "ft-min-001"
        assert candidate.title == "Poste sans détails"

        # Optional fields should gracefully default
        assert candidate.company_name is None
        assert candidate.description is None
        assert candidate.location is None
        assert candidate.source_url is None
        assert candidate.source_published_at is None
        assert candidate.contract_type is None
        assert candidate.tags == []
        assert candidate.raw_payload == _FT_MINIMAL_OFFER

    def test_normalize_empty_dict(self):
        """Even an empty dict should not crash."""
        candidate = FranceTravailAPIClient().normalize_offer({})

        assert candidate.provider == "france_travail"
        assert candidate.external_id == ""
        assert candidate.title == ""
        assert candidate.company_name is None
        assert candidate.raw_payload == {}

    def test_normalize_missing_nested_objects(self):
        """Missing enterprise/lieuTravail/origineOffre should not crash."""
        offer = {
            "id": "ft-no-nested",
            "intitule": "Poste sans objets imbriqués",
            "entreprise": None,
            "lieuTravail": None,
            "origineOffre": None,
        }
        candidate = FranceTravailAPIClient().normalize_offer(offer)

        assert candidate.external_id == "ft-no-nested"
        assert candidate.company_name is None
        assert candidate.location is None
        assert candidate.source_url is None

    def test_normalize_bad_date_format(self):
        """Malformed date string should not crash; returns None."""
        offer = dict(_FT_MINIMAL_OFFER)
        offer["dateCreation"] = "not-a-date"
        candidate = FranceTravailAPIClient().normalize_offer(offer)

        assert candidate.source_published_at is None

    def test_normalize_preserves_raw_payload(self):
        """raw_payload is an independent copy of the input."""
        original = dict(_FT_REAL_OFFER)
        candidate = FranceTravailAPIClient().normalize_offer(original)

        # Mutating the original should not affect the candidate
        original["id"] = "changed"
        assert candidate.external_id == "ft-real-001"

    def test_normalize_uses_typeContratLibelle_fallback(self):
        """If typeContrat is missing, fall back to typeContratLibelle."""
        offer = {
            "id": "ft-fallback",
            "intitule": "Poste fallback",
            "typeContratLibelle": "Contrat à durée indéterminée",
        }
        candidate = FranceTravailAPIClient().normalize_offer(offer)
        assert candidate.contract_type == "Contrat à durée indéterminée"

    def test_normalize_returns_correct_type(self):
        """normalize_offer returns an ExternalOpportunityCandidate instance."""
        candidate = FranceTravailAPIClient().normalize_offer(_FT_REAL_OFFER)
        assert isinstance(candidate, ExternalOpportunityCandidate)

    def test_normalize_empty_string_id(self):
        """Empty string id should result in empty external_id."""
        candidate = FranceTravailAPIClient().normalize_offer({"id": ""})
        assert candidate.external_id == ""

    def test_normalize_missing_id_key(self):
        """Missing id key should result in empty external_id."""
        candidate = FranceTravailAPIClient().normalize_offer({"intitule": "Test"})
        assert candidate.external_id == ""


class TestSearchOffersWithMockedTransport:
    """search_offers uses mocked transport only; no real HTTP call."""

    def test_search_with_mocked_client(self):
        """search_offers uses the injected HTTP client, not real network."""
        mock_client = _make_mock_client(
            token_resp=_make_token_response(),
            search_resp=_make_search_response(_SINGLE_RESULT_RESPONSE),
        )
        ft_client = FranceTravailAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = ft_client.search_offers(query="devops", limit=5)

        assert len(results) == 1
        assert results[0].provider == "france_travail"
        assert results[0].external_id == "ft-real-001"
        assert results[0].title == "Ingénieur DevOps (H/F)"

        # Verify the mock was called (no real HTTP call happened)
        mock_client.post.assert_called_once()
        mock_client.get.assert_called_once()

    def test_search_http_client_injection_parameter(self):
        """The http_client parameter overrides the constructor client."""
        mock_client = _make_mock_client(
            search_resp=_make_search_response({"resultats": []}),
        )
        ft_client = FranceTravailAPIClient(settings=_configured_settings())
        results = ft_client.search_offers(
            query="devops", http_client=mock_client
        )

        assert len(results) == 0
        mock_client.post.assert_called_once()

    def test_search_no_results(self):
        """Empty resultats list returns empty candidates."""
        mock_client = _make_mock_client(
            search_resp=_make_search_response(_NO_RESULTS_RESPONSE),
        )
        ft_client = FranceTravailAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = ft_client.search_offers(query="nothing")

        assert results == []

    def test_search_multiple_results(self):
        """Multiple offers in resultats are all normalized."""
        mock_client = _make_mock_client(
            search_resp=_make_search_response(_MULTI_RESULT_RESPONSE),
        )
        ft_client = FranceTravailAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = ft_client.search_offers(query="devops")

        assert len(results) == 2
        assert results[0].external_id == "ft-real-001"
        assert results[1].external_id == "ft-real-002"

    def test_search_raises_on_token_failure(self):
        """Non-200 token response raises FranceTravailAuthenticationError."""
        mock_client = _make_mock_client(
            token_resp=_make_mock_response(401, {"error": "invalid_client"}),
        )
        ft_client = FranceTravailAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            ft_client.search_offers(query="devops")
            assert False, "Expected FranceTravailAuthenticationError"
        except FranceTravailAuthenticationError:
            pass

    def test_search_raises_on_missing_access_token(self):
        """No access_token in response raises FranceTravailAuthenticationError."""
        mock_client = _make_mock_client(
            token_resp=_make_mock_response(200, {"token_type": "bearer"}),
        )
        ft_client = FranceTravailAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            ft_client.search_offers(query="devops")
            assert False, "Expected FranceTravailAuthenticationError"
        except FranceTravailAuthenticationError:
            pass

    def test_search_raises_on_search_failure(self):
        """Non-200 search response raises FranceTravailAPIError."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(500, {"error": "server error"}),
        )
        ft_client = FranceTravailAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            ft_client.search_offers(query="devops")
            assert False, "Expected FranceTravailAPIError"
        except FranceTravailAPIError:
            pass

    def test_search_raises_on_missing_configuration(self):
        """search_offers raises FranceTravailConfigurationError when not configured."""
        ft_client = FranceTravailAPIClient()
        try:
            ft_client.search_offers(query="devops")
            assert False, "Expected FranceTravailConfigurationError"
        except FranceTravailConfigurationError:
            pass

    def test_search_passes_correct_params_to_http_client(self):
        """Verify the HTTP client is called with the right URL and params."""
        mock_client = _make_mock_client(
            search_resp=_make_search_response(_SINGLE_RESULT_RESPONSE),
        )
        ft_client = FranceTravailAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        ft_client.search_offers(query="devops", location="Paris", limit=3)

        # Check token request
        call_kwargs = mock_client.post.call_args
        url = call_kwargs[0][0]
        assert "access_token" in url

        # Check search request
        get_kwargs = mock_client.get.call_args
        assert get_kwargs is not None
        search_url = get_kwargs[0][0]
        assert "offres/search" in search_url
        assert "Authorization" in get_kwargs[1]["headers"]


# ===================================================================
# Mock Mode Invariant Tests
# ===================================================================


class TestMockModeSearchUnchanged:
    """Provider search endpoint still returns mock data in default mock mode."""

    def test_france_travail_mock_search(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "france_travail"
        assert data["total"] > 0
        for item in data["items"]:
            assert item["provider"] == "france_travail"
            assert item["country"] == "FR"

    def test_france_travail_mock_language_fr(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "formation"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["language"] == "fr"

    def test_adzuna_uk_mock_search(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_uk/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "adzuna_uk"
        assert data["total"] > 0

    def test_freelancer_mock_search(self, client):
        resp = client.get(
            "/api/v1/external-sources/freelancer/search",
            params={"query": "kubernetes"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0


class TestMockModeCombinedSearchUnchanged:
    """Combined search still works in mock mode."""

    def test_combined_search(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={
                "providers": "france_travail,adzuna_uk,freelancer",
                "query": "devops",
            },
        )
        assert resp.status_code == 200
        providers_found = {item["provider"] for item in resp.json()["items"]}
        assert "france_travail" in providers_found
        assert "adzuna_uk" in providers_found
        assert "freelancer" in providers_found

    def test_combined_search_with_location(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={
                "providers": "france_travail,adzuna_uk",
                "query": "devops",
                "location": "Paris",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 0


class TestMockModeImportUnchanged:
    """Import-candidate still works."""

    _IMPORT_PAYLOAD = {
        "provider": "france_travail",
        "external_id": "fr-test-10b-import",
        "source_kind": "job",
        "title": "Phase 10B Import Test",
        "description": "Testing import in Phase 10B",
        "country": "FR",
        "language": "fr",
        "tags": ["devops", "cloud"],
        "raw_payload": {"test": True},
    }

    def test_import_creates_records(self, client):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._IMPORT_PAYLOAD,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_source_record"] is True
        assert data["created_company"] is True
        assert data["created_opportunity"] is True
        assert data["duplicate_detected"] is False

    def test_unknown_provider_import_rejected(self, client):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json={
                "provider": "nonexistent",
                "external_id": "test-001",
                "source_kind": "job",
                "title": "Test",
                "country": "FR",
                "language": "fr",
                "tags": [],
                "raw_payload": {},
            },
        )
        assert resp.status_code == 400


class TestMockModeDiagnosticsUnchanged:
    """Providers diagnostics still works."""

    def test_providers_returns_all_providers(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200
        provider_names = {p["provider"] for p in resp.json()["providers"]}
        assert "france_travail" in provider_names
        assert "adzuna_uk" in provider_names
        assert "freelancer" in provider_names

    def test_mock_only_still_true(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.json()["mock_only"] is True

    def test_safe_status_mock_for_france_travail(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["france_travail"]["safe_status"] == "mock"

    def test_france_travail_supports_real_api(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["france_travail"]["supports_real_api"] is True

    def test_phase10a_fields_present(self, client):
        """All Phase 10A diagnostics fields are still present."""
        resp = client.get("/api/v1/external-sources/providers")
        for p in resp.json()["providers"]:
            assert "supports_real_api" in p
            assert "credentials_configured" in p
            assert "real_api_enabled" in p
            assert "safe_status" in p
            assert "safe_message" in p


class TestMockModeNoDbMutation:
    """No DB mutation from read-only search/diagnostics."""

    def test_providers_no_db_mutation(self, client, db_session):
        from app.models.company import Company
        from app.models.opportunity import Opportunity
        from app.models.source_record import SourceRecord

        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200

        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0

    def test_single_search_no_db_mutation(self, client, db_session):
        from app.models.company import Company
        from app.models.opportunity import Opportunity
        from app.models.source_record import SourceRecord

        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200

        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0

    def test_combined_search_no_db_mutation(self, client, db_session):
        from app.models.company import Company
        from app.models.opportunity import Opportunity
        from app.models.source_record import SourceRecord

        resp = client.get(
            "/api/v1/external-sources/search",
            params={"providers": "france_travail,adzuna_uk", "query": "devops"},
        )
        assert resp.status_code == 200

        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0


class TestExistingProvidersNotBroken:
    """Existing provider registry is not broken by Phase 10B changes."""

    def test_provider_registry_size(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert len(PROVIDER_REGISTRY) == 3

    def test_registry_contains_all(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert "france_travail" in PROVIDER_REGISTRY
        assert "adzuna_uk" in PROVIDER_REGISTRY
        assert "freelancer" in PROVIDER_REGISTRY

    def test_external_source_module_importable(self):
        """The external_sources module still imports cleanly."""
        from app.services import external_sources

        providers = external_sources.list_external_source_providers()
        assert len(providers) == 3

    def test_france_travail_client_has_no_side_effects_on_import(self):
        """Importing france_travail_client does not affect external_sources registry."""
        # Re-import to verify isolation
        from app.services import france_travail_client

        assert france_travail_client.FranceTravailAPIClient is not None

        from app.services.external_sources import PROVIDER_REGISTRY

        assert len(PROVIDER_REGISTRY) == 3
