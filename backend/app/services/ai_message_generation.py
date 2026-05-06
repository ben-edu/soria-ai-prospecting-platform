"""AI message generation for SORIA opportunities.

Uses the prompt builder and provider abstraction to generate drafts.
Currently resolves to the deterministic MockAIProvider — no external
AI API is called.
"""

from typing import Optional

from app.core.config import settings
from app.models.academy_resource import AcademyResource
from app.models.company import Company
from app.models.contact import Contact
from app.models.offer import Offer
from app.models.opportunity import Opportunity
from app.services.ai_prompt_builder import build_prompt_context
from app.services.ai_providers import get_ai_provider


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

    # Resolve provider and delegate generation
    provider = get_ai_provider(
        provider_name, model_name=settings.AI_DRAFT_MODEL_NAME
    )
    result = provider.generate(prompt_context)

    # Enrich result with top-level metadata
    result["prompt_profile"] = prompt_context["prompt_profile"]
    return result
