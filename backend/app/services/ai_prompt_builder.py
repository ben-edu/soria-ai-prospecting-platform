"""Prompt building layer for SORIA prospecting AI drafts.

Builds structured prompt/context objects that describe an opportunity
and its context, including system safety instructions and user/entity
data. Designed to be consumed by AI providers.

Phase 14B: enriched with Behnam profile context and draft type inference.
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
    "Ce brouillon a été généré par un assistant IA et doit être "
    "relu, validé et envoyé par un opérateur humain. Aucun message "
    "automatique n'est envoyé sans validation humaine explicite via "
    "le workflow SORIA (validation humaine préalable obligatoire)."
)

SYSTEM_INSTRUCTIONS = (
    "Tu aides Behnam, un professionnel DevOps / Admin Systèmes basé "
    "en France, à rédiger des messages de prospection personnalisés.\n\n"
    "Règles impératives :\n"
    "1. Rédige en français sauf si l'offre ou le contexte est clairement "
    "en anglais.\n"
    "2. Le ton doit être professionnel, direct, humain, pas trop long, "
    "pas arrogant, pas générique.\n"
    "3. N'exagère pas le profil de Behnam. Reste factuel.\n"
    "4. Ne mentionne le portfolio ou les projets que si c'est pertinent "
    "par rapport à l'opportunité.\n"
    "5. Tu ne dois jamais envoyer de message sans validation humaine.\n"
    "6. Ne mens pas et n'invente pas d'information que tu ne possèdes pas.\n"
    "7. Tu t'adaptes au besoin détecté et aux ressources disponibles."
)

BEHNAM_PROFILE_V1 = (
    "Profil de Behnam :\n"
    "- Admin Systèmes / DevOps basé en France\n"
    "- Compétences : infrastructure, DevOps, cloud, automatisation, "
    "IAM, plateformes SOC-ready\n"
    "- Projets / réalisations clés :\n"
    "  1. Infrastructure OVH/Proxmox avec firewall OPNsense en edge "
    "(routage, DMZ, segmentation réseau)\n"
    "  2. Plateforme Kubernetes K3S avec Traefik ingress et déploiements "
    "automatisés\n"
    "  3. Pipeline CI/CD Jenkins + Harbor (registry privé)\n"
    "  4. Surveillance / sécurité Wazuh – plateforme SOC-ready\n"
    "  5. Authentification et sécurité d'accès Keycloak / IAM / SSO\n"
    "  6. Plateforme de prospection IA SORIA (ce projet)\n"
    "- Portfolio / CV : https://cv.behnam.fr\n\n"
    "Instructions par type de message :\n"
    "- Mission freelance : message court, direct, orienté mission, "
    "avec 2-3 preuves pertinentes et une proposition de collaboration.\n"
    "- Candidature / email recruteur : court, reprendre les mots-clés "
    "de l'offre, style lettre de motivation.\n"
    "- Relance : poli, court, non-insistant.\n"
    "- Prospection / email commercial : professionnel, personnalisé "
    "selon le contexte de l'opportunité."
)


def infer_draft_type(
    opportunity: Opportunity,
) -> str:
    """Infer the draft type from opportunity context.

    Priority order:
    1. Explicit ``opportunity_type`` (freelance → freelance, job → job)
    2. Platform/source strong freelance signals (Malt, Codeur, Free-Work, ...)
    3. Job strong signals (CDI, CDD, alternance, stage, ...)
    4. Strong freelance textual signals (freelance, indépendant, TJM, ...)
    5. Follow-up signals
    6. Default → ``prospecting_email``

    Generic words that appear in both freelance and salaried offers
    (mission, client, project, prestation) are deliberately excluded
    from freelance classification to avoid false positives.

    Returns one of: freelance_proposal, job_application_email,
    lettre_de_motivation, recruiter_message, follow_up,
    prospecting_email.
    """
    title = (opportunity.title or "").lower()
    description = (opportunity.description or "").lower()
    source = (opportunity.source.value if opportunity.source else "").lower()
    opp_type = (
        opportunity.opportunity_type.value if opportunity.opportunity_type else ""
    ).lower()

    # 1. Explicit opportunity_type
    if opp_type == "freelance":
        return "freelance_proposal"
    if opp_type == "job":
        return "job_application_email"

    text_all = f"{title} {description} {source}"
    text_no_source = f"{title} {description}"

    # 2. Platform/source strong freelance signals
    platform_signals = [
        "malt", "codeur", "free-work", "freework",
        "le hibou", "lehibou", "comet", "freelancer",
    ]
    for signal in platform_signals:
        if signal in text_all:
            return "freelance_proposal"

    # 3. Job strong signals
    job_keywords = [
        "cdi", "cdd", "alternance", "stage", "emploi",
        "poste", "recrutement", "recruteur", "recruiter",
        "salarié", "salarie",
    ]
    for kw in job_keywords:
        if kw in text_no_source:
            return "job_application_email"

    # 4. Strong freelance textual signals
    #    (multi-word phrases checked first to avoid splitting)
    freelance_phrases = [
        "mission freelance",
        "consultant indépendant",
        "consultant independant",
        "prestation freelance",
    ]
    for phrase in freelance_phrases:
        if phrase in text_no_source:
            return "freelance_proposal"

    freelance_words = ["freelance", "indépendant", "independant", "tjm"]
    for word in freelance_words:
        if word in text_no_source:
            return "freelance_proposal"

    # 5. Follow-up signals
    followup_keywords = [
        "follow-up", "follow up", "relance", "suivi",
    ]
    for kw in followup_keywords:
        if kw in text_no_source:
            return "follow_up"

    # 6. Default
    return "prospecting_email"


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
    context, Behnam profile context, draft type, and a safety note.
    Designed to be consumed by an AI provider's ``generate()`` method.
    """
    draft_type = infer_draft_type(opportunity)

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
        "draft_type": draft_type,
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
        "profile_context": BEHNAM_PROFILE_V1,
        "draft_type": draft_type,
        "user_context": user_context,
    }
