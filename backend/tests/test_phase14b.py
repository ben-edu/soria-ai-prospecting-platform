"""Phase 14B — Real AI Draft Engine (DeepSeek) tests.

Covers:
- DeepSeekProvider (mock httpx): success, missing key, non-2xx,
  timeout, malformed JSON, missing fields
- Draft type inference (freelance, job, follow-up, default)
- Prompt builder enrichment (profile context, updated instructions)
- Provider registry (deepseek registered, resolvable)
"""

import json
from unittest.mock import MagicMock

import httpx
import pytest

from app.core.config import settings
from app.services.ai_prompt_builder import (
    BEHNAM_PROFILE_V1,
    build_prompt_context,
    infer_draft_type,
)
from app.services.ai_providers import (
    PROVIDER_REGISTRY,
    AIProviderGenerationError,
    DeepSeekProvider,
    InvalidAIProviderOutputError,
    get_ai_provider,
    list_available_ai_providers,
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
    obj.source = kw.get("source")
    obj.opportunity_type = kw.get("opportunity_type")
    return obj


def _make_mock_company(**kw):
    obj = MagicMock()
    obj.name = kw.get("name", "ACME Corp")
    return obj


def _make_mock_contact(**kw):
    obj = MagicMock()
    obj.full_name = kw.get("full_name", "Jean Dupont")
    return obj


# ---------------------------------------------------------------------------
# Provider registry tests
# ---------------------------------------------------------------------------


class TestDeepSeekProviderRegistry:
    """DeepSeek provider is registered and resolvable."""

    def test_deepseek_is_in_registry(self):
        """PROVIDER_REGISTRY has 'deepseek' mapped to DeepSeekProvider."""
        assert "deepseek" in PROVIDER_REGISTRY
        assert PROVIDER_REGISTRY["deepseek"] is DeepSeekProvider

    def test_list_available_includes_deepseek(self):
        """list_available_ai_providers() includes 'deepseek'."""
        providers = list_available_ai_providers()
        assert "deepseek" in providers

    def test_resolves_deepseek_provider(self):
        """get_ai_provider('deepseek') returns a DeepSeekProvider instance."""
        provider = get_ai_provider("deepseek")
        assert isinstance(provider, DeepSeekProvider)

    def test_deepseek_provider_metadata(self):
        """DeepSeekProvider has correct provider name and default model."""
        provider = DeepSeekProvider()
        assert provider.provider == "deepseek"
        assert provider._model == "deepseek-v4-flash"

    def test_deepseek_custom_model_name(self):
        """Constructor accepts custom model name."""
        provider = DeepSeekProvider(model_name="custom-model")
        assert provider._model == "custom-model"


# ---------------------------------------------------------------------------
# DeepSeek provider —— httpx mocking
# ---------------------------------------------------------------------------


def _build_prompt_context(**kw):
    """Build a minimal prompt context for provider tests."""
    opp = _make_mock_opportunity(**kw)
    company = _make_mock_company()
    return build_prompt_context(opp, company=company)


def _mock_httpx_response(status_code=200, content_json=None):
    """Build a mock httpx Response."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    if content_json is not None:
        mock_resp.json.return_value = content_json
    mock_resp.text = json.dumps(content_json) if content_json else ""
    return mock_resp


def _mock_httpx_client(mock_response, monkeypatch):
    """Patch httpx.Client to return *mock_response* from .post()."""

    class FakeResponse:
        def __init__(self, resp):
            self._resp = resp

        def __enter__(self):
            return self._resp

        def __exit__(self, *args):
            pass

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            return mock_response

    monkeypatch.setattr("httpx.Client", FakeClient)


_VALID_MODEL_JSON = {
    "subject": "Proposition DevOps – ACME Corp",
    "body": "Bonjour Jean Dupont,\n\nJe vous propose mes services...\n\nCordialement,\nBehnam",
    "draft_type": "prospecting_email",
    "language": "fr",
    "confidence": 0.85,
    "reasoning_summary": "Opportunité DevOps correspond au profil",
    "recommended_next_action": "Planifier un appel de découverte",
    "portfolio_points_used": ["Infrastructure OVH/Proxmox", "K3S Kubernetes"],
    "safety_notes": ["Vérifier que le contact est bien le décideur"],
}


class TestDeepSeekProviderGenerate:
    """DeepSeekProvider.generate() with mocked HTTP."""

    def _setup_provider(self, monkeypatch):
        monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "test-key-123")
        return DeepSeekProvider()

    def _make_api_response(self, model_json=None):
        if model_json is None:
            model_json = _VALID_MODEL_JSON
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(model_json, ensure_ascii=False),
                    }
                }
            ]
        }

    def test_successful_generation(self, monkeypatch):
        """Valid API response returns structured result with all keys."""
        provider = self._setup_provider(monkeypatch)
        api_resp = self._make_api_response()

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context(title="Formation DevOps")
        result = provider.generate(ctx)

        assert result["subject"] == _VALID_MODEL_JSON["subject"]
        assert result["body"] == _VALID_MODEL_JSON["body"]
        assert result["provider"] == "deepseek"
        assert result["model_name"] == "deepseek-v4-flash"
        assert result["prompt_version"] == "ai-draft-v1"
        assert "safety_note" in result
        assert result["draft_type"] == "prospecting_email"
        assert result["language"] == "fr"
        assert result["confidence"] == 0.85
        assert result["reasoning_summary"] is not None
        assert result["recommended_next_action"] is not None
        assert result["portfolio_points_used"] == _VALID_MODEL_JSON["portfolio_points_used"]
        assert result["safety_notes"] == _VALID_MODEL_JSON["safety_notes"]

    def test_missing_api_key(self, monkeypatch):
        """Missing DEEPSEEK_API_KEY raises AIProviderGenerationError."""
        monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", None)
        provider = DeepSeekProvider()
        ctx = _build_prompt_context()

        with pytest.raises(AIProviderGenerationError, match="API key is not configured"):
            provider.generate(ctx)

    def test_empty_api_key(self, monkeypatch):
        """Empty DEEPSEEK_API_KEY raises AIProviderGenerationError."""
        monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "")
        provider = DeepSeekProvider()
        ctx = _build_prompt_context()

        with pytest.raises(AIProviderGenerationError, match="API key is not configured"):
            provider.generate(ctx)

    def test_non_2xx_response(self, monkeypatch):
        """Non-200 status code raises AIProviderGenerationError."""
        provider = self._setup_provider(monkeypatch)

        mock_resp = _mock_httpx_response(status_code=401, content_json={"error": "unauthorized"})
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        with pytest.raises(AIProviderGenerationError, match="HTTP 401"):
            provider.generate(ctx)

    def test_timeout(self, monkeypatch):
        """Request timeout raises AIProviderGenerationError."""

        class TimeoutClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, **kwargs):
                raise httpx.TimeoutException("Connection timed out", request=None)

        monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "test-key-123")
        monkeypatch.setattr("httpx.Client", TimeoutClient)

        provider = DeepSeekProvider()
        ctx = _build_prompt_context()

        with pytest.raises(AIProviderGenerationError, match="timed out"):
            provider.generate(ctx)

    def test_network_error(self, monkeypatch):
        """Network error raises AIProviderGenerationError."""

        class BrokenClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, **kwargs):
                raise httpx.RequestError("Connection refused", request=None)

        monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "test-key-123")
        monkeypatch.setattr("httpx.Client", BrokenClient)

        provider = DeepSeekProvider()
        ctx = _build_prompt_context()

        with pytest.raises(AIProviderGenerationError, match="RequestError"):
            provider.generate(ctx)

    def test_malformed_json_response(self, monkeypatch):
        """Non-JSON response from API raises InvalidAIProviderOutputError."""
        provider = self._setup_provider(monkeypatch)

        # Mock a response where response.json() raises json.JSONDecodeError
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.side_effect = json.JSONDecodeError("bad json", "", 0)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        with pytest.raises(InvalidAIProviderOutputError, match="non-JSON response"):
            provider.generate(ctx)

    def test_empty_choices(self, monkeypatch):
        """Response with empty choices list raises InvalidAIProviderOutputError."""
        provider = self._setup_provider(monkeypatch)
        api_resp = {"choices": []}

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        with pytest.raises(InvalidAIProviderOutputError, match="no choices"):
            provider.generate(ctx)

    def test_empty_message_content(self, monkeypatch):
        """Response with empty message content raises InvalidAIProviderOutputError."""
        provider = self._setup_provider(monkeypatch)
        api_resp = {"choices": [{"message": {"content": ""}}]}

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        with pytest.raises(InvalidAIProviderOutputError, match="content is empty"):
            provider.generate(ctx)

    def test_model_output_not_json(self, monkeypatch):
        """Model returns non-JSON string content."""
        provider = self._setup_provider(monkeypatch)
        api_resp = {"choices": [{"message": {"content": "not json at all"}}]}

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        with pytest.raises(InvalidAIProviderOutputError, match="not valid JSON"):
            provider.generate(ctx)

    def test_model_output_missing_subject(self, monkeypatch):
        """JSON without 'subject' raises InvalidAIProviderOutputError."""
        provider = self._setup_provider(monkeypatch)
        model_json = {"body": "Hello", "draft_type": "prospecting_email"}
        api_resp = {"choices": [{"message": {"content": json.dumps(model_json)}}]}

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        with pytest.raises(InvalidAIProviderOutputError, match="subject"):
            provider.generate(ctx)

    def test_model_output_missing_body(self, monkeypatch):
        """JSON without 'body' raises InvalidAIProviderOutputError."""
        provider = self._setup_provider(monkeypatch)
        model_json = {"subject": "Test", "draft_type": "prospecting_email"}
        api_resp = {"choices": [{"message": {"content": json.dumps(model_json)}}]}

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        with pytest.raises(InvalidAIProviderOutputError, match="body"):
            provider.generate(ctx)

    def test_empty_subject_in_model_output(self, monkeypatch):
        """Empty subject string raises InvalidAIProviderOutputError."""
        provider = self._setup_provider(monkeypatch)
        model_json = {"subject": "", "body": "Hello"}
        api_resp = {"choices": [{"message": {"content": json.dumps(model_json)}}]}

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        with pytest.raises(InvalidAIProviderOutputError, match="subject"):
            provider.generate(ctx)

    def test_empty_body_in_model_output(self, monkeypatch):
        """Empty body string raises InvalidAIProviderOutputError."""
        provider = self._setup_provider(monkeypatch)
        model_json = {"subject": "Test", "body": ""}
        api_resp = {"choices": [{"message": {"content": json.dumps(model_json)}}]}

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        with pytest.raises(InvalidAIProviderOutputError, match="body"):
            provider.generate(ctx)

    def test_model_output_with_markdown_fences(self, monkeypatch):
        """Model output wrapped in ```json fences is parsed correctly."""
        provider = self._setup_provider(monkeypatch)
        model_json = {"subject": "Test", "body": "Hello world"}
        raw = f"```json\n{json.dumps(model_json)}\n```"
        api_resp = {"choices": [{"message": {"content": raw}}]}

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        result = provider.generate(ctx)
        assert result["subject"] == "Test"
        assert result["body"] == "Hello world"

    def test_custom_model_used(self, monkeypatch):
        """Custom model name from constructor is used in metadata."""
        monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "test-key-123")
        provider = DeepSeekProvider(model_name="deepseek-custom-v1")
        api_resp = self._make_api_response()

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        result = provider.generate(ctx)
        assert result["model_name"] == "deepseek-custom-v1"

    def test_safety_notes_merged(self, monkeypatch):
        """Model safety_notes are appended to system safety_note."""
        provider = self._setup_provider(monkeypatch)
        model_json = {
            "subject": "Test",
            "body": "Hello",
            "safety_notes": ["Vérifier le contact"],
        }
        api_resp = {"choices": [{"message": {"content": json.dumps(model_json)}}]}

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        result = provider.generate(ctx)
        assert "Vérifier le contact" in result["safety_note"]

    def test_non_dict_model_output(self, monkeypatch):
        """Model returns a JSON array instead of object."""
        provider = self._setup_provider(monkeypatch)
        api_resp = {
            "choices": [{"message": {"content": '["not", "a", "dict"]'}}]
        }

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        with pytest.raises(InvalidAIProviderOutputError, match="not a JSON object"):
            provider.generate(ctx)

    def test_non_string_subject(self, monkeypatch):
        """Non-string subject raises InvalidAIProviderOutputError."""
        provider = self._setup_provider(monkeypatch)
        model_json = {"subject": 123, "body": "Hello"}
        api_resp = {"choices": [{"message": {"content": json.dumps(model_json)}}]}

        mock_resp = _mock_httpx_response(status_code=200, content_json=api_resp)
        _mock_httpx_client(mock_resp, monkeypatch)

        ctx = _build_prompt_context()
        with pytest.raises(InvalidAIProviderOutputError, match="subject"):
            provider.generate(ctx)


# ---------------------------------------------------------------------------
# Draft type inference tests
# ---------------------------------------------------------------------------


class _FakeSource:
    """Minimal source-like object with .value."""

    def __init__(self, value):
        self.value = value


class _FakeOpportunityType:
    """Minimal opportunity_type-like object with .value."""

    def __init__(self, value):
        self.value = value


def _opp_with(title="", description="", source=None, opp_type=None):
    """Build a mock opportunity for draft type inference."""
    return _make_mock_opportunity(
        title=title,
        description=description,
        source=_FakeSource(source) if source else None,
        opportunity_type=_FakeOpportunityType(opp_type) if opp_type else None,
    )


class TestInferDraftType:
    """infer_draft_type() classification logic."""

    def test_freelance_from_title(self):
        """Title containing 'freelance' returns freelance_proposal."""
        opp = _opp_with(title="Mission freelance DevOps")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_from_description(self):
        """Description containing 'mission freelance' returns freelance_proposal."""
        opp = _opp_with(description="Mission freelance en régie pour client")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_from_source(self):
        """Source 'Malt' returns freelance_proposal."""
        opp = _opp_with(source="Malt")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_codeur(self):
        """Source 'Codeur' returns freelance_proposal."""
        opp = _opp_with(source="Codeur")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_freework(self):
        """Title containing 'Free-Work' returns freelance_proposal."""
        opp = _opp_with(title="Free-Work mission")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_comet(self):
        """Title containing 'Comet' returns freelance_proposal."""
        opp = _opp_with(title="Comet mission DevOps")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_freelancer_source(self):
        """Source 'freelancer' returns freelance_proposal."""
        opp = _opp_with(source="freelancer")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_le_hibou(self):
        """Source 'LeHibou' returns freelance_proposal."""
        opp = _opp_with(source="LeHibou")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_independant(self):
        """Title containing 'indépendant' returns freelance_proposal."""
        opp = _opp_with(title="Consultant indépendant DevOps")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_independant_no_accent(self):
        """Title containing 'independant' (no accent) returns freelance_proposal."""
        opp = _opp_with(title="Consultant independant DevOps")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_tjm(self):
        """Title containing 'TJM' returns freelance_proposal."""
        opp = _opp_with(title="TJM 500€ mission")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_consultant_independant(self):
        """Phrase 'consultant indépendant' returns freelance_proposal."""
        opp = _opp_with(title="Consultant indépendant système")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_prestation_freelance(self):
        """Phrase 'prestation freelance' returns freelance_proposal."""
        opp = _opp_with(description="Recherche prestation freelance en DevOps")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_freelance_freework_no_dash(self):
        """Title containing 'freework' (no dash) returns freelance_proposal."""
        opp = _opp_with(title="Freework mission DevOps")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_job_from_title(self):
        """Title containing 'CDI' returns job_application_email."""
        opp = _opp_with(title="CDI DevOps Engineer")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_from_description(self):
        """Description containing 'recrutement' returns job_application_email."""
        opp = _opp_with(description="Recrutement en cours")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_recruiter(self):
        """Title containing 'recruiter' returns job_application_email."""
        opp = _opp_with(title="Recruiter - poste DevOps CDI")
        assert infer_draft_type(opp) == "job_application_email"

    def test_follow_up(self):
        """Title containing 'follow-up' returns follow_up."""
        opp = _opp_with(title="Follow-up après entretien")
        assert infer_draft_type(opp) == "follow_up"

    def test_follow_up_relance(self):
        """Title containing 'relance' returns follow_up."""
        opp = _opp_with(title="Relance SORIA")
        assert infer_draft_type(opp) == "follow_up"

    def test_default_prospecting(self):
        """Generic title without keywords returns prospecting_email."""
        opp = _opp_with(title="Formation Kubernetes")
        assert infer_draft_type(opp) == "prospecting_email"

    def test_default_prospecting_other(self):
        """Empty title returns prospecting_email."""
        opp = _opp_with(title="")
        assert infer_draft_type(opp) == "prospecting_email"

    def test_opportunity_type_freelance(self):
        """opportunity_type 'freelance' returns freelance_proposal."""
        opp = _opp_with(opp_type="freelance")
        assert infer_draft_type(opp) == "freelance_proposal"

    def test_opportunity_type_job(self):
        """opportunity_type 'job' returns job_application_email."""
        opp = _opp_with(opp_type="job")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_cdd(self):
        """Title containing 'CDD' returns job_application_email."""
        opp = _opp_with(title="CDD Administrateur Systèmes")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_poste(self):
        """Title containing 'poste' returns job_application_email."""
        opp = _opp_with(title="Poste en cybersécurité")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_cdi_with_mission(self):
        """CDI title with 'vos missions' still returns job_application_email."""
        opp = _opp_with(title="CDI DevOps - vos missions")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_cdd_with_mission(self):
        """CDD description with 'missions' still returns job_application_email."""
        opp = _opp_with(title="CDD Administrateur", description="Missions variées")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_alternance(self):
        """Title containing 'alternance' returns job_application_email."""
        opp = _opp_with(title="Alternance DevOps")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_stage(self):
        """Title containing 'stage' returns job_application_email."""
        opp = _opp_with(title="Stage DevOps")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_salarie(self):
        """Title containing 'salarié' returns job_application_email."""
        opp = _opp_with(title="Salarié DevOps confirmé")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_salarie_no_accent(self):
        """Title containing 'salarie' (no accent) returns job_application_email."""
        opp = _opp_with(title="Salarie Administrateur Systèmes")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_emploi(self):
        """Title containing 'emploi' returns job_application_email."""
        opp = _opp_with(title="Emploi DevOps")
        assert infer_draft_type(opp) == "job_application_email"

    def test_job_recruteur(self):
        """Title containing 'recruteur' returns job_application_email."""
        opp = _opp_with(title="Recruteur - CDI DevOps")
        assert infer_draft_type(opp) == "job_application_email"

    # --- Generic words alone must NOT trigger freelance ---

    def test_vos_missions_alone_not_freelance(self):
        """'Vos missions' alone does NOT return freelance_proposal."""
        opp = _opp_with(title="DevOps", description="Vos missions")
        assert infer_draft_type(opp) != "freelance_proposal"

    def test_projets_clients_alone_not_freelance(self):
        """'Projets clients' alone does NOT return freelance_proposal."""
        opp = _opp_with(title="DevOps", description="Projets clients ambitieux")
        assert infer_draft_type(opp) != "freelance_proposal"

    def test_client_projects_not_freelance(self):
        """'Client project' alone does NOT return freelance_proposal."""
        opp = _opp_with(title="DevOps", description="Client project delivery")
        assert infer_draft_type(opp) != "freelance_proposal"

    def test_prestation_alone_not_freelance(self):
        """'Prestation' alone does NOT return freelance_proposal."""
        opp = _opp_with(title="Prestation de services")
        assert infer_draft_type(opp) != "freelance_proposal"

    def test_consulting_alone_not_freelance(self):
        """'Consulting' alone does NOT return freelance_proposal."""
        opp = _opp_with(title="Consulting en infrastructure")
        assert infer_draft_type(opp) != "freelance_proposal"

    def test_mission_alone_not_freelance(self):
        """'Mission' alone in description does NOT return freelance_proposal."""
        opp = _opp_with(title="DevOps Engineer", description="Les missions")
        assert infer_draft_type(opp) != "freelance_proposal"


# ---------------------------------------------------------------------------
# Prompt builder enrichment tests
# ---------------------------------------------------------------------------


class TestPromptBuilderPhase14B:
    """build_prompt_context() enrichment from Phase 14B."""

    def test_profile_context_present(self):
        """Prompt context includes profile_context with Behnam profile."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp)
        assert "profile_context" in ctx
        assert ctx["profile_context"] == BEHNAM_PROFILE_V1
        assert "Behnam" in ctx["profile_context"]

    def test_draft_type_in_user_context(self):
        """User context includes inferred draft_type."""
        opp = _make_mock_opportunity(title="Mission freelance")
        ctx = build_prompt_context(opp)
        assert ctx["user_context"]["draft_type"] == "freelance_proposal"

    def test_draft_type_in_top_level_context(self):
        """Top-level context includes draft_type."""
        opp = _make_mock_opportunity(title="Formation générale")
        ctx = build_prompt_context(opp)
        assert ctx["draft_type"] == "prospecting_email"

    def test_system_instructions_mention_behnam(self):
        """Updated system instructions reference Behnam."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp)
        assert "Behnam" in ctx["system_instructions"]
        assert "DevOps" in ctx["system_instructions"]

    def test_system_instructions_not_generic(self):
        """System instructions are no longer SORIA Academy generic."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp)
        instructions = ctx["system_instructions"]
        assert "SORIA Academy" not in instructions
        assert "organisme de formation" not in instructions

    def test_existing_keys_preserved(self):
        """All existing prompt context keys are still present."""
        opp = _make_mock_opportunity()
        company = _make_mock_company()
        contact = _make_mock_contact()
        ctx = build_prompt_context(opp, company=company, contact=contact)

        assert "prompt_profile" in ctx
        assert "prompt_version" in ctx
        assert "system_instructions" in ctx
        assert "safety_note" in ctx
        assert "user_context" in ctx
        assert ctx["user_context"]["company"]["name"] == "ACME Corp"
        assert ctx["user_context"]["contact"]["full_name"] == "Jean Dupont"

    def test_profile_context_is_new_key(self):
        """profile_context is separate from system_instructions."""
        opp = _make_mock_opportunity()
        ctx = build_prompt_context(opp)
        assert ctx["system_instructions"] != ctx["profile_context"]
        assert "CV" in ctx["profile_context"]
        assert "cv.behnam.fr" in ctx["profile_context"]

    def test_draft_type_prospecting_default(self):
        """Default draft_type is prospecting_email."""
        opp = _make_mock_opportunity(title="Kubernetes avancé")
        ctx = build_prompt_context(opp)
        assert ctx["draft_type"] == "prospecting_email"
