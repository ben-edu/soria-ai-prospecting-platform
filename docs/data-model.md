# Data Model

## Entity-Relationship Overview

```
ServiceCategory ──1:N── Offer
AcademyCategory ──1:N── AcademyResource

Company ──1:N── Contact
Company ──1:N── Opportunity
Company ──1:N── ComplianceEvent

Contact ──1:N── Opportunity
Contact ──1:N── MessageDraft
Contact ──1:N── FollowUp
Contact ──1:N── Interaction
Contact ──1:N── ComplianceEvent

Opportunity ──1:N── OpportunityScore
Opportunity ──1:N── MessageDraft
Opportunity ──1:N── FollowUp
Opportunity ──1:N── Interaction
Opportunity ──1:N── ComplianceEvent
```

## Core Entities

### Companies
Target organizations (training centers, schools, companies, etc.)

### Contacts
People within companies. Track email verification status, opt-out preferences.

### Opportunities
Prospecting opportunities linked to a company, optionally to a contact, offer, or academy resource.

### Service Categories & Offers
What SORIA sells — training, DevOps, cloud, security services.

### Academy Categories & Resources
Learning content available through SORIA Academy.

### Message Drafts
AI-generated or manually written messages requiring human approval before sending.

### Compliance Events
Audit trail for RGPD/legal compliance — tracks contact collection, message generation, approval, sending, and opt-out requests.

## Key Constraints

- Every message draft has a status lifecycle: draft → needs_review → approved/rejected → sent_manually/sent_by_system
- Opportunities have a detailed status pipeline from discovery to closure
- Follow-ups track planned actions with due dates
- Source records preserve raw imported data
