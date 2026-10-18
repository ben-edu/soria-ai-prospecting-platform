"""MVCS-3 B2B pilot qualification and commercial-routing rules.

This module is deliberately deterministic and evidence-first. It does not
perform discovery, scrape external sites, or send messages.
"""

from datetime import datetime, timezone
from typing import Optional

from app.core.enums import CompanyType, OpportunityType, SourceType
from app.models.company import Company
from app.models.contact import Contact
from app.models.offer import Offer
from app.models.opportunity import Opportunity

B2B_SCORING_VERSION = "mvcs3-b2b-v1"
B2B_QUALIFICATION_THRESHOLD = 70

DIAGNOSTIC_SLUG = "diagnostic-deploiement-infrastructure"
INDUSTRIALISATION_SLUG = "industrialisation-deploiements"
RELIABILITY_SLUG = "fiabilite-production-exploitation"

B2B_OFFER_SLUGS = {
    DIAGNOSTIC_SLUG,
    INDUSTRIALISATION_SLUG,
    RELIABILITY_SLUG,
}

_B2B_SOURCES = {
    SourceType.manual,
    SourceType.company_website,
    SourceType.linkedin_manual,
}

_INDUSTRIALISATION_SIGNALS = (
    "ci/cd",
    "cicd",
    "pipeline",
    "deployment",
    "déploiement",
    "deploiement",
    "release",
    "gitops",
    "argocd",
    "jenkins",
    "github actions",
    "gitlab ci",
    "automation",
    "automatisation",
    "reproductible",
    "reproducible",
)

_RELIABILITY_SIGNALS = (
    "sre",
    "reliability",
    "fiabilité",
    "fiabilite",
    "incident",
    "production",
    "on-call",
    "astreinte",
    "observability",
    "observabilité",
    "observabilite",
    "monitoring",
    "recovery",
    "reprise",
    "backup",
    "sauvegarde",
    "availability",
    "disponibilité",
    "disponibilite",
)

_TECHNICAL_SIGNAL_KEYWORDS = (
    "devops",
    "platform",
    "plateforme",
    "sre",
    "cloud",
    "kubernetes",
    "docker",
    "infrastructure",
    "ci/cd",
    "cicd",
    "deployment",
    "déploiement",
    "deploiement",
    "production",
    "reliability",
    "fiabilité",
    "fiabilite",
    "observability",
    "observabilité",
    "monitoring",
    "terraform",
    "ansible",
)

_PRIMARY_SECTOR_KEYWORDS = (
    "software",
    "saas",
    "logiciel",
    "éditeur",
    "editeur",
    "digital",
    "numérique",
    "numerique",
    "technology",
    "technologie",
    "tech",
    "online product",
    "plateforme",
    "platform",
)


def is_mvcs_b2b_context(opportunity: Opportunity) -> bool:
    """Return whether the record belongs to the controlled MVCS B2B pilot.

    Job/freelance records keep their historical workflow. A B2B record must be
    explicitly typed as DevOps/Cloud and come from a curated/manual public-web
    source used by the pilot.
    """

    return (
        opportunity.opportunity_type == OpportunityType.devops_cloud
        and opportunity.source in _B2B_SOURCES
    )


def _opportunity_text(opportunity: Opportunity) -> str:
    return " ".join(
        part
        for part in (
            opportunity.title,
            opportunity.description,
            opportunity.detected_need,
        )
        if part
    ).lower()


def select_mvcs_offer_slug(opportunity: Opportunity) -> str:
    """Select the safest productised SORIA offer for a curated B2B signal."""

    text = _opportunity_text(opportunity)
    reliability_hits = sum(1 for keyword in _RELIABILITY_SIGNALS if keyword in text)
    industrialisation_hits = sum(
        1 for keyword in _INDUSTRIALISATION_SIGNALS if keyword in text
    )

    if reliability_hits > industrialisation_hits and reliability_hits > 0:
        return RELIABILITY_SLUG
    if industrialisation_hits > 0:
        return INDUSTRIALISATION_SLUG
    return DIAGNOSTIC_SLUG


def _freshness_points(published_at: Optional[datetime]) -> tuple[int, str]:
    if published_at is None:
        return 0, "Signal freshness is unknown."

    value = published_at
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    age_days = max(0, (datetime.now(timezone.utc) - value).days)
    if age_days <= 90:
        return 7, f"Public signal is fresh ({age_days} days old)."
    if age_days <= 180:
        return 5, f"Public signal is moderately fresh ({age_days} days old)."
    if age_days <= 365:
        return 2, f"Public signal is older ({age_days} days old)."
    return 0, f"Public signal is stale ({age_days} days old)."


def qualify_mvcs_b2b(
    opportunity: Opportunity,
    company: Company,
    contact: Optional[Contact],
    matched_offer: Offer,
) -> dict:
    """Compute the frozen evidence-backed MVCS-3 B2B score.

    The function only evaluates stored facts and an explicitly labelled pain
    hypothesis. It does not infer vendor intent from a public signal.
    """

    breakdown: dict[str, int] = {
        "icp_fit": 0,
        "public_signal": 0,
        "offer_hypothesis_fit": 0,
        "contactability": 0,
        "evidence_quality": 0,
    }
    reasons: dict[str, list[str]] = {key: [] for key in breakdown}

    # ICP fit: 0-35
    if company.company_type in {CompanyType.startup, CompanyType.it_company}:
        breakdown["icp_fit"] += 15
        reasons["icp_fit"].append("Company type fits the primary software/tech ICP.")
    elif company.company_type in {CompanyType.pme, CompanyType.enterprise}:
        breakdown["icp_fit"] += 5
        reasons["icp_fit"].append("Company type is only a selective MVCS segment fit.")

    sector = (company.sector or "").lower()
    if any(keyword in sector for keyword in _PRIMARY_SECTOR_KEYWORDS):
        breakdown["icp_fit"] += 10
        reasons["icp_fit"].append("Sector text supports software/SaaS/online-product fit.")

    if (company.country or "").strip().lower() == "france":
        breakdown["icp_fit"] += 5
        reasons["icp_fit"].append("Company is France-based for the first pilot.")

    if company.website_url or company.domain:
        breakdown["icp_fit"] += 5
        reasons["icp_fit"].append("A public company/product web presence is recorded.")

    breakdown["icp_fit"] = min(35, breakdown["icp_fit"])

    # Public-signal relevance/freshness: 0-30
    if opportunity.source_url:
        breakdown["public_signal"] += 8
        reasons["public_signal"].append("An attributable public evidence URL is stored.")

    description = (opportunity.description or "").strip()
    if len(description) >= 40:
        breakdown["public_signal"] += 7
        reasons["public_signal"].append("A substantive factual signal summary is stored.")
    elif description:
        breakdown["public_signal"] += 4
        reasons["public_signal"].append("A short public-signal summary is stored.")

    signal_text = f"{opportunity.title or ''} {description}".lower()
    if any(keyword in signal_text for keyword in _TECHNICAL_SIGNAL_KEYWORDS):
        breakdown["public_signal"] += 8
        reasons["public_signal"].append(
            "The observed signal is relevant to deployment/platform/reliability work."
        )

    freshness_score, freshness_reason = _freshness_points(
        opportunity.source_published_at
    )
    breakdown["public_signal"] += freshness_score
    reasons["public_signal"].append(freshness_reason)
    breakdown["public_signal"] = min(30, breakdown["public_signal"])

    # Offer / pain-hypothesis fit: 0-20
    hypothesis = (opportunity.detected_need or "").strip()
    if "hypoth" in hypothesis.lower():
        breakdown["offer_hypothesis_fit"] += 10
        reasons["offer_hypothesis_fit"].append(
            "The potential pain is explicitly recorded as a hypothesis."
        )
    elif hypothesis:
        reasons["offer_hypothesis_fit"].append(
            "A detected need exists but is not explicitly labelled as a hypothesis."
        )

    if matched_offer.slug in B2B_OFFER_SLUGS:
        breakdown["offer_hypothesis_fit"] += 10
        reasons["offer_hypothesis_fit"].append(
            f"Signal is routed to the productised offer '{matched_offer.name}'."
        )

    # Contactability: 0-10
    if contact is not None and not contact.opt_out:
        breakdown["contactability"] += 3
        reasons["contactability"].append("A non-opted-out contact is attached.")
        if contact.role_title or contact.contact_type.value != "unknown":
            breakdown["contactability"] += 2
            reasons["contactability"].append("Decision-maker role context is recorded.")
        if contact.email:
            breakdown["contactability"] += 3
            reasons["contactability"].append("An email channel is available.")
        if contact.linkedin_url:
            breakdown["contactability"] += 2
            reasons["contactability"].append("A manual LinkedIn channel is available.")
    elif contact is not None and contact.opt_out:
        reasons["contactability"].append("Contact has opted out; outbound is not allowed.")
    else:
        reasons["contactability"].append("No decision-maker contact is attached yet.")

    breakdown["contactability"] = min(10, breakdown["contactability"])

    # Evidence quality: 0-5
    if opportunity.source_url:
        if opportunity.source == SourceType.company_website:
            breakdown["evidence_quality"] = 5
            reasons["evidence_quality"].append("Evidence comes from the company website.")
        elif opportunity.source == SourceType.linkedin_manual:
            breakdown["evidence_quality"] = 4
            reasons["evidence_quality"].append(
                "Evidence was manually curated from a public LinkedIn source."
            )
        elif opportunity.source == SourceType.manual:
            breakdown["evidence_quality"] = 3
            reasons["evidence_quality"].append(
                "Evidence was manually curated and retains its public URL."
            )
    else:
        reasons["evidence_quality"].append("No attributable public evidence URL is stored.")

    total = sum(breakdown.values())
    qualified = total >= B2B_QUALIFICATION_THRESHOLD

    return {
        "score": total,
        "breakdown": breakdown,
        "reasons": reasons,
        "qualified": qualified,
        "threshold": B2B_QUALIFICATION_THRESHOLD,
        "scoring_version": B2B_SCORING_VERSION,
    }
