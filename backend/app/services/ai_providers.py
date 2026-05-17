"""AI provider abstraction layer for SORIA prospecting.

Defines a provider registry, a deterministic MockAIProvider, a
DeepSeek provider (OpenAI-compatible), and a resolver function.
"""

import json
from typing import Any, Optional

import httpx

from app.core.config import settings

# -------------------------------------------------------------------
# Exception hierarchy
# -------------------------------------------------------------------


class AIProviderError(Exception):
    """Base exception for all AI provider errors."""


class UnknownAIProviderError(AIProviderError, ValueError):
    """Raised when the requested provider is not in the registry."""


class AIProviderGenerationError(AIProviderError):
    """Raised when the provider encounters an unexpected runtime error."""


class InvalidAIProviderOutputError(AIProviderError):
    """Raised when the provider returns invalid or incomplete output."""


# -------------------------------------------------------------------
# Registry
# -------------------------------------------------------------------

PROVIDER_REGISTRY: dict[str, type] = {}


def register_provider(name: str):
    """Decorator to register an AI provider implementation."""
    def wrapper(cls):
        PROVIDER_REGISTRY[name] = cls
        return cls
    return wrapper


def get_ai_provider(provider_name: str, model_name: Optional[str] = None):
    """Resolve an AI provider by name, optionally specifying a model.

    Parameters
    ----------
    provider_name
        Registered provider name.
    model_name
        Optional model override passed to the provider constructor.

    Returns
    -------
    An instance of the registered provider class.

    Raises
    ------
    UnknownAIProviderError
        If *provider_name* is not in the registry.
    """
    if provider_name not in PROVIDER_REGISTRY:
        available = ", ".join(sorted(PROVIDER_REGISTRY))
        raise UnknownAIProviderError(
            f"Unknown AI provider: '{provider_name}'. "
            f"Available providers: [{available}]"
        )
    provider_cls = PROVIDER_REGISTRY[provider_name]
    if model_name is not None:
        return provider_cls(model_name=model_name)
    return provider_cls()


def list_available_ai_providers() -> list[str]:
    """Return sorted list of registered AI provider names."""
    return sorted(PROVIDER_REGISTRY)


def get_provider_registry_snapshot() -> dict:
    """Return a diagnostic-friendly snapshot of the provider registry.

    Returns a dict mapping provider name to class qualified name.
    """
    return {
        name: f"{cls.__module__}.{cls.__qualname__}"
        for name, cls in sorted(PROVIDER_REGISTRY.items())
    }


# -------------------------------------------------------------------
# Mock provider
# -------------------------------------------------------------------


@register_provider("mock_ai")
class MockAIProvider:
    """Deterministic mock AI provider for SORIA prospecting drafts.

    Generates structured French prospecting email content from the
    given prompt context without calling any external AI API.
    The output is fully deterministic — the same context always
    produces the same draft.
    """

    provider = "mock_ai"
    model_name = "mock-soria-v1"
    prompt_version = "ai-draft-v1"

    def __init__(self, model_name: Optional[str] = None):
        if model_name is not None:
            self.model_name = model_name

    def generate(self, prompt_context: dict) -> dict:
        """Generate a deterministic draft from *prompt_context*.

        Returns a dict with keys: ``subject``, ``body``, ``provider``,
        ``model_name``, ``prompt_version``, ``safety_note``.
        """
        ctx = prompt_context["user_context"]
        contact_name = ctx["contact"]["full_name"]
        company_name = ctx["company"]["name"]
        opp_title = ctx["opportunity"]["title"]
        opp_description = ctx["opportunity"]["description"]
        detected_need = ctx["opportunity"]["detected_need"]
        landing_page = ctx["opportunity"]["recommended_landing_page"]

        matched_offer = ctx.get("matched_offer")
        matched_resource = ctx.get("matched_resource")

        # ----- Subject -----
        subject = (
            f"Accompagnement sur mesure — {opp_title} — {company_name}"
        )

        # ----- Body -----
        parts: list[str] = []

        # Salutation
        parts.append(f"Bonjour {contact_name},")
        parts.append("")

        # Introduction — contextual
        parts.append(
            f"Nous avons récemment identifié que {company_name} pourrait "
            f"bénéficier d'un accompagnement dans le domaine "
            f"« {opp_title} »."
        )

        if opp_description:
            parts.append(
                f"Au vu du contexte suivant : {opp_description}"
            )

        # Detected need
        if detected_need:
            parts.append("")
            parts.append(f"**Besoins détectés :** {detected_need}")
            parts.append(
                "Notre équipe a analysé ces besoins et propose une réponse "
                "structurée ci-dessous."
            )

        # Matched offer section
        if matched_offer:
            parts.append("")
            parts.append(
                f"**Offre recommandée :** {matched_offer['name']}"
            )
            if matched_offer.get("short_description"):
                parts.append(matched_offer["short_description"])
            if matched_offer.get("landing_page_url"):
                parts.append(
                    f"Page de l'offre : {matched_offer['landing_page_url']}"
                )

        # Matched academy resource section
        if matched_resource:
            parts.append("")
            parts.append(
                f"**Ressource associée :** {matched_resource['title']}"
            )
            if matched_resource.get("short_description"):
                parts.append(matched_resource["short_description"])
            if matched_resource.get("public_url"):
                parts.append(
                    f"En savoir plus : {matched_resource['public_url']}"
                )

        # Recommended landing page
        if landing_page:
            landing_label = "Page dédiée"
            if matched_offer and matched_offer.get("name"):
                landing_label = f"Page dédiée à {matched_offer['name']}"
            parts.append("")
            parts.append(f"{landing_label} : {landing_page}")

        # Closing
        parts.append("")
        parts.append(
            "Je me tiens à votre disposition pour échanger sur ces pistes "
            "et adapter notre proposition à vos besoins spécifiques."
        )
        parts.append("")
        parts.append("Cordialement,")
        parts.append("L'équipe SORIA")

        body = "\n".join(parts)

        return {
            "subject": subject,
            "body": body,
            "provider": self.provider,
            "model_name": self.model_name,
            "prompt_version": prompt_context.get(
                "prompt_version", self.prompt_version
            ),
            "safety_note": prompt_context.get("safety_note", ""),
        }


# -------------------------------------------------------------------
# DeepSeek provider (OpenAI-compatible)
# -------------------------------------------------------------------


@register_provider("deepseek")
class DeepSeekProvider:
    """Real AI provider calling DeepSeek chat/completions API.

    Uses the OpenAI-compatible ``/chat/completions`` endpoint via
    httpx.  Expects the model to return strict JSON with ``subject``
    and ``body`` fields at minimum.

    Environment variables
    ---------------------
    DEEPSEEK_API_KEY : str
        API key (required — generation raises ``AIProviderGenerationError``
        when missing).
    DEEPSEEK_MODEL : str
        Model name override (default: ``deepseek-v4-flash``).
    DEEPSEEK_BASE_URL : str
        Base URL for the API (default: ``https://api.deepseek.com``).
    """

    provider = "deepseek"
    _default_model = "deepseek-v4-flash"

    def __init__(self, model_name: Optional[str] = None):
        if model_name is not None:
            self._model = model_name
        else:
            self._model = settings.DEEPSEEK_MODEL or self._default_model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, prompt_context: dict) -> dict:
        """Generate a draft via the DeepSeek API.

        Parameters
        ----------
        prompt_context
            Structured context dict from ``build_prompt_context()``.

        Returns
        -------
        dict with keys: subject, body, provider, model_name,
        prompt_version, safety_note, plus extra metadata from the
        structured JSON output (draft_type, language, confidence,
        reasoning_summary, recommended_next_action,
        portfolio_points_used, safety_notes).

        Raises
        ------
        AIProviderGenerationError
            On missing API key, network error, non-2xx response,
            or timeout.
        InvalidAIProviderOutputError
            If the model output cannot be parsed as JSON or is
            missing required fields.
        """
        if not settings.DEEPSEEK_API_KEY:
            raise AIProviderGenerationError(
                "DeepSeek API key is not configured. "
                "Set DEEPSEEK_API_KEY environment variable."
            )

        messages = self._build_messages(prompt_context)
        payload = self._build_payload(messages)

        response_data = self._call_api(payload)
        parsed = self._parse_response(response_data)

        return self._build_result(parsed, prompt_context)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_messages(self, prompt_context: dict) -> list[dict]:
        """Build system + user messages from *prompt_context*."""
        system_instructions = prompt_context.get("system_instructions", "")
        profile_context = prompt_context.get("profile_context", "")
        user_context = prompt_context.get("user_context", {})
        draft_type = prompt_context.get("draft_type", "prospecting_email")
        language_hint = prompt_context.get("language_hint", "unknown")

        format_instructions = (
            "Tu dois répondre UNIQUEMENT avec un objet JSON valide "
            "(sans balise markdown, sans bloc de code). "
            "L'objet JSON doit contenir les champs suivants :\n"
            '{\n'
            '  "subject": "Sujet du message",\n'
            '  "body": "Corps du message en texte brut, paragraphes '
            'séparés par \\n\\n",\n'
            '  "draft_type": "freelance_proposal | '
            'job_application_email | lettre_de_motivation | '
            'recruiter_message | follow_up | prospecting_email",\n'
            '  "language": "fr | en",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "reasoning_summary": "Résumé interne très court — '
            'pas du chain-of-thought",\n'
            '  "recommended_next_action": "...",\n'
            '  "portfolio_points_used": ["..."],\n'
            '  "safety_notes": ["..."]\n'
            '}\n\n'
            f"Type de message demandé : {draft_type}\n"
            f"Langue détectée (language_hint) : {language_hint}"
        )

        system_content = (
            f"{system_instructions}\n\n{profile_context}\n\n{format_instructions}"
        )

        import json as _json

        user_content = (
            "Voici le contexte de l'opportunité :\n"
            f"{_json.dumps(user_context, indent=2, ensure_ascii=False)}"
        )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def _build_payload(self, messages: list[dict]) -> dict:
        """Build the request payload for the chat/completions endpoint."""
        return {
            "model": self._model,
            "messages": messages,
            "temperature": settings.AI_DRAFT_TEMPERATURE,
            "max_tokens": settings.AI_DRAFT_MAX_TOKENS,
        }

    def _call_api(self, payload: dict) -> dict:
        """POST to the DeepSeek chat/completions endpoint.

        Raises
        ------
        AIProviderGenerationError
            On network error, non-2xx status, or timeout.
        """
        url = f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException:
            raise AIProviderGenerationError(
                "DeepSeek API request timed out after 60s."
            )
        except httpx.RequestError as exc:
            raise AIProviderGenerationError(
                f"DeepSeek API request failed: {exc.__class__.__name__}"
            )

        if response.status_code != 200:
            raise AIProviderGenerationError(
                f"DeepSeek API returned HTTP {response.status_code}. "
                f"Response: {response.text[:500]}"
            )

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise InvalidAIProviderOutputError(
                f"DeepSeek API returned non-JSON response: {exc}"
            )

    def _parse_response(self, response_data: dict) -> dict:
        """Extract and parse the assistant message content as JSON.

        Raises
        ------
        InvalidAIProviderOutputError
            If the response structure is unexpected, content is missing,
            or content cannot be parsed as valid JSON with the required
            ``subject`` and ``body`` fields.
        """
        try:
            choices = response_data.get("choices", [])
            if not choices:
                raise InvalidAIProviderOutputError(
                    "DeepSeek response contains no choices."
                )
            message = choices[0].get("message", {})
            content: str = message.get("content", "")
            if not content:
                raise InvalidAIProviderOutputError(
                    "DeepSeek response message content is empty."
                )
        except (IndexError, KeyError, TypeError) as exc:
            raise InvalidAIProviderOutputError(
                f"Unexpected DeepSeek response structure: {exc}"
            )

        # Strip markdown code fences if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (possibly with language identifier)
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline + 1 :]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise InvalidAIProviderOutputError(
                f"DeepSeek model output is not valid JSON: {exc}. "
                f"Raw output (first 300 chars): {cleaned[:300]}"
            )

        if not isinstance(parsed, dict):
            raise InvalidAIProviderOutputError(
                f"DeepSeek model output is not a JSON object, "
                f"got {type(parsed).__name__}."
            )

        # Validate required fields
        missing = {"subject", "body"} - parsed.keys()
        if missing:
            raise InvalidAIProviderOutputError(
                f"DeepSeek model output missing required keys: "
                f"{', '.join(sorted(missing))}."
            )

        if not isinstance(parsed.get("subject"), str) or not parsed["subject"].strip():
            raise InvalidAIProviderOutputError(
                "DeepSeek model output 'subject' must be a non-empty string."
            )

        if not isinstance(parsed.get("body"), str) or not parsed["body"].strip():
            raise InvalidAIProviderOutputError(
                "DeepSeek model output 'body' must be a non-empty string."
            )

        return parsed

    def _build_result(self, parsed: dict, prompt_context: dict) -> dict:
        """Build the standard result dict from parsed model output.

        Maps the structured JSON fields onto the keys expected by
        ``ai_message_generation`` and the rest of the system.
        """
        # Merge system safety note with model-level safety notes
        system_safety = prompt_context.get("safety_note", "")
        model_safety_notes: list = parsed.get("safety_notes") or []
        if model_safety_notes:
            safety_note = system_safety + "\n" + "\n".join(model_safety_notes)
        else:
            safety_note = system_safety

        result: dict[str, Any] = {
            "subject": parsed["subject"],
            "body": parsed["body"],
            "provider": self.provider,
            "model_name": self._model,
            "prompt_version": prompt_context.get(
                "prompt_version", "ai-draft-v1"
            ),
            "safety_note": safety_note,
        }

        # Pass through optional structured metadata (not required by
        # validation but useful for downstream consumers)
        for key in (
            "draft_type",
            "language",
            "confidence",
            "reasoning_summary",
            "recommended_next_action",
            "portfolio_points_used",
            "safety_notes",
        ):
            if key in parsed:
                result[key] = parsed[key]

        return result
