from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_db
from app.core.enums import ContactType, EmailVerificationStatus
from app.models.company import Company
from app.models.contact import Contact
from app.schemas.contact import (
    ContactCreate,
    ContactListResponse,
    ContactRead,
    ContactUpdate,
)

router = APIRouter()


@router.get("", response_model=ContactListResponse)
def list_contacts(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    company_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    contact_type: Optional[ContactType] = Query(None),
    email_verification_status: Optional[EmailVerificationStatus] = Query(None),
    opt_out: Optional[bool] = Query(None),
):
    conditions = []

    if company_id:
        try:
            import uuid

            conditions.append(Contact.company_id == uuid.UUID(company_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid company ID format")

    if search:
        like_pattern = f"%{search}%"
        conditions.append(
            Contact.full_name.ilike(like_pattern)
            | Contact.email.ilike(like_pattern)
            | Contact.role_title.ilike(like_pattern)
        )

    if contact_type:
        conditions.append(Contact.contact_type == contact_type)

    if email_verification_status:
        conditions.append(Contact.email_verification_status == email_verification_status)

    if opt_out is not None:
        conditions.append(Contact.opt_out == opt_out)

    count_stmt = select(func.count(Contact.id))
    for c in conditions:
        count_stmt = count_stmt.where(c)
    total = db.execute(count_stmt).scalar_one()

    stmt = select(Contact)
    for c in conditions:
        stmt = stmt.where(c)
    stmt = stmt.offset(skip).limit(limit)
    items = db.exec(stmt).all()

    return ContactListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=ContactRead, status_code=201)
def create_contact(data: ContactCreate, db: Session = Depends(get_db)):
    # Validate company exists
    company = db.get(Company, data.company_id)
    if not company:
        raise HTTPException(status_code=400, detail="Referenced company does not exist")

    contact = Contact(**data.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactRead)
def get_contact(contact_id: str, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(contact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid contact ID format")

    contact = db.get(Contact, uid)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.patch("/{contact_id}", response_model=ContactRead)
def update_contact(contact_id: str, data: ContactUpdate, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(contact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid contact ID format")

    contact = db.get(Contact, uid)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # If changing company_id, validate the new company exists
    if data.company_id is not None and data.company_id != contact.company_id:
        company = db.get(Company, data.company_id)
        if not company:
            raise HTTPException(status_code=400, detail="Referenced company does not exist")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contact, key, value)

    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact
