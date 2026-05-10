# MVP User Guide — SORIA AI Prospecting Platform

## Purpose

This guide describes the end-to-end MVP workflow for SORIA operators. It covers how to discover external opportunities, import candidates, review them, generate AI-assisted message drafts, complete the human validation workflow, and maintain compliance traceability.

> **Production status:** This MVP runs in **mock mode** by default (`EXTERNAL_SOURCES_MODE=mock`). Real API connectors for France Travail, Adzuna UK, and Freelancer.com are implemented and gated behind configuration — they are not active in production without explicit operator action. See [Phase 10 docs](phase-10-real-external-api-foundation.md) for details.

---

## End-to-End Workflow

```
Search External Source
        │
        ▼
Import Candidate
        │
        ▼
Review Imported Opportunity  (imported_pending_review)
        │
        ├── Mark as Interesting   → proceed to draft
        ├── Mark as Not Relevant  → discard
        └── Leave as Pending      → revisit later
                │
                ▼
        Preview AI Draft  (read-only, no data created)
                │
                ▼
        Generate AI Draft  (creates MessageDraft, compliance event)
                │
                ▼
        Submit Draft for Review
                │
                ├── Approve Draft
                │       │
                │       ▼
                │   Mark Sent Manually
                │       │
                │       ▼
                │   Follow-Up Needed  (7-day follow-up scheduled)
                │
                └── Reject Draft → revise and resubmit
```

---

## Step-by-Step Instructions

### 1. Search External Sources

**Purpose:** Discover potential prospects from job boards and freelance marketplaces.

**How to:**

1. Navigate to the **Cockpit** → **External Sources** resource
2. Select a provider from the available list:
   - **France Travail** (mock) — French job board (DevOps, cloud, training roles)
   - **Adzuna UK** (mock) — UK job aggregation
   - **Freelancer.com** (mock) — Global freelance marketplace
3. Enter a search query (e.g. "DevOps", "cloud architect")
4. Optionally enter a location filter
5. Click **Search**

**What you see:**

- Each provider lists its mode (`mock`) and credential status
- Search results display as candidate cards with title, company, location, and source details
- The `raw_payload` field contains the full source data for audit purposes

> **Note:** In production (mock mode), results are deterministic — the same query always returns the same results. Real API searches require `EXTERNAL_SOURCES_MODE=live` and valid credentials.

### 2. Import a Candidate

**Purpose:** Bring an external opportunity into SORIA as a tracked record.

**How to:**

1. From the search results, click **Import** on a candidate
2. The system creates three linked records:
   - **SourceRecord** — provenance record with raw payload and external ID
   - **Company** — looked up by name + country, or created if new
   - **Opportunity** — with status `imported_pending_review`

**What happens:**

- Duplicate prevention: if the same `(source_name, external_id)` pair already exists, the system returns the existing records with a `duplicate_detected` warning
- The opportunity is created with `status = imported_pending_review`, ready for human review
- A SourceRecord is created with full provenance data for compliance

### 3. Review an Imported Opportunity

**Purpose:** Evaluate whether an imported opportunity is worth pursuing.

**How to:**

1. Go to **Opportunities** in the Cockpit
2. Apply the status filter: **Imported — Pending Review** (`imported_pending_review`)
3. Click on an opportunity to view its details
4. Review the title, description, location, company, and source provenance
5. Look for the orange warning badge indicating "Imported — Pending Review"

**Key information available:**

- Opportunity title and description
- Linked company details
- Source URL and publication date
- Import provenance (SourceRecord external ID, provider name, import timestamp)
- Raw source payload

### 4. Mark as Interesting or Not Relevant

**Purpose:** Decide which imported opportunities to pursue.

**How to — Mark as Interesting:**

1. Open the opportunity detail view
2. Click **Edit**
3. Set **Status** to `interesting`
4. Save

**How to — Mark as Not Relevant:**

1. Open the opportunity detail view
2. Click **Edit**
3. Set **Status** to `not_relevant`
4. Save

**What happens next:**

- **Interesting:** The opportunity is now active and ready for AI draft generation
- **Not relevant:** The opportunity is archived from the active workflow
- The status can be changed later if needed

### 5. Preview an AI Draft

**Purpose:** See what an AI-generated message would look like before creating a draft.

**How to:**

1. Open an opportunity with status `interesting` (or any status that permits drafts)
2. Click **AI Draft Preview**
3. A dialog shows:
   - **Subject** — the proposed email subject line
   - **Body** — the proposed email content
   - **Safety note** — informational banner about human validation requirements
   - **Provider metadata** — which AI provider generated it

**Important:**

- This is **read-only** — no data is created, no draft is saved, no compliance event is logged
- You can preview as many times as needed
- The preview is deterministic in mock mode (same result every time)

### 6. Generate an AI Draft

**Purpose:** Create an AI-generated MessageDraft that can go through the human review workflow.

**How to:**

1. Open an opportunity
2. Click **Generate AI Draft**
3. The system creates:
   - A **MessageDraft** with `generated_by = "ai"`, `status = draft`
   - A **ComplianceEvent** of type `message_generated`

**Duplicate prevention:**

- If an active AI draft already exists for this opportunity, the system returns the existing draft (no duplicate created)
- Use **Regenerate** to create a new draft (archives the old one after success)

### 7. Submit a Draft for Review

**Purpose:** Signal that a draft is ready for approval or rejection.

**How to:**

1. Navigate to **Message Drafts** in the Cockpit
2. Open the draft you want to submit
3. In the **WorkflowPanel**, click **Submit for Review**
4. Optionally add review notes
5. Confirm

**What happens:**

- Draft status changes from `draft` to `needs_review`
- The parent opportunity status syncs to `waiting_validation`
- The draft is now in the approval queue

### 8. Approve a Draft

**Purpose:** Give explicit human approval for the draft content.

**How to:**

1. Open a draft with status `needs_review`
2. In the **WorkflowPanel**, click **Approve**
3. Optionally add review notes
4. Confirm

**What happens:**

- Draft status changes from `needs_review` to `approved`
- `approved_at` timestamp is recorded
- A **ComplianceEvent** of type `message_approved` is created
- The parent opportunity status syncs to `approved`

**If you reject instead:**

- Draft status changes from `needs_review` to `rejected`
- Parent opportunity status syncs to `draft_needed`
- You can revise and resubmit via **Submit for Review**

### 9. Mark as Sent Manually

**Purpose:** Record that the approved message was sent outside the platform (e.g. via email client).

**How to:**

1. Open an approved draft
2. In the **WorkflowPanel**, click **Mark Sent Manually**
3. Confirm the explicit warning that no actual email is sent

**What happens:**

- Draft status changes from `approved` to `sent_manually`
- `sent_at` timestamp is recorded
- A **ComplianceEvent** of type `message_sent` is created
- A 7-day **FollowUp** is automatically scheduled
- Parent opportunity status syncs to `follow_up_needed`

> **Warning:** SORIA does not send emails. "Mark Sent Manually" is a record-keeping action — you must send the actual message through your email client.

### 10. Follow-Up Needed

**Purpose:** Track opportunities that need follow-up attention after the initial message was sent.

**How to:**

1. Filter opportunities by status `follow_up_needed`
2. Review the scheduled follow-up date (7 days after manual send)
3. When ready, update the status manually (e.g. to `closed_won` or `closed_lost`)

**What you see:**

- The **FollowUp** record shows the scheduled date and completion status
- The opportunity status `follow_up_needed` persists until manually changed

### 11. Compliance Traceability

**Purpose:** Every action in the workflow is logged for audit and compliance.

**Compliance events recorded:**

| Action | Compliance Event Type | Records |
|--------|----------------------|---------|
| AI draft generated | `message_generated` | Who generated, which provider, timestamp |
| Draft approved | `message_approved` | Who approved, timestamp, optional notes |
| Draft sent (manual) | `message_sent` | Who recorded send, timestamp |

**SourceRecord provenance:**

Each import creates a SourceRecord with:
- Source provider name
- External ID from the source system
- Full raw payload (complete source API response)
- Import timestamp

**MessageDraft audit fields:**

| Field | Description |
|-------|-------------|
| `generated_by` | Origin: `ai`, `manual`, `rule_based`, or `system` |
| `ai_provider` | Provider name (e.g. `mock_ai`) |
| `model_name` | Model name (e.g. `mock-soria-v1`) |
| `prompt_profile` | Prompt profile identifier |
| `prompt_version` | Prompt version identifier |
| `review_notes` | Human notes from submit, approve, or reject |
| `approved_at` | Timestamp of human approval |
| `sent_at` | Timestamp of manual send |

---

## Safety Rules

1. **No automated external messages** — Every external communication requires explicit human approval
2. **No automatic email sending** — The platform records manual sends but does not integrate with any email provider
3. **Mock mode by default** — External source API calls use deterministic mock data unless `EXTERNAL_SOURCES_MODE=live` + valid credentials are configured
4. **Real connectors are gated** — France Travail, Adzuna UK, and Freelancer live connectors exist but are inactive by default
5. **Duplicate prevention** — Re-importing the same external candidate returns existing records, not duplicates
6. **All contact collection is logged** — SourceRecord provenance captures every import for compliance

---

## Known Limitations (MVP)

| Area | Limitation |
|------|-----------|
| **External sources** | Running in mock mode; real API credentials not enabled in production |
| **AI drafts** | Using `mock_ai` deterministic provider; no real OpenAI/Claude integration |
| **Email sending** | No email integration; all sends are recorded manually |
| **Data persistence** | Runtime validation test data still present in database |
| **External enrichment** | No Hunter.io, Dropcontact, or website scraping yet |
| **Scoring** | Basic opportunity scoring; no LLM-based qualification |
