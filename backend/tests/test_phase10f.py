"""Phase 10F — Freelancer real connector tests.

Covers:
- Config readiness (is_ready, validate_configuration)
- Missing token safe failure
- No secret leakage
- Search param mapping (query, location, limit)
- Normalization of typical Freelancer project response
- Minimal/empty response handling
- Mocked HTTP transport success/failure
- Provider diagnostics (credentials_configured, real_api_enabled, safe_status)
- Live mode with credentials routes to FreelancerAPIClient
- Live mode missing credentials falls back to mock
- Mock mode unchanged
- No DB mutation on search
- France Travail & Adzuna UK behavior unchanged
- Combined provider search still works
"""

from unittest.mock import MagicMock, patch

import httpx

from app.core.config import Settings
from app.schemas.external_source import ExternalOpportunityCandidate
from app.services.freelancer_client import (
    FreelancerAPIClient,
    FreelancerAPIError,
    FreelancerClientError,
    FreelancerConfigurationError,
)

# ---------------------------------------------------------------------------
# Representative Freelancer API project payloads
# ---------------------------------------------------------------------------

_FREELANCER_REAL_PROJECT = {
    "id": 123456,
    "title": "Kubernetes Cluster Setup and Migration",
    "description": (
        "Need an experienced freelancer to set up a production-grade "
        "Kubernetes cluster and migrate existing workloads."
    ),
    "owner_id": 98765,
    "type": "fixed",
    "budget": {"minimum": 3000.0, "maximum": 8000.0},
    "currency": {"id": 1, "code": "USD", "sign": "$", "name": "US Dollar"},
    "skills": [
        {"id": 101, "name": "Kubernetes"},
        {"id": 102, "name": "DevOps"},
        {"id": 103, "name": "Cloud"},
    ],
    "jobs": [
        {"id": 201, "name": "DevOps"},
    ],
    "location": {
        "country": {"name": "United States"},
        "name": "Remote",
    },
    "seo_url": "/projects/kubernetes-cluster-setup-123456",
    "time_created": "2025-08-01 12:00:00",
    "bid_stats": {"bid_count": 5, "bid_avg": 4500.0, "bid_max": 8000.0},
    "status": "active",
}

_FREELANCER_MINIMAL_PROJECT: dict = {
    "id": 654321,
    "title": "Minimal Project",
}

_NO_RESULTS_RESPONSE: dict = {
    "status": "success",
    "result": {
        "projects": [],
        "total_count": 0,
    },
}

_SINGLE_RESULT_RESPONSE: dict = {
    "status": "success",
    "result": {
        "projects": [_FREELANCER_REAL_PROJECT],
        "total_count": 1,
    },
}

_MULTI_RESULT_RESPONSE: dict = {
    "status": "success",
    "result": {
        "projects": [
            _FREELANCER_REAL_PROJECT,
            {
                "id": 234567,
                "title": "AWS Infrastructure Automation",
                "description": "Design and implement Terraform modules.",
                "type": "fixed",
                "budget": {"minimum": 2500.0, "maximum": 6000.0},
                "currency": {"code": "USD"},
                "skills": [
                    {"id": 104, "name": "AWS"},
                    {"id": 105, "name": "Terraform"},
                ],
                "seo_url": "/projects/aws-infrastructure-234567",
                "time_created": "2025-08-05 10:00:00",
                "bid_stats": {"bid_count": 3},
                "status": "active",
            },
        ],
        "total_count": 2,
    },
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


def _make_mock_client(
    search_resp: MagicMock | None = None,
) -> MagicMock:
    """Create a mock httpx.Client with pre-configured get return value."""
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = search_resp or _make_mock_response(
        200, _SINGLE_RESULT_RESPONSE
    )
    return client


def _configured_settings() -> Settings:
    """Return Settings with Freelancer credentials configured."""
    return Settings(
        FREELANCER_OAUTH_TOKEN="test-oauth-token",
        EXTERNAL_SOURCES_MODE="live",
    )


# ===================================================================
# Freelancer Connector Unit Tests
# ===================================================================


class TestConnectorInstantiation:
    """Freelancer connector can be instantiated with various configs."""

    def test_instantiate_without_settings(self):
        """Connector can be created without any settings."""
        client = FreelancerAPIClient()
        assert client.oauth_token is None
        assert client.api_base_url is not None

    def test_not_ready_without_token(self):
        """Without token, is_ready() returns False."""
        client = FreelancerAPIClient()
        assert client.is_ready() is False

    def test_ready_with_token(self):
        """With token, is_ready() returns True."""
        client = FreelancerAPIClient(settings=_configured_settings())
        assert client.is_ready() is True

    def test_default_base_url(self):
        """Default API base URL is used when settings provide no override."""
        client = FreelancerAPIClient(settings=_configured_settings())
        assert "freelancer.com" in client.api_base_url

    def test_custom_base_url_from_settings(self):
        """Custom base URL from settings overrides default."""
        settings = Settings(
            FREELANCER_API_BASE_URL="https://custom.example.com/api",
        )
        client = FreelancerAPIClient(settings=settings)
        assert client.api_base_url == "https://custom.example.com/api"

    def test_custom_exceptions_are_subclasses(self):
        """All custom exceptions inherit from FreelancerClientError."""
        assert issubclass(FreelancerConfigurationError, FreelancerClientError)
        assert issubclass(FreelancerAPIError, FreelancerClientError)
        assert issubclass(FreelancerClientError, Exception)


class TestValidateConfiguration:
    """validate_configuration fails safely when config is missing."""

    def test_raises_when_token_missing(self):
        client = FreelancerAPIClient()
        try:
            client.validate_configuration()
            assert False, "Expected FreelancerConfigurationError"
        except FreelancerConfigurationError as e:
            assert "FREELANCER_OAUTH_TOKEN" in str(e)

    def test_returns_true_when_configured(self):
        client = FreelancerAPIClient(settings=_configured_settings())
        assert client.validate_configuration() is True

    def test_error_message_does_not_expose_values(self):
        """Exception message mentions env var name, not actual value."""
        client = FreelancerAPIClient()
        try:
            client.validate_configuration()
        except FreelancerConfigurationError as e:
            msg = str(e)
            assert "FREELANCER_OAUTH_TOKEN" in msg
            # Values must not appear in error message
            assert "test" not in msg

    def test_no_secret_logging_in_validate(self):
        """validate_configuration does not log or expose secrets."""
        client = FreelancerAPIClient(
            settings=Settings(FREELANCER_OAUTH_TOKEN="super-secret-token")
        )
        try:
            client.validate_configuration()
        except FreelancerConfigurationError as e:
            msg = str(e)
            assert "super-secret-token" not in msg

    def test_raises_with_empty_token(self):
        """Empty string token should fail validation."""
        settings = Settings(FREELANCER_OAUTH_TOKEN="")
        client = FreelancerAPIClient(settings=settings)
        try:
            client.validate_configuration()
            assert False, "Expected FreelancerConfigurationError"
        except FreelancerConfigurationError as e:
            assert "FREELANCER_OAUTH_TOKEN" in str(e)


class TestBuildSearchParams:
    """Search param builder maps query/location/limit correctly."""

    def test_maps_query_to_query(self):
        client = FreelancerAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops")
        assert params["query"] == "devops"

    def test_maps_location(self):
        client = FreelancerAPIClient(settings=_configured_settings())
        params = client.build_search_params(
            query="devops", location="United States"
        )
        assert params["location"] == "United States"

    def test_omits_location_when_empty(self):
        client = FreelancerAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", location="")
        assert "location" not in params

    def test_omits_location_when_none(self):
        client = FreelancerAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", location=None)
        assert "location" not in params

    def test_maps_limit(self):
        client = FreelancerAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", limit=5)
        assert params["limit"] == 5

    def test_caps_limit_at_50(self):
        client = FreelancerAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", limit=100)
        assert params["limit"] == 50

    def test_floor_limit_at_1(self):
        client = FreelancerAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", limit=0)
        assert params["limit"] == 1

    def test_strips_query_whitespace(self):
        client = FreelancerAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="  devops  ")
        assert params["query"] == "devops"

    def test_strips_location_whitespace(self):
        client = FreelancerAPIClient(settings=_configured_settings())
        params = client.build_search_params(
            query="devops", location="  United States  "
        )
        assert params["location"] == "United States"

    def test_includes_offset_default(self):
        client = FreelancerAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops")
        assert params["offset"] == 0


class TestNormalizeProject:
    """normalize_project maps raw Freelancer payload to ExternalOpportunityCandidate."""

    def test_normalize_full_project(self):
        """All fields are correctly mapped from a representative payload."""
        candidate = FreelancerAPIClient().normalize_project(
            _FREELANCER_REAL_PROJECT
        )

        assert candidate.provider == "freelancer"
        assert candidate.source_kind == "freelance_project"
        assert candidate.country == "United States"
        assert candidate.language == "en"

        assert candidate.external_id == "123456"
        assert candidate.title == "Kubernetes Cluster Setup and Migration"
        assert candidate.description is not None
        assert "production-grade" in candidate.description
        assert candidate.location == "Remote"

        # Contract type derived from project type
        assert candidate.contract_type == "project"
        assert candidate.remote_type == "remote"

        # Source URL from seo_url
        assert candidate.source_url is not None
        assert "freelancer.com" in candidate.source_url
        assert "kubernetes-cluster-setup-123456" in candidate.source_url

        # Published date
        assert candidate.source_published_at is not None

        # Budget fields
        assert candidate.budget_min == 3000.0
        assert candidate.budget_max == 8000.0
        assert candidate.budget_currency == "USD"

        # Tags from skills and jobs
        assert "kubernetes" in candidate.tags
        assert "devops" in candidate.tags
        assert "cloud" in candidate.tags

        # raw_payload should be a copy of the input
        assert candidate.raw_payload is not None
        assert candidate.raw_payload.get("_bid_count") == 5

    def test_normalize_minimal_project(self):
        """Missing optional fields do not crash normalization."""
        candidate = FreelancerAPIClient().normalize_project(
            _FREELANCER_MINIMAL_PROJECT
        )

        assert candidate.provider == "freelancer"
        assert candidate.external_id == "654321"
        assert candidate.title == "Minimal Project"

        # Optional fields should gracefully default
        assert candidate.company_name is None
        assert candidate.description is None
        assert candidate.location is None
        assert candidate.country == "GLOBAL"
        assert candidate.language == "en"
        assert candidate.source_url is None
        assert candidate.source_published_at is None
        assert candidate.contract_type is None
        assert candidate.remote_type == "remote"
        assert candidate.budget_min is None
        assert candidate.budget_max is None
        assert candidate.budget_currency is None
        assert candidate.tags == []
        assert candidate.raw_payload == _FREELANCER_MINIMAL_PROJECT

    def test_normalize_empty_dict(self):
        """Even an empty dict should not crash."""
        candidate = FreelancerAPIClient().normalize_project({})

        assert candidate.provider == "freelancer"
        assert candidate.external_id == ""
        assert candidate.title == ""
        assert candidate.company_name is None
        assert candidate.country == "GLOBAL"
        assert candidate.language == "en"
        assert candidate.raw_payload == {}

    def test_normalize_missing_nested_objects(self):
        """Missing budget/currency/skills/location should not crash."""
        project = {
            "id": 999,
            "title": "No Nested Objects",
            "budget": None,
            "currency": None,
            "skills": None,
            "location": None,
        }
        candidate = FreelancerAPIClient().normalize_project(project)

        assert candidate.external_id == "999"
        assert candidate.budget_min is None
        assert candidate.budget_max is None
        assert candidate.budget_currency is None
        assert candidate.tags == []
        assert candidate.country == "GLOBAL"

    def test_normalize_bad_date_format(self):
        """Malformed date string should not crash; returns None."""
        project = dict(_FREELANCER_MINIMAL_PROJECT)
        project["time_created"] = "not-a-date"
        candidate = FreelancerAPIClient().normalize_project(project)

        assert candidate.source_published_at is None

    def test_normalize_preserves_raw_payload(self):
        """raw_payload is an independent copy of the input."""
        original = dict(_FREELANCER_REAL_PROJECT)
        candidate = FreelancerAPIClient().normalize_project(original)

        # Mutating the original should not affect the candidate
        original["id"] = 99999999
        assert candidate.external_id == "123456"

    def test_normalize_returns_correct_type(self):
        """normalize_project returns an ExternalOpportunityCandidate instance."""
        candidate = FreelancerAPIClient().normalize_project(
            _FREELANCER_REAL_PROJECT
        )
        assert isinstance(candidate, ExternalOpportunityCandidate)

    def test_normalize_missing_id_key(self):
        """Missing id key should result in empty external_id."""
        candidate = FreelancerAPIClient().normalize_project(
            {"title": "Test"}
        )
        assert candidate.external_id == ""

    def test_normalize_int_id_becomes_string(self):
        """Integer id should be converted to string."""
        candidate = FreelancerAPIClient().normalize_project(
            {"id": 42, "title": "Test"}
        )
        assert candidate.external_id == "42"
        assert isinstance(candidate.external_id, str)

    def test_normalize_with_hourly_type(self):
        """Hourly project type maps to contract_type='hourly'."""
        project = dict(_FREELANCER_REAL_PROJECT)
        project["type"] = "hourly"
        candidate = FreelancerAPIClient().normalize_project(project)
        assert candidate.contract_type == "hourly"

    def test_normalize_with_bid_count(self):
        """Bid count is stored in raw_payload."""
        candidate = FreelancerAPIClient().normalize_project(
            _FREELANCER_REAL_PROJECT
        )
        assert candidate.raw_payload.get("_bid_count") == 5

    def test_normalize_without_bid_stats(self):
        """Missing bid_stats does not crash."""
        project = {
            "id": 777,
            "title": "No Bids Yet",
        }
        candidate = FreelancerAPIClient().normalize_project(project)
        assert candidate.raw_payload.get("_bid_count") is None

    def test_normalize_without_skills_list(self):
        """Empty skills list results in empty tags."""
        project = {
            "id": 888,
            "title": "No Skills",
            "skills": [],
            "jobs": [],
        }
        candidate = FreelancerAPIClient().normalize_project(project)
        assert candidate.tags == []

    def test_normalize_seo_url_without_slash(self):
        """seo_url that doesn't start with '/' is used as-is."""
        project = dict(_FREELANCER_REAL_PROJECT)
        project["seo_url"] = "https://custom.example.com/project/123"
        candidate = FreelancerAPIClient().normalize_project(project)
        assert candidate.source_url == "https://custom.example.com/project/123"

    def test_normalize_country_from_location_data(self):
        """Country is extracted from location.country.name."""
        project = {
            "id": 1001,
            "title": "With Country",
            "location": {
                "country": {"name": "United Kingdom"},
            },
        }
        candidate = FreelancerAPIClient().normalize_project(project)
        assert candidate.country == "United Kingdom"

    def test_normalize_default_global_country(self):
        """Country defaults to GLOBAL when location is missing."""
        candidate = FreelancerAPIClient().normalize_project(
            {"id": 1002, "title": "Global Project"}
        )
        assert candidate.country == "GLOBAL"

    def test_normalize_id_none(self):
        """None id should result in empty string external_id."""
        candidate = FreelancerAPIClient().normalize_project(
            {"id": None, "title": "Test"}
        )
        assert candidate.external_id == ""


class TestSearchProjectsWithMockedTransport:
    """search_projects uses mocked transport only; no real HTTP call."""

    def test_search_with_mocked_client(self):
        """search_projects uses the injected HTTP client, not real network."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _SINGLE_RESULT_RESPONSE),
        )
        fl_client = FreelancerAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = fl_client.search_projects(query="kubernetes", limit=5)

        assert len(results) == 1
        assert results[0].provider == "freelancer"
        assert results[0].external_id == "123456"
        assert results[0].title == "Kubernetes Cluster Setup and Migration"

        # Verify the mock was called (no real HTTP call happened)
        mock_client.get.assert_called_once()

    def test_search_http_client_injection_parameter(self):
        """The http_client parameter overrides the constructor client."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _NO_RESULTS_RESPONSE),
        )
        fl_client = FreelancerAPIClient(settings=_configured_settings())
        results = fl_client.search_projects(
            query="nothing", http_client=mock_client
        )

        assert len(results) == 0
        mock_client.get.assert_called_once()

    def test_search_no_results(self):
        """Empty results list returns empty candidates."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _NO_RESULTS_RESPONSE),
        )
        fl_client = FreelancerAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = fl_client.search_projects(query="nothing")

        assert results == []

    def test_search_multiple_results(self):
        """Multiple projects in results are all normalized."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _MULTI_RESULT_RESPONSE),
        )
        fl_client = FreelancerAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = fl_client.search_projects(query="devops")

        assert len(results) == 2
        assert results[0].external_id == "123456"
        assert results[1].external_id == "234567"

    def test_search_raises_on_api_failure(self):
        """Non-200 search response raises FreelancerAPIError."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(500, {"error": "server error"}),
        )
        fl_client = FreelancerAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            fl_client.search_projects(query="devops")
            assert False, "Expected FreelancerAPIError"
        except FreelancerAPIError:
            pass

    def test_search_raises_on_unauthorized(self):
        """401 response raises FreelancerAPIError."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(401, {"error": "unauthorized"}),
        )
        fl_client = FreelancerAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            fl_client.search_projects(query="devops")
            assert False, "Expected FreelancerAPIError"
        except FreelancerAPIError:
            pass

    def test_search_raises_on_missing_configuration(self):
        """search_projects raises FreelancerConfigurationError when not configured."""
        fl_client = FreelancerAPIClient()
        try:
            fl_client.search_projects(query="devops")
            assert False, "Expected FreelancerConfigurationError"
        except FreelancerConfigurationError:
            pass

    def test_search_passes_correct_params_to_http_client(self):
        """Verify the HTTP client is called with the right URL, params, and headers."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _SINGLE_RESULT_RESPONSE),
        )
        fl_client = FreelancerAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        fl_client.search_projects(
            query="kubernetes", location="United States", limit=3
        )

        # Check the search request
        call_kwargs = mock_client.get.call_args
        assert call_kwargs is not None
        search_url = call_kwargs[0][0]
        assert "projects/0.1/projects/active/" in search_url

        # Check query params
        params = call_kwargs[1].get("params", {})
        assert params["query"] == "kubernetes"
        assert params["location"] == "United States"
        assert params["limit"] == 3

        # Check auth header
        headers = call_kwargs[1].get("headers", {})
        assert "Authorization" in headers
        assert "Bearer" in headers["Authorization"]
        assert "test-oauth-token" in headers["Authorization"]

    def test_error_message_contains_no_secrets(self):
        """Error responses never expose the OAuth token."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(401, {"error": "unauthorized"}),
        )
        fl_client = FreelancerAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            fl_client.search_projects(query="devops")
        except FreelancerAPIError as e:
            msg = str(e)
            assert "test-oauth-token" not in msg

    def test_constructor_timeout_from_settings(self):
        """Timeout is read from settings when available."""
        settings = Settings(
            FREELANCER_OAUTH_TOKEN="test-token",
            EXTERNAL_SOURCE_HTTP_TIMEOUT_SECONDS=30,
        )
        client = FreelancerAPIClient(settings=settings)
        assert client.timeout == 30

    def test_auth_header_with_token(self):
        """Authorization header contains Bearer token."""
        client = FreelancerAPIClient(settings=_configured_settings())
        headers = client._get_auth_headers()
        assert headers["Authorization"] == "Bearer test-oauth-token"

    def test_auth_header_without_token(self):
        """Authorization header has empty token when not configured."""
        client = FreelancerAPIClient()
        headers = client._get_auth_headers()
        assert headers["Authorization"] == "Bearer "


# ===================================================================
# Live-Mode Gating Tests
# ===================================================================


class TestFreelancerLiveModeWithCredentials:
    """Live mode with credentials routes to FreelancerAPIClient."""

    def test_search_routes_to_real_client(self, client):
        """Verify search_projects is called when credentials and live mode are set."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = "live-test-token"

        _LIVE_CANDIDATE = ExternalOpportunityCandidate(
            provider="freelancer",
            external_id="live-fl-001",
            source_kind="freelance_project",
            title="Live Kubernetes Project",
            company_name=None,
            description="Live project description.",
            location="Remote",
            country="GLOBAL",
            language="en",
            contract_type="project",
            remote_type="remote",
            tags=["kubernetes", "devops"],
            raw_payload={"id": "live-fl-001"},
        )

        try:
            with patch(
                "app.services.freelancer_client.FreelancerAPIClient.search_projects",
                return_value=[_LIVE_CANDIDATE],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/freelancer/search",
                    params={"query": "kubernetes"},
                )
                assert resp.status_code == 200
                assert mock_search.call_count >= 1

                data = resp.json()
                assert data["total"] >= 1
                assert data["items"][0]["external_id"] == "live-fl-001"
                assert data["items"][0]["title"] == "Live Kubernetes Project"
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token

    def test_search_passes_parameters(self, client):
        """Verify the real client is called with the right search parameters."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = "live-test-token"

        _LIVE_CANDIDATE = ExternalOpportunityCandidate(
            provider="freelancer",
            external_id="live-fl-002",
            source_kind="freelance_project",
            title="Live DevOps Project",
            company_name=None,
            description="Test",
            location="Remote",
            country="GLOBAL",
            language="en",
            contract_type="project",
            remote_type="remote",
            tags=[],
            raw_payload={},
        )

        try:
            with patch(
                "app.services.freelancer_client.FreelancerAPIClient.search_projects",
                return_value=[_LIVE_CANDIDATE],
            ) as mock_search:
                client.get(
                    "/api/v1/external-sources/freelancer/search",
                    params={
                        "query": "devops",
                        "location": "United States",
                        "limit": 5,
                    },
                )
                mock_search.assert_called_once()
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["query"] == "devops"
                assert call_kwargs["location"] == "United States"
                assert call_kwargs["limit"] == 5
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token

    def test_live_mode_with_multiple_results(self, client):
        """Multiple results from the real client are all returned."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = "live-test-token"

        _LIVE_CANDIDATE_1 = ExternalOpportunityCandidate(
            provider="freelancer",
            external_id="live-fl-003",
            source_kind="freelance_project",
            title="Project One",
            company_name=None,
            description="First project",
            location="Remote",
            country="GLOBAL",
            language="en",
            tags=[],
            raw_payload={},
        )
        _LIVE_CANDIDATE_2 = ExternalOpportunityCandidate(
            provider="freelancer",
            external_id="live-fl-004",
            source_kind="freelance_project",
            title="Project Two",
            company_name=None,
            description="Second project",
            location="Remote",
            country="GLOBAL",
            language="en",
            tags=[],
            raw_payload={},
        )

        try:
            with patch(
                "app.services.freelancer_client.FreelancerAPIClient.search_projects",
                return_value=[_LIVE_CANDIDATE_1, _LIVE_CANDIDATE_2],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/freelancer/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 2
                ids = {item["external_id"] for item in data["items"]}
                assert "live-fl-003" in ids
                assert "live-fl-004" in ids
                mock_search.assert_called_once()
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token

    def test_diagnostics_reflect_real_api_enabled(self, client):
        """Diagnostics shows real_api_enabled=True in live+credentialed mode."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = "live-test-token"

        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            fl = providers["freelancer"]
            assert fl["real_api_enabled"] is True
            assert fl["safe_status"] == "ready"
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token


class TestFreelancerLiveModeMissingCredentials:
    """Live mode missing credentials does not call FreelancerAPIClient."""

    def test_missing_credentials_falls_back_to_mock(self, client):
        """Without credentials, search falls back to mock, no real client call."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = None

        try:
            with patch(
                "app.services.freelancer_client.FreelancerAPIClient.search_projects",
                return_value=[ExternalOpportunityCandidate(
                    provider="freelancer",
                    external_id="live-fl-should-not-appear",
                    source_kind="freelance_project",
                    title="Should Not Appear",
                    company_name=None,
                    description="Should not be returned",
                    country="GLOBAL",
                    language="en",
                    tags=[],
                    raw_payload={},
                )],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/freelancer/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 200
                # The real client should NOT have been called
                mock_search.assert_not_called()

                data = resp.json()
                assert data["total"] > 0
                # Results are mock data, not live
                for item in data["items"]:
                    assert item["provider"] == "freelancer"
                    # Mock IDs start with "fl-", not "live-"
                    assert item["external_id"].startswith("fl-")
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token

    def test_diagnostics_shows_missing_credentials(self, client):
        """Diagnostics shows missing_credentials when mode != mock but no creds."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = None

        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            fl = providers["freelancer"]
            assert fl["real_api_enabled"] is False
            assert fl["safe_status"] == "missing_credentials"
            assert "not configured" in fl["safe_message"].lower()
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token


class TestFreelancerClientErrorHandling:
    """FreelancerClientError subclasses become safe ValueError / HTTP 400."""

    def test_configuration_error_becomes_400(self, client):
        """FreelancerConfigurationError raises HTTP 400."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = "test-token"

        try:
            with patch(
                "app.services.freelancer_client.FreelancerAPIClient.search_projects",
                side_effect=FreelancerConfigurationError(
                    "FREELANCER_OAUTH_TOKEN is not configured."
                ),
            ):
                resp = client.get(
                    "/api/v1/external-sources/freelancer/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 400
                assert "freelancer" in resp.json()["detail"].lower()
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token

    def test_api_error_becomes_400(self, client):
        """FreelancerAPIError raises HTTP 400."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = "test-token"

        try:
            with patch(
                "app.services.freelancer_client.FreelancerAPIClient.search_projects",
                side_effect=FreelancerAPIError("Search failed."),
            ):
                resp = client.get(
                    "/api/v1/external-sources/freelancer/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 400
                assert "freelancer" in resp.json()["detail"].lower()
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token

    def test_no_credential_leakage_in_error(self, client):
        """Error responses never expose the OAuth token."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = "super-secret-token-value"

        try:
            with patch(
                "app.services.freelancer_client.FreelancerAPIClient.search_projects",
                side_effect=FreelancerConfigurationError(
                    "FREELANCER_OAUTH_TOKEN is not configured."
                ),
            ):
                resp = client.get(
                    "/api/v1/external-sources/freelancer/search",
                    params={"query": "devops"},
                )
                detail = resp.json()["detail"].lower()
                # The env var NAME is acceptable; its VALUE must not appear
                assert "super-secret-token-value" not in detail
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token

    def test_missing_credentials_not_an_error(self, client):
        """When credentials are missing but mode is live, no error is raised."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = None

        try:
            resp = client.get(
                "/api/v1/external-sources/freelancer/search",
                params={"query": "devops"},
            )
            # Safe fallback to mock — no error
            assert resp.status_code == 200
            assert resp.json()["total"] > 0
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token


# ===================================================================
# Mock Mode Unchanged
# ===================================================================


class TestMockModeUnchanged:
    """Mock mode behavior unchanged by Phase 10F changes."""

    def test_mock_only_still_true(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.json()["mock_only"] is True
        assert resp.json()["mode"] == "mock"

    def test_all_providers_have_mock_safe_status(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        for p in resp.json()["providers"]:
            assert p["safe_status"] == "mock"

    def test_freelancer_mock_search_returns_data(self, client):
        resp = client.get(
            "/api/v1/external-sources/freelancer/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "freelancer"
        assert data["total"] > 0
        for item in data["items"]:
            assert item["provider"] == "freelancer"
            assert item["country"] == "GLOBAL"
            assert item["language"] == "en"

    def test_freelancer_mock_search_location_filter(self, client):
        resp = client.get(
            "/api/v1/external-sources/freelancer/search",
            params={"query": "devops", "location": "Remote"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            combined = (
                (item.get("location") or "")
                + " "
                + (item.get("country") or "")
            ).lower()
            assert "remote" in combined

    def test_freelancer_mock_limit_respected(self, client):
        resp = client.get(
            "/api/v1/external-sources/freelancer/search",
            params={"query": "devops", "limit": 2},
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2

    def test_france_travail_still_mock(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_adzuna_uk_still_mock(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_uk/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0


# ===================================================================
# Combined Search
# ===================================================================


class TestCombinedSearch:
    """Combined search still works with all providers."""

    def test_combined_mock_mode(self, client):
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

    def test_combined_live_freelancer_mock_others(self, client):
        """Combined search: live freelancer + mock france_travail + mock adzuna_uk."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = "live-test-token"

        _LIVE_CANDIDATE = ExternalOpportunityCandidate(
            provider="freelancer",
            external_id="live-fl-combined-001",
            source_kind="freelance_project",
            title="Live Combined Project",
            company_name=None,
            description="Live combined project.",
            location="Remote",
            country="GLOBAL",
            language="en",
            contract_type="project",
            remote_type="remote",
            tags=["devops"],
            raw_payload={"id": "live-fl-combined-001"},
        )

        try:
            with patch(
                "app.services.freelancer_client.FreelancerAPIClient.search_projects",
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

                # The FreelancerAPIClient was called
                mock_search.assert_called_once()

                providers_found = {item["provider"] for item in data["items"]}
                assert "france_travail" in providers_found
                assert "adzuna_uk" in providers_found
                assert "freelancer" in providers_found

                # At least one live candidate is present
                live_items = [
                    item
                    for item in data["items"]
                    if item["external_id"] == "live-fl-combined-001"
                ]
                assert len(live_items) >= 1
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token

    def test_combined_live_missing_creds_all_mock(self, client):
        """Combined search with live mode but no freelancer creds: all mock."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_token = global_settings.FREELANCER_OAUTH_TOKEN

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.FREELANCER_OAUTH_TOKEN = None

        try:
            with patch(
                "app.services.freelancer_client.FreelancerAPIClient.search_projects",
                return_value=[ExternalOpportunityCandidate(
                    provider="freelancer",
                    external_id="live-fl-should-not-appear",
                    source_kind="freelance_project",
                    title="Should Not Appear",
                    company_name=None,
                    description="Should not be returned",
                    country="GLOBAL",
                    language="en",
                    tags=[],
                    raw_payload={},
                )],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/search",
                    params={
                        "providers": "france_travail,adzuna_uk,freelancer",
                        "query": "devops",
                    },
                )
                assert resp.status_code == 200
                # FreelancerAPIClient NOT called (missing credentials)
                mock_search.assert_not_called()

                data = resp.json()
                assert data["total"] > 0
                # All results are mock (fr-, uk-, or fl- prefix)
                for item in data["items"]:
                    assert item["external_id"].startswith(("fr-", "uk-", "fl-"))
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.FREELANCER_OAUTH_TOKEN = original_token


# ===================================================================
# Provider Diagnostics
# ===================================================================


class TestProviderDiagnostics:
    """Provider diagnostics reflect Freelancer configuration state."""

    def test_freelancer_supports_real_api(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["freelancer"]["supports_real_api"] is True

    def test_freelancer_credentials_not_configured_by_default(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["freelancer"]["credentials_configured"] is False

    def test_freelancer_credential_fields_correct(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["freelancer"]
        assert cls._credential_fields == ["FREELANCER_OAUTH_TOKEN"]

    def test_freelancer_mock_ready_when_creds_in_settings_only(self, client):
        """Credentials configured but mock mode -> safe_status mock."""
        from app.core.config import settings as global_settings

        original_token = global_settings.FREELANCER_OAUTH_TOKEN
        original_mode = global_settings.EXTERNAL_SOURCES_MODE

        global_settings.FREELANCER_OAUTH_TOKEN = "test-token"
        global_settings.EXTERNAL_SOURCES_MODE = "mock"

        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            fl = providers["freelancer"]
            assert fl["credentials_configured"] is True
            assert fl["real_api_enabled"] is False
            assert fl["safe_status"] == "mock"
        finally:
            global_settings.FREELANCER_OAUTH_TOKEN = original_token
            global_settings.EXTERNAL_SOURCES_MODE = original_mode

    def test_france_travail_unchanged(self, client):
        """france_travail still supports_real_api with correct fields."""
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        ft = providers["france_travail"]
        assert ft["supports_real_api"] is True
        assert ft["safe_status"] == "mock"

    def test_adzuna_uk_unchanged(self, client):
        """adzuna_uk still supports_real_api."""
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        au = providers["adzuna_uk"]
        assert au["supports_real_api"] is True
        assert au["safe_status"] == "mock"


# ===================================================================
# No Database Mutation
# ===================================================================


class TestNoDatabaseMutation:
    """No DB mutation from search endpoints."""

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
            "/api/v1/external-sources/freelancer/search",
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
                "providers": "france_travail,adzuna_uk,freelancer",
                "query": "devops",
            },
        )
        assert resp.status_code == 200
        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0


# ===================================================================
# Service Layer
# ===================================================================


class TestServiceLayer:
    """Direct service-layer tests for Phase 10F changes."""

    def test_provider_registry_size(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert len(PROVIDER_REGISTRY) == 3

    def test_registry_contains_all(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert "france_travail" in PROVIDER_REGISTRY
        assert "adzuna_uk" in PROVIDER_REGISTRY
        assert "freelancer" in PROVIDER_REGISTRY

    def test_freelancer_provider_config(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["freelancer"]
        assert cls.is_mock is True
        assert cls.supports_real_api is True
        assert cls._credential_fields == ["FREELANCER_OAUTH_TOKEN"]

    def test_france_travail_unchanged(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["france_travail"]
        assert cls.is_mock is True
        assert cls.supports_real_api is True
        assert cls._credential_fields == [
            "FRANCE_TRAVAIL_CLIENT_ID",
            "FRANCE_TRAVAIL_CLIENT_SECRET",
        ]

    def test_adzuna_uk_unchanged(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["adzuna_uk"]
        assert cls.is_mock is True
        assert cls.supports_real_api is True
        assert cls._credential_fields == [
            "ADZUNA_UK_APP_ID",
            "ADZUNA_UK_APP_KEY",
        ]

    def test_external_sources_module_importable(self):
        """The external_sources module still imports cleanly."""
        from app.services import external_sources

        providers = external_sources.list_external_source_providers()
        assert len(providers) == 3

    def test_freelancer_client_importable(self):
        """The freelancer_client module imports without side effects."""
        from app.services.freelancer_client import FreelancerAPIClient

        assert FreelancerAPIClient is not None
