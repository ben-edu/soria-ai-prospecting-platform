import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_db
from app.core.enums import MessageStatus, MessageType
from app.models.contact import Contact
from app.models.message_draft import MessageDraft
from app.models.opportunity import Opportunity
from app.schemas.message_draft import (
    MessageDraftActionRequest,
    MessageDraftCreate,
    MessageDraftListResponse,
    MessageDraftRead,
    MessageDraftUpdate,
)

router = APIRouter()


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} format")


def _get_draft_or_404(draft_id: str, db: Session) -> MessageDraft:
    uid = _parse_uuid(draft_id, "message draft ID")
    draft = db.get(MessageDraft, uid)
    if not draft:
        raise HTTPException(status_code=404, detail="Message draft not found")
    return draft


@router.get("", response_model=MessageDraftListResponse)
def list_message_drafts(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    opportunity_id: Optional[str] = Query(None),
    contact_id: Optional[str] = Query(None),
    status: Optional[MessageStatus] = Query(None),
    message_type: Optional[MessageType] = Query(None),
    language: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    conditions = []

    if opportunity_id:
        conditions.append(MessageDraft.opportunity_id == _parse_uuid(opportunity_id, "opportunity ID"))

    if contact_id:
        conditions.append(MessageDraft.contact_id == _parse_uuid(contact_id, "contact ID"))

    if status:
        conditions.append(MessageDraft.status == status)

    if message_type:
        conditions.append(MessageDraft.message_type == message_type)

    if language:
        conditions.append(MessageDraft.language == language)

    if search:
        like_pattern = f"%{search}%"
        conditions.append(MessageDraft.subject.ilike(like_pattern) | MessageDraft.body.ilike(like_pattern))

    count_stmt = select(func.count(MessageDraft.id))
    for c in conditions:
        count_stmt = count_stmt.where(c)
    total = db.execute(count_stmt).scalar_one()

    stmt = select(MessageDraft)
    for c in conditions:
        stmt = stmt.where(c)
    stmt = stmt.offset(skip).limit(limit)
    items = db.exec(stmt).all()

    return MessageDraftListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=MessageDraftRead, status_code=201)
def create_message_draft(data: MessageDraftCreate, db: Session = Depends(get_db)):
    # Validate opportunity exists
    opportunity = db.get(Opportunity, data.opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Resolve contact_id
    contact_id = data.contact_id
    if contact_id is None:
        contact_id = opportunity.contact_id
    else:
        # Validate contact exists
        contact = db.get(Contact, contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        # Check contact belongs to same company as the opportunity
        if contact.company_id != opportunity.company_id:
            raise HTTPException(
                status_code=400,
                detail="Contact must belong to the same company as the opportunity",
            )

    draft = MessageDraft(
        opportunity_id=data.opportunity_id,
        contact_id=contact_id,
        message_type=data.message_type,
        language=data.language,
        subject=data.subject,
        body=data.body,
        tone=data.tone,
        status=data.status,
        generated_by=data.generated_by,
        model_name=data.model_name,
        prompt_version=data.prompt_version,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/{message_draft_id}", response_model=MessageDraftRead)
def get_message_draft(message_draft_id: str, db: Session = Depends(get_db)):
    return _get_draft_or_404(message_draft_id, db)


@router.patch("/{message_draft_id}", response_model=MessageDraftRead)
def update_message_draft(
    message_draft_id: str,
    data: MessageDraftUpdate,
    db: Session = Depends(get_db),
):
    draft = _get_draft_or_404(message_draft_id, db)

    # Cannot edit sent or archived drafts
    if draft.status in (MessageStatus.sent_manually, MessageStatus.archived):
        raise HTTPException(
            status_code=400,
            detail="Cannot edit a message draft that has been sent or archived",
        )

    update_data = data.model_dump(exclude_unset=True)

    # If contact_id is changing, validate it
    if "contact_id" in update_data and update_data["contact_id"] != draft.contact_id:
        new_contact_id = update_data["contact_id"]
        if new_contact_id is not None:
            contact = db.get(Contact, new_contact_id)
            if not contact:
                raise HTTPException(status_code=404, detail="Contact not found")
            # Verify contact belongs to the same company as the opportunity
            opportunity = db.get(Opportunity, draft.opportunity_id)
            if opportunity and contact.company_id != opportunity.company_id:
                raise HTTPException(
                    status_code=400,
                    detail="Contact must belong to the same company as the opportunity",
                )

    for key, value in update_data.items():
        setattr(draft, key, value)

    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{message_draft_id}/submit-review", response_model=MessageDraftRead)
def submit_draft_for_review(
    message_draft_id: str,
    data: MessageDraftActionRequest,
    db: Session = Depends(get_db),
):
    draft = _get_draft_or_404(message_draft_id, db)

    if draft.status not in (MessageStatus.draft, MessageStatus.rejected):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit draft for review from status '{draft.status.value}'. Allowed: draft, rejected",
        )

    if not draft.body or not draft.body.strip():
        raise HTTPException(status_code=400, detail="Cannot submit a draft with empty body for review")

    draft.status = MessageStatus.needs_review
    if data.review_notes is not None:
        draft.review_notes = data.review_notes

    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{message_draft_id}/approve", response_model=MessageDraftRead)
def approve_draft(
    message_draft_id: str,
    data: MessageDraftActionRequest,
    db: Session = Depends(get_db),
):
    draft = _get_draft_or_404(message_draft_id, db)

    if draft.status != MessageStatus.needs_review:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve draft from status '{draft.status.value}'. Allowed: needs_review",
        )

    draft.status = MessageStatus.approved
    draft.approved_at = datetime.now(timezone.utc)
    if data.review_notes is not None:
        draft.review_notes = data.review_notes

    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{message_draft_id}/reject", response_model=MessageDraftRead)
def reject_draft(
    message_draft_id: str,
    data: MessageDraftActionRequest,
    db: Session = Depends(get_db),
):
    draft = _get_draft_or_404(message_draft_id, db)

    if draft.status != MessageStatus.needs_review:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject draft from status '{draft.status.value}'. Allowed: needs_review",
        )

    draft.status = MessageStatus.rejected
    if data.review_notes is not None:
        draft.review_notes = data.review_notes

    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{message_draft_id}/mark-sent-manually", response_model=MessageDraftRead)
def mark_draft_sent_manually(
    message_draft_id: str,
    db: Session = Depends(get_db),
):
    draft = _get_draft_or_404(message_draft_id, db)

    if draft.status != MessageStatus.approved:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mark draft as sent from status '{draft.status.value}'. Allowed: approved",
        )

    draft.status = MessageStatus.sent_manually
    draft.sent_at = datetime.now(timezone.utc)

    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft
