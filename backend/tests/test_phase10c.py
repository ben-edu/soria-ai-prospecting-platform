"""Phase 10C — France Travail live provider gating tests.

Covers:
- Default mock mode unchanged
- france_travail mock search unchanged in mock mode
- Live mode with credentials routes to FranceTravailAPIClient (monkeypatched)
- Live mode missing credentials → mock fallback, no FranceTravailAPIClient call
- FranceTravailClientError → safe ValueError / HTTP 400
- Combined search still works with france_travail + other providers
- No DB mutation from search endpoints
- No secret leakage in error details
"""

from unittest.mock import patch

from app.core.config import settings
from app.models.company import Company
from app.models.opportunity import Opportunity
from app.models.source_record import SourceRecord
from app.schemas.external_source import ExternalOpportunityCandidate
from app.services.france_travail_client import (
    FranceTravailAPIError,
    FranceTravailAuthenticationError,
    FranceTravailConfigurationError,
)

# ---------------------------------------------------------------------------
# Sample live-mode candidate
# ---------------------------------------------------------------------------

_LIVE_CANDIDATE = ExternalOpportunityCandidate(
    provider="france_travail",
    external_id="live-ft-001",
    source_kind="job",
    title="Ingénieur DevOps Live (H/F)",
    company_name="TechCorp Live",
    description="Poste en DevOps avec déploiement continu.",
    location="Paris",
    country="FR",
    language="fr",
    source_url="https://candidat.francetravail.fr/offre/live-ft-001",
    source_published_at=None,
    contract_type="CDI",
    tags=["cdi", "devops"],
    raw_payload={"id": "live-ft-001"},
)

_LIVE_CANDIDATE_2 = ExternalOpportunityCandidate(
    provider="france_travail",
    external_id="live-ft-002",
    source_kind="job",
    title="Architecte Cloud Live (H/F)",
    company_name="CloudCorp Live",
    description="Architecture cloud multi-compte.",
    location="Lyon",
    country="FR",
    language="fr",
    contract_type="CDI",
    tags=["cdi", "cloud"],
    raw_payload={"id": "live-ft-002"},
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _configure_live_settings():
    """Set France Travail credentials + live mode on global settings."""
    original = {
        "mode": settings.EXTERNAL_SOURCES_MODE,
        "client_id": settings.FRANCE_TRAVAIL_CLIENT_ID,
        "client_secret": settings.FRANCE_TRAVAIL_CLIENT_SECRET,
    }
    settings.EXTERNAL_SOURCES_MODE = "live"
    settings.FRANCE_TRAVAIL_CLIENT_ID = "live-test-client-id"
    settings.FRANCE_TRAVAIL_CLIENT_SECRET = "live-test-client-secret"
    return original


def _configure_live_mode_only():
    """Set live mode but NO credentials."""
    original = {
        "mode": settings.EXTERNAL_SOURCES_MODE,
        "client_id": settings.FRANCE_TRAVAIL_CLIENT_ID,
        "client_secret": settings.FRANCE_TRAVAIL_CLIENT_SECRET,
    }
    settings.EXTERNAL_SOURCES_MODE = "live"
    settings.FRANCE_TRAVAIL_CLIENT_ID = None
    settings.FRANCE_TRAVAIL_CLIENT_SECRET = None
    return original


def _restore_settings(original: dict):
    """Restore settings to their original values."""
    settings.EXTERNAL_SOURCES_MODE = original["mode"]
    settings.FRANCE_TRAVAIL_CLIENT_ID = original["client_id"]
    settings.FRANCE_TRAVAIL_CLIENT_SECRET = original["client_secret"]


# ===================================================================
# Default Mock Mode
# ===================================================================


class TestDefaultMockModeUnchanged:
    """Default mock mode unchanged by Phase 10C changes."""

    def test_mock_only_still_true(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.json()["mock_only"] is True
        assert resp.json()["mode"] == "mock"

    def test_all_providers_have_mock_safe_status(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        for p in resp.json()["providers"]:
            assert p["safe_status"] == "mock"

    def test_france_travail_mock_search_no_settings(self, client):
        """Mock search returns data without any settings manipulation."""
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

    def test_mock_search_returns_expected_fields(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        for item in resp.json()["items"]:
            assert "raw_payload" in item
            assert item["language"] == "fr"
            assert item["source_kind"] == "job"


# ===================================================================
# Mock Search Unchanged
# ===================================================================


class TestMockSearchUnchanged:
    """france_travail mock search unchanged in mock mode."""

    def test_france_travail_devops_search(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) > 0
        for item in items:
            assert item["provider"] == "france_travail"

    def test_france_travail_formation_search(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "formation"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["language"] == "fr"

    def test_france_travail_location_filter(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops", "location": "Paris"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "paris" in item.get("location", "").lower()

    def test_france_travail_limit_respected(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops", "limit": 2},
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2

    def test_adzuna_uk_still_mock(self, client):
        """Adzuna UK is completely unchanged — still mock-only."""
        resp = client.get(
            "/api/v1/external-sources/adzuna_uk/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_freelancer_still_mock(self, client):
        resp = client.get(
            "/api/v1/external-sources/freelancer/search",
            params={"query": "kubernetes"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0


# ===================================================================
# Live Mode With Credentials
# ===================================================================


class TestLiveModeWithCredentials:
    """Live mode with credentials routes to FranceTravailAPIClient."""

    def test_search_routes_to_real_client(self, client):
        """Verify search_offers is called when credentials and live mode are set."""
        original = _configure_live_settings()
        try:
            with patch(
                "app.services.france_travail_client.FranceTravailAPIClient.search_offers",
                return_value=[_LIVE_CANDIDATE],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/france_travail/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 200
                assert mock_search.call_count >= 1

                data = resp.json()
                assert data["total"] >= 1
                # The result should be from the patched client (live candidate)
                assert data["items"][0]["external_id"] == "live-ft-001"
                assert data["items"][0]["title"] == "Ingénieur DevOps Live (H/F)"
        finally:
            _restore_settings(original)

    def test_search_passes_parameters(self, client):
        """Verify the real client is called with the right search parameters."""
        original = _configure_live_settings()
        try:
            with patch(
                "app.services.france_travail_client.FranceTravailAPIClient.search_offers",
                return_value=[_LIVE_CANDIDATE],
            ) as mock_search:
                client.get(
                    "/api/v1/external-sources/france_travail/search",
                    params={"query": "devops", "location": "Paris", "limit": 5},
                )
                mock_search.assert_called_once()
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["query"] == "devops"
                assert call_kwargs["location"] == "Paris"
                assert call_kwargs["limit"] == 5
        finally:
            _restore_settings(original)

    def test_live_mode_with_multiple_results(self, client):
        """Multiple results from the real client are all returned."""
        original = _configure_live_settings()
        try:
            with patch(
                "app.services.france_travail_client.FranceTravailAPIClient.search_offers",
                return_value=[_LIVE_CANDIDATE, _LIVE_CANDIDATE_2],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/france_travail/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 2
                ids = {item["external_id"] for item in data["items"]}
                assert "live-ft-001" in ids
                assert "live-ft-002" in ids
                mock_search.assert_called_once()
        finally:
            _restore_settings(original)

    def test_diagnostics_reflect_real_api_enabled(self, client):
        """Diagnostics shows real_api_enabled=True in live+credentialed mode."""
        original = _configure_live_settings()
        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            ft = providers["france_travail"]
            assert ft["real_api_enabled"] is True
            assert ft["safe_status"] == "ready"
        finally:
            _restore_settings(original)


# ===================================================================
# Live Mode Missing Credentials
# ===================================================================


class TestLiveModeMissingCredentials:
    """Live mode missing credentials does not call FranceTravailAPIClient."""

    def test_missing_credentials_falls_back_to_mock(self, client):
        """Without credentials, search falls back to mock, no real client call."""
        original = _configure_live_mode_only()
        try:
            with patch(
                "app.services.france_travail_client.FranceTravailAPIClient.search_offers",
                return_value=[_LIVE_CANDIDATE],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/france_travail/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 200
                # The real client should NOT have been called
                mock_search.assert_not_called()

                data = resp.json()
                assert data["total"] > 0
                # Results are mock data, not live
                for item in data["items"]:
                    assert item["provider"] == "france_travail"
                    # Mock IDs start with "fr-", not "live-"
                    assert item["external_id"].startswith("fr-")
        finally:
            _restore_settings(original)

    def test_diagnostics_shows_missing_credentials(self, client):
        """Diagnostics shows missing_credentials when mode != mock but no creds."""
        original = _configure_live_mode_only()
        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            ft = providers["france_travail"]
            assert ft["real_api_enabled"] is False
            assert ft["safe_status"] == "missing_credentials"
            assert "not configured" in ft["safe_message"].lower()
        finally:
            _restore_settings(original)


# ===================================================================
# Error Handling
# ===================================================================


class TestFranceTravailClientErrorHandling:
    """FranceTravailClientError subclasses become safe ValueError / HTTP 400."""

    def test_configuration_error_becomes_400(self, client):
        """FranceTravailConfigurationError raises HTTP 400."""
        original = _configure_live_settings()
        try:
            with patch(
                "app.services.france_travail_client.FranceTravailAPIClient.search_offers",
                side_effect=FranceTravailConfigurationError("FT not configured."),
            ):
                resp = client.get(
                    "/api/v1/external-sources/france_travail/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 400
                assert "france travail" in resp.json()["detail"].lower()
        finally:
            _restore_settings(original)

    def test_authentication_error_becomes_400(self, client):
        """FranceTravailAuthenticationError raises HTTP 400."""
        original = _configure_live_settings()
        try:
            with patch(
                "app.services.france_travail_client.FranceTravailAPIClient.search_offers",
                side_effect=FranceTravailAuthenticationError(
                    "Token acquisition failed."
                ),
            ):
                resp = client.get(
                    "/api/v1/external-sources/france_travail/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 400
                assert "france travail" in resp.json()["detail"].lower()
        finally:
            _restore_settings(original)

    def test_api_error_becomes_400(self, client):
        """FranceTravailAPIError raises HTTP 400."""
        original = _configure_live_settings()
        try:
            with patch(
                "app.services.france_travail_client.FranceTravailAPIClient.search_offers",
                side_effect=FranceTravailAPIError("Search failed."),
            ):
                resp = client.get(
                    "/api/v1/external-sources/france_travail/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 400
                assert "france travail" in resp.json()["detail"].lower()
        finally:
            _restore_settings(original)

    def test_no_credential_leakage_in_error(self, client):
        """Error responses never expose client_id or client_secret."""
        original = _configure_live_settings()
        try:
            with patch(
                "app.services.france_travail_client.FranceTravailAPIClient.search_offers",
                side_effect=FranceTravailConfigurationError(
                    "FRANCE_TRAVAIL_CLIENT_ID is not configured."
                ),
            ):
                resp = client.get(
                    "/api/v1/external-sources/france_travail/search",
                    params={"query": "devops"},
                )
                detail = resp.json()["detail"].lower()
                # The env var NAME is acceptable; its VALUE must not appear
                assert "live-test-client-id" not in detail
                assert "live-test-client-secret" not in detail
        finally:
            _restore_settings(original)

    def test_missing_credentials_not_an_error(self, client):
        """When credentials are missing but mode is live, no error is raised."""
        original = _configure_live_mode_only()
        try:
            resp = client.get(
                "/api/v1/external-sources/france_travail/search",
                params={"query": "devops"},
            )
            # Safe fallback to mock — no error
            assert resp.status_code == 200
            assert resp.json()["total"] > 0
        finally:
            _restore_settings(original)


# ===================================================================
# Combined Search
# ===================================================================


class TestCombinedSearchWithLiveMode:
    """Combined search still works with france_travail + other providers."""

    def test_combined_mock_mode(self, client):
        """Combined search works in default mock mode."""
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

    def test_combined_live_france_travail_mock_others(self, client):
        """Combined search: live FT + mock adzuna + mock freelancer."""
        original = _configure_live_settings()
        try:
            with patch(
                "app.services.france_travail_client.FranceTravailAPIClient.search_offers",
                return_value=[_LIVE_CANDIDATE],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/search",
                    params={
                        "providers": "france_travail,adzuna_uk,freelancer",
                        "query": "devops",
                    },
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] >= 1

                # The FranceTravailAPIClient was called
                mock_search.assert_called_once()

                providers_found = {item["provider"] for item in data["items"]}
                assert "france_travail" in providers_found
                # adzuna and freelancer still return mock data
                assert "adzuna_uk" in providers_found
                assert "freelancer" in providers_found

                # At least one live candidate is present
                live_items = [
                    item
                    for item in data["items"]
                    if item["external_id"] == "live-ft-001"
                ]
                assert len(live_items) >= 1
        finally:
            _restore_settings(original)

    def test_combined_live_missing_creds_all_mock(self, client):
        """Combined search with live mode but no credentials: all providers mock."""
        original = _configure_live_mode_only()
        try:
            with patch(
                "app.services.france_travail_client.FranceTravailAPIClient.search_offers",
                return_value=[_LIVE_CANDIDATE],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/search",
                    params={
                        "providers": "france_travail,adzuna_uk",
                        "query": "devops",
                    },
                )
                assert resp.status_code == 200
                # FranceTravailAPIClient NOT called (missing credentials)
                mock_search.assert_not_called()

                data = resp.json()
                assert data["total"] > 0
                # All results are mock (fr- prefix)
                for item in data["items"]:
                    assert item["external_id"].startswith(("fr-", "uk-"))
        finally:
            _restore_settings(original)


# ===================================================================
# No Database Mutation
# ===================================================================


class TestNoDatabaseMutation:
    """No DB mutation from search endpoints."""

    def test_providers_no_db_mutation(self, client, db_session):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200
        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0

    def test_single_search_no_db_mutation_mock_mode(self, client, db_session):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0

    def test_combined_search_no_db_mutation_mock_mode(self, client, db_session):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={"providers": "france_travail,adzuna_uk", "query": "devops"},
        )
        assert resp.status_code == 200
        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0

    def test_single_search_no_db_mutation_live_mode(self, client, db_session):
        """Even in live mode, search does not mutate DB."""
        original = _configure_live_settings()
        try:
            with patch(
                "app.services.france_travail_client.FranceTravailAPIClient.search_offers",
                return_value=[_LIVE_CANDIDATE],
            ):
                resp = client.get(
                    "/api/v1/external-sources/france_travail/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 200
                assert db_session.query(SourceRecord).count() == 0
                assert db_session.query(Company).count() == 0
                assert db_session.query(Opportunity).count() == 0
        finally:
            _restore_settings(original)


# ===================================================================
# Service Layer
# ===================================================================


class TestServiceLayer:
    """Direct service-layer tests for Phase 10C changes."""

    def test_get_external_source_provider_with_settings(self):
        """Provider receives settings and can use them."""
        from app.services.external_sources import get_external_source_provider

        # Without settings
        provider = get_external_source_provider("france_travail")
        assert provider._settings is None

        # With settings
        provider = get_external_source_provider("france_travail", settings=settings)
        assert provider._settings is settings

    def test_search_external_opportunities_accepts_settings(self):
        """search_external_opportunities accepts optional settings parameter."""
        from app.services.external_sources import search_external_opportunities

        results = search_external_opportunities(
            "france_travail",
            query="devops",
            settings=settings,
        )
        assert len(results) > 0
        for r in results:
            assert r.provider == "france_travail"

    def test_search_multiple_accepts_settings(self):
        """search_multiple_external_sources accepts optional settings parameter."""
        from app.services.external_sources import search_multiple_external_sources

        results = search_multiple_external_sources(
            ["france_travail", "adzuna_uk"],
            query="devops",
            settings=settings,
        )
        assert len(results) > 0
        providers = {r.provider for r in results}
        assert "france_travail" in providers
        assert "adzuna_uk" in providers

    def test_france_travail_provider_still_mock_by_default(self):
        """FranceTravailMockProvider is_mock is still True."""
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["france_travail"]
        assert cls.is_mock is True

    def test_adzuna_unchanged(self):
        """Adzuna provider has no live-mode routing."""
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["adzuna_uk"]
        assert cls.supports_real_api is True
        assert cls.is_mock is True
        # No live search routing for adzuna in Phase 10C
        assert cls._credential_fields == ["ADZUNA_UK_APP_ID", "ADZUNA_UK_APP_KEY"]
