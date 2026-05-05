from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_db
from app.core.enums import MessageStatus, MessageType, OpportunityPriority, OpportunityStatus, OpportunityType
from app.models.academy_resource import AcademyResource
from app.models.company import Company
from app.models.contact import Contact
from app.models.message_draft import MessageDraft
from app.models.offer import Offer
from app.models.opportunity import Opportunity
from app.schemas.message_draft import MessageDraftRead
from app.schemas.opportunity import (
    EnrichResponse,
    MatchAssetsResponse,
    OpportunityCreate,
    OpportunityListResponse,
    OpportunityRead,
    OpportunityUpdate,
    ScoreResponse,
)
from app.services.enrichment import enrich_opportunity
from app.services.matching import match_assets
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


@router.post("/{opportunity_id}/enrich", response_model=EnrichResponse)
def enrich_opportunity_endpoint(opportunity_id: str, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    opportunity = db.get(Opportunity, uid)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Load company if available (should always exist due to FK)
    company = db.get(Company, opportunity.company_id) if opportunity.company_id else None

    # Apply deterministic enrichment
    result = enrich_opportunity(opportunity, company)

    # Update opportunity fields
    # detected_need: only overwrite if empty (service already handles this)
    opportunity.detected_need = result["detected_need"]
    opportunity.recommended_landing_page = result["recommended_landing_page"]
    opportunity.next_action = result["next_action"]
    # Notes are NOT overwritten (user-provided data preserved)

    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)

    return EnrichResponse(
        opportunity=OpportunityRead.model_validate(opportunity),
        detected_need=result["detected_need"],
        recommended_landing_page=result["recommended_landing_page"],
        next_action=result["next_action"],
        explanation=result["explanation"],
        applied=result["applied"],
        detected_need_overwritten=result["detected_need_overwritten"],
    )


def _build_draft_body(
    opportunity: Opportunity,
    company: Company,
    contact: Optional[Contact],
    matched_offer: Optional[Offer],
    matched_resource: Optional[AcademyResource],
) -> tuple[str, str]:
    """Build the subject and body for a draft, including match context if available."""
    contact_name = contact.full_name if contact else "Responsable"
    company_name = company.name

    subject = f"Proposition d'accompagnement — {company_name}"

    body_parts = [
        f"Bonjour {contact_name},",
        "",
        f"Nous accompagnons les organisations comme {company_name} "
        f"dans le domaine « {opportunity.title} ».",
    ]

    if opportunity.detected_need:
        body_parts.append(
            f"Au regard de vos besoins, nous pensons pouvoir vous apporter "
            f"une réponse concrète : {opportunity.detected_need}"
        )

    # Include matched offer context
    if matched_offer:
        offer_line = (
            f"Notre offre « {matched_offer.name} » correspond "
            f"particulièrement à votre situation."
        )
        if matched_offer.short_description:
            offer_line += f" {matched_offer.short_description}"
        body_parts.append(offer_line)

    # Include matched academy resource context
    if matched_resource:
        body_parts.append(
            f"Nous mettons également à disposition notre ressource "
            f"« {matched_resource.title} » pour approfondir le sujet."
        )

    if opportunity.description:
        body_parts.append(
            f"Pour rappel, le contexte : {opportunity.description}"
        )

    if opportunity.recommended_landing_page:
        landing_label = "Pour en savoir plus"
        if matched_offer and matched_offer.name:
            landing_label += f" sur {matched_offer.name}"
        body_parts.append(
            f"{landing_label}, vous pouvez consulter notre page dédiée : "
            f"{opportunity.recommended_landing_page}."
        )
    elif matched_offer and matched_offer.landing_page_url:
        body_parts.append(
            f"Pour en savoir plus sur {matched_offer.name}, consultez : "
            f"{matched_offer.landing_page_url}."
        )

    body_parts.extend([
        "",
        "Je me tiens à votre disposition pour un échange de quelques minutes "
        "afin de préciser votre besoin et vous présenter comment nous "
        "pourrions collaborer.",
        "",
        "Bien cordialement,",
        "L'équipe SORIA",
    ])

    body = "\n".join(body_parts)
    return subject, body


def _load_match_context(
    opportunity: Opportunity,
    db: Session,
) -> tuple[Optional[Offer], Optional[AcademyResource]]:
    """Load matched offer and academy resource for an opportunity."""
    matched_offer = db.get(Offer, opportunity.offer_id) if opportunity.offer_id else None
    matched_resource = (
        db.get(AcademyResource, opportunity.academy_resource_id)
        if opportunity.academy_resource_id
        else None
    )
    return matched_offer, matched_resource


@router.post("/{opportunity_id}/generate-draft", response_model=MessageDraftRead)
def generate_draft(opportunity_id: str, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    opportunity = db.get(Opportunity, uid)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Check for existing active rule_based draft (duplicate prevention)
    active_statuses = [
        MessageStatus.draft,
        MessageStatus.needs_review,
        MessageStatus.approved,
    ]
    existing = db.exec(
        select(MessageDraft).where(
            MessageDraft.opportunity_id == uid,
            MessageDraft.generated_by == "rule_based",
            MessageDraft.status.in_(active_statuses),
        )
    ).first()
    if existing is not None:
        return existing

    # Load company for context
    company = db.get(Company, opportunity.company_id)
    if not company:
        raise HTTPException(status_code=400, detail="Referenced company not found")

    # Load contact if set
    contact = None
    if opportunity.contact_id is not None:
        contact = db.get(Contact, opportunity.contact_id)

    # Load matched offer and academy resource for context
    matched_offer, matched_resource = _load_match_context(opportunity, db)

    subject, body = _build_draft_body(opportunity, company, contact, matched_offer, matched_resource)

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


@router.post("/{opportunity_id}/regenerate-draft", response_model=MessageDraftRead)
def regenerate_draft(opportunity_id: str, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    opportunity = db.get(Opportunity, uid)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Archive existing active rule_based drafts (draft, needs_review, approved)
    # Do NOT archive sent_manually or sent_by_system drafts
    active_statuses = [
        MessageStatus.draft,
        MessageStatus.needs_review,
        MessageStatus.approved,
    ]
    existing_drafts = db.exec(
        select(MessageDraft).where(
            MessageDraft.opportunity_id == uid,
            MessageDraft.generated_by == "rule_based",
            MessageDraft.status.in_(active_statuses),
        )
    ).all()

    now = None
    for draft in existing_drafts:
        from datetime import datetime, timezone

        if now is None:
            now = datetime.now(timezone.utc)
        draft.status = MessageStatus.archived
        db.add(draft)

    if existing_drafts:
        db.flush()

    # Load company for context
    company = db.get(Company, opportunity.company_id)
    if not company:
        raise HTTPException(status_code=400, detail="Referenced company not found")

    # Load contact if set
    contact = None
    if opportunity.contact_id is not None:
        contact = db.get(Contact, opportunity.contact_id)

    # Load matched offer and academy resource for context
    matched_offer, matched_resource = _load_match_context(opportunity, db)

    subject, body = _build_draft_body(opportunity, company, contact, matched_offer, matched_resource)

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


@router.post("/{opportunity_id}/match-assets", response_model=MatchAssetsResponse)
def match_assets_endpoint(opportunity_id: str, db: Session = Depends(get_db)):
    try:
        import uuid

        uid = uuid.UUID(opportunity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid opportunity ID format")

    opportunity = db.get(Opportunity, uid)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Load company for context
    company = db.get(Company, opportunity.company_id) if opportunity.company_id else None

    # Load all offers and academy resources
    all_offers = db.exec(select(Offer)).all()
    all_resources = db.exec(select(AcademyResource)).all()

    result = match_assets(opportunity, company, all_offers, all_resources)

    # Update opportunity with matched assets
    if result["offer"] is not None:
        opportunity.offer_id = result["offer"].id
    if result["academy_resource"] is not None:
        opportunity.academy_resource_id = result["academy_resource"].id

    # Update recommended_landing_page from matched offer if available
    matched_offer = result["offer"]
    if matched_offer and matched_offer.landing_page_url:
        opportunity.recommended_landing_page = matched_offer.landing_page_url

    # Generate a useful next_action based on match
    if result["offer"] and result["academy_resource"]:
        opportunity.next_action = (
            f"Activer le suivi — offre « {result['offer'].name} » et ressource "
            f"« {result['academy_resource'].title} » identifiées."
        )
    elif result["offer"]:
        opportunity.next_action = (
            f"Activer le suivi — offre « {result['offer'].name} » identifiée."
        )
    elif result["academy_resource"]:
        opportunity.next_action = (
            f"Activer le suivi — ressource « {result['academy_resource'].title} » identifiée."
        )

    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)

    # Build response
    match_offer = result["offer"]
    match_resource = result["academy_resource"]

    return MatchAssetsResponse(
        opportunity=OpportunityRead.model_validate(opportunity),
        offer=offer_to_match_dict(match_offer),
        academy_resource=resource_to_match_dict(match_resource),
        explanation=result["explanation"],
        applied=match_offer is not None or match_resource is not None,
    )


def offer_to_match_dict(offer: Optional[Offer]) -> Optional[dict]:
    """Convert an Offer to a lightweight dict for the response."""
    if offer is None:
        return None
    return {
        "id": offer.id,
        "name": offer.name,
        "slug": offer.slug,
        "short_description": offer.short_description,
        "landing_page_url": offer.landing_page_url,
        "is_active": offer.is_active,
    }


def resource_to_match_dict(resource: Optional[AcademyResource]) -> Optional[dict]:
    """Convert an AcademyResource to a lightweight dict for the response."""
    if resource is None:
        return None
    return {
        "id": resource.id,
        "title": resource.title,
        "slug": resource.slug,
        "short_description": resource.short_description,
        "resource_type": resource.resource_type.value,
        "level": resource.level.value,
        "public_url": resource.public_url,
        "academy_url": resource.academy_url,
        "is_published": resource.is_published,
    }
