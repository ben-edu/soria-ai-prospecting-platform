"""Phase 10E — Adzuna UK real connector tests.

Covers:
- Config readiness (is_ready, validate_configuration)
- Missing credentials safe failure
- Search param mapping (query, location, limit)
- Normalization of typical Adzuna response
- Minimal/empty response handling
- Mocked HTTP transport success/failure
- Provider diagnostics (credentials_configured, real_api_enabled, safe_status)
- Mock mode unchanged
- No DB mutation on search
- France Travail behavior unchanged
- Freelancer behavior unchanged
"""

from unittest.mock import MagicMock, patch

import httpx

from app.core.config import Settings
from app.schemas.external_source import ExternalOpportunityCandidate
from app.services.adzuna_uk_client import (
    AdzunaUKAPIClient,
    AdzunaUKAPIError,
    AdzunaUKClientError,
    AdzunaUKConfigurationError,
)

# ---------------------------------------------------------------------------
# Representative Adzuna UK API job payload
# ---------------------------------------------------------------------------

_ADZUNA_REAL_JOB = {
    "id": 12345678,
    "title": "DevOps Engineer",
    "company": {
        "display_name": "CloudBase Ltd",
    },
    "location": {
        "display_name": "London",
    },
    "description": (
        "Join our platform team to build and maintain CI/CD pipelines "
        "and Kubernetes infrastructure."
    ),
    "created": "2025-06-15T10:00:00Z",
    "redirect_url": "https://www.adzuna.co.uk/jobs/land/ad/12345678",
    "contract_type": "permanent",
    "salary_min": 45000,
    "salary_max": 65000,
    "salary_currency": "GBP",
    "category": {
        "tag": "engineering-jobs",
        "label": "Engineering Jobs",
    },
}

_ADZUNA_MINIMAL_JOB: dict = {
    "id": 87654321,
    "title": "Minimal Job",
}

_NO_RESULTS_RESPONSE: dict = {
    "results": [],
    "count": 0,
}

_SINGLE_RESULT_RESPONSE: dict = {
    "results": [_ADZUNA_REAL_JOB],
    "count": 1,
}

_MULTI_RESULT_RESPONSE: dict = {
    "results": [
        _ADZUNA_REAL_JOB,
        {
            "id": 23456789,
            "title": "Cloud Architect",
            "company": {"display_name": "TechInnovate UK"},
            "location": {"display_name": "Manchester"},
            "description": "Design and implement scalable cloud solutions.",
            "created": "2025-06-20T08:00:00Z",
            "redirect_url": "https://www.adzuna.co.uk/jobs/land/ad/23456789",
            "contract_type": "permanent",
            "category": {"label": "IT Jobs"},
        },
    ],
    "count": 2,
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
    """Return Settings with Adzuna UK credentials configured."""
    return Settings(
        ADZUNA_UK_APP_ID="test-app-id",
        ADZUNA_UK_APP_KEY="test-app-key",
        EXTERNAL_SOURCES_MODE="live",
    )


# ===================================================================
# Adzuna UK Connector Unit Tests
# ===================================================================


class TestConnectorInstantiation:
    """Adzuna UK connector can be instantiated with various configs."""

    def test_instantiate_without_settings(self):
        """Connector can be created without any settings."""
        client = AdzunaUKAPIClient()
        assert client.app_id is None
        assert client.app_key is None
        assert client.api_base_url is not None

    def test_not_ready_without_credentials(self):
        """Without credentials, is_ready() returns False."""
        client = AdzunaUKAPIClient()
        assert client.is_ready() is False

    def test_ready_with_credentials(self):
        """With credentials, is_ready() returns True."""
        client = AdzunaUKAPIClient(settings=_configured_settings())
        assert client.is_ready() is True

    def test_not_ready_with_partial_credentials(self):
        """With only app_id, is_ready() returns False."""
        settings = Settings(
            ADZUNA_UK_APP_ID="test-id",
            ADZUNA_UK_APP_KEY=None,
        )
        client = AdzunaUKAPIClient(settings=settings)
        assert client.is_ready() is False

    def test_default_base_url(self):
        """Default API base URL is used when settings provide no override."""
        client = AdzunaUKAPIClient(settings=_configured_settings())
        assert "api.adzuna.com" in client.api_base_url

    def test_custom_base_url_from_settings(self):
        """Custom base URL from settings overrides default."""
        settings = Settings(
            ADZUNA_UK_API_BASE_URL="https://custom.example.com/api",
        )
        client = AdzunaUKAPIClient(settings=settings)
        assert client.api_base_url == "https://custom.example.com/api"

    def test_custom_exceptions_are_subclasses(self):
        """All custom exceptions inherit from AdzunaUKClientError."""
        assert issubclass(AdzunaUKConfigurationError, AdzunaUKClientError)
        assert issubclass(AdzunaUKAPIError, AdzunaUKClientError)
        assert issubclass(AdzunaUKClientError, Exception)


class TestValidateConfiguration:
    """validate_configuration fails safely when config is missing."""

    def test_raises_when_app_id_missing(self):
        client = AdzunaUKAPIClient()
        try:
            client.validate_configuration()
            assert False, "Expected AdzunaUKConfigurationError"
        except AdzunaUKConfigurationError as e:
            assert "ADZUNA_UK_APP_ID" in str(e)

    def test_raises_when_app_key_missing(self):
        settings = Settings(
            ADZUNA_UK_APP_ID="test-id",
            ADZUNA_UK_APP_KEY=None,
        )
        client = AdzunaUKAPIClient(settings=settings)
        try:
            client.validate_configuration()
            assert False, "Expected AdzunaUKConfigurationError"
        except AdzunaUKConfigurationError as e:
            assert "ADZUNA_UK_APP_KEY" in str(e)

    def test_returns_true_when_configured(self):
        client = AdzunaUKAPIClient(settings=_configured_settings())
        assert client.validate_configuration() is True

    def test_error_message_does_not_expose_values(self):
        """Exception message mentions env var names, not actual values."""
        client = AdzunaUKAPIClient()
        try:
            client.validate_configuration()
        except AdzunaUKConfigurationError as e:
            msg = str(e)
            assert "ADZUNA_UK_APP_ID" in msg
            # Values must not appear in error message
            assert "test" not in msg

    def test_no_secret_logging_in_validate(self):
        """validate_configuration does not log or expose secrets."""
        client = AdzunaUKAPIClient(
            settings=Settings(ADZUNA_UK_APP_ID="secret-id", ADZUNA_UK_APP_KEY=None)
        )
        try:
            client.validate_configuration()
        except AdzunaUKConfigurationError as e:
            msg = str(e)
            assert "secret-id" not in msg

    def test_partial_credentials_false(self):
        """Only one of two credentials → validate_configuration fails."""
        client = AdzunaUKAPIClient(
            settings=Settings(ADZUNA_UK_APP_ID="test-id", ADZUNA_UK_APP_KEY=None)
        )
        try:
            client.validate_configuration()
            assert False, "Expected AdzunaUKConfigurationError"
        except AdzunaUKConfigurationError:
            pass


class TestBuildSearchParams:
    """Search param builder maps query/location/limit correctly."""

    def test_maps_query_to_q(self):
        client = AdzunaUKAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops")
        assert params["q"] == "devops"

    def test_maps_location_to_where(self):
        client = AdzunaUKAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", location="London")
        assert params["where"] == "London"

    def test_omits_location_when_empty(self):
        client = AdzunaUKAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", location="")
        assert "where" not in params

    def test_omits_location_when_none(self):
        client = AdzunaUKAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", location=None)
        assert "where" not in params

    def test_maps_limit_to_max_results(self):
        client = AdzunaUKAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", limit=5)
        assert params["max_results"] == 5

    def test_caps_limit_at_50(self):
        client = AdzunaUKAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", limit=100)
        assert params["max_results"] == 50

    def test_floor_limit_at_1(self):
        client = AdzunaUKAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", limit=0)
        assert params["max_results"] == 1

    def test_strips_query_whitespace(self):
        client = AdzunaUKAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="  devops  ")
        assert params["q"] == "devops"

    def test_strips_location_whitespace(self):
        client = AdzunaUKAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops", location="  London  ")
        assert params["where"] == "London"

    def test_includes_app_id_and_app_key(self):
        """Auth credentials are included as query params."""
        client = AdzunaUKAPIClient(settings=_configured_settings())
        params = client.build_search_params(query="devops")
        assert params["app_id"] == "test-app-id"
        assert params["app_key"] == "test-app-key"


class TestNormalizeJob:
    """normalize_job maps raw Adzuna payload to ExternalOpportunityCandidate."""

    def test_normalize_full_job(self):
        """All fields are correctly mapped from a representative payload."""
        candidate = AdzunaUKAPIClient().normalize_job(_ADZUNA_REAL_JOB)

        assert candidate.provider == "adzuna_uk"
        assert candidate.source_kind == "job"
        assert candidate.country == "GB"
        assert candidate.language == "en"

        assert candidate.external_id == "12345678"
        assert candidate.title == "DevOps Engineer"
        assert candidate.company_name == "CloudBase Ltd"
        assert candidate.description is not None
        assert "CI/CD" in candidate.description
        assert candidate.location == "London"
        assert candidate.contract_type == "permanent"

        assert candidate.source_url == (
            "https://www.adzuna.co.uk/jobs/land/ad/12345678"
        )
        assert candidate.source_published_at is not None

        # Budget fields
        assert candidate.budget_min == 45000
        assert candidate.budget_max == 65000
        assert candidate.budget_currency == "GBP"

        # Tags include category label and contract type
        assert "engineering jobs" in candidate.tags
        assert "permanent" in candidate.tags

        # raw_payload should be a copy of the input
        assert candidate.raw_payload == _ADZUNA_REAL_JOB

    def test_normalize_minimal_job(self):
        """Missing optional fields do not crash normalization."""
        candidate = AdzunaUKAPIClient().normalize_job(_ADZUNA_MINIMAL_JOB)

        assert candidate.provider == "adzuna_uk"
        assert candidate.external_id == "87654321"
        assert candidate.title == "Minimal Job"

        # Optional fields should gracefully default
        assert candidate.company_name is None
        assert candidate.description is None
        assert candidate.location is None
        assert candidate.source_url is None
        assert candidate.source_published_at is None
        assert candidate.contract_type is None
        assert candidate.budget_min is None
        assert candidate.budget_max is None
        assert candidate.budget_currency is None
        assert candidate.tags == []
        assert candidate.raw_payload == _ADZUNA_MINIMAL_JOB

    def test_normalize_empty_dict(self):
        """Even an empty dict should not crash."""
        candidate = AdzunaUKAPIClient().normalize_job({})

        assert candidate.provider == "adzuna_uk"
        assert candidate.external_id == ""
        assert candidate.title == ""
        assert candidate.company_name is None
        assert candidate.raw_payload == {}

    def test_normalize_missing_nested_objects(self):
        """Missing company/location objects should not crash."""
        job = {
            "id": 999,
            "title": "No Nested Objects",
            "company": None,
            "location": None,
        }
        candidate = AdzunaUKAPIClient().normalize_job(job)

        assert candidate.external_id == "999"
        assert candidate.company_name is None
        assert candidate.location is None

    def test_normalize_bad_date_format(self):
        """Malformed date string should not crash; returns None."""
        job = dict(_ADZUNA_MINIMAL_JOB)
        job["created"] = "not-a-date"
        candidate = AdzunaUKAPIClient().normalize_job(job)

        assert candidate.source_published_at is None

    def test_normalize_preserves_raw_payload(self):
        """raw_payload is an independent copy of the input."""
        original = dict(_ADZUNA_REAL_JOB)
        candidate = AdzunaUKAPIClient().normalize_job(original)

        # Mutating the original should not affect the candidate
        original["id"] = 99999999
        assert candidate.external_id == "12345678"

    def test_normalize_returns_correct_type(self):
        """normalize_job returns an ExternalOpportunityCandidate instance."""
        candidate = AdzunaUKAPIClient().normalize_job(_ADZUNA_REAL_JOB)
        assert isinstance(candidate, ExternalOpportunityCandidate)

    def test_normalize_missing_id_key(self):
        """Missing id key should result in empty external_id."""
        candidate = AdzunaUKAPIClient().normalize_job({"title": "Test"})
        assert candidate.external_id == ""

    def test_normalize_int_id_becomes_string(self):
        """Integer id should be converted to string."""
        candidate = AdzunaUKAPIClient().normalize_job({"id": 42, "title": "Test"})
        assert candidate.external_id == "42"
        assert isinstance(candidate.external_id, str)

    def test_normalize_without_category(self):
        """Missing category should not crash and tags should be empty."""
        job = {
            "id": 555,
            "title": "No Category Job",
            "contract_type": "contract",
        }
        candidate = AdzunaUKAPIClient().normalize_job(job)
        assert candidate.tags == ["contract"]

    def test_normalize_with_salary_data(self):
        """Salary fields are correctly mapped when present."""
        job = dict(_ADZUNA_REAL_JOB)
        candidate = AdzunaUKAPIClient().normalize_job(job)
        assert candidate.budget_min == 45000
        assert candidate.budget_max == 65000
        assert candidate.budget_currency == "GBP"

    def test_normalize_remote_type_none(self):
        """Remote type is None for Adzuna (no dedicated field)."""
        candidate = AdzunaUKAPIClient().normalize_job(_ADZUNA_REAL_JOB)
        assert candidate.remote_type is None

    def test_normalize_id_none(self):
        """None id should result in empty string external_id."""
        candidate = AdzunaUKAPIClient().normalize_job({"id": None, "title": "Test"})
        assert candidate.external_id == ""


class TestSearchJobsWithMockedTransport:
    """search_jobs uses mocked transport only; no real HTTP call."""

    def test_search_with_mocked_client(self):
        """search_jobs uses the injected HTTP client, not real network."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _SINGLE_RESULT_RESPONSE),
        )
        au_client = AdzunaUKAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = au_client.search_jobs(query="devops", limit=5)

        assert len(results) == 1
        assert results[0].provider == "adzuna_uk"
        assert results[0].external_id == "12345678"
        assert results[0].title == "DevOps Engineer"

        # Verify the mock was called (no real HTTP call happened)
        mock_client.get.assert_called_once()

    def test_search_http_client_injection_parameter(self):
        """The http_client parameter overrides the constructor client."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _NO_RESULTS_RESPONSE),
        )
        au_client = AdzunaUKAPIClient(settings=_configured_settings())
        results = au_client.search_jobs(
            query="devops", http_client=mock_client
        )

        assert len(results) == 0
        mock_client.get.assert_called_once()

    def test_search_no_results(self):
        """Empty results list returns empty candidates."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _NO_RESULTS_RESPONSE),
        )
        au_client = AdzunaUKAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = au_client.search_jobs(query="nothing")

        assert results == []

    def test_search_multiple_results(self):
        """Multiple jobs in results are all normalized."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _MULTI_RESULT_RESPONSE),
        )
        au_client = AdzunaUKAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = au_client.search_jobs(query="devops")

        assert len(results) == 2
        assert results[0].external_id == "12345678"
        assert results[1].external_id == "23456789"

    def test_search_raises_on_api_failure(self):
        """Non-200 search response raises AdzunaUKAPIError."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(500, {"error": "server error"}),
        )
        au_client = AdzunaUKAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            au_client.search_jobs(query="devops")
            assert False, "Expected AdzunaUKAPIError"
        except AdzunaUKAPIError:
            pass

    def test_search_raises_on_unauthorized(self):
        """401 response raises AdzunaUKAPIError."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(401, {"error": "unauthorized"}),
        )
        au_client = AdzunaUKAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            au_client.search_jobs(query="devops")
            assert False, "Expected AdzunaUKAPIError"
        except AdzunaUKAPIError:
            pass

    def test_search_raises_on_missing_configuration(self):
        """search_jobs raises AdzunaUKConfigurationError when not configured."""
        au_client = AdzunaUKAPIClient()
        try:
            au_client.search_jobs(query="devops")
            assert False, "Expected AdzunaUKConfigurationError"
        except AdzunaUKConfigurationError:
            pass

    def test_search_passes_correct_params_to_http_client(self):
        """Verify the HTTP client is called with the right URL and params."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _SINGLE_RESULT_RESPONSE),
        )
        au_client = AdzunaUKAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        au_client.search_jobs(query="devops", location="London", limit=3)

        # Check the search request
        call_kwargs = mock_client.get.call_args
        assert call_kwargs is not None
        search_url = call_kwargs[0][0]
        assert "search/1" in search_url

        # Check query params
        params = call_kwargs[1].get("params", {})
        assert params["q"] == "devops"
        assert params["where"] == "London"
        assert params["max_results"] == 3
        assert params["app_id"] == "test-app-id"
        assert params["app_key"] == "test-app-key"

    def test_error_message_contains_no_secrets(self):
        """Error responses never expose app_id or app_key."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(401, {"error": "unauthorized"}),
        )
        au_client = AdzunaUKAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            au_client.search_jobs(query="devops")
        except AdzunaUKAPIError as e:
            msg = str(e)
            assert "test-app-id" not in msg
            assert "test-app-key" not in msg

    def test_constructor_timeout_from_settings(self):
        """Timeout is read from settings when available."""
        settings = Settings(
            ADZUNA_UK_APP_ID="test-id",
            ADZUNA_UK_APP_KEY="test-key",
            EXTERNAL_SOURCE_HTTP_TIMEOUT_SECONDS=30,
        )
        client = AdzunaUKAPIClient(settings=settings)
        assert client.timeout == 30


# ===================================================================
# Live-Mode Gating Tests
# ===================================================================


class TestAdzunaLiveModeWithCredentials:
    """Live mode with credentials routes to AdzunaUKAPIClient."""

    def test_search_routes_to_real_client(self, client):
        """Verify search_jobs is called when credentials and live mode are set."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = "live-test-app-id"
        global_settings.ADZUNA_UK_APP_KEY = "live-test-app-key"

        _LIVE_CANDIDATE = ExternalOpportunityCandidate(
            provider="adzuna_uk",
            external_id="live-uk-001",
            source_kind="job",
            title="Live DevOps Engineer",
            company_name="Live Corp",
            description="Live job description.",
            location="London",
            country="GB",
            language="en",
            contract_type="permanent",
            tags=["devops"],
            raw_payload={"id": "live-uk-001"},
        )

        try:
            with patch(
                "app.services.adzuna_uk_client.AdzunaUKAPIClient.search_jobs",
                return_value=[_LIVE_CANDIDATE],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/adzuna_uk/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 200
                assert mock_search.call_count >= 1

                data = resp.json()
                assert data["total"] >= 1
                assert data["items"][0]["external_id"] == "live-uk-001"
                assert data["items"][0]["title"] == "Live DevOps Engineer"
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key

    def test_search_passes_parameters(self, client):
        """Verify the real client is called with the right search parameters."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = "live-test-app-id"
        global_settings.ADZUNA_UK_APP_KEY = "live-test-app-key"

        _LIVE_CANDIDATE = ExternalOpportunityCandidate(
            provider="adzuna_uk",
            external_id="live-uk-002",
            source_kind="job",
            title="Live DevOps",
            company_name="Live Corp",
            description="Test",
            location="London",
            country="GB",
            language="en",
            contract_type="permanent",
            tags=[],
            raw_payload={},
        )

        try:
            with patch(
                "app.services.adzuna_uk_client.AdzunaUKAPIClient.search_jobs",
                return_value=[_LIVE_CANDIDATE],
            ) as mock_search:
                client.get(
                    "/api/v1/external-sources/adzuna_uk/search",
                    params={"query": "devops", "location": "London", "limit": 5},
                )
                mock_search.assert_called_once()
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["query"] == "devops"
                assert call_kwargs["location"] == "London"
                assert call_kwargs["limit"] == 5
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key

    def test_live_mode_with_multiple_results(self, client):
        """Multiple results from the real client are all returned."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = "live-test-app-id"
        global_settings.ADZUNA_UK_APP_KEY = "live-test-app-key"

        _LIVE_CANDIDATE_1 = ExternalOpportunityCandidate(
            provider="adzuna_uk",
            external_id="live-uk-003",
            source_kind="job",
            title="Job One",
            company_name="Corp A",
            description="First job",
            location="London",
            country="GB",
            language="en",
            tags=[],
            raw_payload={},
        )
        _LIVE_CANDIDATE_2 = ExternalOpportunityCandidate(
            provider="adzuna_uk",
            external_id="live-uk-004",
            source_kind="job",
            title="Job Two",
            company_name="Corp B",
            description="Second job",
            location="Manchester",
            country="GB",
            language="en",
            tags=[],
            raw_payload={},
        )

        try:
            with patch(
                "app.services.adzuna_uk_client.AdzunaUKAPIClient.search_jobs",
                return_value=[_LIVE_CANDIDATE_1, _LIVE_CANDIDATE_2],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/adzuna_uk/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] == 2
                ids = {item["external_id"] for item in data["items"]}
                assert "live-uk-003" in ids
                assert "live-uk-004" in ids
                mock_search.assert_called_once()
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key

    def test_diagnostics_reflect_real_api_enabled(self, client):
        """Diagnostics shows real_api_enabled=True in live+credentialed mode."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = "live-test-app-id"
        global_settings.ADZUNA_UK_APP_KEY = "live-test-app-key"

        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            au = providers["adzuna_uk"]
            assert au["real_api_enabled"] is True
            assert au["safe_status"] == "ready"
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key


class TestAdzunaLiveModeMissingCredentials:
    """Live mode missing credentials does not call AdzunaUKAPIClient."""

    def test_missing_credentials_falls_back_to_mock(self, client):
        """Without credentials, search falls back to mock, no real client call."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = None
        global_settings.ADZUNA_UK_APP_KEY = None

        try:
            with patch(
                "app.services.adzuna_uk_client.AdzunaUKAPIClient.search_jobs",
                return_value=[ExternalOpportunityCandidate(
                    provider="adzuna_uk",
                    external_id="live-uk-999",
                    source_kind="job",
                    title="Should Not Appear",
                    company_name="Fake Corp",
                    description="Should not be returned",
                    country="GB",
                    language="en",
                    tags=[],
                    raw_payload={},
                )],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/adzuna_uk/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 200
                # The real client should NOT have been called
                mock_search.assert_not_called()

                data = resp.json()
                assert data["total"] > 0
                # Results are mock data, not live
                for item in data["items"]:
                    assert item["provider"] == "adzuna_uk"
                    # Mock IDs start with "uk-", not "live-"
                    assert item["external_id"].startswith("uk-")
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key

    def test_diagnostics_shows_missing_credentials(self, client):
        """Diagnostics shows missing_credentials when mode != mock but no creds."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = None
        global_settings.ADZUNA_UK_APP_KEY = None

        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            au = providers["adzuna_uk"]
            assert au["real_api_enabled"] is False
            assert au["safe_status"] == "missing_credentials"
            assert "not configured" in au["safe_message"].lower()
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key


class TestAdzunaClientErrorHandling:
    """AdzunaUKClientError subclasses become safe ValueError / HTTP 400."""

    def test_configuration_error_becomes_400(self, client):
        """AdzunaUKConfigurationError raises HTTP 400."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = "test-id"
        global_settings.ADZUNA_UK_APP_KEY = "test-key"

        try:
            with patch(
                "app.services.adzuna_uk_client.AdzunaUKAPIClient.search_jobs",
                side_effect=AdzunaUKConfigurationError("Adzuna not configured."),
            ):
                resp = client.get(
                    "/api/v1/external-sources/adzuna_uk/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 400
                assert "adzuna uk" in resp.json()["detail"].lower()
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key

    def test_api_error_becomes_400(self, client):
        """AdzunaUKAPIError raises HTTP 400."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = "test-id"
        global_settings.ADZUNA_UK_APP_KEY = "test-key"

        try:
            with patch(
                "app.services.adzuna_uk_client.AdzunaUKAPIClient.search_jobs",
                side_effect=AdzunaUKAPIError("Search failed."),
            ):
                resp = client.get(
                    "/api/v1/external-sources/adzuna_uk/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 400
                assert "adzuna uk" in resp.json()["detail"].lower()
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key

    def test_no_credential_leakage_in_error(self, client):
        """Error responses never expose app_id or app_key."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = "secret-app-id-value"
        global_settings.ADZUNA_UK_APP_KEY = "secret-app-key-value"

        try:
            with patch(
                "app.services.adzuna_uk_client.AdzunaUKAPIClient.search_jobs",
                side_effect=AdzunaUKConfigurationError(
                    "ADZUNA_UK_APP_ID is not configured."
                ),
            ):
                resp = client.get(
                    "/api/v1/external-sources/adzuna_uk/search",
                    params={"query": "devops"},
                )
                detail = resp.json()["detail"].lower()
                # The env var NAME is acceptable; its VALUE must not appear
                assert "secret-app-id-value" not in detail
                assert "secret-app-key-value" not in detail
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key

    def test_missing_credentials_not_an_error(self, client):
        """When credentials are missing but mode is live, no error is raised."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = None
        global_settings.ADZUNA_UK_APP_KEY = None

        try:
            resp = client.get(
                "/api/v1/external-sources/adzuna_uk/search",
                params={"query": "devops"},
            )
            # Safe fallback to mock — no error
            assert resp.status_code == 200
            assert resp.json()["total"] > 0
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key


# ===================================================================
# Mock Mode Unchanged
# ===================================================================


class TestMockModeUnchanged:
    """Mock mode behavior unchanged by Phase 10E changes."""

    def test_mock_only_still_true(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.json()["mock_only"] is True
        assert resp.json()["mode"] == "mock"

    def test_all_providers_have_mock_safe_status(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        for p in resp.json()["providers"]:
            assert p["safe_status"] == "mock"

    def test_adzuna_uk_mock_search_returns_data(self, client):
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
            assert item["language"] == "en"

    def test_adzuna_uk_mock_search_location_filter(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_uk/search",
            params={"query": "devops", "location": "London"},
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert "london" in item.get("location", "").lower()

    def test_adzuna_uk_mock_limit_respected(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_uk/search",
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

    def test_freelancer_still_mock(self, client):
        resp = client.get(
            "/api/v1/external-sources/freelancer/search",
            params={"query": "kubernetes"},
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

    def test_combined_live_adzuna_mock_others(self, client):
        """Combined search: live adzuna + mock france_travail + mock freelancer."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = "live-test-app-id"
        global_settings.ADZUNA_UK_APP_KEY = "live-test-app-key"

        _LIVE_CANDIDATE = ExternalOpportunityCandidate(
            provider="adzuna_uk",
            external_id="live-uk-combined-001",
            source_kind="job",
            title="Live Combined Job",
            company_name="Live Combined Corp",
            description="Live combined job.",
            location="London",
            country="GB",
            language="en",
            contract_type="permanent",
            tags=["devops"],
            raw_payload={"id": "live-uk-combined-001"},
        )

        try:
            with patch(
                "app.services.adzuna_uk_client.AdzunaUKAPIClient.search_jobs",
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

                # The AdzunaUKAPIClient was called
                mock_search.assert_called_once()

                providers_found = {item["provider"] for item in data["items"]}
                assert "france_travail" in providers_found
                assert "adzuna_uk" in providers_found
                assert "freelancer" in providers_found

                # At least one live candidate is present
                live_items = [
                    item
                    for item in data["items"]
                    if item["external_id"] == "live-uk-combined-001"
                ]
                assert len(live_items) >= 1
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key

    def test_combined_live_missing_creds_all_mock(self, client):
        """Combined search with live mode but no adzuna credentials: all mock."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.ADZUNA_UK_APP_ID = None
        global_settings.ADZUNA_UK_APP_KEY = None

        try:
            with patch(
                "app.services.adzuna_uk_client.AdzunaUKAPIClient.search_jobs",
                return_value=[ExternalOpportunityCandidate(
                    provider="adzuna_uk",
                    external_id="live-uk-should-not-appear",
                    source_kind="job",
                    title="Should Not Appear",
                    company_name="Fake Corp",
                    description="Should not be returned",
                    country="GB",
                    language="en",
                    tags=[],
                    raw_payload={},
                )],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/search",
                    params={
                        "providers": "france_travail,adzuna_uk",
                        "query": "devops",
                    },
                )
                assert resp.status_code == 200
                # AdzunaUKAPIClient NOT called (missing credentials)
                mock_search.assert_not_called()

                data = resp.json()
                assert data["total"] > 0
                # All results are mock (fr- or uk- prefix)
                for item in data["items"]:
                    assert item["external_id"].startswith(("fr-", "uk-"))
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key


# ===================================================================
# Provider Diagnostics
# ===================================================================


class TestProviderDiagnostics:
    """Provider diagnostics reflect Adzuna UK configuration state."""

    def test_adzuna_uk_supports_real_api(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["adzuna_uk"]["supports_real_api"] is True

    def test_adzuna_uk_credentials_not_configured_by_default(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["adzuna_uk"]["credentials_configured"] is False

    def test_adzuna_uk_credential_fields_correct(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["adzuna_uk"]
        assert cls._credential_fields == [
            "ADZUNA_UK_APP_ID",
            "ADZUNA_UK_APP_KEY",
        ]

    def test_adzuna_mock_ready_when_creds_in_settings_only(self, client):
        """Credentials configured but mock mode → safe_status mock."""
        from app.core.config import settings as global_settings

        original_id = global_settings.ADZUNA_UK_APP_ID
        original_key = global_settings.ADZUNA_UK_APP_KEY
        original_mode = global_settings.EXTERNAL_SOURCES_MODE

        global_settings.ADZUNA_UK_APP_ID = "test-id"
        global_settings.ADZUNA_UK_APP_KEY = "test-key"
        global_settings.EXTERNAL_SOURCES_MODE = "mock"

        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            au = providers["adzuna_uk"]
            assert au["credentials_configured"] is True
            assert au["real_api_enabled"] is False
            assert au["safe_status"] == "mock"
        finally:
            global_settings.ADZUNA_UK_APP_ID = original_id
            global_settings.ADZUNA_UK_APP_KEY = original_key
            global_settings.EXTERNAL_SOURCES_MODE = original_mode

    def test_france_travail_unchanged(self, client):
        """france_travail still supports_real_api with correct fields."""
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        ft = providers["france_travail"]
        assert ft["supports_real_api"] is True
        assert ft["safe_status"] == "mock"

    def test_freelancer_supports_real_api_in_phase10f(self, client):
        """freelancer now supports real API (Phase 10F)."""
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        fl = providers["freelancer"]
        assert fl["supports_real_api"] is True
        assert fl["safe_status"] == "mock"


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
            "/api/v1/external-sources/adzuna_uk/search",
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


# ===================================================================
# Service Layer
# ===================================================================


class TestServiceLayer:
    """Direct service-layer tests for Phase 10E changes."""

    def test_provider_registry_size(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert len(PROVIDER_REGISTRY) == 3

    def test_registry_contains_all(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert "france_travail" in PROVIDER_REGISTRY
        assert "adzuna_uk" in PROVIDER_REGISTRY
        assert "freelancer" in PROVIDER_REGISTRY

    def test_adzuna_uk_provider_still_mock_by_default(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["adzuna_uk"]
        assert cls.is_mock is True
        assert cls.supports_real_api is True

    def test_france_travail_unchanged(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["france_travail"]
        assert cls.is_mock is True
        assert cls.supports_real_api is True
        assert cls._credential_fields == [
            "FRANCE_TRAVAIL_CLIENT_ID",
            "FRANCE_TRAVAIL_CLIENT_SECRET",
        ]

    def test_freelancer_now_supports_real_api(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["freelancer"]
        assert cls.is_mock is True
        assert cls.supports_real_api is True
        assert cls._credential_fields == ["FREELANCER_OAUTH_TOKEN"]

    def test_external_sources_module_importable(self):
        """The external_sources module still imports cleanly."""
        from app.services import external_sources

        providers = external_sources.list_external_source_providers()
        assert len(providers) == 3

    def test_adzuna_uk_client_importable(self):
        """The adzuna_uk_client module imports without side effects."""
        from app.services.adzuna_uk_client import AdzunaUKAPIClient

        assert AdzunaUKAPIClient is not None
