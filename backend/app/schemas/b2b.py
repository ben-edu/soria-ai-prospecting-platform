from pydantic import BaseModel

from app.schemas.opportunity import OpportunityRead


class B2BQualificationResponse(BaseModel):
    score: int
    threshold: int
    qualified: bool
    scoring_version: str
    matched_offer_name: str
    matched_offer_slug: str
    landing_page_url: str
    breakdown: dict[str, int]
    reasons: dict[str, list[str]]
    opportunity: OpportunityRead
