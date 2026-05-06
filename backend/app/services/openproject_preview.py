"""Build a read-only OpenProject work package preview from an Opportunity."""

from typing import Optional

from app.models.academy_resource import AcademyResource
from app.models.company import Company
from app.models.contact import Contact
from app.models.offer import Offer
from app.models.opportunity import Opportunity


def _map_status(opportunity: Opportunity) -> str:
    """Map SORIA OpportunityStatus to an OpenProject-style status label."""
    mapping = {
        "new": "To analyse",
        "to_analyze": "To analyse",
        "scored": "To analyse",
        "interesting": "To analyse",
        "draft_needed": "To analyse",
        "draft_ready": "To analyse",
        "waiting_validation": "Draft prepared",
        "approved": "Draft prepared",
        "sent": "Contacted",
        "follow_up_needed": "Contacted",
        "response_received": "Follow-up",
        "meeting_scheduled": "Meeting",
        "converted": "Won",
        "lost": "Lost",
        "closed": "Lost",
        "not_relevant": "Lost",
    }
    return mapping.get(opportunity.status.value, "To analyse")


def _map_priority(opportunity: Opportunity) -> str:
    """Map SORIA OpportunityPriority to an OpenProject-style priority label."""
    mapping = {
        "urgent": "High",
        "high": "High",
        "medium": "Normal",
        "low": "Low",
    }
    return mapping.get(opportunity.priority.value, "Normal")


def _build_description(
    opportunity: Opportunity,
    company: Optional[Company],
    contact: Optional[Contact],
    offer: Optional[Offer],
    academy_resource: Optional[AcademyResource],
) -> str:
    """Build a clean Markdown description in French."""

    parts: list[str] = []
    parts.append("# Opportunité SORIA")
    parts.append("")
    parts.append("## Résumé")
    parts.append("")
    parts.append(f"- **ID interne :** {opportunity.id}")
    parts.append(f"- **Titre :** {opportunity.title}")
    parts.append(f"- **Type :** {opportunity.opportunity_type.value}")
    parts.append(f"- **Statut :** {opportunity.status.value}")
    parts.append(f"- **Priorité :** {opportunity.priority.value}")
    if opportunity.score is not None:
        parts.append(f"- **Score :** {opportunity.score}/100")
    if opportunity.detected_need:
        parts.append("")
        parts.append("**Besoins détectés :**")
        parts.append("")
        parts.append(opportunity.detected_need)
    parts.append("")

    # Entreprise
    parts.append("## Entreprise")
    parts.append("")
    if company:
        parts.append(f"- **Nom :** {company.name}")
        if company.company_type:
            parts.append(f"- **Type :** {company.company_type.value}")
        if company.website_url:
            parts.append(f"- **Site web :** {company.website_url}")
        if company.city:
            location_parts = [company.city]
            if company.country:
                location_parts.append(company.country)
            parts.append(f"- **Localisation :** {', '.join(location_parts)}")
    else:
        parts.append("*Non renseignée*")
    parts.append("")

    # Contact
    parts.append("## Contact")
    parts.append("")
    if contact:
        parts.append(f"- **Nom :** {contact.full_name}")
        if contact.role_title:
            parts.append(f"- **Fonction :** {contact.role_title}")
        if contact.email:
            parts.append(f"- **Email :** {contact.email}")
    else:
        parts.append("*Aucun contact associé*")
    parts.append("")

    # Qualification
    parts.append("## Qualification")
    parts.append("")
    parts.append(f"- **Need détecté :** {opportunity.detected_need or 'Non renseigné'}")
    parts.append(f"- **Page d'atterrissage recommandée :** {opportunity.recommended_landing_page or 'Non renseignée'}")
    parts.append(f"- **Prochaine action :** {opportunity.next_action or 'Non renseignée'}")
    parts.append("")

    # Offre / Ressource associée
    parts.append("## Offre / Ressource associée")
    parts.append("")
    if offer:
        parts.append(f"- **Offre :** {offer.name}")
        if offer.landing_page_url:
            parts.append(f"- **Page de l'offre :** {offer.landing_page_url}")
    else:
        parts.append("*Aucune offre associée*")
    parts.append("")
    if academy_resource:
        parts.append(f"- **Ressource Académie :** {academy_resource.title}")
        if academy_resource.public_url:
            parts.append(f"- **URL publique :** {academy_resource.public_url}")
        if academy_resource.academy_url:
            parts.append(f"- **URL Académie :** {academy_resource.academy_url}")
    else:
        parts.append("*Aucune ressource Académie associée*")
    parts.append("")

    # Suivi recommandé
    parts.append("## Suivi recommandé")
    parts.append("")
    parts.append(opportunity.next_action or "Aucune action recommandée pour le moment.")
    parts.append("")

    # Conformité
    parts.append("## Conformité")
    parts.append("")
    parts.append("Aucun message externe ne doit être envoyé sans validation humaine.")
    parts.append("")

    # Liens / références
    parts.append("## Liens / références")
    parts.append("")
    parts.append(f"- **Source :** {opportunity.source.value}")
    if opportunity.source_url:
        parts.append(f"- **URL source :** {opportunity.source_url}")
    if opportunity.openproject_work_package_id:
        parts.append(
            f"- **Work package OpenProject existant :** "
            f"{opportunity.openproject_work_package_id}"
        )
    parts.append("")

    return "\n".join(parts)


def build_openproject_work_package_preview(
    opportunity: Opportunity,
    company: Optional[Company] = None,
    contact: Optional[Contact] = None,
    offer: Optional[Offer] = None,
    academy_resource: Optional[AcademyResource] = None,
) -> dict:
    """Build a read-only OpenProject work package preview dict.

    Returns a dictionary with keys:
        suggested_type, suggested_status, suggested_priority,
        subject, description
    """
    company_name = company.name if company else "Unknown company"

    subject = f"[SORIA] {opportunity.title} — {company_name}"

    description = _build_description(
        opportunity, company, contact, offer, academy_resource
    )

    return {
        "suggested_type": "Opportunity",
        "suggested_status": _map_status(opportunity),
        "suggested_priority": _map_priority(opportunity),
        "subject": subject,
        "description": description,
    }
