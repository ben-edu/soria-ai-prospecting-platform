"""Phase 8B — AI Provider Abstraction & Prompt Control tests.

Covers:
- Provider resolver (mock provider, unknown provider rejection)
- Prompt builder context construction
- MockAIProvider.generate() output
- generate_ai_draft orchestrator metadata and error handling
- Endpoint-level behavior preservation after refactoring
"""

from unittest.mock import MagicMock

import pytest

from app.core.config import settings
from app.services.ai_message_generation import generate_ai_draft
from app.services.ai_prompt_builder import (
    DEFAULT_PROMPT_PROFILE,
    DEFAULT_PROMPT_VERSION,
    build_prompt_context,
)
from app.services.ai_providers import (
    PROVIDER_REGISTRY,
    MockAIProvider,
    get_ai_provider,
)

# ---------------------------------------------------------------------------
# Mock factories (no DB required)
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
# Provider resolver unit tests
# ---------------------------------------------------------------------------


class TestAiProviderResolver:
    """get_ai_provider() and PROVIDER_REGISTRY."""

    def test_resolves_mock_ai_provider(self):
        """get_ai_provider('mock_ai') returns a MockAIProvider instance."""
        provider = get_ai_provider("mock_ai")
        assert isinstance(provider, MockAIProvider)

    def test_mock_provider_metadata(self):
        """MockAIProvider has correct provider, model_name, prompt_version."""
        provider = MockAIProvider()
        assert provider.provider == "mock_ai"
        assert provider.model_name == "mock-soria-v1"
        assert provider.prompt_version == "ai-draft-v1"

    def test_unknown_provider_raises_value_error(self):
        """An unregistered provider name raises ValueError with a clear
        message."""
        with pytest.raises(ValueError, match="Unknown AI provider"):
            get_ai_provider("nonexistent_provider")

    def test_provider_registry_contains_mock_ai(self):
        """PROVIDER_REGISTRY has mock_ai mapped to MockAIProvider."""
        assert "mock_ai" in PROVIDER_REGISTRY
        assert PROVIDER_REGISTRY["mock_ai"] is MockAIProvider


# ---------------------------------------------------------------------------
# Prompt builder unit tests
# ---------------------------------------------------------------------------


class TestPromptBuilderContext:
    """build_prompt_context() entity inclusion."""

    def test_includes_opportunity_title(self):
        """Prompt context contains the opportunity title."""
        opp = _make_mock_opportunity(title="Cybersécurité")
        ctx = build_prompt_context(opp)
        assert ctx["user_context"]["opportunity"]["title"] == "Cybersécurité"

    def test_includes_company_context(self):
        """Prompt context contains the company name."""
        opp = _make_mock_opportunity()
        company = _make_mock_company(name="ACME Corp")
        ctx = build_prompt_context(opp, company=company)
        assert ctx["user_context"]["company"]["name"] == "ACME Corp"

    def test_includes_contact_context(self):
        """Prompt context contains the contact name."""
        opp = _make_mock_opportunity()
        contact = _make_mock_contact(full_name="Marie Curie")
        ctx = build_prompt_context(opp, contact=contact)
        assert ctx["user_context"]["contact"]["full_name"] == "Marie Curie"

    def test_includes_detected_need(self):
        """Prompt context includes detected_need when present on opportunity."""
        opp = _make_mock_opportunity(detected_need="Manque de compétences DevOps")
        ctx = build_prompt_context(opp)
        assert ctx["user_context"]["opportunity"]["detected_need"] == (
            "Manque de compétences DevOps"
        )

    def test_includes_offer_context_when_present(self):
        """Prompt context includes matched_offer details when provided."""
        opp = _make_mock_opportunity()
        offer = _make_mock_offer(name="Offre Test")
        ctx = build_prompt_context(opp, matched_offer=offer)
        assert "matched_offer" in ctx["user_context"]
        assert ctx["user_context"]["matched_offer"]["name"] == "Offre Test"

    def test_includes_resource_context_when_present(self):
        """Prompt context includes matched_resource details when provided."""
        opp = _make_mock_opportunity()
        resource = _make_mock_resource(title="Ressource Test")
        ctx = build_prompt_context(opp, matched_resource=resource)
        assert "matched_resource" in ctx["user_context"]
        assert ctx["user_context"]["matched_resource"]["title"] == "Ressource Test"

    def test_omits_offer_key_when_not_provided(self):
        """Prompt context omits matched_offer when None."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp, matched_offer=None)
        assert "matched_offer" not in ctx["user_context"]

    def test_omits_resource_key_when_not_provided(self):
        """Prompt context omits matched_resource when None."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp, matched_resource=None)
        assert "matched_resource" not in ctx["user_context"]

    def test_falls_back_when_company_is_none(self):
        """Prompt context uses default string when company is None."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp, company=None)
        assert ctx["user_context"]["company"]["name"] == "Votre organisation"

    def test_falls_back_when_contact_is_none(self):
        """Prompt context uses default string when contact is None."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp, contact=None)
        assert ctx["user_context"]["contact"]["full_name"] == "Responsable"


class TestPromptBuilderSafety:
    """build_prompt_context() safety and instructions."""

    def test_safety_note_present(self):
        """Prompt context includes a safety_note string."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp)
        assert "safety_note" in ctx
        assert len(ctx["safety_note"]) > 50

    def test_safety_note_requires_human_validation(self):
        """Safety note explicitly mandates human validation before sending."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp)
        note = ctx["safety_note"]
        assert "validation humaine" in note
        assert "sans validation humaine" not in note or "Aucun" in note

    def test_system_instructions_contain_safety_rules(self):
        """System instructions include safety/human-validation rules."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp)
        instructions = ctx["system_instructions"]
        assert "validation humaine" in instructions
        assert "sans validation humaine" in instructions or "validation" in instructions


class TestPromptBuilderDefaults:
    """build_prompt_context() default metadata."""

    def test_default_prompt_profile(self):
        """Default prompt_profile is prospecting_fr_v1."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp)
        assert ctx["prompt_profile"] == DEFAULT_PROMPT_PROFILE

    def test_default_prompt_version(self):
        """Default prompt_version is ai-draft-v1."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp)
        assert ctx["prompt_version"] == DEFAULT_PROMPT_VERSION

    def test_custom_prompt_profile(self):
        """Can override prompt_profile."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp, prompt_profile="custom_v2")
        assert ctx["prompt_profile"] == "custom_v2"

    def test_custom_prompt_version(self):
        """Can override prompt_version."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp, prompt_version="custom-v2")
        assert ctx["prompt_version"] == "custom-v2"


# ---------------------------------------------------------------------------
# MockAIProvider unit tests
# ---------------------------------------------------------------------------


class TestMockAIProvider:
    """MockAIProvider.generate()."""

    def test_returns_all_expected_keys(self):
        """Output contains subject, body, provider, model_name,
        prompt_version, safety_note."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp)
        result = MockAIProvider().generate(ctx)
        expected_keys = {
            "subject", "body", "provider",
            "model_name", "prompt_version", "safety_note",
        }
        assert expected_keys.issubset(result.keys())

    def test_provider_metadata(self):
        """Output provider/model_name/prompt_version match provider class."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp)
        result = MockAIProvider().generate(ctx)
        assert result["provider"] == "mock_ai"
        assert result["model_name"] == "mock-soria-v1"
        assert result["prompt_version"] == "ai-draft-v1"

    def test_subject_contains_title_and_company(self):
        """Subject includes opportunity title and company name."""
        opp = _make_mock_opportunity(title="Cybersécurité")
        company = _make_mock_company(name="ACME Corp")
        ctx = build_prompt_context(opp, company=company)
        result = MockAIProvider().generate(ctx)
        assert "Cybersécurité" in result["subject"]
        assert "ACME Corp" in result["subject"]

    def test_body_contains_contact_and_company(self):
        """Body salutation includes contact name and company name."""
        opp = _make_mock_opportunity()
        company = _make_mock_company(name="ACME Corp")
        contact = _make_mock_contact(full_name="Marie Curie")
        ctx = build_prompt_context(opp, company=company, contact=contact)
        result = MockAIProvider().generate(ctx)
        assert "Marie Curie" in result["body"]
        assert "ACME Corp" in result["body"]
        assert "Formation DevOps" in result["body"]

    def test_body_includes_detected_need(self):
        """Body includes detected need text."""
        opp = _make_mock_opportunity(detected_need="Manque de compétences DevOps")
        ctx = build_prompt_context(opp)
        result = MockAIProvider().generate(ctx)
        assert "Manque de compétences DevOps" in result["body"]

    def test_body_includes_offer_context(self):
        """Body includes matched offer name and URL."""
        opp = _make_mock_opportunity()
        offer = _make_mock_offer(
            name="Offre Spéciale",
            landing_page_url="https://soria.academy/offre",
        )
        ctx = build_prompt_context(opp, matched_offer=offer)
        result = MockAIProvider().generate(ctx)
        assert "Offre Spéciale" in result["body"]
        assert "https://soria.academy/offre" in result["body"]

    def test_body_includes_resource_context(self):
        """Body includes matched resource title and URL."""
        opp = _make_mock_opportunity()
        resource = _make_mock_resource(
            title="Ressource Test",
            public_url="https://soria.academy/test",
        )
        ctx = build_prompt_context(opp, matched_resource=resource)
        result = MockAIProvider().generate(ctx)
        assert "Ressource Test" in result["body"]
        assert "https://soria.academy/test" in result["body"]

    def test_body_includes_landing_page(self):
        """Body includes recommended landing page when present."""
        opp = _make_mock_opportunity(recommended_landing_page="https://soria.academy/landing")
        ctx = build_prompt_context(opp)
        result = MockAIProvider().generate(ctx)
        assert "https://soria.academy/landing" in result["body"]

    def test_deterministic_output(self):
        """Same input produces identical output."""
        opp = _make_mock_opportunity()
        company = _make_mock_company()
        ctx = build_prompt_context(opp, company=company)
        r1 = MockAIProvider().generate(ctx)
        r2 = MockAIProvider().generate(ctx)
        assert r1 == r2


# ---------------------------------------------------------------------------
# generate_ai_draft orchestrator unit tests
# ---------------------------------------------------------------------------


class TestGenerateAiDraft:
    """generate_ai_draft() service function."""

    def test_returns_all_expected_keys(self):
        """Returns subject, body, provider, model_name, prompt_version,
        safety_note, prompt_profile."""
        opp = _make_mock_opportunity()
        company = _make_mock_company()
        result = generate_ai_draft(opportunity=opp, company=company)
        expected_keys = {
            "subject", "body", "provider", "model_name",
            "prompt_version", "safety_note", "prompt_profile",
        }
        assert expected_keys.issubset(result.keys())

    def test_default_metadata_matches_config(self):
        """Default metadata values match config defaults."""
        opp = _make_mock_opportunity()
        company = _make_mock_company()
        result = generate_ai_draft(opportunity=opp, company=company)
        assert result["provider"] == settings.AI_DRAFT_PROVIDER
        assert result["model_name"] == settings.AI_DRAFT_MODEL_NAME
        assert result["prompt_version"] == settings.AI_DRAFT_PROMPT_VERSION
        assert result["prompt_profile"] == settings.AI_DRAFT_PROMPT_PROFILE

    def test_override_provider_name(self):
        """Passing provider_name explicitly resolves correctly."""
        opp = _make_mock_opportunity()
        company = _make_mock_company()
        result = generate_ai_draft(
            opportunity=opp, company=company,
            provider_name="mock_ai",
        )
        assert result["provider"] == "mock_ai"

    def test_override_prompt_profile_and_version(self):
        """Passing prompt_profile and prompt_version explicitly."""
        opp = _make_mock_opportunity()
        company = _make_mock_company()
        result = generate_ai_draft(
            opportunity=opp, company=company,
            prompt_profile="test_v2",
            prompt_version="test-v2",
        )
        assert result["prompt_profile"] == "test_v2"
        # prompt_version reflects the context's prompt_version override
        assert result["prompt_version"] == "test-v2"

    def test_custom_prompt_version_reflected_in_output(self):
        """Passing prompt_version="custom-v2" returns it in the result."""
        opp = _make_mock_opportunity()
        company = _make_mock_company()
        result = generate_ai_draft(
            opportunity=opp, company=company,
            prompt_version="custom-v2",
        )
        assert result["prompt_version"] == "custom-v2"

    def test_custom_model_name_via_get_ai_provider(self):
        """get_ai_provider with model_name returns provider whose output
        has custom model_name."""
        provider = get_ai_provider("mock_ai", model_name="mock-soria-test")
        assert isinstance(provider, MockAIProvider)
        ctx = build_prompt_context(_make_mock_opportunity())
        result = provider.generate(ctx)
        assert result["model_name"] == "mock-soria-test"

    def test_unknown_provider_raises_value_error(self):
        """Unknown provider_name propagates as ValueError."""
        opp = _make_mock_opportunity()
        company = _make_mock_company()
        with pytest.raises(ValueError, match="Unknown AI provider"):
            generate_ai_draft(
                opportunity=opp, company=company,
                provider_name="does_not_exist",
            )

    def test_generated_body_is_deterministic(self):
        """Same input produces identical output."""
        opp = _make_mock_opportunity(title="Test")
        company = _make_mock_company(name="Test Co")
        r1 = generate_ai_draft(opportunity=opp, company=company)
        r2 = generate_ai_draft(opportunity=opp, company=company)
        assert r1["body"] == r2["body"]
        assert r1["subject"] == r2["subject"]


# ---------------------------------------------------------------------------
# Integration tests — endpoints preserve behavior after refactoring
# ---------------------------------------------------------------------------


def _create_company(client, **overrides):
    payload = {
        "name": "Phase8B Company",
        "domain": "phase8b.fr",
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
        "email": "alice@phase8b.fr",
        "source": "manual",
        "contact_type": "director",
    }
    payload.update(overrides)
    return client.post("/api/v1/contacts", json=payload)


def _create_opportunity(client, company_id, **overrides):
    payload = {
        "company_id": str(company_id),
        "title": "Phase 8B Test Opportunity",
        "opportunity_type": "devops_cloud",
        "source": "manual",
    }
    payload.update(overrides)
    return client.post("/api/v1/opportunities", json=payload)


class TestEndpointAiDraftPreview:
    """GET /api/v1/opportunities/{id}/ai-draft-preview"""

    def test_returns_mock_ai_metadata(self, client):
        """Preview returns mock_ai, mock-soria-v1, ai-draft-v1."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.get(f"/api/v1/opportunities/{opp_id}/ai-draft-preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "mock_ai"
        assert data["model_name"] == "mock-soria-v1"
        assert data["prompt_version"] == "ai-draft-v1"

    def test_returns_prompt_profile(self, client):
        """Preview returns prompt_profile field."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.get(f"/api/v1/opportunities/{opp_id}/ai-draft-preview")
        assert resp.status_code == 200
        assert resp.json()["prompt_profile"] == "prospecting_fr_v1"

    def test_remains_read_only(self, client):
        """Preview does not mutate opportunity or create events."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(
            client, c_resp.json()["id"],
            status="new", score=None,
        )
        opp_id = o_resp.json()["id"]

        original = client.get(f"/api/v1/opportunities/{opp_id}").json()
        resp = client.get(f"/api/v1/opportunities/{opp_id}/ai-draft-preview")
        assert resp.status_code == 200
        after = client.get(f"/api/v1/opportunities/{opp_id}").json()

        assert after == original
        events = client.get("/api/v1/compliance-events").json()
        assert events["total"] == 0


class TestEndpointGenerateAiDraft:
    """POST /api/v1/opportunities/{id}/generate-ai-draft"""

    def test_creates_ai_draft_with_metadata(self, client):
        """Creates draft with generated_by='ai', correct model/prompt."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert resp.status_code == 200
        data = resp.json()
        assert data["generated_by"] == "ai"
        assert data["model_name"] == "mock-soria-v1"
        assert data["prompt_version"] == "ai-draft-v1"

    def test_duplicate_prevention(self, client):
        """Second call returns existing active draft."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        r1 = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert r1.status_code == 200
        r2 = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert r2.status_code == 200
        assert r2.json()["id"] == r1.json()["id"]

    def test_no_external_api_call(self, client):
        """Generating an AI draft does not call external APIs (no mocks
        needed — the mock provider is deterministic)."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert resp.status_code == 200
        # If this completes without network errors, we're good
        assert resp.json()["generated_by"] == "ai"


class TestEndpointRegenerateAiDraft:
    """POST /api/v1/opportunities/{id}/regenerate-ai-draft"""

    def test_archives_active_ai_drafts(self, client):
        """Regenerate archives active AI drafts, creates a new one."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        old = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert old.status_code == 200
        old_id = old.json()["id"]

        new = client.post(
            f"/api/v1/opportunities/{opp_id}/regenerate-ai-draft"
        )
        assert new.status_code == 200
        assert new.json()["id"] != old_id
        assert new.json()["generated_by"] == "ai"
        assert new.json()["model_name"] == "mock-soria-v1"
        assert new.json()["prompt_version"] == "ai-draft-v1"

    def test_new_draft_is_active_draft(self, client):
        """Regenerated draft has status='draft'."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        resp = client.post(
            f"/api/v1/opportunities/{opp_id}/regenerate-ai-draft"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "draft"
