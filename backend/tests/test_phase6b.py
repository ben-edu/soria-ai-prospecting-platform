"""Phase 6B — FollowUp + ComplianceEvent MVP tests."""

from uuid import uuid4


def _create_company(client, **overrides):
    payload = {
        "name": "Test Company",
        "domain": "testcompany.fr",
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
        "full_name": "Jean Dupont",
        "email": "jean@testcompany.fr",
        "source": "manual",
        "contact_type": "director",
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


def _create_follow_up(client, opportunity_id, **overrides):
    from datetime import datetime, timezone

    payload = {
        "opportunity_id": str(opportunity_id),
        "due_date": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(overrides)
    return client.post("/api/v1/follow-ups", json=payload)


# ---------------------------------------------------------------------------
# FollowUp tests
# ---------------------------------------------------------------------------


def test_create_follow_up_with_opportunity(client):
    """Create a follow-up with a valid opportunity."""
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]
    opp_resp = _create_opportunity(client, company_id)
    opp_id = opp_resp.json()["id"]

    resp = _create_follow_up(client, opp_id)
    assert resp.status_code == 201
    data = resp.json()
    assert data["opportunity_id"] == opp_id
    assert data["status"] == "planned"
    assert data["action_type"] == "send_follow_up"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_follow_up_with_contact_from_same_company(client):
    """Create follow-up with contact belonging to the same company as opportunity."""
    company_resp = _create_company(client)
    company_id = company_resp.json()["id"]
    contact_resp = _create_contact(client, company_id)
    contact_id = contact_resp.json()["id"]
    opp_resp = _create_opportunity(client, company_id, contact_id=contact_id)
    opp_id = opp_resp.json()["id"]

    resp = _create_follow_up(client, opp_id, contact_id=str(contact_id))
    assert resp.status_code == 201
    data = resp.json()
    assert data["contact_id"] == contact_id


def test_reject_follow_up_with_contact_from_another_company(client):
    """Follow-up with contact from another company must be rejected."""
    company_a = _create_company(client, name="Company A", domain="a.fr").json()["id"]
    company_b = _create_company(client, name="Company B", domain="b.fr").json()["id"]

    contact_b = _create_contact(client, company_b).json()["id"]
    opp_a = _create_opportunity(client, company_a).json()["id"]

    resp = _create_follow_up(client, opp_a, contact_id=str(contact_b))
    assert resp.status_code == 400
    assert "same company" in resp.json()["detail"].lower()


def test_create_follow_up_missing_opportunity_returns_404(client):
    """Creating a follow-up with a non-existent opportunity should 404."""
    resp = _create_follow_up(client, str(uuid4()))
    assert resp.status_code == 404


def test_list_follow_ups_filtered_by_opportunity(client):
    """List follow-ups filtered by opportunity_id."""
    company = _create_company(client).json()["id"]
    opp1 = _create_opportunity(client, company).json()["id"]
    opp2 = _create_opportunity(client, company, title="Cybersecurity").json()["id"]

    _create_follow_up(client, opp1)
    _create_follow_up(client, opp1)
    _create_follow_up(client, opp2)

    resp = client.get(f"/api/v1/follow-ups?opportunity_id={opp1}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_patch_follow_up(client):
    """Update a follow-up via PATCH."""
    company = _create_company(client).json()["id"]
    opp = _create_opportunity(client, company).json()["id"]
    fu = _create_follow_up(client, opp).json()

    resp = client.patch(
        f"/api/v1/follow-ups/{fu['id']}",
        json={"notes": "Updated notes", "action_type": "call"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"] == "Updated notes"
    assert data["action_type"] == "call"
    # other fields unchanged
    assert data["status"] == "planned"


def test_mark_done(client):
    """Mark a planned follow-up as done."""
    company = _create_company(client).json()["id"]
    opp = _create_opportunity(client, company).json()["id"]
    fu = _create_follow_up(client, opp).json()

    resp = client.post(f"/api/v1/follow-ups/{fu['id']}/mark-done")
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


def test_cannot_cancel_done_follow_up(client):
    """Cannot cancel a follow-up that is already done."""
    company = _create_company(client).json()["id"]
    opp = _create_opportunity(client, company).json()["id"]
    fu = _create_follow_up(client, opp).json()

    client.post(f"/api/v1/follow-ups/{fu['id']}/mark-done")

    resp = client.post(f"/api/v1/follow-ups/{fu['id']}/cancel")
    assert resp.status_code == 400
    assert "already done" in resp.json()["detail"].lower()


def test_cancel_planned_follow_up(client):
    """Cancel a planned follow-up."""
    company = _create_company(client).json()["id"]
    opp = _create_opportunity(client, company).json()["id"]
    fu = _create_follow_up(client, opp).json()

    resp = client.post(f"/api/v1/follow-ups/{fu['id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_get_missing_follow_up_returns_404(client):
    """Get a non-existent follow-up returns 404."""
    resp = client.get(f"/api/v1/follow-ups/{uuid4()}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# ComplianceEvent tests
# ---------------------------------------------------------------------------


def _create_compliance_event(client, **overrides):
    payload = {
        "event_type": "manual",
    }
    payload.update(overrides)

    # Convert UUIDs to strings if needed
    for key in ("company_id", "contact_id", "opportunity_id"):
        if key in payload and payload[key] is not None:
            payload[key] = str(payload[key])

    return client.post("/api/v1/compliance-events", json=payload)


def test_create_compliance_event_with_all_links(client):
    """Create a compliance event with company, contact, and opportunity."""
    company = _create_company(client).json()["id"]
    contact = _create_contact(client, company).json()["id"]
    opp = _create_opportunity(client, company).json()["id"]

    resp = _create_compliance_event(
        client,
        company_id=company,
        contact_id=contact,
        opportunity_id=opp,
        event_type="contact_collected",
        reason_for_contact="Prospection initiale",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["company_id"] == company
    assert data["contact_id"] == contact
    assert data["opportunity_id"] == opp
    assert data["event_type"] == "contact_collected"
    assert data["source"] == "manual"
    assert "id" in data
    assert "created_at" in data


def test_reject_compliance_event_without_linked_entity(client):
    """Compliance event without any linked entity must be rejected."""
    resp = _create_compliance_event(client, event_type="email_verified")
    assert resp.status_code == 400
    assert "at least one" in resp.json()["detail"].lower()


def test_reject_compliance_event_different_companies(client):
    """Reject compliance event where contact and opportunity are from different companies."""
    company_a = _create_company(client, name="A", domain="a.fr").json()["id"]
    company_b = _create_company(client, name="B", domain="b.fr").json()["id"]
    contact_a = _create_contact(client, company_a).json()["id"]
    opp_b = _create_opportunity(client, company_b).json()["id"]

    resp = _create_compliance_event(
        client,
        contact_id=contact_a,
        opportunity_id=opp_b,
        event_type="email_verified",
    )
    assert resp.status_code == 400
    assert "same company" in resp.json()["detail"].lower()


def test_list_compliance_events_filtered_by_opportunity(client):
    """List compliance events filtered by opportunity_id."""
    company = _create_company(client).json()["id"]
    opp1 = _create_opportunity(client, company).json()["id"]
    opp2 = _create_opportunity(client, company, title="Security").json()["id"]

    _create_compliance_event(client, opportunity_id=opp1, event_type="email_verified")
    _create_compliance_event(client, opportunity_id=opp1, event_type="contact_collected", reason_for_contact="test")
    _create_compliance_event(client, opportunity_id=opp2, event_type="email_verified")

    resp = client.get(f"/api/v1/compliance-events?opportunity_id={opp1}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_list_compliance_events_filtered_by_event_type(client):
    """List compliance events filtered by event_type."""
    company = _create_company(client).json()["id"]
    opp = _create_opportunity(client, company).json()["id"]

    _create_compliance_event(client, opportunity_id=opp, event_type="email_verified")
    _create_compliance_event(client, opportunity_id=opp, event_type="opt_out_requested")

    resp = client.get("/api/v1/compliance-events?event_type=email_verified")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_get_missing_compliance_event_returns_404(client):
    """Get a non-existent compliance event returns 404."""
    resp = client.get(f"/api/v1/compliance-events/{uuid4()}")
    assert resp.status_code == 404


def test_require_reason_for_contact_for_message_generated(client):
    """reason_for_contact is required for event_type message_generated."""
    company = _create_company(client).json()["id"]
    resp = _create_compliance_event(
        client,
        company_id=company,
        event_type="message_generated",
    )
    assert resp.status_code == 400
    assert "reason_for_contact" in resp.json()["detail"].lower()


def test_require_reason_for_contact_for_message_approved(client):
    """reason_for_contact is required for event_type message_approved."""
    company = _create_company(client).json()["id"]
    resp = _create_compliance_event(
        client,
        company_id=company,
        event_type="message_approved",
    )
    assert resp.status_code == 400
    assert "reason_for_contact" in resp.json()["detail"].lower()


def test_require_reason_for_contact_for_message_sent(client):
    """reason_for_contact is required for event_type message_sent."""
    company = _create_company(client).json()["id"]
    resp = _create_compliance_event(
        client,
        company_id=company,
        event_type="message_sent",
    )
    assert resp.status_code == 400
    assert "reason_for_contact" in resp.json()["detail"].lower()


def test_require_reason_for_contact_for_contact_collected(client):
    """reason_for_contact is required for event_type contact_collected."""
    company = _create_company(client).json()["id"]
    resp = _create_compliance_event(
        client,
        company_id=company,
        event_type="contact_collected",
    )
    assert resp.status_code == 400
    assert "reason_for_contact" in resp.json()["detail"].lower()
