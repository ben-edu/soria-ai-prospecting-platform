"""Prompt building layer for SORIA prospecting AI drafts.

Builds structured prompt/context objects that describe an opportunity
and its context, including system safety instructions and user/entity
data. Designed to be consumed by AI providers.
"""

from typing import Optional

from app.models.academy_resource import AcademyResource
from app.models.company import Company
from app.models.contact import Contact
from app.models.offer import Offer
from app.models.opportunity import Opportunity

# Default profile identifiers
DEFAULT_PROMPT_PROFILE = "prospecting_fr_v1"
DEFAULT_PROMPT_VERSION = "ai-draft-v1"

SAFETY_NOTE = (
    "Ce brouillon a été généré par un assistant IA (mock) et doit être "
    "relu, validé et envoyé par un opérateur humain. Aucun message "
    "automatique n'est envoyé sans validation humaine explicite via "
    "le workflow SORIA (validation humaine préalable obligatoire)."
)

SYSTEM_INSTRUCTIONS = (
    "Tu es un assistant de prospection commerciale pour SORIA Academy, "
    "un organisme de formation français. Tu rédiges des emails de "
    "prospection en français, personnalisés selon le contexte de "
    "l'opportunité, de l'entreprise et du contact ciblé.\n\n"
    "Règles impératives :\n"
    "1. Tous les messages doivent être rédigés en français.\n"
    "2. Le ton doit être professionnel et courtois.\n"
    "3. Tu ne dois jamais envoyer de message sans validation humaine.\n"
    "4. Tu ne dois pas inventer des informations que tu ne possèdes pas.\n"
    "5. Tu t'adaptes au besoin détecté et aux ressources disponibles."
)


def build_prompt_context(
    opportunity: Opportunity,
    company: Optional[Company] = None,
    contact: Optional[Contact] = None,
    matched_offer: Optional[Offer] = None,
    matched_resource: Optional[AcademyResource] = None,
    *,
    prompt_profile: str = DEFAULT_PROMPT_PROFILE,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> dict:
    """Build a structured prompt context for AI draft generation.

    Returns a dict containing metadata, system instructions, entity
    context, and a safety note. Designed to be consumed by an AI
    provider's ``generate()`` method.
    """
    user_context = {
        "opportunity": {
            "title": opportunity.title,
            "description": opportunity.description or "",
            "detected_need": opportunity.detected_need or "",
            "recommended_landing_page": opportunity.recommended_landing_page or "",
        },
        "company": {
            "name": company.name if company else "Votre organisation",
        },
        "contact": {
            "full_name": contact.full_name if contact else "Responsable",
        },
    }

    if matched_offer is not None:
        user_context["matched_offer"] = {
            "name": matched_offer.name,
            "short_description": matched_offer.short_description or "",
            "landing_page_url": matched_offer.landing_page_url or "",
        }

    if matched_resource is not None:
        user_context["matched_resource"] = {
            "title": matched_resource.title,
            "short_description": matched_resource.short_description or "",
            "public_url": matched_resource.public_url or "",
        }

    return {
        "prompt_profile": prompt_profile,
        "prompt_version": prompt_version,
        "system_instructions": SYSTEM_INSTRUCTIONS,
        "safety_note": SAFETY_NOTE,
        "user_context": user_context,
    }
