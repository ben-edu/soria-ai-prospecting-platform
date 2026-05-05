"""Deterministic rule-based opportunity enrichment service."""

from typing import Optional

from app.core.enums import CompanyType, OpportunityType
from app.models.company import Company
from app.models.opportunity import Opportunity

# Keyword groups per domain
_DEVOPS_KEYWORDS = [
    "devops", "kubernetes", "k8s", "docker", "ci/cd", "ci cd",
    "cloud", "container", "conteneur", "déploiement", "deploiement",
    "infrastructure", "aws", "gcp", "azure", "automatisation",
    "terraform", "ansible", "jenkins", "gitlab ci", "github actions",
    "microservice", "orchestration", "iaas", "paas",
]

_FORMATION_KEYWORDS = [
    "formation", "bts", "sio", "sisr", "apprentissage",
    "pédagogique", "pedagogique", "cours", "training",
    "stage", "alternance", "compétence", "competence",
    "atelier", "workshop", "certification", "module",
    "programme", "référentiel", "referentiel", "competence",
    "bloc", "compétence",
]

_CYBER_KEYWORDS = [
    "cyber", "cybersécurité", "cybersecurite", "sécurité", "securite",
    "soc", "monitoring", "iam", "sso", "firewall",
    "pentest", "ransomware", "vulnérabilité", "vulnerabilite",
    "audit", "conformité", "conformite", "rgpd",
    "siem", "edr", "xdr", "mfa", "2fa",
    "détection", "detection", "incident", "response",
]


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    """Count how many distinct keywords appear in *text*."""
    lower = text.lower()
    return sum(1 for kw in keywords if kw in lower)


def _detect_primary_domain(
    opportunity: Opportunity,
    company_type: Optional[CompanyType],
) -> tuple[str, list[str]]:
    """Determine the primary enrichment domain and which domains matched.

    Returns (domain, matched_domains) where *domain* is one of
    ``formation``, ``cybersecurity``, ``devops``, or ``generic``.
    """
    title_lower = (opportunity.title or "").lower()
    desc_lower = (opportunity.description or "").lower()
    combined = f"{title_lower} {desc_lower}"

    scores: list[tuple[str, int]] = [
        ("formation", _count_keyword_hits(combined, _FORMATION_KEYWORDS)),
        ("cybersecurity", _count_keyword_hits(combined, _CYBER_KEYWORDS)),
        ("devops", _count_keyword_hits(combined, _DEVOPS_KEYWORDS)),
    ]

    # Bonus from opportunity_type
    if opportunity.opportunity_type == OpportunityType.formation:
        scores[0] = (scores[0][0], scores[0][1] + 3)
    elif opportunity.opportunity_type in (
        OpportunityType.cybersecurity_soc,
        OpportunityType.iam_sso,
        OpportunityType.monitoring,
    ):
        scores[1] = (scores[1][0], scores[1][1] + 3)
    elif opportunity.opportunity_type == OpportunityType.devops_cloud:
        scores[2] = (scores[2][0], scores[2][1] + 3)

    # Bonus from company_type
    if company_type in (
        CompanyType.training_center,
        CompanyType.school,
        CompanyType.cfa,
        CompanyType.university,
    ):
        scores[0] = (scores[0][0], scores[0][1] + 2)
    elif company_type in (
        CompanyType.it_company,
        CompanyType.web_agency,
        CompanyType.startup,
        CompanyType.enterprise,
        CompanyType.pme,
    ):
        scores[2] = (scores[2][0], scores[2][1] + 2)

    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)

    matched = [d for d, s in scores if s > 0]
    top_domain = scores[0][0] if scores[0][1] > 0 else "generic"

    return top_domain, matched if matched else ["generic"]


def _generate_detected_need(
    domain: str,
    opportunity: Opportunity,
    company_type: Optional[CompanyType],
) -> str:
    """Produce a human-readable detected_need string."""
    title = opportunity.title or ""

    needs: dict[str, str] = {
        "formation": (
            "Besoin en formation et accompagnement pédagogique — "
            "l'organisation recherche un renforcement des compétences "
            "techniques de ses équipes ou apprenants."
        ),
        "cybersecurity": (
            "Besoin en cybersécurité, supervision et sécurité des accès — "
            "l'organisation doit renforcer sa posture de sécurité, "
            "améliorer la détection d'incidents et sécuriser ses accès."
        ),
        "devops": (
            "Besoin en DevOps, automatisation Cloud et optimisation "
            "d'infrastructure — l'organisation cherche à moderniser "
            "son pipeline de déploiement et son infrastructure."
        ),
    }

    if domain in needs:
        return needs[domain]

    # Generic fallback — derive from title
    return (
        f"Accompagnement spécialisé dans le domaine « {title} » "
        f"— besoin identifié à préciser lors d'un échange."
    )


def _generate_landing_page(domain: str) -> str:
    """Map the primary domain to a recommended landing page path."""
    mapping = {
        "devops": "/services/devops-automation",
        "formation": "/services/formation-it-devops",
        "cybersecurity": "/services/cybersecurity-monitoring",
    }
    # Sub-variant for IAM/SSO
    return mapping.get(domain, "/services/general")


def _generate_cyber_landing_page(opportunity: Opportunity) -> str:
    """Check if IAM/SSO keywords are present for a more specific landing page."""
    title_lower = (opportunity.title or "").lower()
    desc_lower = (opportunity.description or "").lower()
    combined = f"{title_lower} {desc_lower}"
    iam_keywords = ["iam", "sso", "authentification", "annuaire", "ldap", "azure ad", "active directory"]
    if any(kw in combined for kw in iam_keywords):
        return "/services/iam-sso-access-security"
    return "/services/cybersecurity-monitoring"


def _generate_next_action(domain: str, priority: str) -> str:
    """Suggest a next action based on enrichment domain and priority."""
    high_priority = priority in ("high", "urgent")
    prefix = "Contacter rapidement" if high_priority else "Préparer"

    actions = {
        "formation": (
            f"{prefix} une proposition de catalogue de formations "
            f"adapté au besoin détecté."
        ),
        "cybersecurity": (
            f"{prefix} une proposition d'audit de sécurité et "
            f"de conformité."
        ),
        "devops": (
            f"{prefix} une proposition d'audit d'infrastructure "
            f"et d'automatisation."
        ),
    }

    if domain in actions:
        return actions[domain]

    return f"{prefix} un premier contact pour préciser le besoin."


def _generate_explanation(
    domain: str,
    matched_domains: list[str],
    overwrote: bool,
) -> str:
    """Build an explanation string for the enrichment result."""
    domain_labels = {
        "formation": "formation / pédagogique",
        "cybersecurity": "cybersécurité / monitoring / accès",
        "devops": "DevOps / Cloud / automatisation",
        "generic": "générique",
    }

    primary_label = domain_labels.get(domain, domain)
    all_labels = ", ".join(
        domain_labels.get(d, d) for d in matched_domains if d != "generic"
    )

    parts = [
        f"Enrichissement basé sur l'analyse du titre, du type d'opportunité"
        f"{', de la description' if all_labels else ''} et du type d'entreprise."
    ]
    parts.append(
        f"Domaine principal détecté : {primary_label}."
    )
    if all_labels:
        parts.append(f"Domaines supplémentaires : {all_labels}.")
    if overwrote:
        parts.append("Le besoin détecté existant a été mis à jour.")
    else:
        parts.append("Le besoin détecté existant a été conservé.")

    return " ".join(parts)


def enrich_opportunity(
    opportunity: Opportunity,
    company: Optional[Company] = None,
) -> dict:
    """Apply deterministic rule-based enrichment to an *opportunity*.

    Returns a dict with keys:
        detected_need, recommended_landing_page, next_action,
        explanation, applied.
    """
    company_type = company.company_type if company is not None else None
    domain, matched_domains = _detect_primary_domain(opportunity, company_type)

    # Generate new values
    new_detected_need = _generate_detected_need(domain, opportunity, company_type)

    if domain == "cybersecurity":
        new_landing_page = _generate_cyber_landing_page(opportunity)
    else:
        new_landing_page = _generate_landing_page(domain)

    new_next_action = _generate_next_action(domain, opportunity.priority.value)

    # Decide whether to apply detected_need
    # Only overwrite existing detected_need if it's empty/null
    overwrote = False
    final_detected_need: Optional[str] = None

    if opportunity.detected_need:
        final_detected_need = opportunity.detected_need
    else:
        final_detected_need = new_detected_need
        overwrote = True

    explanation = _generate_explanation(domain, matched_domains, overwrote)

    return {
        "detected_need": final_detected_need,
        "recommended_landing_page": new_landing_page,
        "next_action": new_next_action,
        "explanation": explanation,
        "applied": True,
        "detected_need_overwritten": overwrote,
    }
