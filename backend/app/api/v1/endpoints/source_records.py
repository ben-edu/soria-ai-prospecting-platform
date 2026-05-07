"""Read-only API endpoints for SourceRecord provenance.

Phase 9D — SourceRecord / Import Provenance UX.
Exposes GET /source-records and GET /source-records/{id} for audit
and provenance visibility in the SORIA Cockpit.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.source_record import SourceRecord
from app.schemas.source_record import SourceRecordListResponse, SourceRecordRead

router = APIRouter()


@router.get("", response_model=SourceRecordListResponse)
def list_source_records(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    source_name: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    external_id: Optional[str] = Query(None),
    processed: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    """List SourceRecords with optional filters and pagination.

    Supports filtering by source_name, source_type, external_id, processed,
    and a global search across source_name, external_id, source_url,
    and processing_notes.
    """
    conditions = []

    if source_name:
        conditions.append(SourceRecord.source_name == source_name)
    if source_type:
        conditions.append(SourceRecord.source_type == source_type)
    if external_id:
        conditions.append(SourceRecord.external_id == external_id)
    if processed is not None:
        conditions.append(SourceRecord.processed == processed)
    if search:
        like = f"%{search}%"
        conditions.append(
            SourceRecord.source_name.ilike(like)
            | SourceRecord.external_id.ilike(like)
            | SourceRecord.source_url.ilike(like)
            | SourceRecord.processing_notes.ilike(like)
        )

    count_stmt = select(func.count(SourceRecord.id))
    for c in conditions:
        count_stmt = count_stmt.where(c)
    total = db.execute(count_stmt).scalar_one()

    stmt = select(SourceRecord)
    for c in conditions:
        stmt = stmt.where(c)
    stmt = stmt.order_by(SourceRecord.imported_at.desc()).offset(skip).limit(limit)
    items = db.exec(stmt).all()

    return SourceRecordListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{source_record_id}", response_model=SourceRecordRead)
def get_source_record(source_record_id: str, db: Session = Depends(get_db)):
    """Get a single SourceRecord by ID."""
    try:
        uid = UUID(source_record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid SourceRecord ID format")

    source_record = db.get(SourceRecord, uid)
    if not source_record:
        raise HTTPException(status_code=404, detail="SourceRecord not found")

    return source_record
