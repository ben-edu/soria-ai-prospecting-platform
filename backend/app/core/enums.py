import enum


class ServiceCategoryStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class CompanyType(str, enum.Enum):
    training_center = "training_center"
    school = "school"
    cfa = "cfa"
    university = "university"
    pme = "pme"
    startup = "startup"
    web_agency = "web_agency"
    it_company = "it_company"
    recruiter = "recruiter"
    public_organization = "public_organization"
    nonprofit = "nonprofit"
    enterprise = "enterprise"
    unknown = "unknown"


class CompanyStatus(str, enum.Enum):
    new = "new"
    to_review = "to_review"
    qualified = "qualified"
    not_relevant = "not_relevant"
    contacted = "contacted"
    active_opportunity = "active_opportunity"
    closed = "closed"


class ContactType(str, enum.Enum):
    director = "director"
    training_manager = "training_manager"
    it_manager = "it_manager"
    hr = "hr"
    recruiter = "recruiter"
    technical_lead = "technical_lead"
    founder = "founder"
    generic_contact = "generic_contact"
    academic_contact = "academic_contact"
    unknown = "unknown"


class EmailVerificationStatus(str, enum.Enum):
    unknown = "unknown"
    not_checked = "not_checked"
    valid = "valid"
    invalid = "invalid"
    risky = "risky"


class OpportunityType(str, enum.Enum):
    formation = "formation"
    devops_cloud = "devops_cloud"
    cybersecurity_soc = "cybersecurity_soc"
    iam_sso = "iam_sso"
    monitoring = "monitoring"
    freelance = "freelance"
    job = "job"
    academic = "academic"
    partnership = "partnership"
    academy = "academy"
    other = "other"


class OpportunityStatus(str, enum.Enum):
    new = "new"
    to_analyze = "to_analyze"
    scored = "scored"
    interesting = "interesting"
    not_relevant = "not_relevant"
    contact_to_find = "contact_to_find"
    contact_found = "contact_found"
    draft_needed = "draft_needed"
    draft_ready = "draft_ready"
    waiting_validation = "waiting_validation"
    approved = "approved"
    sent = "sent"
    follow_up_needed = "follow_up_needed"
    response_received = "response_received"
    meeting_scheduled = "meeting_scheduled"
    converted = "converted"
    lost = "lost"
    closed = "closed"


class OpportunityPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class AcademyResourceType(str, enum.Enum):
    guide = "guide"
    article = "article"
    checklist = "checklist"
    course = "course"
    lab = "lab"
    workshop = "workshop"
    project = "project"
    moodle_path = "moodle_path"
    support_material = "support_material"
    case_study = "case_study"


class AcademyLevel(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    mixed = "mixed"


class MessageType(str, enum.Enum):
    prospecting_email = "prospecting_email"
    linkedin_message = "linkedin_message"
    follow_up_email = "follow_up_email"
    training_proposal = "training_proposal"
    devops_proposal = "devops_proposal"
    cybersecurity_proposal = "cybersecurity_proposal"
    academy_invitation = "academy_invitation"
    motivation_letter = "motivation_letter"
    cv_summary = "cv_summary"
    internal_note = "internal_note"


class MessageStatus(str, enum.Enum):
    draft = "draft"
    needs_review = "needs_review"
    approved = "approved"
    rejected = "rejected"
    sent_manually = "sent_manually"
    sent_by_system = "sent_by_system"
    archived = "archived"


class FollowUpActionType(str, enum.Enum):
    send_first_message = "send_first_message"
    send_follow_up = "send_follow_up"
    call = "call"
    linkedin_manual_message = "linkedin_manual_message"
    prepare_proposal = "prepare_proposal"
    schedule_meeting = "schedule_meeting"
    update_openproject = "update_openproject"
    close_opportunity = "close_opportunity"


class FollowUpStatus(str, enum.Enum):
    planned = "planned"
    done = "done"
    cancelled = "cancelled"
    overdue = "overdue"


class InteractionType(str, enum.Enum):
    email = "email"
    linkedin = "linkedin"
    phone = "phone"
    meeting = "meeting"
    note = "note"
    system_event = "system_event"


class InteractionDirection(str, enum.Enum):
    inbound = "inbound"
    outbound = "outbound"
    internal = "internal"


class ComplianceEventType(str, enum.Enum):
    contact_collected = "contact_collected"
    email_verified = "email_verified"
    message_generated = "message_generated"
    message_approved = "message_approved"
    message_sent = "message_sent"
    opt_out_requested = "opt_out_requested"
    data_deleted = "data_deleted"


class SourceType(str, enum.Enum):
    manual = "manual"
    france_travail = "france_travail"
    company_website = "company_website"
    linkedin_manual = "linkedin_manual"
    csv = "csv"
    hunter = "hunter"
    dropcontact = "dropcontact"
    soria_website_form = "soria_website_form"
    academy = "academy"
    openproject = "openproject"
    other = "other"
