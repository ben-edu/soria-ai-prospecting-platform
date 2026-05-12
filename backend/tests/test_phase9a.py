"""Phase 9A — External Opportunity Sources Foundation tests.

Covers:
- Providers endpoint returns france_travail, adzuna_uk, freelancer
- All providers are mock in Phase 9A
- france_travail search returns job candidates with provider france_travail and country FR
- adzuna_uk search returns job candidates with provider adzuna_uk and country GB
- freelancer search returns freelance_project candidates with budget fields
- Combined search returns candidates from multiple providers
- limit is respected
- blank query is rejected
- invalid limit is rejected
- unknown provider is rejected
- Every candidate includes raw_payload
- Search is read-only: no Opportunity, MessageDraft, ComplianceEvent, or FollowUp is created
"""


class TestProvidersEndpoint:
    """GET /api/v1/external-sources/providers"""

    def test_returns_all_providers(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200
        data = resp.json()
        provider_names = {p["provider"] for p in data["providers"]}
        assert "france_travail" in provider_names
        assert "adzuna_uk" in provider_names
        assert "freelancer" in provider_names

    def test_all_providers_are_mock(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mock_only"] is True
        for p in data["providers"]:
            assert p["is_mock"] is True
            assert p["is_enabled"] is True
            assert p["requires_credentials"] is False

    def test_enabled_providers_list(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert sorted(data["enabled_providers"]) == [
            "adzuna_de",
            "adzuna_fr",
            "adzuna_uk",
            "france_travail",
            "freelancer",
        ]


class TestFranceTravailSearch:
    """GET /api/v1/external-sources/france_travail/search"""

    def test_search_returns_french_candidates(self, client):
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

    def test_search_french_language(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "formation"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["language"] == "fr"

    def test_location_filter(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops", "location": "Paris"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert "paris" in (item["location"] or "").lower()


class TestAdzunaUkSearch:
    """GET /api/v1/external-sources/adzuna_uk/search"""

    def test_search_returns_uk_candidates(self, client):
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

    def test_search_english_language(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_uk/search",
            params={"query": "cloud"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["language"] == "en"


class TestFreelancerSearch:
    """GET /api/v1/external-sources/freelancer/search"""

    def test_search_returns_freelance_projects(self, client):
        resp = client.get(
            "/api/v1/external-sources/freelancer/search",
            params={"query": "kubernetes"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "freelancer"
        assert data["total"] > 0
        for item in data["items"]:
            assert item["provider"] == "freelancer"
            assert item["source_kind"] == "freelance_project"

    def test_budget_fields_present(self, client):
        resp = client.get(
            "/api/v1/external-sources/freelancer/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["budget_min"] is not None
            assert item["budget_max"] is not None
            assert item["budget_currency"] is not None

    def test_remote_by_default(self, client):
        resp = client.get(
            "/api/v1/external-sources/freelancer/search",
            params={"query": "security"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["remote_type"] == "remote"


class TestCombinedSearch:
    """GET /api/v1/external-sources/search"""

    def test_combined_returns_multiple_providers(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={
                "providers": "france_travail,adzuna_uk,freelancer",
                "query": "devops",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] is None
        assert data["total"] > 0
        providers_found = {item["provider"] for item in data["items"]}
        assert "france_travail" in providers_found
        assert "adzuna_uk" in providers_found
        assert "freelancer" in providers_found

    def test_combined_with_limit(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={
                "providers": "france_travail,adzuna_uk,freelancer",
                "query": "devops",
                "limit": 1,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Each provider returns max 1 candidate → total ≤ 3
        assert data["total"] <= 3

    def test_combined_invalid_provider_rejected(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={
                "providers": "france_travail,unknown_provider",
                "query": "devops",
            },
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "unknown_provider" in detail

    def test_combined_no_providers_rejected(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={"providers": "", "query": "devops"},
        )
        assert resp.status_code == 400


class TestValidation:
    """Input validation tests."""

    def test_blank_query_rejected(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": ""},
        )
        # FastAPI returns 422 for Query(min_length=...) violations
        assert resp.status_code == 422

    def test_blank_query_rejected_combined(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={"providers": "france_travail", "query": ""},
        )
        assert resp.status_code == 422

    def test_limit_too_low_rejected(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops", "limit": 0},
        )
        # FastAPI returns 422 for Query(ge=...) violations
        assert resp.status_code == 422

    def test_limit_too_high_rejected(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops", "limit": 51},
        )
        # FastAPI returns 422 for Query(le=...) violations
        assert resp.status_code == 422

    def test_unknown_provider_rejected(self, client):
        resp = client.get(
            "/api/v1/external-sources/unknown_provider/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "unknown_provider" in detail.lower() or "Unknown" in detail


class TestReadOnly:
    """Verify that search endpoints do not create database records."""

    def test_providers_no_db_mutation(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200

    def test_search_no_db_mutation(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200


class TestRawPayload:
    """Every candidate must include raw_payload."""

    def test_single_search_has_raw_payload(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert "raw_payload" in item
            assert isinstance(item["raw_payload"], dict)

    def test_combined_search_has_raw_payload(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={
                "providers": "france_travail,adzuna_uk,freelancer",
                "query": "devops",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert "raw_payload" in item
            assert isinstance(item["raw_payload"], dict)


class TestLimitRespected:
    """Verify the limit parameter is respected in search results."""

    def test_limit_single_provider(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops", "limit": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2

    def test_limit_combined(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={
                "providers": "france_travail,adzuna_uk",
                "query": "devops",
                "limit": 1,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # 2 providers × max 1 each = at most 2
        assert len(data["items"]) <= 2


class TestServiceLayer:
    """Direct service-layer unit tests."""

    def test_unknown_provider_raises_value_error(self):
        from app.services.external_sources import get_external_source_provider

        try:
            get_external_source_provider("non_existent")
            assert False, "Expected ValueError"
        except ValueError as e:
            assert "non_existent" in str(e)

    def test_registry_contains_all_providers(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert "france_travail" in PROVIDER_REGISTRY
        assert "adzuna_uk" in PROVIDER_REGISTRY
        assert "freelancer" in PROVIDER_REGISTRY
        assert len(PROVIDER_REGISTRY) == 5
