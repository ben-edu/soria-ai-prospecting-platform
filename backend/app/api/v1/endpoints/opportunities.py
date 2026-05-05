from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_db
from app.core.enums import OpportunityPriority, OpportunityStatus, OpportunityType
from app.models.academy_resource import AcademyResource
from app.models.company import Company
from app.models.contact import Contact
from app.models.offer import Offer
from app.models.opportunity import Opportunity
from app.schemas.message_draft import MessageDraftRead
from app.schemas.opportunity import (
    OpportunityCreate,
    OpportunityListResponse,
    OpportunityRead,
    OpportunityUpdate,
    ScoreResponse,
)
from app.services.scoring import score_opportunity, suggest_next_action

router = APIRouter()


def _resolve_opportunity_filters(
    company_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    opportunity_type: Optional[OpportunityType] = None,
    status: Optional[OpportunityStatus] = None,
    priority: Optional[OpportunityPriority] = None,
    min_score: Optional[int] = None,
    search: Optional[str] = None,
):
    import uuid

    conditions = []

    if company_id:
        try:
            conditions.append(Opportunity.company_id == uuid.UUID(company_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid company ID format")

    if contact_id:
        try:
            conditions.append(Opportunity.contact_id == uuid.UUID(contact_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid contact ID format")

    if opportunity_type:
        conditions.append(Opportunity.opportunity_type == opportunity_type)

    if status:
        conditions.append(Opportunity.status == status)

    if priority:
        conditions.append(Opportunity.priority == priority)

    if min_score is not None:
        conditions.append(Opportunity.score >= min_score)

    if search:
        like_pattern = f"%{search}%"
        conditions.append(
            Opportunity.title.ilike(like_pattern)
            | Opportunity.description.ilike(like_pattern)
            | Opportunity.detected_need.ilike(like_pattern)
        )

    return conditions


@router.get("", response_model=OpportunityListResponse)
def list_opportunities(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    company_id: Optional[str] = Query(None),
    contact_id: Optional[str] = Query(None),
    opportunity_type: Optional[OpportunityType] = Query(None),
    status: Optional[OpportunityStatus] = Query(None),
    priority: Optional[OpportunityPriority] = Query(None),
    min_score: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
):
    conditions = _resolve_opportunity_filters(
        company_id=company_id,
        contact_id=contact_id,
        opportunity_type=opportunity_type,
        status=status,
        priority=priority,
        min_score=min_score,
        search=search,
    )

    count_stmt = select(func.count(Opportunity.id))
    for c in conditions:
        count_stmt = count_stmt.where(c)
    total = db.execute(count_stmt).scalar_one()

    stmt = select(Opportunity)
    for c in conditions:
        stmt = stmt.where(c)
    stmt = stmt.offset(skip).limit(limit)
    items = db.exec(stmt).all()

    return OpportunityListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=OpportunityRead, status_code=201)
def create_opportunity(data: OpportunityCreate, db: Session = Depends(get_db)):
    # Validate company exists
    company = db.get(Company, data.company_id)
    if not company:
        raise HTTPException(status_code=400, detail="Referenced company does not exist")

    # Validate contact exists if provided
    if data.contact_id is not None:
        contact = db.get(Contact, data.contact_id)
        if not contact:
            raise HTTPException(status_code=400, detail="Referenced contact does not exist")

    # Validate offer exists if provided
    if data.offer_id is not None:
        offer = db.get(Offer, data.offer_id)
        if not offer:
            raise HTTPException(status_code=400, detail="Referenced offer does not exist")

    # Validate academy resource exists if provided
    if data.academy_resource_id is not None:
        resource = db.get(AcademyResource, data.academy_resource_id)
        if not resource:
            raise HTTPException(status_code=400, detail="Referenced academy resource does not exist")

    opportunity = Opportunity(**data.model_dump())
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.get("/{opportunity_id}", response_model=OpportunityRead)
def get_opportunity(opportunity_id: str, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    opportunity = db.get(Opportunity, uid)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity


@router.patch("/{opportunity_id}", response_model=OpportunityRead)
def update_opportunity(
    opportunity_id: str,
    data: OpportunityUpdate,
    db: Session = Depends(get_db),
):
    try:
        import uuid

        uid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    opportunity = db.get(Opportunity, uid)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Validate foreign key references if changed
    if data.company_id is not None and data.company_id != opportunity.company_id:
        company = db.get(Company, data.company_id)
        if not company:
            raise HTTPException(status_code=400, detail="Referenced company does not exist")

    if data.contact_id is not None and data.contact_id != opportunity.contact_id:
        contact = db.get(Contact, data.contact_id)
        if not contact:
            raise HTTPException(status_code=400, detail="Referenced contact does not exist")

    if data.offer_id is not None and data.offer_id != opportunity.offer_id:
        offer = db.get(Offer, data.offer_id)
        if not offer:
            raise HTTPException(status_code=400, detail="Referenced offer does not exist")

    if data.academy_resource_id is not None and data.academy_resource_id != opportunity.academy_resource_id:
        resource = db.get(AcademyResource, data.academy_resource_id)
        if not resource:
            raise HTTPException(status_code=400, detail="Referenced academy resource does not exist")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(opportunity, key, value)

    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.post("/{opportunity_id}/score", response_model=ScoreResponse)
def score_opportunity_endpoint(opportunity_id: str, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    opportunity = db.get(Opportunity, uid)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    result = score_opportunity(opportunity)
    opportunity.score = result["score"]
    opportunity.next_action = suggest_next_action(result["score"])

    # Advance status to scored only if it's still new
    if opportunity.status.value == "new":
        from app.core.enums import OpportunityStatus
        opportunity.status = OpportunityStatus.scored

    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)

    return ScoreResponse(
        score=result["score"],
        explanation=result["explanation"],
        breakdown=result["breakdown"],
        opportunity=OpportunityRead.model_validate(opportunity),
    )


@router.post("/{opportunity_id}/generate-draft", response_model=MessageDraftRead, status_code=201)
def generate_draft(opportunity_id: str, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    opportunity = db.get(Opportunity, uid)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Load company for context
    company = db.get(Company, opportunity.company_id)
    if not company:
        raise HTTPException(status_code=400, detail="Referenced company not found")

    # Load contact if set
    contact = None
    if opportunity.contact_id is not None:
        contact = db.get(Contact, opportunity.contact_id)

    # Build a simple template-based draft
    contact_name = contact.full_name if contact else "Responsable"
    company_name = company.name

    subject = f"Proposition d'accompagnement — {company_name}"

    body_parts = [
        f"Bonjour {contact_name},",
        "",
        f"Nous avons identifié que {company_name} pourrait être intéressé "
        f"par notre offre « {opportunity.title} ».",
    ]

    if opportunity.description:
        body_parts.append(f"Description : {opportunity.description}")

    if opportunity.detected_need:
        body_parts.append(
            f"Nous avons noté le besoin suivant : {opportunity.detected_need}."
        )

    body_parts.extend([
        "",
        "N'hésitez pas à me contacter pour échanger sur ce sujet et voir "
        "comment nous pourrons collaborer.",
        "",
        "Cordialement,",
        "L'équipe SORIA",
    ])

    body = "\n".join(body_parts)

    from app.core.enums import MessageType
    from app.models.message_draft import MessageDraft

    draft = MessageDraft(
        opportunity_id=uid,
        contact_id=opportunity.contact_id,
        message_type=MessageType.prospecting_email,
        language=opportunity.language,
        subject=subject,
        body=body,
        status="draft",
        generated_by="rule_based",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft
