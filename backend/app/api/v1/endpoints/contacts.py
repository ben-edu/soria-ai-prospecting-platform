from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db
from app.models.contact import Contact

router = APIRouter()


@router.get("", response_model=List[Contact])
def list_contacts(db: Session = Depends(get_db)):
    contacts = db.exec(select(Contact)).all()
    return contacts


@router.post("", response_model=Contact)
def create_contact(contact: Contact, db: Session = Depends(get_db)):
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact
