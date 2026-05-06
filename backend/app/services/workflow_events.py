"""Workflow event helpers — create ComplianceEvent and FollowUp records from
message workflow actions without committing (caller owns the commit)."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from app.core.enums import (
    ComplianceEventType,
    FollowUpActionType,
    FollowUpStatus,
    OpportunityStatus,
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


# ---------------------------------------------------------------------------
# Opportunity status sync helpers — update status and next_action in response
# to MessageDraft workflow actions, respecting terminal business statuses.
# Caller owns commit.
# ---------------------------------------------------------------------------

TERMINAL_OPPORTUNITY_STATUSES = frozenset({
    OpportunityStatus.converted,
    OpportunityStatus.lost,
    OpportunityStatus.closed,
})


def _sync_opportunity_status(
    opportunity: Opportunity,
    new_status: OpportunityStatus,
    next_action: str,
) -> None:
    """Update opportunity status and next_action unless it is in a terminal state."""
    if opportunity.status in TERMINAL_OPPORTUNITY_STATUSES:
        return
    opportunity.status = new_status
    opportunity.next_action = next_action


def sync_opportunity_to_draft_ready(opportunity: Opportunity) -> None:
    """Set opportunity status to draft_ready when a draft is created."""
    _sync_opportunity_status(
        opportunity,
        OpportunityStatus.draft_ready,
        "Relire le brouillon et le soumettre à validation humaine.",
    )


def sync_opportunity_to_waiting_validation(opportunity: Opportunity) -> None:
    """Set opportunity status to waiting_validation when a draft is submitted for review."""
    _sync_opportunity_status(
        opportunity,
        OpportunityStatus.waiting_validation,
        "Valider humainement le brouillon avant tout envoi externe.",
    )


def sync_opportunity_to_approved(opportunity: Opportunity) -> None:
    """Set opportunity status to approved when a draft is approved."""
    _sync_opportunity_status(
        opportunity,
        OpportunityStatus.approved,
        "Envoyer le message manuellement puis marquer l'envoi comme effectué.",
    )


def sync_opportunity_to_draft_needed(opportunity: Opportunity) -> None:
    """Set opportunity status to draft_needed when a draft is rejected."""
    _sync_opportunity_status(
        opportunity,
        OpportunityStatus.draft_needed,
        "Corriger ou régénérer le brouillon avant nouvelle validation.",
    )


def sync_opportunity_to_follow_up_needed(opportunity: Opportunity) -> None:
    """Set opportunity status to follow_up_needed when a draft is marked as sent manually."""
    _sync_opportunity_status(
        opportunity,
        OpportunityStatus.follow_up_needed,
        "Message envoyé manuellement — suivre la relance planifiée.",
    )


def sync_opportunity_after_follow_up_done(opportunity: Opportunity) -> None:
    """Set opportunity status to sent when a follow-up is marked done.

    Only applies if the opportunity is not in a terminal state.
    """
    _sync_opportunity_status(
        opportunity,
        OpportunityStatus.sent,
        "Relance effectuée — attendre une réponse ou planifier une nouvelle action.",
    )


def sync_opportunity_after_follow_up_cancelled(opportunity: Opportunity) -> None:
    """Set opportunity status to closed when a follow-up is cancelled.

    Only applies if the opportunity is not in a terminal state.
    """
    _sync_opportunity_status(
        opportunity,
        OpportunityStatus.closed,
        "Suivi annulé — opportunité clôturée ou à réévaluer.",
    )
