"""Phase 8D — AI Provider Runtime Diagnostics & Safe Failure Handling tests.

Covers:
- Diagnostics endpoint returns correct provider configuration
- Provider resolver raises UnknownAIProviderError for unknown providers
- Service validation catches invalid/missing output keys
- Endpoint safe failures — no partial mutations on AI failure
- Regression — all existing behavior still works
"""

from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.services.ai_message_generation import (
    _validate_ai_result,
    generate_ai_draft,
)
from app.services.ai_providers import (
    AIProviderError,
    AIProviderGenerationError,
    InvalidAIProviderOutputError,
    MockAIProvider,
    UnknownAIProviderError,
    get_ai_provider,
    list_available_ai_providers,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_opportunity(**kw):
    obj = MagicMock()
    obj.title = kw.get("title", "Formation DevOps")
    obj.description = kw.get("description", "")
    obj.detected_need = kw.get("detected_need", "")
    obj.recommended_landing_page = kw.get("recommended_landing_page", "")
    return obj


def _make_mock_company(**kw):
    obj = MagicMock()
    obj.name = kw.get("name", "ACME Corp")
    return obj


def _make_mock_contact(**kw):
    obj = MagicMock()
    obj.full_name = kw.get("full_name", "Jean Dupont")
    return obj


def _make_mock_offer(**kw):
    obj = MagicMock()
    obj.name = kw.get("name", "Accompagnement DevOps")
    obj.short_description = kw.get("short_description", "Formation DevOps complète")
    obj.landing_page_url = kw.get("landing_page_url", "https://soria.academy/devops")
    return obj


def _make_mock_resource(**kw):
    obj = MagicMock()
    obj.title = kw.get("title", "Guide DevOps")
    obj.short_description = kw.get("short_description", "Un guide complet")
    obj.public_url = kw.get("public_url", "https://soria.academy/guide-devops")
    return obj


# ---------------------------------------------------------------------------
# Diagnostics endpoint tests
# ---------------------------------------------------------------------------


class TestAiDiagnostics:
    """GET /api/v1/opportunities/ai-diagnostics/provider"""

    def test_returns_configured_provider(self, client):
        """Diagnostics endpoint returns the configured provider."""
        resp = client.get("/api/v1/opportunities/ai-diagnostics/provider")
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured_provider"] == settings.AI_DRAFT_PROVIDER

    def test_available_providers_contains_mock_ai(self, client):
        """available_providers list contains mock_ai."""
        resp = client.get("/api/v1/opportunities/ai-diagnostics/provider")
        assert resp.status_code == 200
        data = resp.json()
        assert "mock_ai" in data["available_providers"]

    def test_provider_available_is_true(self, client):
        """provider_available is true when configured provider is in
        the registry."""
        resp = client.get("/api/v1/opportunities/ai-diagnostics/provider")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider_available"] is True

    def test_returns_config_metadata(self, client):
        """Endpoint returns model name, prompt profile, prompt version."""
        resp = client.get("/api/v1/opportunities/ai-diagnostics/provider")
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured_model_name"] == settings.AI_DRAFT_MODEL_NAME
        assert data["configured_prompt_profile"] == settings.AI_DRAFT_PROMPT_PROFILE
        assert data["configured_prompt_version"] == settings.AI_DRAFT_PROMPT_VERSION

    def test_does_not_create_drafts_or_events(self, client):
        """Diagnostics endpoint does not create MessageDraft or
        ComplianceEvent."""
        # Check no drafts exist before
        drafts_before = client.get("/api/v1/message-drafts").json()
        events_before = client.get("/api/v1/compliance-events").json()

        resp = client.get("/api/v1/opportunities/ai-diagnostics/provider")
        assert resp.status_code == 200

        drafts_after = client.get("/api/v1/message-drafts").json()
        events_after = client.get("/api/v1/compliance-events").json()

        assert drafts_after["total"] == drafts_before["total"]
        assert events_after["total"] == events_before["total"]

    def test_status_ok_when_provider_available(self, client):
        """Status is 'ok' and message is positive when provider is
        registered."""
        resp = client.get("/api/v1/opportunities/ai-diagnostics/provider")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "is available" in data["message"]
        assert "mock_ai" in data["message"]


# ---------------------------------------------------------------------------
# Provider resolver unit tests
# ---------------------------------------------------------------------------


class TestProviderResolverExceptions:
    """get_ai_provider() with new exception hierarchy."""

    def test_unknown_provider_raises_unknown_ai_provider_error(self):
        """Unknown provider raises UnknownAIProviderError."""
        with pytest.raises(UnknownAIProviderError, match="Unknown AI provider"):
            get_ai_provider("does_not_exist")

    def test_unknown_ai_provider_error_is_also_value_error(self):
        """UnknownAIProviderError is a subclass of ValueError (backward
        compat with Phase 8B tests)."""
        with pytest.raises(ValueError, match="Unknown AI provider"):
            get_ai_provider("does_not_exist")

    def test_unknown_ai_provider_error_is_ai_provider_error(self):
        """UnknownAIProviderError is a subclass of AIProviderError."""
        assert issubclass(UnknownAIProviderError, AIProviderError)

    def test_unknown_ai_provider_error_inheritance(self):
        """Verify MRO of UnknownAIProviderError."""
        assert issubclass(UnknownAIProviderError, ValueError)
        assert issubclass(UnknownAIProviderError, AIProviderError)

    def test_resolves_mock_ai_provider(self):
        """get_ai_provider('mock_ai') returns a MockAIProvider instance."""
        provider = get_ai_provider("mock_ai")
        assert isinstance(provider, MockAIProvider)

    def test_list_available_contains_mock_ai(self):
        """list_available_ai_providers() includes mock_ai."""
        providers = list_available_ai_providers()
        assert "mock_ai" in providers


# ---------------------------------------------------------------------------
# Service validation unit tests
# ---------------------------------------------------------------------------


class TestAiResultValidation:
    """_validate_ai_result() private function."""

    def _valid_result(self, **overrides):
        result = {
            "subject": "Test subject",
            "body": "Test body content",
            "provider": "mock_ai",
            "model_name": "mock-soria-v1",
            "prompt_version": "ai-draft-v1",
            "safety_note": "Requires human validation",
        }
        result.update(overrides)
        return result

    def test_valid_result_passes(self):
        """Valid result passes validation unchanged."""
        result = self._valid_result()
        assert _validate_ai_result(result) is result

    def test_missing_subject_raises_error(self):
        """Missing 'subject' key raises InvalidAIProviderOutputError."""
        result = self._valid_result()
        del result["subject"]
        with pytest.raises(InvalidAIProviderOutputError, match="subject"):
            _validate_ai_result(result)

    def test_missing_body_raises_error(self):
        """Missing 'body' key raises InvalidAIProviderOutputError."""
        result = self._valid_result()
        del result["body"]
        with pytest.raises(InvalidAIProviderOutputError, match="body"):
            _validate_ai_result(result)

    def test_missing_provider_raises_error(self):
        """Missing 'provider' key raises InvalidAIProviderOutputError."""
        result = self._valid_result()
        del result["provider"]
        with pytest.raises(InvalidAIProviderOutputError, match="provider"):
            _validate_ai_result(result)

    def test_missing_model_name_raises_error(self):
        """Missing 'model_name' key raises InvalidAIProviderOutputError."""
        result = self._valid_result()
        del result["model_name"]
        with pytest.raises(InvalidAIProviderOutputError, match="model_name"):
            _validate_ai_result(result)

    def test_missing_prompt_version_raises_error(self):
        """Missing 'prompt_version' key raises InvalidAIProviderOutputError."""
        result = self._valid_result()
        del result["prompt_version"]
        with pytest.raises(InvalidAIProviderOutputError, match="prompt_version"):
            _validate_ai_result(result)

    def test_missing_safety_note_raises_error(self):
        """Missing 'safety_note' key raises InvalidAIProviderOutputError."""
        result = self._valid_result()
        del result["safety_note"]
        with pytest.raises(InvalidAIProviderOutputError, match="safety_note"):
            _validate_ai_result(result)

    def test_empty_subject_raises_error(self):
        """Empty string subject raises InvalidAIProviderOutputError."""
        result = self._valid_result(subject="")
        with pytest.raises(InvalidAIProviderOutputError, match="subject"):
            _validate_ai_result(result)

    def test_blank_subject_raises_error(self):
        """Whitespace-only subject raises InvalidAIProviderOutputError."""
        result = self._valid_result(subject="   ")
        with pytest.raises(InvalidAIProviderOutputError, match="subject"):
            _validate_ai_result(result)

    def test_empty_body_raises_error(self):
        """Empty string body raises InvalidAIProviderOutputError."""
        result = self._valid_result(body="")
        with pytest.raises(InvalidAIProviderOutputError, match="body"):
            _validate_ai_result(result)

    def test_empty_provider_raises_error(self):
        """Empty string provider raises InvalidAIProviderOutputError."""
        result = self._valid_result(provider="")
        with pytest.raises(InvalidAIProviderOutputError, match="provider"):
            _validate_ai_result(result)

    def test_empty_model_name_raises_error(self):
        """Empty string model_name raises InvalidAIProviderOutputError."""
        result = self._valid_result(model_name="")
        with pytest.raises(InvalidAIProviderOutputError, match="model_name"):
            _validate_ai_result(result)

    def test_empty_prompt_version_raises_error(self):
        """Empty string prompt_version raises InvalidAIProviderOutputError."""
        result = self._valid_result(prompt_version="")
        with pytest.raises(InvalidAIProviderOutputError, match="prompt_version"):
            _validate_ai_result(result)

    def test_non_string_subject_raises_error(self):
        """Non-string subject (int) raises InvalidAIProviderOutputError."""
        result = self._valid_result(subject=123)
        with pytest.raises(InvalidAIProviderOutputError, match="subject"):
            _validate_ai_result(result)


class TestProviderRuntimeErrorWrapping:
    """Provider runtime errors are wrapped in AIProviderGenerationError."""

    def test_provider_runtime_error_is_wrapped(self):
        """Unexpected exception from provider.generate raises
        AIProviderGenerationError."""
        opp = _make_mock_opportunity()
        company = _make_mock_company()

        # Monkey-patch the provider to raise an unexpected error
        original_generate = MockAIProvider.generate
        try:
            def broken_generate(self, ctx):
                raise RuntimeError("Connection refused")

            MockAIProvider.generate = broken_generate
            with pytest.raises(AIProviderGenerationError, match="failed to generate"):
                generate_ai_draft(opportunity=opp, company=company)
        finally:
            MockAIProvider.generate = original_generate

    def test_unknown_provider_propagates_unchanged(self):
        """UnknownAIProviderError propagates through generate_ai_draft
        unchanged (not wrapped)."""
        opp = _make_mock_opportunity()
        company = _make_mock_company()

        with pytest.raises(UnknownAIProviderError, match="Unknown AI provider"):
            generate_ai_draft(
                opportunity=opp,
                company=company,
                provider_name="nonexistent_provider",
            )

    def test_invalid_output_propagates_unchanged(self):
        """InvalidAIProviderOutputError propagates when the provider
        returns invalid output."""
        opp = _make_mock_opportunity()
        company = _make_mock_company()

        original_generate = MockAIProvider.generate
        try:
            def broken_generate(self, ctx):
                return {"subject": "", "body": "test", "provider": "mock_ai",
                        "model_name": "v1", "prompt_version": "v1",
                        "safety_note": "note"}

            MockAIProvider.generate = broken_generate
            with pytest.raises(InvalidAIProviderOutputError, match="subject"):
                generate_ai_draft(opportunity=opp, company=company)
        finally:
            MockAIProvider.generate = original_generate


# ---------------------------------------------------------------------------
# Endpoint safe failure tests
# ---------------------------------------------------------------------------


def _create_company(client, **overrides):
    payload = {
        "name": "Phase8D Company",
        "domain": "phase8d.fr",
        "city": "Paris",
        "country": "France",
        "source": "manual",
        "status": "new",
        "company_type": "unknown",
    }
    payload.update(overrides)
    return client.post("/api/v1/companies", json=payload)


def _create_contact(client, company_id, **overrides):
    payload = {
        "company_id": str(company_id),
        "first_name": "Alice",
        "last_name": "Martin",
        "full_name": "Alice Martin",
        "role_title": "CTO",
        "email": "alice@phase8d.fr",
        "source": "manual",
        "contact_type": "director",
    }
    payload.update(overrides)
    return client.post("/api/v1/contacts", json=payload)


def _create_opportunity(client, company_id, **overrides):
    payload = {
        "company_id": str(company_id),
        "title": "Phase 8D Test Opportunity",
        "opportunity_type": "devops_cloud",
        "source": "manual",
    }
    payload.update(overrides)
    return client.post("/api/v1/opportunities", json=payload)


class TestEndpointAiDraftPreviewSafeFailure:
    """GET /api/v1/opportunities/{id}/ai-draft-preview with AI failure."""

    def test_unknown_provider_returns_503(self, client, monkeypatch):
        """Preview with unknown provider returns 503."""
        monkeypatch.setattr(settings, "AI_DRAFT_PROVIDER", "nonexistent")
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.get(f"/api/v1/opportunities/{opp_id}/ai-draft-preview")
        assert resp.status_code == 503
        assert "AI provider is not available" in resp.json()["detail"]

    def test_unknown_provider_creates_no_drafts_or_events(self, client, monkeypatch):
        """Preview with unknown provider creates no drafts or events."""
        monkeypatch.setattr(settings, "AI_DRAFT_PROVIDER", "nonexistent")
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        drafts_before = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}").json()
        events_before = client.get("/api/v1/compliance-events").json()

        resp = client.get(f"/api/v1/opportunities/{opp_id}/ai-draft-preview")
        assert resp.status_code == 503

        drafts_after = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}").json()
        events_after = client.get("/api/v1/compliance-events").json()

        assert drafts_after["total"] == drafts_before["total"]
        assert events_after["total"] == events_before["total"]

    def test_unknown_provider_does_not_mutate_opportunity(self, client, monkeypatch):
        """Preview failure does not mutate the opportunity."""
        monkeypatch.setattr(settings, "AI_DRAFT_PROVIDER", "nonexistent")
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        original = client.get(f"/api/v1/opportunities/{opp_id}").json()
        resp = client.get(f"/api/v1/opportunities/{opp_id}/ai-draft-preview")
        assert resp.status_code == 503
        after = client.get(f"/api/v1/opportunities/{opp_id}").json()
        assert after == original


class TestEndpointGenerateAiDraftSafeFailure:
    """POST /api/v1/opportunities/{id}/generate-ai-draft with AI failure."""

    def test_unknown_provider_returns_503(self, client, monkeypatch):
        """Generate with unknown provider returns 503."""
        monkeypatch.setattr(settings, "AI_DRAFT_PROVIDER", "nonexistent")
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert resp.status_code == 503
        assert "AI provider is not available" in resp.json()["detail"]

    def test_unknown_provider_creates_no_drafts_or_events(self, client, monkeypatch):
        """Generate failure creates no drafts or events."""
        monkeypatch.setattr(settings, "AI_DRAFT_PROVIDER", "nonexistent")
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        drafts_before = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}").json()
        events_before = client.get("/api/v1/compliance-events").json()

        resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert resp.status_code == 503

        drafts_after = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}").json()
        events_after = client.get("/api/v1/compliance-events").json()

        assert drafts_after["total"] == drafts_before["total"]
        assert events_after["total"] == events_before["total"]

    def test_unknown_provider_opportunity_unchanged(self, client, monkeypatch):
        """Opportunity status and fields remain unchanged after failure."""
        monkeypatch.setattr(settings, "AI_DRAFT_PROVIDER", "nonexistent")
        c_resp = _create_company(client)
        o_resp = _create_opportunity(
            client, c_resp.json()["id"],
            status="new", score=None,
        )
        opp_id = o_resp.json()["id"]

        original = client.get(f"/api/v1/opportunities/{opp_id}").json()
        resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert resp.status_code == 503
        after = client.get(f"/api/v1/opportunities/{opp_id}").json()
        assert after == original

    def test_invalid_output_returns_502(self, client, monkeypatch):
        """Provider returning invalid output returns 502."""
        original_generate = MockAIProvider.generate
        try:
            def broken_generate(self, ctx):
                return {"subject": "", "body": "test", "provider": "mock_ai",
                        "model_name": "v1", "prompt_version": "v1",
                        "safety_note": "note"}

            MockAIProvider.generate = broken_generate
            c_resp = _create_company(client)
            o_resp = _create_opportunity(client, c_resp.json()["id"])
            opp_id = o_resp.json()["id"]

            resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
            assert resp.status_code == 502
            assert "AI provider returned invalid output" in resp.json()["detail"]
        finally:
            MockAIProvider.generate = original_generate

    def test_invalid_output_creates_no_drafts_or_events(self, client, monkeypatch):
        """Invalid output does not create drafts or events."""
        original_generate = MockAIProvider.generate
        try:
            def broken_generate(self, ctx):
                return {"subject": "", "body": "test", "provider": "mock_ai",
                        "model_name": "v1", "prompt_version": "v1",
                        "safety_note": "note"}

            MockAIProvider.generate = broken_generate
            c_resp = _create_company(client)
            o_resp = _create_opportunity(client, c_resp.json()["id"])
            opp_id = o_resp.json()["id"]

            drafts_before = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}").json()
            events_before = client.get("/api/v1/compliance-events").json()

            resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
            assert resp.status_code == 502

            drafts_after = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}").json()
            events_after = client.get("/api/v1/compliance-events").json()

            assert drafts_after["total"] == drafts_before["total"]
            assert events_after["total"] == events_before["total"]
        finally:
            MockAIProvider.generate = original_generate


class TestEndpointRegenerateAiDraftSafeFailure:
    """POST /api/v1/opportunities/{id}/regenerate-ai-draft with AI failure."""

    def test_unknown_provider_returns_503(self, client, monkeypatch):
        """Regenerate with unknown provider returns 503."""
        monkeypatch.setattr(settings, "AI_DRAFT_PROVIDER", "nonexistent")
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.post(f"/api/v1/opportunities/{opp_id}/regenerate-ai-draft")
        assert resp.status_code == 503
        assert "AI provider is not available" in resp.json()["detail"]

    def test_unknown_provider_does_not_archive_old_draft(self, client, monkeypatch):
        """Regeneration failure does not archive the old AI draft."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        # Create an initial AI draft
        old = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert old.status_code == 200
        old_id = old.json()["id"]

        # Now try to regenerate with broken provider
        monkeypatch.setattr(settings, "AI_DRAFT_PROVIDER", "nonexistent")
        resp = client.post(f"/api/v1/opportunities/{opp_id}/regenerate-ai-draft")
        assert resp.status_code == 503

        # Old draft should still be active (not archived)
        old_draft = client.get(f"/api/v1/message-drafts/{old_id}")
        assert old_draft.status_code == 200
        assert old_draft.json()["status"] != "archived"

    def test_provider_failure_returns_502_and_keeps_old_draft(self, client):
        """Regenerate with provider runtime failure returns 502 and old
        AI draft remains active."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        # Create an initial AI draft
        old = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert old.status_code == 200
        old_id = old.json()["id"]

        # Break the provider
        original_generate = MockAIProvider.generate
        try:
            def broken_generate(self, ctx):
                raise RuntimeError("Provider crashed")

            MockAIProvider.generate = broken_generate
            resp = client.post(f"/api/v1/opportunities/{opp_id}/regenerate-ai-draft")
            assert resp.status_code == 502
            assert "AI provider failed to generate" in resp.json()["detail"]
        finally:
            MockAIProvider.generate = original_generate

        # Old draft should still be active
        old_draft = client.get(f"/api/v1/message-drafts/{old_id}")
        assert old_draft.status_code == 200
        assert old_draft.json()["status"] != "archived"


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------


class TestRegression:
    """All existing behavior must still work."""

    def test_normal_preview_still_works(self, client):
        """Normal mock_ai preview returns 200 with all expected fields."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.get(f"/api/v1/opportunities/{opp_id}/ai-draft-preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "mock_ai"
        assert data["model_name"] == "mock-soria-v1"
        assert data["prompt_version"] == "ai-draft-v1"
        assert data["prompt_profile"] == "prospecting_fr_v1"
        assert data["subject"]
        assert data["body"]
        assert data["safety_note"]

    def test_normal_generate_creates_ai_draft_with_metadata(self, client):
        """Normal generate-ai-draft creates draft with audit metadata."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert resp.status_code == 200
        data = resp.json()
        assert data["generated_by"] == "ai"
        assert data["ai_provider"] == "mock_ai"
        assert data["model_name"] == "mock-soria-v1"
        assert data["prompt_profile"] == "prospecting_fr_v1"
        assert data["prompt_version"] == "ai-draft-v1"

    def test_normal_generate_creates_compliance_event(self, client):
        """Normal generate-ai-draft creates a ComplianceEvent."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert resp.status_code == 200

        events = client.get("/api/v1/compliance-events").json()
        matching = [
            e for e in events["items"]
            if e["event_type"] == "message_generated"
            and e["opportunity_id"] == str(opp_id)
        ]
        assert len(matching) == 1

    def test_normal_regenerate_archives_and_creates(self, client):
        """Normal regenerate-ai-draft archives old draft and creates new
        one with audit metadata."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        old = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert old.status_code == 200
        old_id = old.json()["id"]

        new = client.post(f"/api/v1/opportunities/{opp_id}/regenerate-ai-draft")
        assert new.status_code == 200
        data = new.json()
        assert data["id"] != old_id
        assert data["generated_by"] == "ai"
        assert data["ai_provider"] == "mock_ai"
        assert data["model_name"] == "mock-soria-v1"
        assert data["prompt_profile"] == "prospecting_fr_v1"
        assert data["prompt_version"] == "ai-draft-v1"

        # Old draft should be archived
        old_draft = client.get(f"/api/v1/message-drafts/{old_id}")
        assert old_draft.status_code == 200
        assert old_draft.json()["status"] == "archived"

    def test_duplicate_prevention_still_works(self, client):
        """Duplicate prevention returns existing active draft."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        r1 = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert r1.status_code == 200
        r2 = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert r2.status_code == 200
        assert r2.json()["id"] == r1.json()["id"]
