"""Message draft workflow API tests."""

from uuid import uuid4


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


def _create_message_draft(client, opportunity_id, **overrides):
    payload = {
        "opportunity_id": str(opportunity_id),
        "body": "Bonjour, nous souhaitons vous proposer nos services...",
    }
    payload.update(overrides)
    return client.post("/api/v1/message-drafts", json=payload)


# --- Setup helpers ---


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


# --- Tests ---


def test_create_message_draft(client):
    """Create a message draft linked to an opportunity."""
    _, contact_id, opp_id = _setup_company_contact_opportunity(client)

    resp = _create_message_draft(client, opp_id)
    assert resp.status_code == 201
    data = resp.json()
    assert data["body"] == "Bonjour, nous souhaitons vous proposer nos services..."
    assert data["opportunity_id"] == opp_id
    assert data["contact_id"] == contact_id
    assert data["status"] == "draft"
    assert data["generated_by"] == "manual"
    assert data["message_type"] == "prospecting_email"
    assert data["language"] == "fr"
    assert data["subject"] is None
    assert data["tone"] is None
    assert data["model_name"] is None
    assert data["prompt_version"] is None
    assert data["approved_at"] is None
    assert data["sent_at"] is None
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_message_draft_without_contact_id(client):
    """Create a draft without contact_id and verify it uses the opportunity's contact_id."""
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]

    contact_resp = _create_contact(client, company_id)
    contact_id = contact_resp.json()["id"]

    opp_resp = _create_opportunity(client, company_id, contact_id=contact_id)
    opp_id = opp_resp.json()["id"]

    # Create draft without contact_id
    resp = _create_message_draft(client, opp_id)
    assert resp.status_code == 201
    assert resp.json()["contact_id"] == contact_id


def test_create_message_draft_with_contact_id(client):
    """Create a draft with an explicit contact_id."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    resp = _create_message_draft(client, opp_id, subject="Test Subject", tone="formal")
    assert resp.status_code == 201
    data = resp.json()
    assert data["subject"] == "Test Subject"
    assert data["tone"] == "formal"


def test_create_message_draft_nonexistent_opportunity(client):
    """Reject create with non-existing opportunity_id."""
    resp = _create_message_draft(client, str(uuid4()))
    assert resp.status_code == 404
    assert "opportunity" in resp.json()["detail"].lower()


def test_create_message_draft_nonexistent_contact(client):
    """Reject create with non-existing contact_id."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    resp = _create_message_draft(client, opp_id, contact_id=str(uuid4()))
    assert resp.status_code == 404
    assert "contact" in resp.json()["detail"].lower()


def test_create_message_draft_wrong_company_contact(client):
    """Reject contact from another company."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    # Create a second company with a different contact
    other_company = _create_company(client, name="Other Company", domain="other.fr")
    other_company_id = other_company.json()["id"]
    other_contact = _create_contact(client, other_company_id, email="other@other.fr")
    other_contact_id = other_contact.json()["id"]

    # Try to use the other company's contact with the first opportunity
    resp = _create_message_draft(client, opp_id, contact_id=other_contact_id)
    assert resp.status_code == 400
    assert "same company" in resp.json()["detail"].lower()


def test_list_message_drafts_by_opportunity(client):
    """List message drafts filtered by opportunity_id."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    _create_message_draft(client, opp_id)
    _create_message_draft(client, opp_id, body="Second draft body")

    resp = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_list_message_drafts_by_status(client):
    """List message drafts filtered by status."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    _create_message_draft(client, opp_id)
    _create_message_draft(client, opp_id, status="needs_review", body="Needs review body")

    resp = client.get("/api/v1/message-drafts?status=draft")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_get_message_draft_by_id(client):
    """Retrieve a single message draft by ID."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id, subject="Find Me")
    draft_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/message-drafts/{draft_id}")
    assert resp.status_code == 200
    assert resp.json()["subject"] == "Find Me"


def test_get_message_draft_not_found(client):
    """Getting a non-existent draft returns 404."""
    resp = client.get(f"/api/v1/message-drafts/{uuid4()}")
    assert resp.status_code == 404


def test_get_message_draft_invalid_id(client):
    """Getting a draft with malformed ID returns 400."""
    resp = client.get("/api/v1/message-drafts/not-a-uuid")
    assert resp.status_code == 400


def test_patch_message_draft(client):
    """Update subject, body, and tone via PATCH."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id)
    draft_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/message-drafts/{draft_id}",
        json={"subject": "Updated Subject", "body": "Updated body content", "tone": "formal"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["subject"] == "Updated Subject"
    assert data["body"] == "Updated body content"
    assert data["tone"] == "formal"


def test_patch_message_draft_cannot_set_status_directly(client):
    """Verify PATCH cannot modify status directly (status is not in the schema)."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id)
    draft_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "draft"

    # Try to set status via PATCH — it should be ignored
    resp = client.patch(
        f"/api/v1/message-drafts/{draft_id}",
        json={"status": "approved", "body": "Still just a draft"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


def test_patch_message_draft_sent_or_archived_blocked(client):
    """Cannot edit a draft after it has been sent_manually."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    # Create → submit-review → approve → mark-sent-manually
    create_resp = _create_message_draft(client, opp_id, status="needs_review")
    draft_id = create_resp.json()["id"]

    client.post(f"/api/v1/message-drafts/{draft_id}/approve", json={})
    client.post(f"/api/v1/message-drafts/{draft_id}/mark-sent-manually")

    resp = client.patch(f"/api/v1/message-drafts/{draft_id}", json={"body": "Should fail"})
    assert resp.status_code == 400
    assert "sent" in resp.json()["detail"].lower()


def test_submit_draft_for_review(client):
    """Submit a draft for review (draft → needs_review)."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id)
    draft_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/submit-review", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "needs_review"


def test_submit_rejected_draft_for_review(client):
    """Submit a rejected draft for review again (rejected → needs_review)."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id, status="needs_review")
    draft_id = create_resp.json()["id"]

    client.post(f"/api/v1/message-drafts/{draft_id}/reject", json={})

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/submit-review", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "needs_review"


def test_approve_draft(client):
    """Approve a draft and verify approved_at is set."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id, status="needs_review")
    draft_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/approve", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["approved_at"] is not None


def test_approve_draft_with_review_notes(client):
    """Approve a draft and pass review_notes."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id, status="needs_review")
    draft_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/v1/message-drafts/{draft_id}/approve",
        json={"review_notes": "Looks good, ready to send"},
    )
    assert resp.status_code == 200
    assert resp.json()["review_notes"] == "Looks good, ready to send"


def test_reject_draft(client):
    """Reject a needs_review draft."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id, status="needs_review")
    draft_id = create_resp.json()["id"]

    resp = client.post(
        f"/api/v1/message-drafts/{draft_id}/reject",
        json={"review_notes": "Needs more details"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["review_notes"] == "Needs more details"


def test_mark_draft_sent_manually(client):
    """Mark an approved draft as sent and verify sent_at is set."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id, status="needs_review")
    draft_id = create_resp.json()["id"]

    client.post(f"/api/v1/message-drafts/{draft_id}/approve", json={})
    resp = client.post(f"/api/v1/message-drafts/{draft_id}/mark-sent-manually")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent_manually"
    assert data["sent_at"] is not None


def test_approve_before_needs_review_fails(client):
    """Cannot approve a draft that hasn't been submitted for review."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id)
    draft_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/approve", json={})
    assert resp.status_code == 400
    assert "needs_review" in resp.json()["detail"]


def test_mark_sent_before_approved_fails(client):
    """Cannot mark a draft as sent before it is approved."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id, status="needs_review")
    draft_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/mark-sent-manually")
    assert resp.status_code == 400
    assert "approved" in resp.json()["detail"]


def test_reject_before_needs_review_fails(client):
    """Cannot reject a draft that hasn't been submitted for review."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id)
    draft_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/reject", json={})
    assert resp.status_code == 400
    assert "needs_review" in resp.json()["detail"]


def test_create_draft_with_invalid_status_fails(client):
    """Cannot create a draft with status approved, rejected, or sent_manually."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    for invalid_status in ("approved", "rejected", "sent_manually", "sent_by_system", "archived"):
        resp = _create_message_draft(client, opp_id, status=invalid_status)
        assert resp.status_code == 422


def test_create_draft_empty_body_fails(client):
    """Cannot create a draft with empty body."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    resp = _create_message_draft(client, opp_id, body="")
    assert resp.status_code == 422

    resp = _create_message_draft(client, opp_id, body="   ")
    assert resp.status_code == 422


def test_list_message_drafts_pagination(client):
    """List message drafts with skip/limit."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    for i in range(5):
        _create_message_draft(client, opp_id, body=f"Draft body {i}")

    resp = client.get("/api/v1/message-drafts?skip=0&limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3
    assert data["total"] == 5


def test_list_message_drafts_search(client):
    """Search message drafts by subject/body content."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    _create_message_draft(client, opp_id, body="Offre de formation DevOps")
    _create_message_draft(client, opp_id, body="Proposition Cybersécurité")

    resp = client.get("/api/v1/message-drafts?search=DevOps")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp = client.get("/api/v1/message-drafts?search=Cybersécurité")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_archive_draft_from_draft(client):
    """Archive a draft from draft status."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id)
    draft_id = create_resp.json()["id"]

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/archive")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "archived"
    assert data["id"] == draft_id
    assert data["approved_at"] is None
    assert data["sent_at"] is None


def test_archive_missing_draft_returns_404(client):
    """Archive a non-existent draft returns 404."""
    resp = client.post(f"/api/v1/message-drafts/{uuid4()}/archive")
    assert resp.status_code == 404


def test_archive_sent_manually_draft_returns_400(client):
    """Archive a sent_manually draft returns 400."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id, status="needs_review")
    draft_id = create_resp.json()["id"]

    client.post(f"/api/v1/message-drafts/{draft_id}/approve", json={})
    client.post(f"/api/v1/message-drafts/{draft_id}/mark-sent-manually")

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/archive")
    assert resp.status_code == 400
    assert "sent" in resp.json()["detail"].lower()


def test_archive_already_archived_returns_400(client):
    """Archive an already archived draft returns 400."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id)
    draft_id = create_resp.json()["id"]

    client.post(f"/api/v1/message-drafts/{draft_id}/archive")

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/archive")
    assert resp.status_code == 400
    assert "already archived" in resp.json()["detail"].lower()


def test_archive_draft_preserves_approved_at_and_sent_at(client):
    """Archiving an approved draft preserves approved_at and sent_at."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    create_resp = _create_message_draft(client, opp_id, status="needs_review")
    draft_id = create_resp.json()["id"]

    client.post(f"/api/v1/message-drafts/{draft_id}/approve", json={})
    client.post(f"/api/v1/message-drafts/{draft_id}/mark-sent-manually")

    # sent_manually should be rejected, so test with approved only
    # Create a fresh approved draft
    create_resp2 = _create_message_draft(client, opp_id, status="needs_review")
    draft_id2 = create_resp2.json()["id"]

    approve_resp = client.post(f"/api/v1/message-drafts/{draft_id2}/approve", json={})
    approved_at = approve_resp.json()["approved_at"]

    archive_resp = client.post(f"/api/v1/message-drafts/{draft_id2}/archive")
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "archived"
    assert archive_resp.json()["approved_at"] == approved_at
    assert archive_resp.json()["sent_at"] is None


def test_health_endpoint_still_works(client):
    """Health endpoint still works."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"] == "SORIA AI Prospecting Platform"
