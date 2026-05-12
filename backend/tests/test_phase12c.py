"""Phase 12C-1 — Adzuna France and Germany backend providers.

Covers:
- AdzunaUKAPIClient default country remains gb
- AdzunaUKAPIClient cross-country URL building
- Normalized FR/DE candidate metadata (country, language, provider)
- Provider registration and diagnostics
- Mock search for adzuna_fr and adzuna_de
- Combined search with uk + fr + de
- No DB mutation on search
- Import flow for FR and DE candidates
- France Travail and Freelancer unchanged
"""

import uuid
from unittest.mock import MagicMock, patch

import httpx
from sqlmodel import Session

from app.core.config import Settings
from app.schemas.external_source import ExternalOpportunityCandidate
from app.services.adzuna_uk_client import AdzunaUKAPIClient

# ---------------------------------------------------------------------------
# Representative Adzuna API job payloads
# ---------------------------------------------------------------------------

_ADZUNA_SAMPLE_JOB = {
    "id": 12345678,
    "title": "DevOps Engineer",
    "company": {"display_name": "CloudBase Ltd"},
    "location": {"display_name": "London"},
    "description": "Build and maintain CI/CD pipelines.",
    "created": "2025-06-15T10:00:00Z",
    "redirect_url": "https://www.adzuna.co.uk/jobs/land/ad/12345678",
    "contract_type": "permanent",
    "salary_min": 45000,
    "salary_max": 65000,
    "salary_currency": "GBP",
    "category": {"tag": "engineering-jobs", "label": "Engineering Jobs"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(status_code: int, json_data: dict) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


def _configured_settings() -> Settings:
    return Settings(
        ADZUNA_UK_APP_ID="test-app-id",
        ADZUNA_UK_APP_KEY="test-app-key",
        EXTERNAL_SOURCES_MODE="live",
    )


# ===================================================================
# 1. AdzunaUKAPIClient default country remains gb
# ===================================================================


class TestDefaultCountry:
    """AdzunaUKAPIClient defaults to country_code='gb'."""

    def test_default_country_code(self):
        client = AdzunaUKAPIClient()
        assert client.country_code == "gb"

    def test_default_api_base_url_contains_gb(self):
        client = AdzunaUKAPIClient()
        assert "jobs/gb" in client.api_base_url

    def test_gb_country_config_mapping(self):
        """With default gb, normalize_job returns GB/en/adzuna_uk."""
        candidate = AdzunaUKAPIClient().normalize_job(_ADZUNA_SAMPLE_JOB)
        assert candidate.provider == "adzuna_uk"
        assert candidate.country == "GB"
        assert candidate.language == "en"


# ===================================================================
# 2. AdzunaUKAPIClient can build/search URL for fr and de
# ===================================================================


class TestCrossCountryURL:
    """AdzunaUKAPIClient builds correct URLs for fr and de."""

    def test_fr_api_base_url(self):
        client = AdzunaUKAPIClient(country_code="fr")
        assert "jobs/fr" in client.api_base_url
        assert client.country_code == "fr"

    def test_de_api_base_url(self):
        client = AdzunaUKAPIClient(country_code="de")
        assert "jobs/de" in client.api_base_url
        assert client.country_code == "de"

    def test_fr_search_url_via_mocked_client(self):
        """Verify the HTTP request URL for fr contains /jobs/fr/search/1."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _make_mock_response(
            200, {"results": [], "count": 0}
        )

        au_client = AdzunaUKAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
            country_code="fr",
        )
        au_client.search_jobs(query="devops")

        call_kwargs = mock_client.get.call_args
        assert call_kwargs is not None
        search_url = call_kwargs[0][0]
        assert "jobs/fr/search/1" in search_url

    def test_de_search_url_via_mocked_client(self):
        """Verify the HTTP request URL for de contains /jobs/de/search/1."""
        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = _make_mock_response(
            200, {"results": [], "count": 0}
        )

        au_client = AdzunaUKAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
            country_code="de",
        )
        au_client.search_jobs(query="devops")

        call_kwargs = mock_client.get.call_args
        assert call_kwargs is not None
        search_url = call_kwargs[0][0]
        assert "jobs/de/search/1" in search_url

    def test_fr_normalize_job_metadata(self):
        """normalize_job with country_code=fr returns FR/fr/adzuna_fr."""
        candidate = AdzunaUKAPIClient(country_code="fr").normalize_job(
            _ADZUNA_SAMPLE_JOB
        )
        assert candidate.provider == "adzuna_fr"
        assert candidate.country == "FR"
        assert candidate.language == "fr"

    def test_de_normalize_job_metadata(self):
        """normalize_job with country_code=de returns DE/de/adzuna_de."""
        candidate = AdzunaUKAPIClient(country_code="de").normalize_job(
            _ADZUNA_SAMPLE_JOB
        )
        assert candidate.provider == "adzuna_de"
        assert candidate.country == "DE"
        assert candidate.language == "de"


# ===================================================================
# 3 & 4. Normalized FR/DE candidates have correct metadata
# ===================================================================


class TestNormalizedCandidates:
    """Mock provider returns candidates with correct country/language/provider."""

    def test_fr_candidate_metadata(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        provider = PROVIDER_REGISTRY["adzuna_fr"](settings=None)
        results = provider.search(query="devops", limit=1)
        assert len(results) >= 1
        for c in results:
            assert c.country == "FR"
            assert c.language == "fr"
            assert c.provider == "adzuna_fr"

    def test_de_candidate_metadata(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        provider = PROVIDER_REGISTRY["adzuna_de"](settings=None)
        results = provider.search(query="devops", limit=1)
        assert len(results) >= 1
        for c in results:
            assert c.country == "DE"
            assert c.language == "de"
            assert c.provider == "adzuna_de"


# ===================================================================
# 5. adzuna_fr and adzuna_de are registered providers
# ===================================================================


class TestProviderRegistration:
    """New providers are registered in the global registry."""

    def test_fr_registered(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert "adzuna_fr" in PROVIDER_REGISTRY

    def test_de_registered(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert "adzuna_de" in PROVIDER_REGISTRY

    def test_registry_size(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert len(PROVIDER_REGISTRY) == 5

    def test_registry_contains_all_expected(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        expected = {
            "france_travail",
            "adzuna_uk",
            "adzuna_fr",
            "adzuna_de",
            "freelancer",
        }
        assert set(PROVIDER_REGISTRY) == expected

    def test_fr_provider_attributes(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["adzuna_fr"]
        assert cls.provider == "adzuna_fr"
        assert cls.label == "Adzuna France"
        assert cls.country == "FR"
        assert cls.language == "fr"
        assert cls.source_kind == "job"
        assert cls.supports_real_api is True
        assert cls._credential_fields == ["ADZUNA_UK_APP_ID", "ADZUNA_UK_APP_KEY"]

    def test_de_provider_attributes(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["adzuna_de"]
        assert cls.provider == "adzuna_de"
        assert cls.label == "Adzuna Germany"
        assert cls.country == "DE"
        assert cls.language == "de"
        assert cls.source_kind == "job"
        assert cls.supports_real_api is True
        assert cls._credential_fields == ["ADZUNA_UK_APP_ID", "ADZUNA_UK_APP_KEY"]


# ===================================================================
# 6. /external-sources/providers includes adzuna_fr and adzuna_de
# ===================================================================


class TestProvidersEndpoint:
    """Providers API endpoint includes new providers."""

    def test_providers_includes_fr(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert "adzuna_fr" in providers

    def test_providers_includes_de(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert "adzuna_de" in providers

    def test_providers_count(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert len(resp.json()["providers"]) == 5

    def test_fr_provider_info(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        fr = providers["adzuna_fr"]
        assert fr["label"] == "Adzuna France"
        assert fr["country"] == "FR"
        assert fr["source_kind"] == "job"
        assert fr["supports_real_api"] is True

    def test_de_provider_info(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        de = providers["adzuna_de"]
        assert de["label"] == "Adzuna Germany"
        assert de["country"] == "DE"
        assert de["source_kind"] == "job"
        assert de["supports_real_api"] is True

    def test_adzuna_uk_still_present(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert "adzuna_uk" in providers


# ===================================================================
# 7 & 8. Mock search for adzuna_fr and adzuna_de returns results
# ===================================================================


class TestMockSearch:
    """Mock search returns deterministic results for new providers."""

    def test_fr_mock_search_returns_data(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_fr/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "adzuna_fr"
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["provider"] == "adzuna_fr"
            assert item["country"] == "FR"
            assert item["language"] == "fr"

    def test_fr_mock_search_location_filter(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_fr/search",
            params={"query": "devops", "location": "Paris"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "paris" in item.get("location", "").lower()

    def test_fr_mock_search_limit(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_fr/search",
            params={"query": "devops", "limit": 2},
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2

    def test_fr_mock_has_three_or_more_candidates(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_fr/search",
            params={"query": "cloud", "limit": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 3

    def test_de_mock_search_returns_data(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_de/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "adzuna_de"
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["provider"] == "adzuna_de"
            assert item["country"] == "DE"
            assert item["language"] == "de"

    def test_de_mock_search_location_filter(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_de/search",
            params={"query": "devops", "location": "Berlin"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "berlin" in item.get("location", "").lower()

    def test_de_mock_search_limit(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_de/search",
            params={"query": "devops", "limit": 2},
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2

    def test_de_mock_has_three_or_more_candidates(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_de/search",
            params={"query": "cloud", "limit": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 3


# ===================================================================
# 9. Combined search works with adzuna_uk, adzuna_fr, adzuna_de
# ===================================================================


class TestCombinedSearch:
    """Combined search across all three Adzuna providers."""

    def test_combined_adzuna_providers(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={
                "providers": "adzuna_uk,adzuna_fr,adzuna_de",
                "query": "devops",
            },
        )
        assert resp.status_code == 200
        providers_found = {item["provider"] for item in resp.json()["items"]}
        assert "adzuna_uk" in providers_found
        assert "adzuna_fr" in providers_found
        assert "adzuna_de" in providers_found

    def test_combined_all_providers(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={
                "providers": "france_travail,adzuna_uk,adzuna_fr,adzuna_de,freelancer",
                "query": "devops",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        providers_found = {item["provider"] for item in data["items"]}
        assert "france_travail" in providers_found
        assert "adzuna_uk" in providers_found
        assert "adzuna_fr" in providers_found
        assert "adzuna_de" in providers_found
        assert "freelancer" in providers_found
        assert data["total"] >= 5

    def test_combined_live_mode_fr(self, client):
        """Combined search: live mode for adzuna providers with credentials."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = "live-test-app-id"
        global_settings.ADZUNA_UK_APP_KEY = "live-test-app-key"

        _LIVE_FR = ExternalOpportunityCandidate(
            provider="adzuna_fr",
            external_id="live-fr-001",
            source_kind="job",
            title="Live DevOps FR",
            company_name="Live Corp FR",
            description="Live job in France.",
            location="Paris",
            country="FR",
            language="fr",
            contract_type="CDI",
            tags=["devops"],
            raw_payload={"id": "live-fr-001"},
        )

        try:
            with patch(
                "app.services.adzuna_uk_client.AdzunaUKAPIClient.search_jobs",
                return_value=[_LIVE_FR],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/search",
                    params={
                        "providers": "adzuna_uk,adzuna_fr,adzuna_de",
                        "query": "devops",
                    },
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] >= 1
                mock_search.assert_called()
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key


# ===================================================================
# 10. Search does not create SourceRecord, Company, or Opportunity
# ===================================================================


class TestNoDatabaseMutation:
    """No DB mutation from search endpoints for new providers."""

    def test_fr_search_no_db_mutation(self, client, db_session):
        from app.models.company import Company
        from app.models.opportunity import Opportunity
        from app.models.source_record import SourceRecord

        resp = client.get(
            "/api/v1/external-sources/adzuna_fr/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0

    def test_de_search_no_db_mutation(self, client, db_session):
        from app.models.company import Company
        from app.models.opportunity import Opportunity
        from app.models.source_record import SourceRecord

        resp = client.get(
            "/api/v1/external-sources/adzuna_de/search",
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
            params={
                "providers": "adzuna_uk,adzuna_fr,adzuna_de",
                "query": "devops",
            },
        )
        assert resp.status_code == 200
        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0


# ===================================================================
# 11. Import a candidate from adzuna_fr or adzuna_de
# ===================================================================


class TestImportCandidate:
    """Importing candidates from adzuna_fr/adzuna_de creates records properly."""

    def _make_candidate(
        self, provider: str, external_id: str, country: str, language: str
    ) -> ExternalOpportunityCandidate:
        return ExternalOpportunityCandidate(
            provider=provider,
            external_id=external_id,
            source_kind="job",
            title="DevOps Engineer",
            company_name="CloudBase Ltd",
            description="Build and maintain CI/CD pipelines.",
            location="Paris" if country == "FR" else "Berlin",
            country=country,
            language=language,
            source_url=None,
            source_published_at=None,
            contract_type="permanent",
            tags=["devops", "cloud"],
            raw_payload={"id": external_id},
        )

    def test_import_fr_candidate(self, db_session: Session):
        from app.core.enums import OpportunityStatus, SourceType
        from app.models.opportunity import Opportunity
        from app.models.source_record import SourceRecord
        from app.services.external_sources import import_external_candidate

        candidate = self._make_candidate(
            provider="adzuna_fr",
            external_id="import-fr-001",
            country="FR",
            language="fr",
        )
        result = import_external_candidate(candidate, db_session)

        assert result.created_source_record is True
        assert result.created_company is True
        assert result.created_opportunity is True
        assert result.duplicate_detected is False

        # Opportunity should have imported_pending_review status
        opp = db_session.get(
            Opportunity, uuid.UUID(result.opportunity["id"])
        )
        assert opp is not None
        assert opp.status == OpportunityStatus.imported_pending_review
        # source should be SourceType.other
        assert opp.source == SourceType.other

        # SourceRecord should have source_type other
        sr = db_session.get(
            SourceRecord, uuid.UUID(result.source_record["id"])
        )
        assert sr is not None
        assert sr.source_type == SourceType.other
        assert sr.source_name == "adzuna_fr"
        assert sr.external_id == "import-fr-001"

    def test_import_de_candidate(self, db_session: Session):
        from app.core.enums import OpportunityStatus, SourceType
        from app.models.opportunity import Opportunity
        from app.models.source_record import SourceRecord
        from app.services.external_sources import import_external_candidate

        candidate = self._make_candidate(
            provider="adzuna_de",
            external_id="import-de-001",
            country="DE",
            language="de",
        )
        result = import_external_candidate(candidate, db_session)

        assert result.created_source_record is True
        assert result.created_company is True
        assert result.created_opportunity is True
        assert result.duplicate_detected is False

        opp = db_session.get(
            Opportunity, uuid.UUID(result.opportunity["id"])
        )
        assert opp is not None
        assert opp.status == OpportunityStatus.imported_pending_review
        assert opp.source == SourceType.other

        sr = db_session.get(
            SourceRecord, uuid.UUID(result.source_record["id"])
        )
        assert sr is not None
        assert sr.source_type == SourceType.other
        assert sr.source_name == "adzuna_de"
        assert sr.external_id == "import-de-001"

    def test_import_fr_duplicate(self, db_session: Session):
        """Importing the same candidate twice detects duplicate."""
        from app.services.external_sources import import_external_candidate

        candidate = self._make_candidate(
            provider="adzuna_fr",
            external_id="import-fr-dup",
            country="FR",
            language="fr",
        )
        result1 = import_external_candidate(candidate, db_session)
        assert result1.created_source_record is True

        result2 = import_external_candidate(candidate, db_session)
        assert result2.duplicate_detected is True

    def test_import_de_duplicate(self, db_session: Session):
        """Importing the same DE candidate twice detects duplicate."""
        from app.services.external_sources import import_external_candidate

        candidate = self._make_candidate(
            provider="adzuna_de",
            external_id="import-de-dup",
            country="DE",
            language="de",
        )
        result1 = import_external_candidate(candidate, db_session)
        assert result1.created_source_record is True

        result2 = import_external_candidate(candidate, db_session)
        assert result2.duplicate_detected is True


# ===================================================================
# 12. Existing France Travail and Freelancer behavior unchanged
# ===================================================================


class TestExistingProvidersUnchanged:
    """France Travail and Freelancer mock search still works."""

    def test_france_travail_still_mock(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0
        for item in resp.json()["items"]:
            assert item["provider"] == "france_travail"

    def test_freelancer_still_mock(self, client):
        resp = client.get(
            "/api/v1/external-sources/freelancer/search",
            params={"query": "kubernetes"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0
        for item in resp.json()["items"]:
            assert item["provider"] == "freelancer"

    def test_providers_list_unchanged_existing(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["france_travail"]["supports_real_api"] is True
        assert providers["france_travail"]["safe_status"] == "mock"
        assert providers["freelancer"]["supports_real_api"] is True
        assert providers["freelancer"]["safe_status"] == "mock"
        assert providers["adzuna_uk"]["supports_real_api"] is True
        assert providers["adzuna_uk"]["safe_status"] == "mock"
