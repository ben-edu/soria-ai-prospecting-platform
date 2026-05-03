"""Tests for enum imports and values."""

from app.core.enums import (
    AcademyLevel,
    AcademyResourceType,
    CompanyStatus,
    CompanyType,
    ComplianceEventType,
    ContactType,
    EmailVerificationStatus,
    FollowUpActionType,
    FollowUpStatus,
    InteractionDirection,
    InteractionType,
    MessageStatus,
    MessageType,
    OpportunityPriority,
    OpportunityStatus,
    OpportunityType,
    ServiceCategoryStatus,
    SourceType,
)


def test_service_category_status_values():
    assert ServiceCategoryStatus.active.value == "active"
    assert ServiceCategoryStatus.inactive.value == "inactive"


def test_company_type_has_expected_values():
    expected = {
        "training_center", "school", "cfa", "university", "pme",
        "startup", "web_agency", "it_company", "recruiter",
        "public_organization", "nonprofit", "enterprise", "unknown",
    }
    actual = {e.value for e in CompanyType}
    assert actual == expected


def test_company_status_values():
    expected = {
        "new", "to_review", "qualified", "not_relevant",
        "contacted", "active_opportunity", "closed",
    }
    actual = {e.value for e in CompanyStatus}
    assert actual == expected


def test_opportunity_status_values():
    expected = {
        "new", "to_analyze", "scored", "interesting", "not_relevant",
        "contact_to_find", "contact_found", "draft_needed", "draft_ready",
        "waiting_validation", "approved", "sent", "follow_up_needed",
        "response_received", "meeting_scheduled", "converted", "lost", "closed",
    }
    actual = {e.value for e in OpportunityStatus}
    assert actual == expected


def test_source_type_values():
    expected = {
        "manual", "france_travail", "company_website", "linkedin_manual",
        "csv", "hunter", "dropcontact", "soria_website_form",
        "academy", "openproject", "other",
    }
    actual = {e.value for e in SourceType}
    assert actual == expected


def test_all_enums_importable():
    """Verify all enum classes are importable (catches syntax/import issues)."""
    assert AcademyLevel
    assert AcademyResourceType
    assert CompanyStatus
    assert CompanyType
    assert ComplianceEventType
    assert ContactType
    assert EmailVerificationStatus
    assert FollowUpActionType
    assert FollowUpStatus
    assert InteractionDirection
    assert InteractionType
    assert MessageStatus
    assert MessageType
    assert OpportunityPriority
    assert OpportunityStatus
    assert OpportunityType
    assert ServiceCategoryStatus
    assert SourceType
