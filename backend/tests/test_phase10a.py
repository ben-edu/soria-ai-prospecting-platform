"""Phase 10A — Real External API Configuration Foundation tests.

Covers:
- Default config values (EXTERNAL_SOURCES_MODE=mock, no credentials)
- Diagnostics response includes all Phase 10A fields
- supports_real_api is True for france_travail/adzuna_uk/freelancer
- credentials_configured is False by default, True when env vars are set
- real_api_enabled is False by default (mock mode)
- safe_status is "mock" for all providers in default mode
- Existing Phase 9A search behavior is unchanged
- Existing Phase 9B import behavior is unchanged
- No database mutation from providers/search endpoints
"""

from app.core.config import settings
from app.models.company import Company
from app.models.opportunity import Opportunity
from app.models.source_record import SourceRecord


class TestDefaultConfiguration:
    """Phase 10A default configuration values from Settings."""

    def test_default_external_sources_mode(self):
        assert settings.EXTERNAL_SOURCES_MODE == "mock"

    def test_default_credentials_are_none(self):
        assert settings.FRANCE_TRAVAIL_CLIENT_ID is None
        assert settings.FRANCE_TRAVAIL_CLIENT_SECRET is None
        assert settings.ADZUNA_UK_APP_ID is None
        assert settings.ADZUNA_UK_APP_KEY is None

    def test_default_http_timeout(self):
        assert settings.EXTERNAL_SOURCE_HTTP_TIMEOUT_SECONDS == 10


class TestDiagnosticsResponse:
    """Phase 10A diagnostics fields on GET /api/v1/external-sources/providers."""

    def test_response_has_mode_field(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200
        assert resp.json()["mode"] == "mock"

    def test_mock_only_true_by_default(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.json()["mock_only"] is True

    def test_each_provider_has_phase10a_fields(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        for p in resp.json()["providers"]:
            assert "supports_real_api" in p
            assert "credentials_configured" in p
            assert "real_api_enabled" in p
            assert "safe_status" in p
            assert "safe_message" in p

    def test_france_travail_supports_real_api(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["france_travail"]["supports_real_api"] is True

    def test_adzuna_uk_supports_real_api(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["adzuna_uk"]["supports_real_api"] is True

    def test_freelancer_now_supports_real_api(self, client):
        """Freelancer supports real API starting in Phase 10F."""
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["freelancer"]["supports_real_api"] is True

    def test_credentials_not_configured_by_default(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["france_travail"]["credentials_configured"] is False
        assert providers["adzuna_uk"]["credentials_configured"] is False
        # freelancer supports a real API in Phase 10F, but no credentials are configured by default
        assert providers["freelancer"]["credentials_configured"] is False

    def test_real_api_not_enabled_by_default(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        for p in resp.json()["providers"]:
            assert p["real_api_enabled"] is False

    def test_safe_status_mock_for_all(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        for p in resp.json()["providers"]:
            assert p["safe_status"] == "mock"

    def test_safe_message_present_and_mentions_mock(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        for p in resp.json()["providers"]:
            assert len(p["safe_message"]) > 0
            assert "mock" in p["safe_message"].lower()

    def test_all_providers_still_returned(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        provider_names = {p["provider"] for p in resp.json()["providers"]}
        assert "france_travail" in provider_names
        assert "adzuna_uk" in provider_names
        assert "freelancer" in provider_names


class TestCredentialsConfigured:
    """Diagnostics reflect configured credentials when env vars are set."""

    def test_france_travail_credentials_configured(self, client):
        original_id = settings.FRANCE_TRAVAIL_CLIENT_ID
        original_secret = settings.FRANCE_TRAVAIL_CLIENT_SECRET
        settings.FRANCE_TRAVAIL_CLIENT_ID = "test-client-id"
        settings.FRANCE_TRAVAIL_CLIENT_SECRET = "test-client-secret"
        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            ft = providers["france_travail"]
            assert ft["credentials_configured"] is True
        finally:
            settings.FRANCE_TRAVAIL_CLIENT_ID = original_id
            settings.FRANCE_TRAVAIL_CLIENT_SECRET = original_secret

    def test_adzuna_credentials_configured(self, client):
        original_id = settings.ADZUNA_UK_APP_ID
        original_key = settings.ADZUNA_UK_APP_KEY
        settings.ADZUNA_UK_APP_ID = "test-app-id"
        settings.ADZUNA_UK_APP_KEY = "test-app-key"
        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            au = providers["adzuna_uk"]
            assert au["credentials_configured"] is True
        finally:
            settings.ADZUNA_UK_APP_ID = original_id
            settings.ADZUNA_UK_APP_KEY = original_key

    def test_real_api_not_enabled_in_mock_mode_even_with_credentials(self, client):
        original_mode = settings.EXTERNAL_SOURCES_MODE
        original_id = settings.FRANCE_TRAVAIL_CLIENT_ID
        original_secret = settings.FRANCE_TRAVAIL_CLIENT_SECRET
        settings.EXTERNAL_SOURCES_MODE = "mock"
        settings.FRANCE_TRAVAIL_CLIENT_ID = "test-client-id"
        settings.FRANCE_TRAVAIL_CLIENT_SECRET = "test-client-secret"
        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            ft = providers["france_travail"]
            assert ft["credentials_configured"] is True
            assert ft["real_api_enabled"] is False
            assert ft["safe_status"] == "mock"
        finally:
            settings.EXTERNAL_SOURCES_MODE = original_mode
            settings.FRANCE_TRAVAIL_CLIENT_ID = original_id
            settings.FRANCE_TRAVAIL_CLIENT_SECRET = original_secret

    def test_missing_partial_credentials(self, client):
        """Only one of two required credentials -> not configured."""
        original_id = settings.FRANCE_TRAVAIL_CLIENT_ID
        original_secret = settings.FRANCE_TRAVAIL_CLIENT_SECRET
        settings.FRANCE_TRAVAIL_CLIENT_ID = "test-client-id"
        settings.FRANCE_TRAVAIL_CLIENT_SECRET = None
        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            assert providers["france_travail"]["credentials_configured"] is False
        finally:
            settings.FRANCE_TRAVAIL_CLIENT_ID = original_id
            settings.FRANCE_TRAVAIL_CLIENT_SECRET = original_secret


class TestPhase9ABehaviorUnchanged:
    """Existing Phase 9A search behavior is unchanged by Phase 10A changes."""

    def test_france_travail_search_returns_french_candidates(self, client):
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
            assert item["source_kind"] == "job"

    def test_adzuna_uk_search_returns_uk_candidates(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_uk/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "adzuna_uk"
        assert data["total"] > 0
        for item in data["items"]:
            assert item["provider"] == "adzuna_uk"
            assert item["country"] == "GB"
            assert item["source_kind"] == "job"

    def test_freelancer_search_returns_projects(self, client):
        resp = client.get(
            "/api/v1/external-sources/freelancer/search",
            params={"query": "kubernetes"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "freelancer"
        for item in data["items"]:
            assert item["source_kind"] == "freelance_project"

    def test_combined_search_works(self, client):
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

    def test_unknown_provider_rejected(self, client):
        resp = client.get(
            "/api/v1/external-sources/unknown_provider/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 400

    def test_blank_query_rejected(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": ""},
        )
        assert resp.status_code == 422

    def test_limit_respected(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops", "limit": 2},
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2

    def test_raw_payload_present(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        for item in resp.json()["items"]:
            assert "raw_payload" in item
            assert isinstance(item["raw_payload"], dict)


class TestPhase9BBehaviorUnchanged:
    """Existing Phase 9B import behavior is unchanged by Phase 10A changes."""

    _IMPORT_PAYLOAD = {
        "provider": "france_travail",
        "external_id": "fr-test-import-10a",
        "source_kind": "job",
        "title": "Phase 10A Test DevOps Engineer",
        "description": "Testing that Phase 9B import still works",
        "country": "FR",
        "language": "fr",
        "tags": ["devops", "cloud"],
        "raw_payload": {"test": True},
    }

    def test_import_creates_source_record_and_opportunity(self, client):
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
        assert data["source_record"]["source_name"] == "france_travail"
        assert data["source_record"]["external_id"] == "fr-test-import-10a"

    def test_duplicate_prevention(self, client):
        payload = {
            "provider": "france_travail",
            "external_id": "fr-dup-10a",
            "source_kind": "job",
            "title": "Duplicate Test 10A",
            "description": "Test dedup 10A",
            "country": "FR",
            "language": "fr",
            "tags": [],
            "raw_payload": {},
        }
        resp1 = client.post("/api/v1/external-sources/import-candidate", json=payload)
        assert resp1.status_code == 200
        assert resp1.json()["duplicate_detected"] is False

        resp2 = client.post("/api/v1/external-sources/import-candidate", json=payload)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["duplicate_detected"] is True
        assert data2["created_source_record"] is False
        assert data2["created_opportunity"] is False

    def test_unknown_provider_import_rejected(self, client):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json={
                "provider": "nonexistent",
                "external_id": "test-001",
                "source_kind": "job",
                "title": "Test",
                "description": "Test",
                "country": "FR",
                "language": "fr",
                "tags": [],
                "raw_payload": {},
            },
        )
        assert resp.status_code == 400

    def test_import_sets_correct_source_type(self, client):
        """france_travail imports get source_type=france_travail."""
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._IMPORT_PAYLOAD,
        )
        assert resp.status_code == 200
        assert resp.json()["source_record"]["source_type"] == "france_travail"

    def test_adzuna_import_uses_other_source_type(self, client):
        """Non-france_travail imports get source_type=other."""
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json={
                "provider": "adzuna_uk",
                "external_id": "uk-test-10a",
                "source_kind": "job",
                "title": "Phase 10A Test DevOps",
                "description": "Testing adzuna import",
                "country": "GB",
                "language": "en",
                "tags": ["devops"],
                "raw_payload": {},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["source_record"]["source_type"] == "other"


class TestNoDatabaseMutation:
    """Providers and search endpoints do not mutate the database."""

    def test_providers_no_db_mutation(self, client, db_session):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200

        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0

    def test_single_search_no_db_mutation(self, client, db_session):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200

        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0

    def test_combined_search_no_db_mutation(self, client, db_session):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={"providers": "france_travail,adzuna_uk", "query": "devops"},
        )
        assert resp.status_code == 200

        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0


class TestServiceLayer:
    """Direct service-layer tests for Phase 10A changes."""

    def test_list_providers_without_settings(self):
        """list_external_source_providers() works without settings."""
        from app.services.external_sources import list_external_source_providers

        providers = list_external_source_providers()
        assert len(providers) == 3
        # Without settings, diagnostics should have defaults
        for p in providers:
            assert p.supports_real_api is True or p.supports_real_api is False
            assert p.credentials_configured is False
            assert p.real_api_enabled is False
            assert p.safe_status == "mock"

    def test_list_providers_with_settings(self):
        """list_external_source_providers() works with settings."""
        from app.services.external_sources import list_external_source_providers

        providers = list_external_source_providers(settings=settings)
        assert len(providers) == 3
        for p in providers:
            assert p.credentials_configured is False
            assert p.real_api_enabled is False
            assert p.safe_status == "mock"

    def test_france_travail_credential_fields(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        ft_cls = PROVIDER_REGISTRY["france_travail"]
        assert ft_cls._credential_fields == [
            "FRANCE_TRAVAIL_CLIENT_ID",
            "FRANCE_TRAVAIL_CLIENT_SECRET",
        ]

    def test_adzuna_credential_fields(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        au_cls = PROVIDER_REGISTRY["adzuna_uk"]
        assert au_cls._credential_fields == [
            "ADZUNA_UK_APP_ID",
            "ADZUNA_UK_APP_KEY",
        ]

    def test_freelancer_credential_fields(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        fl_cls = PROVIDER_REGISTRY["freelancer"]
        assert fl_cls._credential_fields == ["FREELANCER_OAUTH_TOKEN"]
        assert fl_cls.supports_real_api is True

    def test_check_credentials_configured_all_present(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        ft_cls = PROVIDER_REGISTRY["france_travail"]
        # Temporarily set credential values on the settings object
        original_id = settings.FRANCE_TRAVAIL_CLIENT_ID
        original_secret = settings.FRANCE_TRAVAIL_CLIENT_SECRET
        settings.FRANCE_TRAVAIL_CLIENT_ID = "test"
        settings.FRANCE_TRAVAIL_CLIENT_SECRET = "test"
        try:
            assert ft_cls.check_credentials_configured(settings) is True
        finally:
            settings.FRANCE_TRAVAIL_CLIENT_ID = original_id
            settings.FRANCE_TRAVAIL_CLIENT_SECRET = original_secret

    def test_check_credentials_configured_missing(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        ft_cls = PROVIDER_REGISTRY["france_travail"]
        original_id = settings.FRANCE_TRAVAIL_CLIENT_ID
        original_secret = settings.FRANCE_TRAVAIL_CLIENT_SECRET
        settings.FRANCE_TRAVAIL_CLIENT_ID = "test"
        settings.FRANCE_TRAVAIL_CLIENT_SECRET = None
        try:
            assert ft_cls.check_credentials_configured(settings) is False
        finally:
            settings.FRANCE_TRAVAIL_CLIENT_ID = original_id
            settings.FRANCE_TRAVAIL_CLIENT_SECRET = original_secret
