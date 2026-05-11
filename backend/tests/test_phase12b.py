"""Phase 12B — French Freelance Source Catalog tests.

Covers:
- GET /external-sources/source-catalog returns 200
- Returns exactly 5 entries (free_work, lehibou, codeur, malt, comet)
- All safety flags are correct across all entries
- All entries have non-empty label, description, usage_guide, interaction_mode
- Each entry has search_url or profile_url
- Endpoint does not create SourceRecord, Company, or Opportunity
- PROVIDER_REGISTRY remains unchanged and does not include the five catalog providers
- GET /external-sources/free_work/search returns 400
- POST /external-sources/import-candidate with provider=free_work returns 400
- /external-sources/providers still works
"""

from sqlmodel import Session

from app.models.company import Company
from app.models.compliance_event import ComplianceEvent
from app.models.follow_up import FollowUp
from app.models.message_draft import MessageDraft
from app.models.opportunity import Opportunity
from app.models.source_record import SourceRecord

EXPECTED_PROVIDERS = {"free_work", "lehibou", "codeur", "malt", "comet"}

SAFETY_FLAGS = {
    "is_manual_source": True,
    "supports_real_api": False,
    "requires_credentials": False,
    "human_review_required": True,
    "importable": False,
    "scraping_allowed": False,
    "external_message_allowed": False,
}

REQUIRED_TEXT_FIELDS = {"label", "description", "usage_guide", "interaction_mode"}


class TestSourceCatalogEndpoint:
    """GET /api/v1/external-sources/source-catalog"""

    def test_returns_200(self, client):
        resp = client.get("/api/v1/external-sources/source-catalog")
        assert resp.status_code == 200

    def test_returns_exactly_five_entries(self, client):
        resp = client.get("/api/v1/external-sources/source-catalog")
        entries = resp.json()
        assert len(entries) == 5

    def test_providers_are_correct(self, client):
        resp = client.get("/api/v1/external-sources/source-catalog")
        providers = {e["provider"] for e in resp.json()}
        assert providers == EXPECTED_PROVIDERS

    def test_all_safety_flags_correct(self, client):
        resp = client.get("/api/v1/external-sources/source-catalog")
        for entry in resp.json():
            for flag, expected in SAFETY_FLAGS.items():
                assert flag in entry, (
                    f"Missing safety flag '{flag}' in {entry['provider']}"
                )
                assert entry[flag] is expected, (
                    f"{entry['provider']}: {flag} should be {expected}, got {entry[flag]}"
                )

    def test_all_entries_have_non_empty_text_fields(self, client):
        resp = client.get("/api/v1/external-sources/source-catalog")
        for entry in resp.json():
            for field in REQUIRED_TEXT_FIELDS:
                val = entry.get(field, "")
                assert val and val.strip(), (
                    f"{entry['provider']}: '{field}' is empty"
                )

    def test_each_entry_has_search_or_profile_url(self, client):
        resp = client.get("/api/v1/external-sources/source-catalog")
        for entry in resp.json():
            has_search = bool(entry.get("search_url", "").strip())
            has_profile = bool(entry.get("profile_url", "").strip())
            assert has_search or has_profile, (
                f"{entry['provider']}: has neither search_url nor profile_url"
            )

    def test_all_entries_have_country_and_language(self, client):
        resp = client.get("/api/v1/external-sources/source-catalog")
        for entry in resp.json():
            assert entry.get("country") == "FR"
            assert entry.get("language") == "fr"

    def test_all_entries_have_source_kind(self, client):
        resp = client.get("/api/v1/external-sources/source-catalog")
        for entry in resp.json():
            assert entry.get("source_kind"), (
                f"{entry['provider']}: missing source_kind"
            )

    def test_endpoint_does_not_create_db_records(self, client, db_session):
        resp = client.get("/api/v1/external-sources/source-catalog")
        assert resp.status_code == 200

        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0
        assert db_session.query(MessageDraft).count() == 0
        assert db_session.query(FollowUp).count() == 0
        assert db_session.query(ComplianceEvent).count() == 0

    def test_response_is_list_of_dicts(self, client):
        resp = client.get("/api/v1/external-sources/source-catalog")
        entries = resp.json()
        assert isinstance(entries, list)
        for entry in entries:
            assert isinstance(entry, dict)
            assert "provider" in entry
            assert "label" in entry


class TestCatalogProvidersNotInRegistry:
    """Ensure catalog providers are NOT in PROVIDER_REGISTRY."""

    def test_registry_unchanged(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        for p in EXPECTED_PROVIDERS:
            assert p not in PROVIDER_REGISTRY, (
                f"Catalog provider '{p}' must not be in PROVIDER_REGISTRY"
            )

    def test_registry_still_has_original_three(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert "france_travail" in PROVIDER_REGISTRY
        assert "adzuna_uk" in PROVIDER_REGISTRY
        assert "freelancer" in PROVIDER_REGISTRY
        assert len(PROVIDER_REGISTRY) == 3


class TestCatalogProvidersRejectedBySearch:
    """GET /external-sources/{provider}/search must reject catalog providers."""

    def test_free_work_search_returns_400(self, client):
        resp = client.get(
            "/api/v1/external-sources/free_work/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "free_work" in detail

    def test_lehibou_search_returns_400(self, client):
        resp = client.get(
            "/api/v1/external-sources/lehibou/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 400

    def test_codeur_search_returns_400(self, client):
        resp = client.get(
            "/api/v1/external-sources/codeur/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 400

    def test_malt_search_returns_400(self, client):
        resp = client.get(
            "/api/v1/external-sources/malt/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 400

    def test_comet_search_returns_400(self, client):
        resp = client.get(
            "/api/v1/external-sources/comet/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 400


class TestCatalogProvidersRejectedByImport:
    """POST /external-sources/import-candidate with catalog provider."""

    _IMPORT_PAYLOAD = {
        "provider": "free_work",
        "external_id": "fw-test-001",
        "source_kind": "freelance_mission_board",
        "title": "Test Mission",
        "description": "A test mission from Free-Work",
        "country": "FR",
        "language": "fr",
        "tags": ["devops"],
        "raw_payload": {},
    }

    def test_import_free_work_returns_400(self, client):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._IMPORT_PAYLOAD,
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "free_work" in detail

    def test_import_lehibou_returns_400(self, client):
        payload = {**self._IMPORT_PAYLOAD, "provider": "lehibou"}
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        assert resp.status_code == 400

    def test_import_codeur_returns_400(self, client):
        payload = {**self._IMPORT_PAYLOAD, "provider": "codeur"}
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        assert resp.status_code == 400

    def test_import_malt_returns_400(self, client):
        payload = {**self._IMPORT_PAYLOAD, "provider": "malt"}
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        assert resp.status_code == 400

    def test_import_comet_returns_400(self, client):
        payload = {**self._IMPORT_PAYLOAD, "provider": "comet"}
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        assert resp.status_code == 400


class TestExistingProvidersEndpoint:
    """GET /api/v1/external-sources/providers still works."""

    def test_providers_returns_200(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200

    def test_providers_still_has_original_three(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"] for p in resp.json()["providers"]}
        assert "france_travail" in providers
        assert "adzuna_uk" in providers
        assert "freelancer" in providers
        assert len(providers) == 3

    def test_providers_does_not_include_catalog_providers(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"] for p in resp.json()["providers"]}
        for p in EXPECTED_PROVIDERS:
            assert p not in providers, (
                f"Catalog provider '{p}' must not appear in /providers"
            )

    def test_providers_still_mock_only(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.json()["mock_only"] is True


class TestExistingSearchUnchanged:
    """Existing search functionality is unchanged."""

    def test_france_travail_search_still_works(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_combined_search_still_works(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={"providers": "france_travail,adzuna_uk", "query": "devops"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_unknown_provider_still_rejected(self, client):
        resp = client.get(
            "/api/v1/external-sources/unknown_provider/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 400


class TestExistingImportUnchanged:
    """Existing import functionality is unchanged."""

    def test_import_france_travail_still_works(self, client):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json={
                "provider": "france_travail",
                "external_id": "fr-phase12b-001",
                "source_kind": "job",
                "title": "Phase 12B DevOps",
                "description": "Regression test",
                "country": "FR",
                "language": "fr",
                "tags": ["devops"],
                "raw_payload": {},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["created_source_record"] is True
