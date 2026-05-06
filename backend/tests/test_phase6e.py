"""Phase 6E — synchronize Opportunity status with FollowUp lifecycle actions."""

from app.core.enums import FollowUpStatus, OpportunityStatus


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


def _setup_follow_up(client, opportunity_status=None):
    """Create company + contact + opportunity + follow-up, return IDs."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    contact_resp = _create_contact(client, company_id)
    assert contact_resp.status_code == 201
    contact_id = contact_resp.json()["id"]

    opp_payload = {"contact_id": contact_id}
    if opportunity_status:
        opp_payload["status"] = opportunity_status
    opp_resp = _create_opportunity(client, company_id, **opp_payload)
    assert opp_resp.status_code == 201
    opp_id = opp_resp.json()["id"]

    fu_resp = client.post(
        "/api/v1/follow-ups",
        json={
            "opportunity_id": opp_id,
            "contact_id": contact_id,
            "due_date": "2026-06-01T00:00:00Z",
            "action_type": "send_follow_up",
            "status": "planned",
        },
    )
    assert fu_resp.status_code == 201
    fu_id = fu_resp.json()["id"]

    return company_id, contact_id, opp_id, fu_id


def _get_opportunity(client, opp_id):
    resp = client.get(f"/api/v1/opportunities/{opp_id}")
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# 1) mark-done sets follow_up.status = done and opportunity.status = sent
# ---------------------------------------------------------------------------


def test_mark_done_sets_follow_up_done_and_opportunity_sent(client):
    """mark-done sets follow_up.status = done and opportunity.status = sent."""
    _, _, opp_id, fu_id = _setup_follow_up(client)

    resp = client.post(f"/api/v1/follow-ups/{fu_id}/mark-done")
    assert resp.status_code == 200
    assert resp.json()["status"] == FollowUpStatus.done.value

    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == OpportunityStatus.sent.value


# ---------------------------------------------------------------------------
# 2) mark-done updates opportunity.next_action
# ---------------------------------------------------------------------------


def test_mark_done_updates_next_action(client):
    """mark-done updates opportunity.next_action appropriately."""
    _, _, opp_id, fu_id = _setup_follow_up(client)

    client.post(f"/api/v1/follow-ups/{fu_id}/mark-done")

    opp = _get_opportunity(client, opp_id)
    assert opp["next_action"] == "Relance effectuée — attendre une réponse ou planifier une nouvelle action."


# ---------------------------------------------------------------------------
# 3) cancel sets follow_up.status = cancelled and opportunity.status = closed
# ---------------------------------------------------------------------------


def test_cancel_sets_follow_up_cancelled_and_opportunity_closed(client):
    """cancel sets follow_up.status = cancelled and opportunity.status = closed."""
    _, _, opp_id, fu_id = _setup_follow_up(client)

    resp = client.post(f"/api/v1/follow-ups/{fu_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == FollowUpStatus.cancelled.value

    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == OpportunityStatus.closed.value


# ---------------------------------------------------------------------------
# 4) cancel updates opportunity.next_action
# ---------------------------------------------------------------------------


def test_cancel_updates_next_action(client):
    """cancel updates opportunity.next_action appropriately."""
    _, _, opp_id, fu_id = _setup_follow_up(client)

    client.post(f"/api/v1/follow-ups/{fu_id}/cancel")

    opp = _get_opportunity(client, opp_id)
    assert opp["next_action"] == "Suivi annulé — opportunité clôturée ou à réévaluer."


# ---------------------------------------------------------------------------
# 5) Terminal statuses are not downgraded by mark-done
# ---------------------------------------------------------------------------


def _assert_terminal_not_downgraded_by_mark_done(client, opp_id, terminal_status):
    """Verify mark-done does not change a terminal opportunity."""
    fu_resp = client.post(
        "/api/v1/follow-ups",
        json={
            "opportunity_id": opp_id,
            "contact_id": None,
            "due_date": "2026-06-01T00:00:00Z",
            "action_type": "send_follow_up",
            "status": "planned",
        },
    )
    assert fu_resp.status_code == 201
    fu_id = fu_resp.json()["id"]

    resp = client.post(f"/api/v1/follow-ups/{fu_id}/mark-done")
    assert resp.status_code == 200

    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == terminal_status


def test_converted_not_downgraded_by_mark_done(client):
    """converted opportunity is not downgraded by mark-done."""
    _, _, opp_id, fu_id = _setup_follow_up(client, opportunity_status="converted")
    _assert_terminal_not_downgraded_by_mark_done(client, opp_id, "converted")


def test_lost_not_downgraded_by_mark_done(client):
    """lost opportunity is not downgraded by mark-done."""
    _, _, opp_id, fu_id = _setup_follow_up(client, opportunity_status="lost")
    _assert_terminal_not_downgraded_by_mark_done(client, opp_id, "lost")


def test_closed_not_downgraded_by_mark_done(client):
    """closed opportunity is not changed by mark-done."""
    _, _, opp_id, fu_id = _setup_follow_up(client, opportunity_status="closed")
    _assert_terminal_not_downgraded_by_mark_done(client, opp_id, "closed")


# ---------------------------------------------------------------------------
# 6) Terminal statuses are not downgraded by cancel
# ---------------------------------------------------------------------------


def _assert_terminal_not_downgraded_by_cancel(client, opp_id, terminal_status):
    """Verify cancel does not change a terminal opportunity."""
    fu_resp = client.post(
        "/api/v1/follow-ups",
        json={
            "opportunity_id": opp_id,
            "contact_id": None,
            "due_date": "2026-06-01T00:00:00Z",
            "action_type": "send_follow_up",
            "status": "planned",
        },
    )
    assert fu_resp.status_code == 201
    fu_id = fu_resp.json()["id"]

    resp = client.post(f"/api/v1/follow-ups/{fu_id}/cancel")
    assert resp.status_code == 200

    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == terminal_status


def test_converted_not_downgraded_by_cancel(client):
    """converted opportunity is not downgraded by cancel."""
    _, _, opp_id, fu_id = _setup_follow_up(client, opportunity_status="converted")
    _assert_terminal_not_downgraded_by_cancel(client, opp_id, "converted")


def test_lost_not_downgraded_by_cancel(client):
    """lost opportunity is not downgraded by cancel."""
    _, _, opp_id, fu_id = _setup_follow_up(client, opportunity_status="lost")
    _assert_terminal_not_downgraded_by_cancel(client, opp_id, "lost")


def test_closed_not_downgraded_by_cancel(client):
    """closed opportunity is not changed by cancel."""
    _, _, opp_id, fu_id = _setup_follow_up(client, opportunity_status="closed")
    _assert_terminal_not_downgraded_by_cancel(client, opp_id, "closed")


# ---------------------------------------------------------------------------
# 7) Existing guards still work
# ---------------------------------------------------------------------------


def test_cancelled_follow_up_cannot_be_marked_done(client):
    """cancelled follow-up cannot be marked done."""
    _, _, _, fu_id = _setup_follow_up(client)

    # Cancel first
    client.post(f"/api/v1/follow-ups/{fu_id}/cancel")

    # Then try to mark done
    resp = client.post(f"/api/v1/follow-ups/{fu_id}/mark-done")
    assert resp.status_code == 400
    assert "cancelled" in resp.json()["detail"].lower()


def test_done_follow_up_cannot_be_cancelled(client):
    """done follow-up cannot be cancelled."""
    _, _, _, fu_id = _setup_follow_up(client)

    # Mark done first
    client.post(f"/api/v1/follow-ups/{fu_id}/mark-done")

    # Then try to cancel
    resp = client.post(f"/api/v1/follow-ups/{fu_id}/cancel")
    assert resp.status_code == 400
    assert "done" in resp.json()["detail"].lower()
