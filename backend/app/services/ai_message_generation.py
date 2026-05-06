"""AI message generation for SORIA opportunities.

Uses the prompt builder and provider abstraction to generate drafts.
Currently resolves to the deterministic MockAIProvider — no external
AI API is called.
"""

from typing import Any, Optional

from app.core.config import settings
from app.models.academy_resource import AcademyResource
from app.models.company import Company
from app.models.contact import Contact
from app.models.offer import Offer
from app.models.opportunity import Opportunity
from app.services.ai_prompt_builder import build_prompt_context
from app.services.ai_providers import (
    AIProviderGenerationError,
    InvalidAIProviderOutputError,
    UnknownAIProviderError,
    get_ai_provider,
)

# Keys that the AI provider output must include.
_REQUIRED_OUTPUT_KEYS: frozenset[str] = frozenset({
    "subject",
    "body",
    "provider",
    "model_name",
    "prompt_version",
    "safety_note",
})

# Keys that must be non-empty strings.
_NON_EMPTY_KEYS: frozenset[str] = frozenset({
    "subject",
    "body",
    "provider",
    "model_name",
    "prompt_version",
})


def _validate_ai_result(result: dict[str, Any]) -> dict[str, Any]:
    """Validate that the AI provider output contains all required keys
    with appropriate values.

    Parameters
    ----------
    result
        Raw output dict from an AI provider.

    Returns
    -------
    The same *result* dict unchanged (identity) on success.

    Raises
    ------
    InvalidAIProviderOutputError
        If any required key is missing or a non-empty key is empty/not a
        string.
    """
    missing = _REQUIRED_OUTPUT_KEYS - result.keys()
    if missing:
        raise InvalidAIProviderOutputError(
            f"AI provider output is missing required keys: "
            f"{', '.join(sorted(missing))}"
        )

    for key in _NON_EMPTY_KEYS:
        value = result[key]
        if not isinstance(value, str) or not value.strip():
            raise InvalidAIProviderOutputError(
                f"AI provider output key '{key}' must be a non-empty string, "
                f"got {type(value).__name__}: {value!r}"
            )

    return result


def generate_ai_draft(
    opportunity: Opportunity,
    company: Optional[Company] = None,
    contact: Optional[Contact] = None,
    matched_offer: Optional[Offer] = None,
    matched_resource: Optional[AcademyResource] = None,
    *,
    provider_name: Optional[str] = None,
    prompt_profile: Optional[str] = None,
    prompt_version: Optional[str] = None,
) -> dict:
    """Generate a deterministic AI draft for the given opportunity context.

    Builds a structured prompt context via the prompt builder, resolves
    the configured AI provider, and delegates generation.

    Returns a dict with keys:
        subject, body, provider, model_name, prompt_version, safety_note,
        prompt_profile

    Raises
    ------
    UnknownAIProviderError
        If the configured provider is not registered.
    AIProviderGenerationError
        If the provider raises an unexpected runtime error.
    InvalidAIProviderOutputError
        If the provider returns invalid or incomplete output.
    """
    provider_name = provider_name or settings.AI_DRAFT_PROVIDER
    prompt_profile = prompt_profile or settings.AI_DRAFT_PROMPT_PROFILE
    prompt_version = prompt_version or settings.AI_DRAFT_PROMPT_VERSION

    # Build structured prompt context from opportunity entities
    prompt_context = build_prompt_context(
        opportunity=opportunity,
        company=company,
        contact=contact,
        matched_offer=matched_offer,
        matched_resource=matched_resource,
        prompt_profile=prompt_profile,
        prompt_version=prompt_version,
    )

    # Resolve provider — may raise UnknownAIProviderError (propagates)
    provider = get_ai_provider(
        provider_name, model_name=settings.AI_DRAFT_MODEL_NAME
    )

    # Delegate generation — wrap unexpected errors
    try:
        result = provider.generate(prompt_context)
    except UnknownAIProviderError:
        raise
    except InvalidAIProviderOutputError:
        raise
    except Exception as exc:
        raise AIProviderGenerationError(
            f"AI provider '{provider_name}' failed to generate a draft: "
            f"{exc.__class__.__name__}"
        ) from exc

    # Validate output — may raise InvalidAIProviderOutputError (propagates)
    _validate_ai_result(result)

    # Enrich result with top-level metadata
    result["prompt_profile"] = prompt_context["prompt_profile"]
    return result
