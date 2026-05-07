"""Pydantic schemas for SourceRecord.

Phase 9D — SourceRecord / Import Provenance UX.
Exposes read-only SourceRecord fields plus computed linked_company_id
and linked_opportunity_id extracted from processing_notes.
"""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.core.enums import SourceType


def _extract_linked_id(notes: Optional[str], prefix: str) -> Optional[str]:
    """Extract a UUID from processing_notes after the given prefix.

    Example notes: "Company <uuid> (created), Opportunity <uuid> (created)"
    Returns the UUID string or None.
    """
    if not notes:
        return None
    pattern = re.compile(rf"{re.escape(prefix)}\s+([0-9a-fA-F-]+)\s*\(")
    m = pattern.search(notes)
    if m:
        try:
            return str(UUID(m.group(1)))
        except ValueError:
            return None
    return None


class SourceRecordRead(BaseModel):
    """Read schema for SourceRecord.

    Exposes all model fields plus computed linked_company_id and
    linked_opportunity_id derived from processing_notes.
    """

    id: UUID
    source_type: SourceType
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    external_id: Optional[str] = None
    raw_payload: Optional[dict] = None
    imported_at: datetime
    processed: bool = False
    processing_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    linked_company_id: Optional[str] = None
    linked_opportunity_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _compute_linked_ids(self):
        """Compute linked IDs from processing_notes."""
        self.linked_company_id = _extract_linked_id(self.processing_notes, "Company")
        self.linked_opportunity_id = _extract_linked_id(self.processing_notes, "Opportunity")
        return self


class SourceRecordListResponse(BaseModel):
    """Paginated list response for SourceRecords."""

    items: list[SourceRecordRead]
    total: int
    skip: int
    limit: int
