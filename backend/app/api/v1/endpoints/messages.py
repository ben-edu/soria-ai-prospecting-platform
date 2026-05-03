from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.message_draft import MessageDraft

router = APIRouter()


@router.get("", response_model=List[MessageDraft])
def list_message_drafts(db: Session = Depends(get_db)):
    drafts = db.exec(select(MessageDraft)).all()
    return drafts


@router.post("", response_model=MessageDraft)
def create_message_draft(draft: MessageDraft, db: Session = Depends(get_db)):
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft
