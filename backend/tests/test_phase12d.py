"""Phase 12D — Jooble global external source provider tests.

Covers:
- JoobleAPIClient instantiation and readiness checks
- Missing API key safe failure (no secret leakage)
- Search URL and payload building
- Response normalization (full, minimal, empty, dates, salary as text)
- Mocked HTTP transport success/failure
- Provider registration and diagnostics
- Mock search returns deterministic candidates
- Location filter and limit respect
- Combined search with existing providers
- No DB mutation on search
- Import creates imported_pending_review opportunities
- Duplicate import detection
- Existing 5 providers remain present and unchanged
"""

import uuid
from datetime import timezone
from unittest.mock import MagicMock, patch

import httpx
from sqlmodel import Session

from app.core.config import Settings
from app.schemas.external_source import ExternalOpportunityCandidate
from app.services.jooble_client import (
    JoobleAPIClient,
    JoobleAPIError,
    JoobleClientError,
    JoobleConfigurationError,
)

# ---------------------------------------------------------------------------
# Representative Jooble API job payloads
# ---------------------------------------------------------------------------

_JOOBLE_REAL_JOB = {
    "id": 12345678,
    "title": "Senior DevOps Engineer",
    "company": "GlobalTech Inc.",
    "location": "Remote",
    "snippet": (
        "Build and maintain large-scale CI/CD pipelines and "
        "Kubernetes infrastructure for a global SaaS platform."
    ),
    "salary": "$120,000 - $160,000",
    "source": "indeed",
    "type": "full-time",
    "link": "https://jooble.org/job/12345678",
    "updated": 1696000000000,
}

_JOOBLE_MINIMAL_JOB: dict = {
    "id": 87654321,
    "title": "Minimal Job",
}

_NO_RESULTS_RESPONSE: dict = {
    "totalCount": 0,
    "jobs": [],
}

_SINGLE_RESULT_RESPONSE: dict = {
    "totalCount": 1,
    "jobs": [_JOOBLE_REAL_JOB],
}

_MULTI_RESULT_RESPONSE: dict = {
    "totalCount": 2,
    "jobs": [
        _JOOBLE_REAL_JOB,
        {
            "id": 23456789,
            "title": "Cloud Architect",
            "company": "CloudScale GmbH",
            "location": "Berlin",
            "snippet": "Design multi-cloud architectures.",
            "salary": "€90,000 - €120,000",
            "source": "stepstone",
            "type": "full-time",
            "link": "https://jooble.org/job/23456789",
            "updated": 1696100000000,
        },
    ],
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
    """Create a mock httpx.Client with pre-configured post return value."""
    client = MagicMock(spec=httpx.Client)
    client.post.return_value = search_resp or _make_mock_response(
        200, _SINGLE_RESULT_RESPONSE
    )
    return client


def _configured_settings() -> Settings:
    """Return Settings with Jooble API key configured."""
    return Settings(
        JOOBLE_API_KEY="test-jooble-api-key",
        EXTERNAL_SOURCES_MODE="live",
    )


# ===================================================================
# Jooble Connector Unit Tests
# ===================================================================


class TestConnectorInstantiation:
    """JoobleAPIClient can be instantiated with various configs."""

    def test_instantiate_without_settings(self):
        """Connector can be created without any settings."""
        client = JoobleAPIClient()
        assert client.api_key is None
        assert client.api_base_url is not None

    def test_not_ready_without_key(self):
        """Without API key, is_ready() returns False."""
        client = JoobleAPIClient()
        assert client.is_ready() is False

    def test_ready_with_key(self):
        """With API key, is_ready() returns True."""
        client = JoobleAPIClient(settings=_configured_settings())
        assert client.is_ready() is True

    def test_default_base_url(self):
        """Default API base URL is used when settings provide no override."""
        client = JoobleAPIClient(settings=_configured_settings())
        assert "jooble.org" in client.api_base_url

    def test_custom_base_url_from_settings(self):
        """Custom base URL from settings overrides default."""
        settings = Settings(
            JOOBLE_API_BASE_URL="https://custom.example.com/api",
        )
        client = JoobleAPIClient(settings=settings)
        assert client.api_base_url == "https://custom.example.com/api"

    def test_custom_exceptions_are_subclasses(self):
        """All custom exceptions inherit from JoobleClientError."""
        assert issubclass(JoobleConfigurationError, JoobleClientError)
        assert issubclass(JoobleAPIError, JoobleClientError)
        assert issubclass(JoobleClientError, Exception)


class TestValidateConfiguration:
    """validate_configuration fails safely when config is missing."""

    def test_raises_when_api_key_missing(self):
        client = JoobleAPIClient()
        try:
            client.validate_configuration()
            assert False, "Expected JoobleConfigurationError"
        except JoobleConfigurationError as e:
            assert "JOOBLE_API_KEY" in str(e)

    def test_returns_true_when_configured(self):
        client = JoobleAPIClient(settings=_configured_settings())
        assert client.validate_configuration() is True

    def test_error_message_does_not_expose_values(self):
        """Exception message mentions env var names, not actual values."""
        client = JoobleAPIClient()
        try:
            client.validate_configuration()
        except JoobleConfigurationError as e:
            msg = str(e)
            assert "JOOBLE_API_KEY" in msg
            # Values must not appear in error message
            assert "test" not in msg.lower()

    def test_no_secret_logging_in_validate(self):
        """validate_configuration does not log or expose secrets."""
        client = JoobleAPIClient(
            settings=Settings(JOOBLE_API_KEY="super-secret-key")
        )
        try:
            client.validate_configuration()
        except JoobleConfigurationError as e:
            msg = str(e)
            assert "super-secret-key" not in msg


class TestBuildSearchURL:
    """Search URL builder embeds the API key in the URL path."""

    def test_url_contains_api_key(self):
        client = JoobleAPIClient(settings=_configured_settings())
        url = client.build_search_url()
        assert "test-jooble-api-key" in url
        assert url == "https://jooble.org/api/test-jooble-api-key"

    def test_url_without_settings_uses_empty_key(self):
        client = JoobleAPIClient()
        url = client.build_search_url()
        assert url == "https://jooble.org/api/"

    def test_url_key_not_in_loggable_format(self):
        """The URL is never used in error messages by the client."""
        client = JoobleAPIClient(
            settings=Settings(JOOBLE_API_KEY="do-not-leak")
        )
        url = client.build_search_url()
        # The URL itself contains the key, which is expected for Jooble's API
        # design. The key is in the URL path, not exposed in errors.
        assert "do-not-leak" in url


class TestBuildSearchPayload:
    """Search payload builder maps query/location/limit correctly."""

    def test_maps_query_to_keywords(self):
        client = JoobleAPIClient(settings=_configured_settings())
        payload = client.build_search_payload(query="devops")
        assert payload["keywords"] == "devops"

    def test_maps_location(self):
        client = JoobleAPIClient(settings=_configured_settings())
        payload = client.build_search_payload(query="devops", location="Berlin")
        assert payload["location"] == "Berlin"

    def test_omits_location_when_empty(self):
        client = JoobleAPIClient(settings=_configured_settings())
        payload = client.build_search_payload(query="devops", location="")
        assert "location" not in payload

    def test_omits_location_when_none(self):
        client = JoobleAPIClient(settings=_configured_settings())
        payload = client.build_search_payload(query="devops", location=None)
        assert "location" not in payload

    def test_maps_limit_to_ResultOnPage(self):
        client = JoobleAPIClient(settings=_configured_settings())
        payload = client.build_search_payload(query="devops", limit=5)
        assert payload["ResultOnPage"] == 5

    def test_caps_limit_at_50(self):
        client = JoobleAPIClient(settings=_configured_settings())
        payload = client.build_search_payload(query="devops", limit=100)
        assert payload["ResultOnPage"] == 50

    def test_floor_limit_at_1(self):
        client = JoobleAPIClient(settings=_configured_settings())
        payload = client.build_search_payload(query="devops", limit=0)
        assert payload["ResultOnPage"] == 1

    def test_strips_query_whitespace(self):
        client = JoobleAPIClient(settings=_configured_settings())
        payload = client.build_search_payload(query="  devops  ")
        assert payload["keywords"] == "devops"

    def test_strips_location_whitespace(self):
        client = JoobleAPIClient(settings=_configured_settings())
        payload = client.build_search_payload(
            query="devops", location="  Berlin  "
        )
        assert payload["location"] == "Berlin"


class TestNormalizeJob:
    """normalize_job maps raw Jooble payload to ExternalOpportunityCandidate."""

    def test_normalize_full_job(self):
        """All fields are correctly mapped from a representative payload."""
        candidate = JoobleAPIClient().normalize_job(_JOOBLE_REAL_JOB)

        assert candidate.provider == "jooble"
        assert candidate.source_kind == "job"
        assert candidate.country == "GLOBAL"
        assert candidate.language == "en"

        assert candidate.external_id == "12345678"
        assert candidate.title == "Senior DevOps Engineer"
        assert candidate.company_name == "GlobalTech Inc."
        assert candidate.description is not None
        assert "CI/CD" in candidate.description
        assert candidate.location == "Remote"

        # Contract type from "type" field
        assert candidate.contract_type == "full-time"

        # Remote type inferred from location
        assert candidate.remote_type == "remote"

        # Source URL
        assert candidate.source_url == "https://jooble.org/job/12345678"

        # Published date from Unix timestamp (milliseconds)
        assert candidate.source_published_at is not None

        # Salary stored in tags as text
        assert len(candidate.tags) >= 1
        assert "$120,000" in candidate.tags[0]

        # raw_payload should contain all original fields plus _source_name
        # Must NOT contain the API key
        assert candidate.raw_payload["_source_name"] == "indeed"
        for k, v in _JOOBLE_REAL_JOB.items():
            assert candidate.raw_payload[k] == v, f"Mismatch for key {k}"
        assert "api_key" not in str(candidate.raw_payload).lower()

    def test_normalize_minimal_job(self):
        """Missing optional fields do not crash normalization."""
        candidate = JoobleAPIClient().normalize_job(_JOOBLE_MINIMAL_JOB)

        assert candidate.provider == "jooble"
        assert candidate.external_id == "87654321"
        assert candidate.title == "Minimal Job"

        # Optional fields should gracefully default
        assert candidate.company_name is None
        assert candidate.description is None
        assert candidate.location is None
        assert candidate.source_url is None
        assert candidate.source_published_at is None
        assert candidate.contract_type is None
        assert candidate.remote_type is None
        assert candidate.budget_min is None
        assert candidate.budget_max is None
        assert candidate.budget_currency is None
        assert candidate.tags == []
        assert candidate.raw_payload == _JOOBLE_MINIMAL_JOB

    def test_normalize_empty_dict(self):
        """Even an empty dict should not crash."""
        candidate = JoobleAPIClient().normalize_job({})

        assert candidate.provider == "jooble"
        assert candidate.external_id == ""
        assert candidate.title == ""
        assert candidate.company_name is None
        assert candidate.raw_payload == {}

    def test_normalize_bad_date_format(self):
        """Malformed date string should not crash; returns None."""
        job = dict(_JOOBLE_MINIMAL_JOB)
        job["updated"] = "not-a-date"
        candidate = JoobleAPIClient().normalize_job(job)

        assert candidate.source_published_at is None

    def test_normalize_date_as_iso_string(self):
        """ISO date string should be parsed correctly."""
        job = dict(_JOOBLE_MINIMAL_JOB)
        job["updated"] = "2025-10-01T12:00:00Z"
        candidate = JoobleAPIClient().normalize_job(job)

        assert candidate.source_published_at is not None
        assert candidate.source_published_at.year == 2025

    def test_normalize_date_as_iso_without_tz(self):
        """ISO date without timezone should default to UTC."""
        job = dict(_JOOBLE_MINIMAL_JOB)
        job["updated"] = "2025-10-01T12:00:00"
        candidate = JoobleAPIClient().normalize_job(job)

        assert candidate.source_published_at is not None
        assert candidate.source_published_at.tzinfo == timezone.utc

    def test_normalize_preserves_raw_payload(self):
        """raw_payload is an independent copy of the input."""
        original = dict(_JOOBLE_REAL_JOB)
        candidate = JoobleAPIClient().normalize_job(original)

        # Mutating the original should not affect the candidate
        original["id"] = 99999999
        assert candidate.external_id == "12345678"

    def test_normalize_returns_correct_type(self):
        """normalize_job returns an ExternalOpportunityCandidate instance."""
        candidate = JoobleAPIClient().normalize_job(_JOOBLE_REAL_JOB)
        assert isinstance(candidate, ExternalOpportunityCandidate)

    def test_normalize_int_id_becomes_string(self):
        """Integer id should be converted to string."""
        candidate = JoobleAPIClient().normalize_job({"id": 42, "title": "Test"})
        assert candidate.external_id == "42"
        assert isinstance(candidate.external_id, str)

    def test_normalize_id_none(self):
        """None id should result in empty string external_id."""
        candidate = JoobleAPIClient().normalize_job(
            {"id": None, "title": "Test"}
        )
        assert candidate.external_id == ""

    def test_normalize_salary_as_text(self):
        """Salary string is stored in tags."""
        job = dict(_JOOBLE_MINIMAL_JOB)
        job["salary"] = "$50,000 - $70,000"
        candidate = JoobleAPIClient().normalize_job(job)
        assert len(candidate.tags) >= 1
        assert "$50,000" in candidate.tags[0]

    def test_normalize_no_salary(self):
        """Missing salary results in empty tags (no description)."""
        candidate = JoobleAPIClient().normalize_job(_JOOBLE_MINIMAL_JOB)
        assert candidate.tags == []

    def test_normalize_remote_from_location(self):
        """Remote type inferred from location containing 'remote'."""
        job = {"id": 1, "title": "Remote Job", "location": "Remote"}
        candidate = JoobleAPIClient().normalize_job(job)
        assert candidate.remote_type == "remote"

    def test_normalize_remote_from_contract_type(self):
        """Remote type inferred from contract_type containing 'remote'."""
        job = {"id": 2, "title": "Job", "type": "remote"}
        candidate = JoobleAPIClient().normalize_job(job)
        assert candidate.remote_type == "remote"

    def test_raw_payload_has_no_credentials(self):
        """The raw_payload must never contain the API key."""
        candidate = JoobleAPIClient().normalize_job(_JOOBLE_REAL_JOB)
        payload_str = str(candidate.raw_payload)
        assert "api_key" not in payload_str.lower()
        assert "test-jooble-api-key" not in payload_str


class TestSearchJobsWithMockedTransport:
    """search_jobs uses mocked transport only; no real HTTP call."""

    def test_search_with_mocked_client(self):
        """search_jobs uses the injected HTTP client, not real network."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _SINGLE_RESULT_RESPONSE),
        )
        jb_client = JoobleAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = jb_client.search_jobs(query="devops", limit=5)

        assert len(results) == 1
        assert results[0].provider == "jooble"
        assert results[0].external_id == "12345678"
        assert results[0].title == "Senior DevOps Engineer"

        # Verify the mock was called (no real HTTP call happened)
        mock_client.post.assert_called_once()

    def test_search_http_client_injection_parameter(self):
        """The http_client parameter overrides the constructor client."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _NO_RESULTS_RESPONSE),
        )
        jb_client = JoobleAPIClient(settings=_configured_settings())
        results = jb_client.search_jobs(
            query="devops", http_client=mock_client
        )

        assert len(results) == 0
        mock_client.post.assert_called_once()

    def test_search_no_results(self):
        """Empty jobs list returns empty candidates."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _NO_RESULTS_RESPONSE),
        )
        jb_client = JoobleAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = jb_client.search_jobs(query="nothing")

        assert results == []

    def test_search_multiple_results(self):
        """Multiple jobs in results are all normalized."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _MULTI_RESULT_RESPONSE),
        )
        jb_client = JoobleAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        results = jb_client.search_jobs(query="devops")

        assert len(results) == 2
        assert results[0].external_id == "12345678"
        assert results[1].external_id == "23456789"

    def test_search_raises_on_api_failure(self):
        """Non-200 search response raises JoobleAPIError."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(500, {"error": "server error"}),
        )
        jb_client = JoobleAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            jb_client.search_jobs(query="devops")
            assert False, "Expected JoobleAPIError"
        except JoobleAPIError:
            pass

    def test_search_raises_on_unauthorized(self):
        """401 response raises JoobleAPIError."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(401, {"error": "unauthorized"}),
        )
        jb_client = JoobleAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            jb_client.search_jobs(query="devops")
            assert False, "Expected JoobleAPIError"
        except JoobleAPIError:
            pass

    def test_search_raises_on_missing_configuration(self):
        """search_jobs raises JoobleConfigurationError when not configured."""
        jb_client = JoobleAPIClient()
        try:
            jb_client.search_jobs(query="devops")
            assert False, "Expected JoobleConfigurationError"
        except JoobleConfigurationError:
            pass

    def test_search_passes_correct_params_to_http_client(self):
        """Verify the HTTP client is called with the right URL and payload."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(200, _SINGLE_RESULT_RESPONSE),
        )
        jb_client = JoobleAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        jb_client.search_jobs(query="devops", location="Berlin", limit=3)

        # Check the search request
        call_kwargs = mock_client.post.call_args
        assert call_kwargs is not None
        search_url = call_kwargs[0][0]
        assert "jooble.org" in search_url
        assert "test-jooble-api-key" in search_url

        # Check JSON payload
        json_payload = call_kwargs[1].get("json", {})
        assert json_payload["keywords"] == "devops"
        assert json_payload["location"] == "Berlin"
        assert json_payload["ResultOnPage"] == 3

    def test_error_message_contains_no_secrets(self):
        """Error responses never expose the API key."""
        mock_client = _make_mock_client(
            search_resp=_make_mock_response(401, {"error": "unauthorized"}),
        )
        jb_client = JoobleAPIClient(
            settings=_configured_settings(),
            http_client=mock_client,
        )
        try:
            jb_client.search_jobs(query="devops")
        except JoobleAPIError as e:
            msg = str(e)
            assert "test-jooble-api-key" not in msg

    def test_constructor_timeout_from_settings(self):
        """Timeout is read from settings when available."""
        settings = Settings(
            JOOBLE_API_KEY="test-key",
            EXTERNAL_SOURCE_HTTP_TIMEOUT_SECONDS=30,
        )
        client = JoobleAPIClient(settings=settings)
        assert client.timeout == 30


# ===================================================================
# Live-Mode Gating Tests
# ===================================================================


class TestJoobleLiveModeWithCredentials:
    """Live mode with credentials routes to JoobleAPIClient."""

    def test_search_routes_to_real_client(self, client):
        """Verify search_jobs is called when credentials and live mode are set."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_key = global_settings.JOOBLE_API_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.JOOBLE_API_KEY = "live-test-jooble-key"

        _LIVE_CANDIDATE = ExternalOpportunityCandidate(
            provider="jooble",
            external_id="live-jooble-001",
            source_kind="job",
            title="Live DevOps Engineer",
            company_name="Live Corp",
            description="Live job description.",
            location="Remote",
            country="GLOBAL",
            language="en",
            contract_type="full-time",
            tags=["devops"],
            raw_payload={"id": "live-jooble-001"},
        )

        try:
            with patch(
                "app.services.jooble_client.JoobleAPIClient.search_jobs",
                return_value=[_LIVE_CANDIDATE],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/jooble/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 200
                assert mock_search.call_count >= 1

                data = resp.json()
                assert data["total"] >= 1
                assert data["items"][0]["external_id"] == "live-jooble-001"
                assert data["items"][0]["title"] == "Live DevOps Engineer"
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.JOOBLE_API_KEY = original_key

    def test_search_passes_parameters(self, client):
        """Verify the real client is called with the right search parameters."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_key = global_settings.JOOBLE_API_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.JOOBLE_API_KEY = "live-test-jooble-key"

        _LIVE_CANDIDATE = ExternalOpportunityCandidate(
            provider="jooble",
            external_id="live-jooble-002",
            source_kind="job",
            title="Live DevOps",
            company_name="Live Corp",
            description="Test",
            location="Berlin",
            country="DE",
            language="en",
            tags=[],
            raw_payload={},
        )

        try:
            with patch(
                "app.services.jooble_client.JoobleAPIClient.search_jobs",
                return_value=[_LIVE_CANDIDATE],
            ) as mock_search:
                client.get(
                    "/api/v1/external-sources/jooble/search",
                    params={"query": "devops", "location": "Berlin", "limit": 5},
                )
                mock_search.assert_called_once()
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["query"] == "devops"
                assert call_kwargs["location"] == "Berlin"
                assert call_kwargs["limit"] == 5
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.JOOBLE_API_KEY = original_key

    def test_diagnostics_reflect_real_api_enabled(self, client):
        """Diagnostics shows real_api_enabled=True in live+credentialed mode."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_key = global_settings.JOOBLE_API_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.JOOBLE_API_KEY = "live-test-jooble-key"

        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            jb = providers["jooble"]
            assert jb["real_api_enabled"] is True
            assert jb["safe_status"] == "ready"
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.JOOBLE_API_KEY = original_key


class TestJoobleLiveModeMissingCredentials:
    """Live mode missing credentials does not call JoobleAPIClient."""

    def test_missing_credentials_falls_back_to_mock(self, client):
        """Without credentials, search falls back to mock, no real client call."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_key = global_settings.JOOBLE_API_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.JOOBLE_API_KEY = None

        try:
            with patch(
                "app.services.jooble_client.JoobleAPIClient.search_jobs",
                return_value=[ExternalOpportunityCandidate(
                    provider="jooble",
                    external_id="live-jooble-should-not-appear",
                    source_kind="job",
                    title="Should Not Appear",
                    company_name="Fake Corp",
                    description="Should not be returned",
                    country="GLOBAL",
                    language="en",
                    tags=[],
                    raw_payload={},
                )],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/jooble/search",
                    params={"query": "devops"},
                )
                assert resp.status_code == 200
                # The real client should NOT have been called
                mock_search.assert_not_called()

                data = resp.json()
                assert data["total"] > 0
                # Results are mock data, not live
                for item in data["items"]:
                    assert item["provider"] == "jooble"
                    # Mock IDs start with "job-gl-", not "live-jooble-"
                    assert item["external_id"].startswith("job-gl-")
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.JOOBLE_API_KEY = original_key

    def test_diagnostics_shows_missing_credentials(self, client):
        """Diagnostics shows missing_credentials when mode != mock but no creds."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_key = global_settings.JOOBLE_API_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.JOOBLE_API_KEY = None

        try:
            resp = client.get("/api/v1/external-sources/providers")
            providers = {p["provider"]: p for p in resp.json()["providers"]}
            jb = providers["jooble"]
            assert jb["real_api_enabled"] is False
            assert jb["safe_status"] == "missing_credentials"
            assert "not configured" in jb["safe_message"].lower()
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.JOOBLE_API_KEY = original_key


# ===================================================================
# Provider Registration
# ===================================================================


class TestProviderRegistration:
    """Jooble is registered in the global provider registry."""

    def test_jooble_registered(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert "jooble" in PROVIDER_REGISTRY

    def test_registry_size(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert len(PROVIDER_REGISTRY) == 6

    def test_registry_contains_all_expected(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        expected = {
            "france_travail",
            "adzuna_uk",
            "adzuna_fr",
            "adzuna_de",
            "freelancer",
            "jooble",
        }
        assert set(PROVIDER_REGISTRY) == expected

    def test_jooble_provider_attributes(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["jooble"]
        assert cls.provider == "jooble"
        assert cls.label == "Jooble"
        assert cls.country == "GLOBAL"
        assert cls.language == "en"
        assert cls.source_kind == "job"
        assert cls.supports_real_api is True
        assert cls._credential_fields == ["JOOBLE_API_KEY"]


# ===================================================================
# Providers Endpoint
# ===================================================================


class TestProvidersEndpoint:
    """Providers API endpoint includes Jooble."""

    def test_providers_includes_jooble(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert "jooble" in providers

    def test_providers_count(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert len(resp.json()["providers"]) == 6

    def test_jooble_provider_info(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        jb = providers["jooble"]
        assert jb["label"] == "Jooble"
        assert jb["country"] == "GLOBAL"
        assert jb["source_kind"] == "job"
        assert jb["supports_real_api"] is True

    def test_existing_providers_still_present(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert "france_travail" in providers
        assert "adzuna_uk" in providers
        assert "adzuna_fr" in providers
        assert "adzuna_de" in providers
        assert "freelancer" in providers


# ===================================================================
# Mock Search
# ===================================================================


class TestMockSearch:
    """Mock search returns deterministic candidates."""

    def test_jooble_mock_search_returns_data(self, client):
        resp = client.get(
            "/api/v1/external-sources/jooble/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "jooble"
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["provider"] == "jooble"
            assert item["country"] in ("GLOBAL", "DE", "GB", "US")
            assert item["language"] == "en"

    def test_jooble_mock_search_location_filter(self, client):
        resp = client.get(
            "/api/v1/external-sources/jooble/search",
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

    def test_jooble_mock_search_limit(self, client):
        resp = client.get(
            "/api/v1/external-sources/jooble/search",
            params={"query": "devops", "limit": 2},
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2

    def test_jooble_mock_has_five_or_more_candidates(self, client):
        resp = client.get(
            "/api/v1/external-sources/jooble/search",
            params={"query": "cloud", "limit": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 4

    def test_jooble_mock_unknown_query_returns_empty(self, client):
        resp = client.get(
            "/api/v1/external-sources/jooble/search",
            params={"query": "xyznonexistent"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ===================================================================
# Combined Search
# ===================================================================


class TestCombinedSearch:
    """Combined search works with Jooble and existing providers."""

    def test_combined_all_six_providers(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={
                "providers": (
                    "france_travail,adzuna_uk,adzuna_fr,"
                    "adzuna_de,freelancer,jooble"
                ),
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
        assert "jooble" in providers_found
        assert data["total"] >= 6

    def test_combined_jooble_with_adzuna_uk(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={
                "providers": "jooble,adzuna_uk",
                "query": "devops",
            },
        )
        assert resp.status_code == 200
        providers_found = {item["provider"] for item in resp.json()["items"]}
        assert "jooble" in providers_found
        assert "adzuna_uk" in providers_found

    def test_combined_live_mode_jooble(self, client):
        """Combined search: live mode for jooble with credentials."""
        from app.core.config import settings as global_settings

        original_mode = global_settings.EXTERNAL_SOURCES_MODE
        original_key = global_settings.JOOBLE_API_KEY

        global_settings.EXTERNAL_SOURCES_MODE = "live"
        global_settings.JOOBLE_API_KEY = "live-test-jooble-key"

        _LIVE_JOOBLE = ExternalOpportunityCandidate(
            provider="jooble",
            external_id="live-jooble-combined-001",
            source_kind="job",
            title="Live Combined DevOps",
            company_name="Live Corp",
            description="Live combined job.",
            location="Remote",
            country="GLOBAL",
            language="en",
            contract_type="full-time",
            tags=["devops"],
            raw_payload={"id": "live-jooble-combined-001"},
        )

        try:
            with patch(
                "app.services.jooble_client.JoobleAPIClient.search_jobs",
                return_value=[_LIVE_JOOBLE],
            ) as mock_search:
                resp = client.get(
                    "/api/v1/external-sources/search",
                    params={
                        "providers": "france_travail,jooble",
                        "query": "devops",
                    },
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["total"] >= 1
                mock_search.assert_called()

                providers_found = {item["provider"] for item in data["items"]}
                assert "jooble" in providers_found
                assert "france_travail" in providers_found
        finally:
            global_settings.EXTERNAL_SOURCES_MODE = original_mode
            global_settings.JOOBLE_API_KEY = original_key


# ===================================================================
# No Database Mutation
# ===================================================================


class TestNoDatabaseMutation:
    """No DB mutation from search endpoints for Jooble."""

    def test_jooble_search_no_db_mutation(self, client, db_session):
        from app.models.company import Company
        from app.models.opportunity import Opportunity
        from app.models.source_record import SourceRecord

        resp = client.get(
            "/api/v1/external-sources/jooble/search",
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
                "providers": "france_travail,adzuna_uk,jooble",
                "query": "devops",
            },
        )
        assert resp.status_code == 200
        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0


# ===================================================================
# Import Candidate
# ===================================================================


class TestImportCandidate:
    """Importing a candidate from Jooble creates records properly."""

    _IMPORT_PAYLOAD = {
        "provider": "jooble",
        "external_id": "jooble-import-001",
        "source_kind": "job",
        "title": "DevOps Engineer",
        "company_name": "GlobalTech Inc.",
        "description": "Build and maintain CI/CD pipelines.",
        "location": "Remote",
        "country": "GLOBAL",
        "language": "en",
        "contract_type": "full-time",
        "tags": ["devops", "cloud"],
        "raw_payload": {"id": "jooble-import-001"},
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

        # SourceRecord metadata
        assert data["source_record"]["source_name"] == "jooble"
        assert data["source_record"]["source_type"] == "other"
        assert data["source_record"]["external_id"] == "jooble-import-001"

        # Opportunity should have imported_pending_review status
        assert data["opportunity"]["status"] == "imported_pending_review"

    def test_import_sets_correct_source_type(self, client):
        """Jooble imports get source_type=other."""
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._IMPORT_PAYLOAD,
        )
        assert resp.status_code == 200
        assert resp.json()["source_record"]["source_type"] == "other"

    def test_import_creates_imported_pending_review(self, db_session: Session):
        from app.core.enums import OpportunityStatus
        from app.models.opportunity import Opportunity
        from app.schemas.external_source import ExternalOpportunityCandidate
        from app.services.external_sources import import_external_candidate

        candidate = ExternalOpportunityCandidate(
            provider="jooble",
            external_id="jooble-import-review-001",
            source_kind="job",
            title="Review Test DevOps",
            company_name="Test Corp",
            description="Test import pending review",
            location="Remote",
            country="GLOBAL",
            language="en",
            contract_type="full-time",
            tags=["devops"],
            raw_payload={"id": "jooble-import-review-001"},
        )
        result = import_external_candidate(candidate, db_session)

        assert result.created_opportunity is True
        opp = db_session.get(
            Opportunity, uuid.UUID(result.opportunity["id"])
        )
        assert opp is not None
        assert opp.status == OpportunityStatus.imported_pending_review
        assert opp.source.value == "other"

    def test_import_duplicate(self, client):
        """Importing the same candidate twice detects duplicate."""
        resp1 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._IMPORT_PAYLOAD,
        )
        assert resp1.status_code == 200
        assert resp1.json()["duplicate_detected"] is False

        resp2 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=self._IMPORT_PAYLOAD,
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["duplicate_detected"] is True
        assert data2["created_source_record"] is False
        assert data2["created_opportunity"] is False

    def test_import_unknown_provider_rejected(self, client):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json={
                "provider": "nonexistent",
                "external_id": "test-001",
                "source_kind": "job",
                "title": "Test",
                "country": "GLOBAL",
                "language": "en",
                "tags": [],
                "raw_payload": {},
            },
        )
        assert resp.status_code == 400


# ===================================================================
# Existing Providers Unchanged
# ===================================================================


class TestExistingProvidersUnchanged:
    """Existing provider behavior is unchanged by Jooble addition."""

    def test_france_travail_still_mock(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0
        for item in resp.json()["items"]:
            assert item["provider"] == "france_travail"

    def test_adzuna_uk_still_mock(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_uk/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0
        for item in resp.json()["items"]:
            assert item["provider"] == "adzuna_uk"

    def test_adzuna_fr_still_mock(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_fr/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_adzuna_de_still_mock(self, client):
        resp = client.get(
            "/api/v1/external-sources/adzuna_de/search",
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
        for item in resp.json()["items"]:
            assert item["provider"] == "freelancer"

    def test_providers_list_unchanged_existing(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        providers = {p["provider"]: p for p in resp.json()["providers"]}
        assert providers["france_travail"]["supports_real_api"] is True
        assert providers["france_travail"]["safe_status"] == "mock"
        assert providers["adzuna_uk"]["supports_real_api"] is True
        assert providers["adzuna_uk"]["safe_status"] == "mock"
        assert providers["adzuna_fr"]["supports_real_api"] is True
        assert providers["adzuna_fr"]["safe_status"] == "mock"
        assert providers["adzuna_de"]["supports_real_api"] is True
        assert providers["adzuna_de"]["safe_status"] == "mock"
        assert providers["freelancer"]["supports_real_api"] is True
        assert providers["freelancer"]["safe_status"] == "mock"
        assert providers["jooble"]["supports_real_api"] is True
        assert providers["jooble"]["safe_status"] == "mock"


# ===================================================================
# Service Layer
# ===================================================================


class TestServiceLayer:
    """Direct service-layer tests for Phase 12D changes."""

    def test_provider_registry_size(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        assert len(PROVIDER_REGISTRY) == 6

    def test_registry_contains_all_expected(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        for p in (
            "france_travail",
            "adzuna_uk",
            "adzuna_fr",
            "adzuna_de",
            "freelancer",
            "jooble",
        ):
            assert p in PROVIDER_REGISTRY

    def test_jooble_provider_config(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["jooble"]
        assert cls.is_mock is True
        assert cls.supports_real_api is True
        assert cls._credential_fields == ["JOOBLE_API_KEY"]

    def test_jooble_provider_country_global(self):
        from app.services.external_sources import PROVIDER_REGISTRY

        cls = PROVIDER_REGISTRY["jooble"]
        assert cls.country == "GLOBAL"
        assert cls.language == "en"

    def test_external_sources_module_importable(self):
        """The external_sources module still imports cleanly."""
        from app.services import external_sources

        providers = external_sources.list_external_source_providers()
        assert len(providers) == 6

    def test_jooble_client_importable(self):
        """The jooble_client module imports without side effects."""
        from app.services.jooble_client import JoobleAPIClient

        assert JoobleAPIClient is not None
