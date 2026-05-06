"""Phase 6D — synchronize Opportunity.status and Opportunity.next_action with
the MessageDraft workflow."""

from app.core.enums import OpportunityStatus


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


def _setup_company_contact_opportunity(client, status=None):
    """Create a company, contact, and opportunity linked together."""
    company_resp = _create_company(client)
    assert company_resp.status_code == 201
    company_id = company_resp.json()["id"]

    contact_resp = _create_contact(client, company_id)
    assert contact_resp.status_code == 201
    contact_id = contact_resp.json()["id"]

    opp_payload = {"contact_id": contact_id}
    if status:
        opp_payload["status"] = status
    opp_resp = _create_opportunity(client, company_id, **opp_payload)
    assert opp_resp.status_code == 201
    opp_id = opp_resp.json()["id"]

    return company_id, contact_id, opp_id


def _get_opportunity(client, opp_id):
    resp = client.get(f"/api/v1/opportunities/{opp_id}")
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# 1) Create manual draft → opportunity status = draft_ready
# ---------------------------------------------------------------------------


def test_create_manual_draft_sets_opportunity_draft_ready(client):
    """Creating a manual MessageDraft sets opportunity status to draft_ready."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    resp = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Bonjour, test...",
        },
    )
    assert resp.status_code == 201

    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == OpportunityStatus.draft_ready.value
    assert opp["next_action"] == "Relire le brouillon et le soumettre à validation humaine."


# ---------------------------------------------------------------------------
# 2) generate-draft → opportunity status = draft_ready
# ---------------------------------------------------------------------------


def test_generate_draft_sets_opportunity_draft_ready(client):
    """generate-draft sets opportunity status to draft_ready."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert resp.status_code == 200

    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == OpportunityStatus.draft_ready.value
    assert opp["next_action"] == "Relire le brouillon et le soumettre à validation humaine."


# ---------------------------------------------------------------------------
# 3) regenerate-draft → opportunity status = draft_ready
# ---------------------------------------------------------------------------


def test_regenerate_draft_sets_opportunity_draft_ready(client):
    """regenerate-draft sets opportunity status to draft_ready."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    # First generate
    client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")

    # Regenerate
    resp = client.post(f"/api/v1/opportunities/{opp_id}/regenerate-draft")
    assert resp.status_code == 200

    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == OpportunityStatus.draft_ready.value
    assert opp["next_action"] == "Relire le brouillon et le soumettre à validation humaine."


# ---------------------------------------------------------------------------
# 4) submit-review → opportunity status = waiting_validation
# ---------------------------------------------------------------------------


def test_submit_review_sets_opportunity_waiting_validation(client):
    """submit-review sets opportunity status to waiting_validation."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    # Create a manual draft
    create_resp = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Bonjour, test...",
        },
    )
    draft_id = create_resp.json()["id"]

    # Submit for review
    resp = client.post(f"/api/v1/message-drafts/{draft_id}/submit-review", json={})
    assert resp.status_code == 200

    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == OpportunityStatus.waiting_validation.value
    assert opp["next_action"] == "Valider humainement le brouillon avant tout envoi externe."


# ---------------------------------------------------------------------------
# 5) approve → opportunity status = approved
# ---------------------------------------------------------------------------


def test_approve_sets_opportunity_approved(client):
    """approve sets opportunity status to approved."""
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

    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == OpportunityStatus.approved.value
    assert opp["next_action"] == "Envoyer le message manuellement puis marquer l'envoi comme effectué."


# ---------------------------------------------------------------------------
# 6) reject → opportunity status = draft_needed
# ---------------------------------------------------------------------------


def test_reject_sets_opportunity_draft_needed(client):
    """reject sets opportunity status to draft_needed."""
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

    resp = client.post(f"/api/v1/message-drafts/{draft_id}/reject", json={})
    assert resp.status_code == 200

    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == OpportunityStatus.draft_needed.value
    assert opp["next_action"] == "Corriger ou régénérer le brouillon avant nouvelle validation."


# ---------------------------------------------------------------------------
# 7) mark-sent-manually → opportunity status = follow_up_needed
# ---------------------------------------------------------------------------


def test_mark_sent_manually_sets_opportunity_follow_up_needed(client):
    """mark-sent-manually sets opportunity status to follow_up_needed."""
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
    resp = client.post(f"/api/v1/message-drafts/{draft_id}/mark-sent-manually")
    assert resp.status_code == 200

    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == OpportunityStatus.follow_up_needed.value
    assert opp["next_action"] == "Message envoyé manuellement — suivre la relance planifiée."


# ---------------------------------------------------------------------------
# 8) Terminal statuses (converted, lost, closed) are not downgraded
# ---------------------------------------------------------------------------


def _assert_terminal_status_not_downgraded(client, opp_id, terminal_status):
    """Verify that draft creation and workflow actions do not change a terminal status."""
    # 8a) create manual draft does not downgrade
    resp = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Should not downgrade",
        },
    )
    assert resp.status_code == 201
    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == terminal_status, f"Manual draft changed {terminal_status}"

    # 8b) generate-draft does not downgrade
    resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert resp.status_code == 200
    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == terminal_status, f"generate-draft changed {terminal_status}"

    # 8c) regenerate-draft does not downgrade
    resp = client.post(f"/api/v1/opportunities/{opp_id}/regenerate-draft")
    assert resp.status_code == 200
    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == terminal_status, f"regenerate-draft changed {terminal_status}"

    # 8d) submit-review does not downgrade (create a draft first, then submit)
    create_resp = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Review test",
        },
    )
    draft_id = create_resp.json()["id"]
    resp = client.post(f"/api/v1/message-drafts/{draft_id}/submit-review", json={})
    assert resp.status_code == 200
    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == terminal_status, f"submit-review changed {terminal_status}"

    # 8e) approve does not downgrade (create a draft in needs_review, then approve)
    create_resp2 = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Approve test",
            "status": "needs_review",
        },
    )
    draft_id2 = create_resp2.json()["id"]
    resp = client.post(f"/api/v1/message-drafts/{draft_id2}/approve", json={})
    assert resp.status_code == 200
    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == terminal_status, f"approve changed {terminal_status}"

    # 8f) reject does not downgrade (create a draft in needs_review, then reject)
    create_resp3 = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Reject test",
            "status": "needs_review",
        },
    )
    draft_id3 = create_resp3.json()["id"]
    resp = client.post(f"/api/v1/message-drafts/{draft_id3}/reject", json={})
    assert resp.status_code == 200
    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == terminal_status, f"reject changed {terminal_status}"

    # 8g) mark-sent-manually does not downgrade
    create_resp4 = client.post(
        "/api/v1/message-drafts",
        json={
            "opportunity_id": opp_id,
            "body": "Mark sent test",
            "status": "needs_review",
        },
    )
    draft_id4 = create_resp4.json()["id"]
    resp = client.post(f"/api/v1/message-drafts/{draft_id4}/approve", json={})
    assert resp.status_code == 200
    resp = client.post(f"/api/v1/message-drafts/{draft_id4}/mark-sent-manually")
    assert resp.status_code == 200
    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == terminal_status, f"mark-sent-manually changed {terminal_status}"


def test_converted_not_downgraded(client):
    """converted status is not downgraded by any message workflow action."""
    _, _, opp_id = _setup_company_contact_opportunity(client, status="converted")
    _assert_terminal_status_not_downgraded(client, opp_id, "converted")


def test_lost_not_downgraded(client):
    """lost status is not downgraded by any message workflow action."""
    _, _, opp_id = _setup_company_contact_opportunity(client, status="lost")
    _assert_terminal_status_not_downgraded(client, opp_id, "lost")


def test_closed_not_downgraded(client):
    """closed status is not downgraded by any message workflow action."""
    _, _, opp_id = _setup_company_contact_opportunity(client, status="closed")
    _assert_terminal_status_not_downgraded(client, opp_id, "closed")


# ---------------------------------------------------------------------------
# 9) Duplicate generate-draft does not create a status regression
# ---------------------------------------------------------------------------


def test_duplicate_generate_draft_no_status_regression(client):
    """Calling generate-draft twice does not regress the opportunity status."""
    _, _, opp_id = _setup_company_contact_opportunity(client)

    # First call creates draft → status becomes draft_ready
    client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == OpportunityStatus.draft_ready.value

    # Now advance to a later status via the manual workflow
    resp = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}")
    draft_id = resp.json()["items"][0]["id"]

    # Submit for review → waiting_validation
    client.post(f"/api/v1/message-drafts/{draft_id}/submit-review", json={})
    opp = _get_opportunity(client, opp_id)
    assert opp["status"] == OpportunityStatus.waiting_validation.value

    # Second generate-draft call returns the existing draft (duplicate prevention)
    # It should NOT regress the status back to draft_ready
    resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
    assert resp.status_code == 200

    opp = _get_opportunity(client, opp_id)
    # Status must remain waiting_validation, not regress to draft_ready
    assert opp["status"] == OpportunityStatus.waiting_validation.value
    assert opp["next_action"] == "Valider humainement le brouillon avant tout envoi externe."
