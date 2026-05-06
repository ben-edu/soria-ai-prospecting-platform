"""Phase 6C — connect message workflow actions to ComplianceEvent and FollowUp records."""



def _create_company(client, **overrides):
    payload = {
        "name": "Test Company",
        "domain": "testcompany.fr",
        "city": "Paris",
        "source": "manual",
        "status": "new",
        "company_type": "unknown",
        "country": "France",
    }
    payload.update(overrides)
    return client.post("/api/v1/companies", json=payload)


def _create_contact(client, company_id, **overrides):
    payload = {
        "company_id": str(company_id),
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "jean.dupont@example.com",
        "contact_type": "director",
        "source": "manual",
    }
    payload.update(overrides)
    return client.post("/api/v1/contacts", json=payload)


def _create_opportunity(client, company_id, **overrides):
    payload = {
        "company_id": str(company_id),
        "title": "Formation DevOps",
        "opportunity_type": "devops_cloud",
        "source": "manual",
    }
    payload.update(overrides)
    return client.post("/api/v1/opportunities", json=payload)


def _setup_company_contact_opportunity(client):
    """Create a company, contact, and opportunity linked together."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    contact_resp = _create_contact(client, company_id)
    assert contact_resp.status_code == 201
    contact_id = contact_resp.json()["id"]

    opp_resp = _create_opportunity(client, company_id, contact_id=contact_id)
    assert opp_resp.status_code == 201
    opp_id = opp_resp.json()["id"]

    return company_id, contact_id, opp_id


def _count_compliance_events(client):
    """Return total number of compliance events."""
    resp = client.get("/api/v1/compliance-events")
    assert resp.status_code == 200
    return resp.json()["total"]


def _count_follow_ups(client):
    """Return total number of follow-ups."""
    resp = client.get("/api/v1/follow-ups")
    assert resp.status_code == 200
    return resp.json()["total"]


# ---------------------------------------------------------------------------
# Manual draft creation → message_generated ComplianceEvent
# ---------------------------------------------------------------------------


def test_create_message_draft_creates_message_generated_event(client):
    """Creating a manual message draft creates one message_generated ComplianceEvent."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    resp = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Bonjour, test...",
        },
    )
    assert resp.status_code == 201

    # Verify one compliance event was created
    assert _count_compliance_events(client) == 1

    # Verify it has the right event_type
    list_resp = client.get("/api/v1/compliance-events")
    events = list_resp.json()["items"]
    assert events[0]["event_type"] == "message_generated"
    assert events[0]["reason_for_contact"] is not None
    assert events[0]["professional_relevance"] is not None
    assert events[0]["notes"] is not None


# ---------------------------------------------------------------------------
# generate-draft → message_generated ComplianceEvent
# ---------------------------------------------------------------------------


def test_generate_draft_creates_message_generated_event(client):
    """generate-draft creates one message_generated ComplianceEvent."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert resp.status_code == 200

    assert _count_compliance_events(client) == 1

    list_resp = client.get("/api/v1/compliance-events")
    events = list_resp.json()["items"]
    assert events[0]["event_type"] == "message_generated"
    assert events[0]["opportunity_id"] == opp_id


def test_generate_draft_duplicate_does_not_create_second_event(client):
    """generate-draft duplicate prevention does not create a second ComplianceEvent."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    # First call creates the draft + event
    client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert _count_compliance_events(client) == 1

    # Second call returns existing draft, should NOT create a new event
    resp2 = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert resp2.status_code == 200

    assert _count_compliance_events(client) == 1


# ---------------------------------------------------------------------------
# regenerate-draft → message_generated ComplianceEvent
# ---------------------------------------------------------------------------


def test_regenerate_draft_creates_message_generated_event(client):
    """regenerate-draft creates a new message_generated ComplianceEvent for the new draft."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    # Create first draft (1 event)
    client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert _count_compliance_events(client) == 1

    # Regenerate (should create 1 new event for the new draft)
    resp = client.post(f"/api/v1/opportunities/{opp_id}/regenerate-draft")
    assert resp.status_code == 200

    assert _count_compliance_events(client) == 2


# ---------------------------------------------------------------------------
# approve draft → message_approved ComplianceEvent
# ---------------------------------------------------------------------------


def _promote_to_needs_review(client, draft_id):
    """Helper: submit a draft for review."""
    return client.post(f"/api/v1/message-drafts/{draft_id}/submit-review", json={})


def test_approve_draft_creates_message_approved_event(client):
    """Approve draft creates message_approved ComplianceEvent."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Bonjour, test...",
            "status": "needs_review",
        },
    )
    draft_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/approve", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # Should have 1 message_generated (from create) + 1 message_approved
    assert _count_compliance_events(client) == 2

    list_resp = client.get("/api/v1/compliance-events?event_type=message_approved")
    assert list_resp.json()["total"] == 1
    event = list_resp.json()["items"][0]
    assert event["reason_for_contact"] is not None
    assert event["professional_relevance"] is not None
    assert event["notes"] is not None


# ---------------------------------------------------------------------------
# mark-sent-manually → message_sent ComplianceEvent + FollowUp
# ---------------------------------------------------------------------------


def test_mark_sent_manually_creates_message_sent_event(client):
    """mark-sent-manually creates message_sent ComplianceEvent."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Bonjour, test...",
            "status": "needs_review",
        },
    )
    draft_id = create_resp.json()["id"]

    # Approve first
    client.post(f"/api/v1/message-drafts/{draft_id}/approve", json={})

    # Mark sent
    resp = client.post(f"/api/v1/message-drafts/{draft_id}/mark-sent-manually")
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent_manually"

    # Should have 3 events: message_generated + message_approved + message_sent
    assert _count_compliance_events(client) == 3

    list_resp = client.get("/api/v1/compliance-events?event_type=message_sent")
    assert list_resp.json()["total"] == 1
    event = list_resp.json()["items"][0]
    assert event["reason_for_contact"] is not None
    assert event["professional_relevance"] is not None
    assert event["notes"] is not None


def test_mark_sent_manually_creates_planned_follow_up(client):
    """mark-sent-manually creates one planned FollowUp."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Bonjour, test...",
            "status": "needs_review",
        },
    )
    draft_id = create_resp.json()["id"]

    client.post(f"/api/v1/message-drafts/{draft_id}/approve", json={})
    client.post(f"/api/v1/message-drafts/{draft_id}/mark-sent-manually")

    assert _count_follow_ups(client) == 1

    list_resp = client.get("/api/v1/follow-ups")
    fu = list_resp.json()["items"][0]
    assert fu["opportunity_id"] == opp_id
    assert fu["action_type"] == "send_follow_up"
    assert fu["status"] == "planned"
    assert fu["due_date"] is not None
    assert fu["notes"] == "Automatically scheduled after manual message send."


def test_mark_sent_manually_does_not_duplicate_follow_up(client):
    """mark-sent-manually does not create duplicate planned FollowUp if one exists."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    # Create and fully promote a draft to sent_manually
    create_resp = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Bonjour, test...",
            "status": "needs_review",
        },
    )
    draft_id_1 = create_resp.json()["id"]

    client.post(f"/api/v1/message-drafts/{draft_id_1}/approve", json={})
    client.post(f"/api/v1/message-drafts/{draft_id_1}/mark-sent-manually")

    assert _count_follow_ups(client) == 1

    # Create a second draft for the same opportunity and send it
    create_resp2 = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Second message body...",
            "status": "needs_review",
        },
    )
    draft_id_2 = create_resp2.json()["id"]

    client.post(f"/api/v1/message-drafts/{draft_id_2}/approve", json={})
    resp = client.post(f"/api/v1/message-drafts/{draft_id_2}/mark-sent-manually")
    assert resp.status_code == 200

    # Should still be 1 follow-up (duplicate prevented)
    assert _count_follow_ups(client) == 1


# ---------------------------------------------------------------------------
# Existing message workflow tests must still pass (smoke check)
# ---------------------------------------------------------------------------


def test_approve_before_needs_review_still_fails(client):
    """Existing guard: cannot approve a draft that hasn't been submitted for review."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Test body",
        },
    )
    draft_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/approve", json={})
    assert resp.status_code == 400
    assert "needs_review" in resp.json()["detail"]


def test_mark_sent_before_approved_still_fails(client):
    """Existing guard: cannot mark as sent before approved."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Test body",
            "status": "needs_review",
        },
    )
    draft_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/mark-sent-manually")
    assert resp.status_code == 400
    assert "approved" in resp.json()["detail"]
