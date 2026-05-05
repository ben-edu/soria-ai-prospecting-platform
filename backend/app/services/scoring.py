"""Deterministic rule-based opportunity scoring service."""

from app.core.enums import OpportunityPriority
from app.models.opportunity import Opportunity


def _priority_bonus(priority: OpportunityPriority) -> int:
    mapping = {
        OpportunityPriority.low: 0,
        OpportunityPriority.medium: 10,
        OpportunityPriority.high: 20,
        OpportunityPriority.urgent: 25,
    }
    return mapping.get(priority, 0)


def score_opportunity(opportunity: Opportunity) -> dict:
    """Compute a deterministic score (0-100) for an opportunity.

    Returns a dict with ``score``, ``breakdown`` (per-criterion points),
    and ``explanation`` (human-readable summary).
    """
    breakdown: dict[str, int] = {}

    # Contact assigned
    if opportunity.contact_id is not None:
        breakdown["contact_assigné"] = 15
    else:
        breakdown["contact_assigné"] = 0

    # Description present
    if opportunity.description:
        breakdown["description_présente"] = 10
    else:
        breakdown["description_présente"] = 0

    # Detected need
    if opportunity.detected_need:
        breakdown["besoin_détecté"] = 15
    else:
        breakdown["besoin_détecté"] = 0

    # Priority
    p_bonus = _priority_bonus(opportunity.priority)
    breakdown[f"priorité_{opportunity.priority.value}"] = p_bonus

    # Offer linked
    if opportunity.offer_id is not None:
        breakdown["offre_liée"] = 10
    else:
        breakdown["offre_liée"] = 0

    # Academy resource linked
    if opportunity.academy_resource_id is not None:
        breakdown["ressource_academy_liée"] = 10
    else:
        breakdown["ressource_academy_liée"] = 0

    # Source URL
    if opportunity.source_url:
        breakdown["source_url_présente"] = 5
    else:
        breakdown["source_url_présente"] = 0

    # Recommended landing page
    if opportunity.recommended_landing_page:
        breakdown["landing_page_recommandée"] = 5
    else:
        breakdown["landing_page_recommandée"] = 0

    # Language — bonus for French (primary market)
    if opportunity.language and opportunity.language.lower() == "fr":
        breakdown["langue_française"] = 5
    else:
        breakdown["langue_française"] = 0

    total = sum(breakdown.values())
    # Clamp
    total = max(0, min(100, total))

    # Build explanation
    detail_parts = [
        f"{label} (+{points})" for label, points in breakdown.items() if points > 0
    ]
    if not detail_parts:
        detail_parts = ["aucun critère rempli"]

    explanation = (
        f"Score calculé : {', '.join(detail_parts)}. "
        f"Total : {total}/100."
    )

    return {"score": total, "breakdown": breakdown, "explanation": explanation}


def suggest_next_action(score: int) -> str:
    """Return a recommended next action based on the score."""
    if score >= 80:
        return "Prêt à contacter — générer un draft de prospection"
    elif score >= 50:
        return "À analyser — affiner le besoin détecté"
    else:
        return "À enrichir — données incomplètes"
