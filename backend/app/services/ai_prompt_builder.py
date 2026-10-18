"""Prompt building layer for SORIA prospecting AI drafts.

Builds structured prompt/context objects that describe an opportunity and its
context. Personal job/freelance modes remain Behnam-centric; the MVCS-3 B2B
commercial mode is SORIA-first and evidence/hypothesis safe.
"""

from typing import Optional

from app.models.academy_resource import AcademyResource
from app.models.company import Company
from app.models.contact import Contact
from app.models.offer import Offer
from app.models.opportunity import Opportunity
from app.services.external_sources import infer_language_hint
from app.services.mvcs_b2b import is_mvcs_b2b_context

DEFAULT_PROMPT_PROFILE = "prospecting_fr_v1"
DEFAULT_PROMPT_VERSION = "ai-draft-v1"
B2B_PROMPT_PROFILE = "soria_b2b_prospecting_fr_v1"
B2B_PROMPT_VERSION = "mvcs3-b2b-v1"

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
    "en anglais. Un champ language_hint est fourni dans le contexte — "
    "il indique la langue détectée (en, fr, unknown). Respecte cette "
    "indication.\n"
    "2. Le ton doit être professionnel, direct, humain, pas trop long, "
    "pas arrogant, pas générique.\n"
    "3. N'exagère pas le profil de Behnam. Reste factuel.\n"
    "4. Ne mentionne le portfolio ou les projets que si c'est pertinent.\n"
    "5. Tu ne dois jamais envoyer de message sans validation humaine.\n"
    "6. Ne mens pas et n'invente pas d'information que tu ne possèdes pas.\n"
    "7. Tu t'adaptes au besoin détecté et aux ressources disponibles."
)

SORIA_COMMERCIAL_SYSTEM_INSTRUCTIONS = (
    "Tu aides SORIA à préparer un brouillon de prospection B2B ciblé. "
    "Le brouillon sera relu et envoyé manuellement par un humain.\n\n"
    "Règles impératives :\n"
    "1. Distingue strictement les faits publics observés de l'hypothèse commerciale.\n"
    "2. Un recrutement, une migration, une publication technique ou un changement "
    "de plateforme est seulement un signal public : ce n'est jamais la preuve que "
    "l'entreprise veut un prestataire externe.\n"
    "3. Formule le besoin potentiel comme une hypothèse prudente (par exemple : "
    "« cela peut indiquer », « si ce sujet est d'actualité », « une piste possible »).\n"
    "4. N'affirme jamais connaître un problème interne, une panne, une urgence, un "
    "budget ou une intention d'achat sans preuve explicite dans le contexte.\n"
    "5. N'invente aucun client, résultat, avis, équipe, partenariat, certification, "
    "SLA, disponibilité 24/7 ou métrique.\n"
    "6. Présente SORIA comme une offre de services DevOps/plateforme portée par "
    "Behnam Eskandari ; ne suggère pas une équipe importante.\n"
    "7. Utilise uniquement l'offre SORIA correspondante et son URL fournie dans le contexte.\n"
    "8. Garde le message court, personnalisé, professionnel et non insistant.\n"
    "9. N'envoie rien : production d'un brouillon uniquement, avec validation humaine obligatoire.\n"
    "10. Respecte language_hint ; français par défaut si la langue est inconnue."
)

BEHNAM_PROFILE_V1 = (
    "Profil de Behnam :\n"
    "- Admin Systèmes / DevOps basé en France\n"
    "- Compétences : infrastructure, DevOps, cloud, automatisation, IAM, plateformes SOC-ready\n"
    "- Projets / réalisations clés : infrastructure OVH/Proxmox + OPNsense ; "
    "Kubernetes K3S + Traefik ; Jenkins + Harbor ; Wazuh ; Keycloak / IAM / SSO ; "
    "plateforme de prospection IA SORIA\n"
    "- Portfolio / CV : https://cv.behnam.fr\n\n"
    "Instructions par type de message :\n"
    "- Mission freelance : court, direct, orienté mission, preuves pertinentes.\n"
    "- Candidature / email recruteur : court, reprendre les mots-clés de l'offre.\n"
    "- Relance : poli, court, non-insistant.\n"
    "- Prospection générique hors MVCS : professionnel et personnalisé."
)

SORIA_COMMERCIAL_PROFILE_V1 = (
    "Contexte commercial SORIA :\n"
    "- SORIA fournit des interventions DevOps / plateforme ciblées en France.\n"
    "- Le positionnement est orienté problèmes et résultats, pas catalogue de technologies.\n"
    "- Offres publiques : Diagnostic déploiement & infrastructure ; Industrialisation "
    "des déploiements ; Fiabilité de production & exploitation.\n"
    "- Destination publique : https://soria-ai.fr/\n"
    "- Preuve de première partie disponible : réalisation CI/CD documentée sur le site.\n"
    "- L'activité est portée par Behnam Eskandari ; ne pas fabriquer une taille d'équipe.\n"
    "- Aucun prix, SLA ou support 24/7 ne doit être inventé."
)


def infer_draft_type(opportunity: Opportunity) -> str:
    """Infer message type while keeping curated MVCS B2B records commercial."""

    if is_mvcs_b2b_context(opportunity):
        return "prospecting_email"

    title = (opportunity.title or "").lower()
    description = (opportunity.description or "").lower()
    source = (opportunity.source.value if opportunity.source else "").lower()
    opp_type = (
        opportunity.opportunity_type.value if opportunity.opportunity_type else ""
    ).lower()

    if opp_type == "freelance":
        return "freelance_proposal"
    if opp_type == "job":
        return "job_application_email"

    text_all = f"{title} {description} {source}"
    text_no_source = f"{title} {description}"

    platform_signals = [
        "malt",
        "codeur",
        "free-work",
        "freework",
        "le hibou",
        "lehibou",
        "comet",
        "freelancer",
    ]
    for signal in platform_signals:
        if signal in text_all:
            return "freelance_proposal"

    job_keywords = [
        "cdi",
        "cdd",
        "alternance",
        "stage",
        "emploi",
        "poste",
        "recrutement",
        "recruteur",
        "recruiter",
        "salarié",
        "salarie",
    ]
    for keyword in job_keywords:
        if keyword in text_no_source:
            return "job_application_email"

    freelance_phrases = [
        "mission freelance",
        "consultant indépendant",
        "consultant independant",
        "prestation freelance",
    ]
    for phrase in freelance_phrases:
        if phrase in text_no_source:
            return "freelance_proposal"

    for word in ["freelance", "indépendant", "independant", "tjm"]:
        if word in text_no_source:
            return "freelance_proposal"

    for keyword in ["follow-up", "follow up", "relance", "suivi"]:
        if keyword in text_no_source:
            return "follow_up"

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
    """Build the provider-neutral prompt context for a draft."""

    draft_type = infer_draft_type(opportunity)
    b2b_commercial = is_mvcs_b2b_context(opportunity) and draft_type == "prospecting_email"

    language_hint = infer_language_hint(
        title=opportunity.title,
        description=opportunity.description,
        source_country=None,
    )

    user_context = {
        "opportunity": {
            "title": opportunity.title,
            "description": opportunity.description or "",
            "detected_need": opportunity.detected_need or "",
            "recommended_landing_page": opportunity.recommended_landing_page or "",
            "source_type": opportunity.source.value if opportunity.source else "",
            "source_url": opportunity.source_url or "",
            "source_published_at": (
                opportunity.source_published_at.isoformat()
                if opportunity.source_published_at
                else ""
            ),
        },
        "company": {
            "name": company.name if company else "Votre organisation",
            "website_url": company.website_url if company else "",
            "sector": company.sector if company else "",
        },
        "contact": {
            "full_name": contact.full_name if contact else "Responsable",
            "role_title": contact.role_title if contact else "",
        },
        "draft_type": draft_type,
        "language_hint": language_hint,
    }

    if b2b_commercial:
        user_context["evidence_contract"] = {
            "public_signal_summary": opportunity.description or "",
            "public_signal_url": opportunity.source_url or "",
            "pain_hypothesis": opportunity.detected_need or "",
            "pain_hypothesis_status": "unverified_hypothesis",
            "vendor_intent": "not_established",
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
        "prompt_profile": B2B_PROMPT_PROFILE if b2b_commercial else prompt_profile,
        "prompt_version": B2B_PROMPT_VERSION if b2b_commercial else prompt_version,
        "system_instructions": (
            SORIA_COMMERCIAL_SYSTEM_INSTRUCTIONS
            if b2b_commercial
            else SYSTEM_INSTRUCTIONS
        ),
        "safety_note": SAFETY_NOTE,
        "profile_context": (
            SORIA_COMMERCIAL_PROFILE_V1 if b2b_commercial else BEHNAM_PROFILE_V1
        ),
        "draft_type": draft_type,
        "language_hint": language_hint,
        "user_context": user_context,
    }
