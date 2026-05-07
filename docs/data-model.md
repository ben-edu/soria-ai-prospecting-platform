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
AI-generated or manually written messages requiring human approval before sending. AI-generated drafts include audit metadata fields: `generated_by` (origin: "ai", "rule_based", "manual", "system"), `ai_provider` (e.g. "mock_ai"), `model_name`, `prompt_profile`, and `prompt_version`. Human review actions are tracked via `review_notes`, `approved_at`, and `sent_at`.

### Compliance Events
Audit trail for RGPD/legal compliance — tracks contact collection, message generation (`message_generated`), approval (`message_approved`), sending (`message_sent`), and opt-out requests.

## External Sources (Phase 9A — Not Yet Imported)

Phase 9A introduces external opportunity source search endpoints that return `ExternalOpportunityCandidate` schemas. These candidates are **not persisted** — Phase 9A is read-only. Phase 9B will import selected candidates into `SourceRecord`, `Company`, and `Opportunity`.

## Key Constraints

- Every message draft has a status lifecycle: draft → needs_review → approved/rejected → sent_manually/sent_by_system
- Opportunities have a detailed status pipeline from discovery to closure
- Follow-ups track planned actions with due dates
- Source records preserve raw imported data
