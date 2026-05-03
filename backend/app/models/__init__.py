"""Import all models so Alembic can detect them."""

from app.models.academy_category import AcademyCategory
from app.models.academy_resource import AcademyResource
from app.models.company import Company
from app.models.compliance_event import ComplianceEvent
from app.models.contact import Contact
from app.models.follow_up import FollowUp
from app.models.interaction import Interaction
from app.models.message_draft import MessageDraft
from app.models.offer import Offer
from app.models.opportunity import Opportunity
from app.models.opportunity_score import OpportunityScore
from app.models.service_category import ServiceCategory
from app.models.source_record import SourceRecord

__all__ = [
    "Company",
    "Contact",
    "ServiceCategory",
    "Offer",
    "AcademyCategory",
    "AcademyResource",
    "Opportunity",
    "OpportunityScore",
    "MessageDraft",
    "FollowUp",
    "Interaction",
    "ComplianceEvent",
    "SourceRecord",
]
