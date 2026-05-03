
import uuid
from typing import TYPE_CHECKING, Optional

from sqlmodel import JSON, Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity


class OpportunityScore(BaseModel, table=True):
    __tablename__ = "opportunity_scores"

    opportunity_id: uuid.UUID = Field(foreign_key="opportunities.id", nullable=False)
    total_score: int = Field(nullable=False)
    training_score: int = Field(default=0)
    devops_score: int = Field(default=0)
    security_score: int = Field(default=0)
    business_score: int = Field(default=0)
    academy_score: int = Field(default=0)
    reasons: Optional[dict] = Field(default=None, sa_type=JSON)
    scoring_version: str = Field(default="v1")

    # relationships
    opportunity: "Opportunity" = Relationship(back_populates="scores")
