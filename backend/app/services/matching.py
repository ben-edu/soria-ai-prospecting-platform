"""Deterministic rule-based opportunity-to-asset matching service."""

from typing import Optional

from app.core.enums import CompanyType, OpportunityType
from app.models.academy_resource import AcademyResource
from app.models.company import Company
from app.models.offer import Offer
from app.models.opportunity import Opportunity


def _normalize_text(value: Optional[str]) -> str:
    """Return lowercase stripped text or empty string."""
    return (value or "").lower().strip()


def _text_score(text: str, keywords: list[str]) -> int:
    """Count how many distinct keywords appear in text."""
    return sum(1 for kw in keywords if kw in text)


def _get_keywords_from_json(keywords_json: Optional[dict]) -> list[str]:
    """Extract keyword strings from the model's JSON field."""
    if not keywords_json:
        return []
    # Could be a dict with a "list" key, or direct list-like structure
    # The field type is Optional[dict] — support multiple shapes
    if isinstance(keywords_json, dict):
        # Try common structures
        if "keywords" in keywords_json and isinstance(keywords_json["keywords"], list):
            return [str(k).lower() for k in keywords_json["keywords"]]
        if "list" in keywords_json and isinstance(keywords_json["list"], list):
            return [str(k).lower() for k in keywords_json["list"]]
        if "tags" in keywords_json and isinstance(keywords_json["tags"], list):
            return [str(k).lower() for k in keywords_json["tags"]]
        # Fallback: use all string values
        result = []
        for v in keywords_json.values():
            if isinstance(v, str):
                result.append(v.lower())
            elif isinstance(v, list):
                result.extend(str(x).lower() for x in v)
        return result
    return []


def _get_technologies_from_json(tech_json: Optional[dict]) -> list[str]:
    """Extract technology strings from the model's JSON field."""
    if not tech_json:
        return []
    if isinstance(tech_json, dict):
        if "technologies" in tech_json and isinstance(tech_json["technologies"], list):
            return [str(t).lower() for t in tech_json["technologies"]]
        if "list" in tech_json and isinstance(tech_json["list"], list):
            return [str(t).lower() for t in tech_json["list"]]
        if "tags" in tech_json and isinstance(tech_json["tags"], list):
            return [str(t).lower() for t in tech_json["tags"]]
        result = []
        for v in tech_json.values():
            if isinstance(v, str):
                result.append(v.lower())
            elif isinstance(v, list):
                result.extend(str(x).lower() for x in v)
        return result
    return []


def _keyword_list_from_str(comma_separated: Optional[str]) -> list[str]:
    """Turn a comma-separated string into a list of lowercased keywords."""
    if not comma_separated:
        return []
    return [k.strip().lower() for k in comma_separated.split(",") if k.strip()]


def _score_offer_for_opportunity(
    offer: Offer,
    opportunity: Opportunity,
    company_type: Optional[CompanyType],
) -> int:
    """Score how well an offer matches an opportunity (higher = better)."""
    score = 0

    title = _normalize_text(opportunity.title)
    desc = _normalize_text(opportunity.description)
    need = _normalize_text(opportunity.detected_need)
    combined = f"{title} {desc} {need}"

    # Extract keywords from the offer
    offer_keywords = _get_keywords_from_json(offer.keywords)
    offer_name = _normalize_text(offer.name)
    offer_short = _normalize_text(offer.short_description)
    offer_full = _normalize_text(offer.full_description)
    offer_text = f"{offer_name} {offer_short} {offer_full}"

    # Score from keywords
    keyword_hits = _text_score(combined, offer_keywords)
    score += keyword_hits * 3

    # Score from opportunity type
    opp_type = opportunity.opportunity_type

    # Match opportunity type to category based on offer name/category
    formation_indicators = ["formation", "bts", "sio", "sisr", "atelier", "training", "cours"]
    devops_indicators = ["devops", "kubernetes", "docker", "ci/cd", "déploiement", "deploiement", "automation"]
    cyber_indicators = ["cyber", "soc", "wazuh", "monitoring", "security", "sécurité", "securite"]
    iam_indicators = ["iam", "sso", "keycloak", "access", "accès", "acces"]
    cloud_indicators = ["cloud", "infrastructure", "proxmox", "opnsense", "réseaux", "reseaux", "vpn"]

    # Boost based on opportunity_type + indicator match
    if opp_type == OpportunityType.formation:
        if any(ind in offer_text for ind in formation_indicators):
            score += 10
    elif opp_type == OpportunityType.devops_cloud:
        if any(ind in offer_text for ind in devops_indicators):
            score += 10
        if any(ind in offer_text for ind in cloud_indicators):
            score += 5
    elif opp_type in (OpportunityType.cybersecurity_soc, OpportunityType.monitoring):
        if any(ind in offer_text for ind in cyber_indicators):
            score += 10
    elif opp_type == OpportunityType.iam_sso:
        if any(ind in offer_text for ind in iam_indicators):
            score += 10

    # Company type boost
    if company_type in (
        CompanyType.training_center,
        CompanyType.school,
        CompanyType.cfa,
        CompanyType.university,
    ):
        if any(ind in offer_text for ind in formation_indicators):
            score += 5
    elif company_type in (
        CompanyType.it_company,
        CompanyType.web_agency,
        CompanyType.startup,
        CompanyType.enterprise,
        CompanyType.pme,
    ):
        if any(ind in offer_text for ind in devops_indicators + cyber_indicators + cloud_indicators):
            score += 5

    # Title keyword matching against offer name
    title_words = set(title.split())
    offer_name_words = set(offer_name.split())
    common = title_words & offer_name_words
    score += len(common) * 2

    return score


def _score_academy_resource_for_opportunity(
    resource: AcademyResource,
    opportunity: Opportunity,
    company_type: Optional[CompanyType],
) -> int:
    """Score how well an academy resource matches an opportunity."""
    score = 0

    title = _normalize_text(opportunity.title)
    desc = _normalize_text(opportunity.description)
    need = _normalize_text(opportunity.detected_need)
    combined = f"{title} {desc} {need}"

    # Extract technologies from the resource
    tech_keywords = _get_technologies_from_json(resource.technologies)
    resource_title = _normalize_text(resource.title)
    resource_short = _normalize_text(resource.short_description)
    resource_text = f"{resource_title} {resource_short}"

    # Score from technologies
    tech_hits = _text_score(combined, tech_keywords)
    score += tech_hits * 3

    # Score from resource title/description
    title_hits = _text_score(combined, resource_title.split())
    score += title_hits * 2

    # Category-based matching
    resource_category = _normalize_text(
        resource.category.name if resource.category else ""
    )
    category_text = f"{resource_text} {resource_category}"

    formation_indicators = ["formation", "pédagogique", "pedagogique", "training", "cours", "bts", "sio"]
    devops_indicators = ["devops", "kubernetes", "docker", "ci/cd", "automatisation", "automatisation"]
    cyber_indicators = ["soc", "siem", "cyber", "threat", "monitoring", "observabilité", "observabilite"]
    iam_indicators = ["iam", "sso", "sécurisation", "securisation", "acces", "accès"]
    cloud_indicators = ["infrastructure", "réseaux", "reseaux", "linux", "administration"]
    infra_as_code = ["infrastructure as code", "iac", "terraform", "ansible"]

    opp_type = opportunity.opportunity_type

    if opp_type == OpportunityType.formation:
        if any(ind in category_text for ind in formation_indicators):
            score += 10
    elif opp_type == OpportunityType.devops_cloud:
        if any(ind in category_text for ind in devops_indicators + cloud_indicators + infra_as_code):
            score += 10
    elif opp_type in (OpportunityType.cybersecurity_soc, OpportunityType.monitoring):
        if any(ind in category_text for ind in cyber_indicators):
            score += 10
    elif opp_type == OpportunityType.iam_sso:
        if any(ind in category_text for ind in iam_indicators):
            score += 10

    # Company type boost
    if company_type in (
        CompanyType.training_center,
        CompanyType.school,
        CompanyType.cfa,
        CompanyType.university,
    ):
        if any(ind in category_text for ind in formation_indicators):
            score += 5

    # Title word overlap
    title_words = set(title.split())
    res_title_words = set(resource_title.split())
    common = title_words & res_title_words
    score += len(common) * 2

    return score


def match_assets(
    opportunity: Opportunity,
    company: Optional[Company] = None,
    offers: Optional[list[Offer]] = None,
    academy_resources: Optional[list[AcademyResource]] = None,
) -> dict:
    """Match an opportunity to the best Offer and AcademyResource.

    Args:
        opportunity: The opportunity to match.
        company: The related company (optional, for company_type context).
        offers: Pre-loaded active offers. If None, caller should load them.
        academy_resources: Pre-loaded active academy resources. If None, caller should load them.

    Returns:
        dict with keys:
            offer: OfferRead-compatible dict or None
            academy_resource: AcademyResourceRead-compatible dict or None
            explanation: human-readable string
            offer_score: int
            academy_resource_score: int
    """
    company_type = company.company_type if company is not None else None

    # Filter to active offers/resources
    active_offers = [o for o in (offers or []) if o.is_active]
    active_resources = [r for r in (academy_resources or []) if r.is_published]

    # Score each offer
    best_offer = None
    best_offer_score = -1
    for offer in active_offers:
        s = _score_offer_for_opportunity(offer, opportunity, company_type)
        if s > best_offer_score:
            best_offer_score = s
            best_offer = offer

    # Score each academy resource
    best_resource = None
    best_resource_score = -1
    for resource in active_resources:
        s = _score_academy_resource_for_opportunity(resource, opportunity, company_type)
        if s > best_resource_score:
            best_resource_score = s
            best_resource = resource

    # Build explanation
    parts = []
    if best_offer:
        parts.append(
            f"Offre correspondante : « {best_offer.name} » "
            f"(score {best_offer_score})"
        )
    else:
        parts.append("Aucune offre active correspondante trouvée")

    if best_resource:
        parts.append(
            f"Ressource Academy correspondante : « {best_resource.title} » "
            f"(score {best_resource_score})"
        )
    else:
        parts.append("Aucune ressource Academy active correspondante trouvée")

    # Confidence level
    max_possible = 50
    combined_score = max(best_offer_score, 0) + max(best_resource_score, 0)
    combined_max = max_possible * 2
    confidence_pct = min(100, int((combined_score / combined_max) * 100)) if combined_max > 0 else 0

    parts.append(f"Confiance : {confidence_pct}%")

    return {
        "offer": best_offer,
        "academy_resource": best_resource,
        "explanation": ". ".join(parts),
        "offer_score": best_offer_score,
        "academy_resource_score": best_resource_score,
    }
