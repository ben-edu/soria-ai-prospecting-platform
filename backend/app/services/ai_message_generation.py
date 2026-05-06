"""Deterministic AI message generation for SORIA opportunities.

Provides a mock_ai provider that builds contextual French prospecting
email drafts without calling any external AI API. The generated output
is more structured and detailed than the rule_based draft, but still
deterministic and safe for development/validation workflows.
"""

from typing import Optional

from app.models.academy_resource import AcademyResource
from app.models.company import Company
from app.models.contact import Contact
from app.models.offer import Offer
from app.models.opportunity import Opportunity

PROVIDER_NAME = "mock_ai"
MODEL_NAME = "mock-soria-v1"
PROMPT_VERSION = "ai-draft-v1"

SAFETY_NOTE = (
    "Ce brouillon a été généré par un assistant IA (mock) et doit être "
    "relu, validé et envoyé par un opérateur humain. Aucun message "
    "automatique n'est envoyé sans validation humaine explicite via "
    "le workflow SORIA (validation humaine préalable obligatoire)."
)


def generate_ai_draft(
    opportunity: Opportunity,
    company: Optional[Company] = None,
    contact: Optional[Contact] = None,
    matched_offer: Optional[Offer] = None,
    matched_resource: Optional[AcademyResource] = None,
) -> dict:
    """Generate a deterministic AI draft for the given opportunity context.

    Returns a dict with keys:
        subject, body, provider, model_name, prompt_version, safety_note

    This is a fully deterministic mock — no external AI API is called.
    """
    contact_name = contact.full_name if contact else "Responsable"
    company_name = company.name if company else "Votre organisation"

    # ----- Subject -----
    subject = (
        f"Accompagnement sur mesure — {opportunity.title} — {company_name}"
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
        f"« {opportunity.title} »."
    )

    if opportunity.description:
        parts.append(
            f"Au vu du contexte suivant : {opportunity.description}"
        )

    # Detected need
    if opportunity.detected_need:
        parts.append("")
        parts.append(
            f"**Besoins détectés :** {opportunity.detected_need}"
        )
        parts.append(
            "Notre équipe a analysé ces besoins et propose une réponse "
            "structurée ci-dessous."
        )

    # Matched offer section
    if matched_offer:
        parts.append("")
        parts.append(
            f"**Offre recommandée :** {matched_offer.name}"
        )
        if matched_offer.short_description:
            parts.append(matched_offer.short_description)
        if matched_offer.landing_page_url:
            parts.append(f"Page de l'offre : {matched_offer.landing_page_url}")

    # Matched academy resource section
    if matched_resource:
        parts.append("")
        parts.append(
            f"**Ressource associée :** {matched_resource.title}"
        )
        if matched_resource.short_description:
            parts.append(matched_resource.short_description)
        if matched_resource.public_url:
            parts.append(f"En savoir plus : {matched_resource.public_url}")

    # Recommended landing page
    if opportunity.recommended_landing_page:
        landing_url = opportunity.recommended_landing_page
        landing_label = "Page dédiée"
        if matched_offer and matched_offer.name:
            landing_label = f"Page dédiée à {matched_offer.name}"
        parts.append("")
        parts.append(f"{landing_label} : {landing_url}")

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
        "provider": PROVIDER_NAME,
        "model_name": MODEL_NAME,
        "prompt_version": PROMPT_VERSION,
        "safety_note": SAFETY_NOTE,
    }
