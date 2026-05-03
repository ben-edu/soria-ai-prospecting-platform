
import uuid
from typing import TYPE_CHECKING, Optional

from sqlmodel import JSON, Field, Relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.opportunity import Opportunity


class Offer(BaseModel, table=True):
    __tablename__ = "offers"

    category_id: uuid.UUID = Field(foreign_key="service_categories.id", nullable=False)
    name: str = Field(index=True, nullable=False)
    slug: str = Field(unique=True, index=True, nullable=False)
    short_description: Optional[str] = Field(default=None)
    full_description: Optional[str] = Field(default=None)
    target_audience: Optional[dict] = Field(default=None, sa_type=JSON)
    keywords: Optional[dict] = Field(default=None, sa_type=JSON)
    landing_page_url: Optional[str] = Field(default=None)
    priority: int = Field(default=0)
    is_active: bool = Field(default=True)

    # relationships
    category: "ServiceCategory" = Relationship(back_populates="offers")
    opportunities: list["Opportunity"] = Relationship(back_populates="offer")
