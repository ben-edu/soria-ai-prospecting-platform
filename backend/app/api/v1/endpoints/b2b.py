import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_db
from app.core.enums import OpportunityStatus
from app.models.company import Company
from app.models.contact import Contact
from app.models.offer import Offer
from app.models.opportunity import Opportunity
from app.models.opportunity_score import OpportunityScore
from app.schemas.b2b import B2BQualificationResponse
from app.services.mvcs_b2b import (
    B2B_SCORING_VERSION,
    is_mvcs_b2b_context,
    qualify_mvcs_b2b,
    select_mvcs_offer_slug,
)

router = APIRouter()


@router.post(
    "/opportunities/{opportunity_id}/qualify",
    response_model=B2BQualificationResponse,
)
def qualify_b2b_opportunity(
    opportunity_id: str,
    db: Session = Depends(get_db),
):
    try:
        opportunity_uuid = uuid.UUID(opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format") from exc

    opportunity = db.get(Opportunity, opportunity_uuid)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if not is_mvcs_b2b_context(opportunity):
        raise HTTPException(
            status_code=400,
            detail=(
                "MVCS B2B qualification is limited to DevOps/Cloud opportunities "
                "curated from manual/company-website/LinkedIn-manual public sources"
            ),
        )

    company = db.get(Company, opportunity.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    contact = None
    if opportunity.contact_id is not None:
        contact = db.get(Contact, opportunity.contact_id)

    offer_slug = select_mvcs_offer_slug(opportunity)
    offer = db.exec(select(Offer).where(Offer.slug == offer_slug)).first()
    if offer is None or not offer.is_active:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Required MVCS B2B offer '{offer_slug}' is not active. "
                "Run the idempotent MVCS B2B catalog seed first."
            ),
        )

    opportunity.offer_id = offer.id
    opportunity.recommended_landing_page = offer.landing_page_url

    result = qualify_mvcs_b2b(opportunity, company, contact, offer)
    opportunity.score = result["score"]

    early_statuses = {
        OpportunityStatus.new,
        OpportunityStatus.imported_pending_review,
        OpportunityStatus.to_analyze,
        OpportunityStatus.scored,
        OpportunityStatus.interesting,
    }
    if opportunity.status in early_statuses:
        opportunity.status = (
            OpportunityStatus.interesting
            if result["qualified"]
            else OpportunityStatus.scored
        )

    if result["qualified"]:
        opportunity.next_action = (
            "Human review: confirm the decision-maker and prepare a hypothesis-safe draft."
        )
    else:
        opportunity.next_action = (
            "Do not draft outreach yet: strengthen ICP, public-signal or contact evidence."
        )

    score_record = OpportunityScore(
        opportunity_id=opportunity.id,
        total_score=result["score"],
        business_score=result["score"],
        reasons={
            "breakdown": result["breakdown"],
            "details": result["reasons"],
            "threshold": result["threshold"],
            "qualified": result["qualified"],
            "matched_offer_slug": offer.slug,
        },
        scoring_version=B2B_SCORING_VERSION,
    )

    db.add(opportunity)
    db.add(score_record)
    db.commit()
    db.refresh(opportunity)

    return B2BQualificationResponse(
        score=result["score"],
        threshold=result["threshold"],
        qualified=result["qualified"],
        scoring_version=result["scoring_version"],
        matched_offer_name=offer.name,
        matched_offer_slug=offer.slug,
        landing_page_url=offer.landing_page_url or "",
        breakdown=result["breakdown"],
        reasons=result["reasons"],
        opportunity=opportunity,
    )
