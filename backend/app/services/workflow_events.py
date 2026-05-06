"""Workflow event helpers — create ComplianceEvent and FollowUp records from
message workflow actions without committing (caller owns the commit)."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from app.core.enums import (
    ComplianceEventType,
    FollowUpActionType,
    FollowUpStatus,
    SourceType,
)
from app.models.compliance_event import ComplianceEvent
from app.models.follow_up import FollowUp
from app.models.message_draft import MessageDraft
from app.models.opportunity import Opportunity


def create_message_generated_compliance_event(
    db: Session,
    draft: MessageDraft,
    opportunity: Optional[Opportunity] = None,
) -> ComplianceEvent:
    """Create a message_generated ComplianceEvent for the given draft."""
    if opportunity is None:
        opportunity = db.get(Opportunity, draft.opportunity_id)

    event = ComplianceEvent(
        company_id=opportunity.company_id if opportunity else None,
        contact_id=draft.contact_id,
        opportunity_id=draft.opportunity_id,
        event_type=ComplianceEventType.message_generated,
        source=SourceType.manual,
        reason_for_contact="Message généré dans le cadre d'une action de prospection commerciale.",
        professional_relevance=(
            "Ce message est lié à une opportunité professionnelle identifiée "
            "et reste dans le cadre du workflow de validation humaine supervisée."
        ),
        notes=f"Message draft created (generated_by={draft.generated_by}, id={draft.id})",
    )
    db.add(event)
    return event


def create_message_approved_compliance_event(
    db: Session,
    draft: MessageDraft,
    opportunity: Optional[Opportunity] = None,
) -> ComplianceEvent:
    """Create a message_approved ComplianceEvent for the given draft."""
    if opportunity is None:
        opportunity = db.get(Opportunity, draft.opportunity_id)

    event = ComplianceEvent(
        company_id=opportunity.company_id if opportunity else None,
        contact_id=draft.contact_id,
        opportunity_id=draft.opportunity_id,
        event_type=ComplianceEventType.message_approved,
        source=SourceType.manual,
        reason_for_contact="Message approuvé dans le cadre du workflow de validation.",
        professional_relevance=(
            "Ce message est lié à une opportunité professionnelle identifiée "
            "et a été approuvé par un validateur humain."
        ),
        notes=f"Message draft approved (id={draft.id})",
    )
    db.add(event)
    return event


def create_message_sent_compliance_event(
    db: Session,
    draft: MessageDraft,
    opportunity: Optional[Opportunity] = None,
) -> ComplianceEvent:
    """Create a message_sent ComplianceEvent for the given draft."""
    if opportunity is None:
        opportunity = db.get(Opportunity, draft.opportunity_id)

    event = ComplianceEvent(
        company_id=opportunity.company_id if opportunity else None,
        contact_id=draft.contact_id,
        opportunity_id=draft.opportunity_id,
        event_type=ComplianceEventType.message_sent,
        source=SourceType.manual,
        reason_for_contact="Message envoyé dans le cadre d'une action de prospection commerciale.",
        professional_relevance=(
            "Ce message est lié à une opportunité professionnelle identifiée "
            "et a été envoyé manuellement après validation."
        ),
        notes=f"Message draft marked as sent manually (id={draft.id})",
    )
    db.add(event)
    return event


def schedule_follow_up_after_manual_send(
    db: Session,
    draft: MessageDraft,
    opportunity: Optional[Opportunity] = None,
) -> Optional[FollowUp]:
    """Schedule a planned follow-up after marking a message as sent manually.

    Avoids creating a duplicate if an active planned follow-up already exists
    for the same opportunity/contact/action_type=send_follow_up/status=planned.
    """
    if opportunity is None:
        opportunity = db.get(Opportunity, draft.opportunity_id)

    # Check for existing planned follow-up for this opportunity/contact
    existing = db.exec(
        select(FollowUp).where(
            FollowUp.opportunity_id == draft.opportunity_id,
            FollowUp.contact_id == draft.contact_id,
            FollowUp.action_type == FollowUpActionType.send_follow_up,
            FollowUp.status == FollowUpStatus.planned,
        )
    ).first()
    if existing is not None:
        return None

    due_date = datetime.now(timezone.utc) + timedelta(days=7)
    follow_up = FollowUp(
        opportunity_id=draft.opportunity_id,
        contact_id=draft.contact_id,
        due_date=due_date,
        action_type=FollowUpActionType.send_follow_up,
        status=FollowUpStatus.planned,
        notes="Automatically scheduled after manual message send.",
    )
    db.add(follow_up)
    return follow_up
