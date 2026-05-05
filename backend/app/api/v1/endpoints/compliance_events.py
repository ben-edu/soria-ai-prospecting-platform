import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_db
from app.core.enums import ComplianceEventType, SourceType
from app.models.company import Company
from app.models.compliance_event import ComplianceEvent
from app.models.contact import Contact
from app.models.opportunity import Opportunity
from app.schemas.compliance_event import (
    ComplianceEventCreate,
    ComplianceEventListResponse,
    ComplianceEventRead,
)

router = APIRouter()

# Event types that require reason_for_contact
REASON_REQUIRED_TYPES = {
    ComplianceEventType.contact_collected,
    ComplianceEventType.message_generated,
    ComplianceEventType.message_approved,
    ComplianceEventType.message_sent,
}


def _get_event_or_404(event_id: str, db: Session) -> ComplianceEvent:
    try:
        uid = uuid.UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid compliance event ID format")
    event = db.get(ComplianceEvent, uid)
    if not event:
        raise HTTPException(status_code=404, detail="Compliance event not found")
    return event


@router.get("", response_model=ComplianceEventListResponse)
def list_compliance_events(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    company_id: Optional[str] = Query(None),
    contact_id: Optional[str] = Query(None),
    opportunity_id: Optional[str] = Query(None),
    event_type: Optional[ComplianceEventType] = Query(None),
    source: Optional[SourceType] = Query(None),
    opt_out_status: Optional[bool] = Query(None),
):
    conditions = []

    if company_id:
        try:
            conditions.append(ComplianceEvent.company_id == uuid.UUID(company_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid company ID format")

    if contact_id:
        try:
            conditions.append(ComplianceEvent.contact_id == uuid.UUID(contact_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid contact ID format")

    if opportunity_id:
        try:
            conditions.append(ComplianceEvent.opportunity_id == uuid.UUID(opportunity_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    if event_type:
        conditions.append(ComplianceEvent.event_type == event_type)

    if source:
        conditions.append(ComplianceEvent.source == source)

    if opt_out_status is not None:
        conditions.append(ComplianceEvent.opt_out_status == opt_out_status)

    count_stmt = select(func.count(ComplianceEvent.id))
    for c in conditions:
        count_stmt = count_stmt.where(c)
    total = db.execute(count_stmt).scalar_one()

    stmt = select(ComplianceEvent)
    for c in conditions:
        stmt = stmt.where(c)
    stmt = stmt.offset(skip).limit(limit)
    items = db.exec(stmt).all()

    return ComplianceEventListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=ComplianceEventRead, status_code=201)
def create_compliance_event(data: ComplianceEventCreate, db: Session = Depends(get_db)):
    # At least one of company_id, contact_id, opportunity_id must be provided
    if data.company_id is None and data.contact_id is None and data.opportunity_id is None:
        raise HTTPException(
            status_code=400,
            detail="At least one of company_id, contact_id, or opportunity_id must be provided",
        )

    # Validate company exists if provided
    if data.company_id is not None:
        company = db.get(Company, data.company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

    # Validate contact exists if provided
    if data.contact_id is not None:
        contact = db.get(Contact, data.contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

    # Validate opportunity exists if provided
    if data.opportunity_id is not None:
        opportunity = db.get(Opportunity, data.opportunity_id)
        if not opportunity:
            raise HTTPException(status_code=404, detail="Opportunity not found")

    # If both contact_id and opportunity_id are provided, they must belong to the same company
    if data.contact_id is not None and data.opportunity_id is not None:
        if data.contact_id is not None and data.opportunity_id is not None:
            contact = db.get(Contact, data.contact_id)
            opportunity = db.get(Opportunity, data.opportunity_id)
            if contact and opportunity and contact.company_id != opportunity.company_id:
                raise HTTPException(
                    status_code=400,
                    detail="Contact and opportunity must belong to the same company",
                )

    # Validate reason_for_contact is required for certain event types
    if data.event_type in REASON_REQUIRED_TYPES and not data.reason_for_contact:
        raise HTTPException(
            status_code=400,
            detail=f"reason_for_contact is required for event_type '{data.event_type.value}'",
        )

    event = ComplianceEvent(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{compliance_event_id}", response_model=ComplianceEventRead)
def get_compliance_event(compliance_event_id: str, db: Session = Depends(get_db)):
    return _get_event_or_404(compliance_event_id, db)
