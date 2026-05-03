from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import JSON, Field

from app.core.enums import SourceType
from app.models.base import BaseModel


class SourceRecord(BaseModel, table=True):
    __tablename__ = "source_records"

    source_type: SourceType = Field(default=SourceType.manual)
    source_name: Optional[str] = Field(default=None)
    source_url: Optional[str] = Field(default=None)
    external_id: Optional[str] = Field(default=None, index=True)
    raw_payload: Optional[dict] = Field(default=None, sa_type=JSON)
    imported_at: datetime = Field(nullable=False, sa_type=DateTime(timezone=True))
    processed: bool = Field(default=False)
    processing_notes: Optional[str] = Field(default=None)
