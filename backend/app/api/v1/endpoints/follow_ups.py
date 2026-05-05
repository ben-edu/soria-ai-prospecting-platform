import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_db
from app.core.enums import FollowUpActionType, FollowUpStatus
from app.models.contact import Contact
from app.models.follow_up import FollowUp
from app.models.opportunity import Opportunity
from app.schemas.follow_up import (
    FollowUpCreate,
    FollowUpListResponse,
    FollowUpRead,
    FollowUpUpdate,
)

router = APIRouter()


def _get_follow_up_or_404(follow_up_id: str, db: Session) -> FollowUp:
    try:
        uid = uuid.UUID(follow_up_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid follow-up ID format")
    follow_up = db.get(FollowUp, uid)
    if not follow_up:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return follow_up


@router.get("", response_model=FollowUpListResponse)
def list_follow_ups(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    opportunity_id: Optional[str] = Query(None),
    contact_id: Optional[str] = Query(None),
    status: Optional[FollowUpStatus] = Query(None),
    action_type: Optional[FollowUpActionType] = Query(None),
):
    conditions = []

    if opportunity_id:
        try:
            conditions.append(FollowUp.opportunity_id == uuid.UUID(opportunity_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    if contact_id:
        try:
            conditions.append(FollowUp.contact_id == uuid.UUID(contact_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid contact ID format")

    if status:
        conditions.append(FollowUp.status == status)

    if action_type:
        conditions.append(FollowUp.action_type == action_type)

    count_stmt = select(func.count(FollowUp.id))
    for c in conditions:
        count_stmt = count_stmt.where(c)
    total = db.execute(count_stmt).scalar_one()

    stmt = select(FollowUp)
    for c in conditions:
        stmt = stmt.where(c)
    stmt = stmt.offset(skip).limit(limit)
    items = db.exec(stmt).all()

    return FollowUpListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=FollowUpRead, status_code=201)
def create_follow_up(data: FollowUpCreate, db: Session = Depends(get_db)):
    # Validate opportunity exists
    opportunity = db.get(Opportunity, data.opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Validate contact if provided
    contact_id = data.contact_id
    if contact_id is not None:
        contact = db.get(Contact, contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        # Contact must belong to the same company as the opportunity
        if contact.company_id != opportunity.company_id:
            raise HTTPException(
                status_code=400,
                detail="Contact must belong to the same company as the opportunity",
            )

    follow_up = FollowUp(
        opportunity_id=data.opportunity_id,
        contact_id=contact_id,
        due_date=data.due_date,
        action_type=data.action_type,
        status=data.status,
        notes=data.notes,
        openproject_work_package_id=data.openproject_work_package_id,
    )
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return follow_up


@router.get("/{follow_up_id}", response_model=FollowUpRead)
def get_follow_up(follow_up_id: str, db: Session = Depends(get_db)):
    return _get_follow_up_or_404(follow_up_id, db)


@router.patch("/{follow_up_id}", response_model=FollowUpRead)
def update_follow_up(
    follow_up_id: str,
    data: FollowUpUpdate,
    db: Session = Depends(get_db),
):
    follow_up = _get_follow_up_or_404(follow_up_id, db)

    update_data = data.model_dump(exclude_unset=True)

    # If contact_id is changing, validate it
    if "contact_id" in update_data and update_data["contact_id"] != follow_up.contact_id:
        new_contact_id = update_data["contact_id"]
        if new_contact_id is not None:
            contact = db.get(Contact, new_contact_id)
            if not contact:
                raise HTTPException(status_code=404, detail="Contact not found")
            # Verify contact belongs to the same company as the opportunity
            opportunity = db.get(Opportunity, follow_up.opportunity_id)
            if opportunity and contact.company_id != opportunity.company_id:
                raise HTTPException(
                    status_code=400,
                    detail="Contact must belong to the same company as the opportunity",
                )

    for key, value in update_data.items():
        setattr(follow_up, key, value)

    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return follow_up


@router.post("/{follow_up_id}/mark-done", response_model=FollowUpRead)
def mark_follow_up_done(follow_up_id: str, db: Session = Depends(get_db)):
    follow_up = _get_follow_up_or_404(follow_up_id, db)

    if follow_up.status == FollowUpStatus.cancelled:
        raise HTTPException(
            status_code=400,
            detail="Cannot mark a cancelled follow-up as done",
        )

    follow_up.status = FollowUpStatus.done
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return follow_up


@router.post("/{follow_up_id}/cancel", response_model=FollowUpRead)
def cancel_follow_up(follow_up_id: str, db: Session = Depends(get_db)):
    follow_up = _get_follow_up_or_404(follow_up_id, db)

    if follow_up.status == FollowUpStatus.done:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel a follow-up that is already done",
        )

    follow_up.status = FollowUpStatus.cancelled
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return follow_up
