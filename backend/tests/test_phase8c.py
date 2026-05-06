"""Phase 8C — AI Draft Audit Metadata tests.

Covers persistence of ai_provider and prompt_profile on MessageDraft
records across AI generation, regeneration, manual creation, and
read-only preview.
"""

def _create_company(client, **overrides):
    payload = {
        "name": "Phase8C Company",
        "domain": "phase8c.fr",
        "city": "Paris",
        "country": "France",
        "source": "manual",
        "status": "new",
        "company_type": "unknown",
    }
    payload.update(overrides)
    return client.post("/api/v1/companies", json=payload)


def _create_contact(client, company_id, **overrides):
    payload = {
        "company_id": str(company_id),
        "first_name": "Alice",
        "last_name": "Martin",
        "full_name": "Alice Martin",
        "role_title": "CTO",
        "email": "alice@phase8c.fr",
        "source": "manual",
        "contact_type": "director",
    }
    payload.update(overrides)
    return client.post("/api/v1/contacts", json=payload)


def _create_opportunity(client, company_id, **overrides):
    payload = {
        "company_id": str(company_id),
        "title": "Phase 8C Test Opportunity",
        "opportunity_type": "devops_cloud",
        "source": "manual",
    }
    payload.update(overrides)
    return client.post("/api/v1/opportunities", json=payload)


# ---------------------------------------------------------------------------
# TestGenerateAiDraftMetadata
# ---------------------------------------------------------------------------


class TestGenerateAiDraftMetadata:
    """POST /api/v1/opportunities/{id}/generate-ai-draft metadata."""

    def test_stores_all_ai_metadata(self, client):
        """AI draft stores generated_by='ai', ai_provider='mock_ai',
        model_name='mock-soria-v1', prompt_profile='prospecting_fr_v1',
        prompt_version='ai-draft-v1'."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert resp.status_code == 200
        data = resp.json()

        assert data["generated_by"] == "ai"
        assert data["ai_provider"] == "mock_ai"
        assert data["model_name"] == "mock-soria-v1"
        assert data["prompt_profile"] == "prospecting_fr_v1"
        assert data["prompt_version"] == "ai-draft-v1"

    def test_duplicate_returns_existing_with_metadata(self, client):
        """Second generate-ai-draft returns same draft with same metadata."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        r1 = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert r1.status_code == 200
        r2 = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert r2.status_code == 200

        assert r2.json()["id"] == r1.json()["id"]
        # Only one MessageDraft exists
        drafts = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}")
        assert drafts.status_code == 200
        assert drafts.json()["total"] == 1

    def test_duplicate_does_not_create_second_compliance_event(self, client):
        """Duplicate prevention does not create a second ComplianceEvent."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")

        events = client.get("/api/v1/compliance-events").json()
        matching = [
            e
            for e in events["items"]
            if e["event_type"] == "message_generated"
            and e["opportunity_id"] == str(opp_id)
        ]
        assert len(matching) == 1

    def test_contact_link_preserved(self, client):
        """Draft links to the opportunity contact."""
        c_resp = _create_company(client)
        contact_resp = _create_contact(client, c_resp.json()["id"])
        contact_id = contact_resp.json()["id"]

        o_resp = _create_opportunity(
            client, c_resp.json()["id"], contact_id=contact_id,
        )
        opp_id = o_resp.json()["id"]

        resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert resp.status_code == 200
        assert resp.json()["contact_id"] == str(contact_id)


# ---------------------------------------------------------------------------
# TestRegenerateAiDraftMetadata
# ---------------------------------------------------------------------------


class TestRegenerateAiDraftMetadata:
    """POST /api/v1/opportunities/{id}/regenerate-ai-draft metadata."""

    def test_new_draft_stores_full_metadata(self, client):
        """Regenerated AI draft stores all audit metadata."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        resp = client.post(
            f"/api/v1/opportunities/{opp_id}/regenerate-ai-draft",
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["generated_by"] == "ai"
        assert data["ai_provider"] == "mock_ai"
        assert data["model_name"] == "mock-soria-v1"
        assert data["prompt_profile"] == "prospecting_fr_v1"
        assert data["prompt_version"] == "ai-draft-v1"

    def test_old_draft_keeps_metadata_after_archival(self, client):
        """Archived AI draft retains its original metadata."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        old = client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")
        assert old.status_code == 200
        old_id = old.json()["id"]

        client.post(f"/api/v1/opportunities/{opp_id}/regenerate-ai-draft")

        # Fetch old draft directly
        old_draft = client.get(f"/api/v1/message-drafts/{old_id}")
        assert old_draft.status_code == 200
        data = old_draft.json()

        assert data["status"] == "archived"
        assert data["generated_by"] == "ai"
        assert data["ai_provider"] == "mock_ai"
        assert data["model_name"] == "mock-soria-v1"
        assert data["prompt_profile"] == "prospecting_fr_v1"
        assert data["prompt_version"] == "ai-draft-v1"


# ---------------------------------------------------------------------------
# TestManualDraftNullMetadata
# ---------------------------------------------------------------------------


class TestManualDraftNullMetadata:
    """Manual MessageDraft creation without ai_provider/prompt_profile."""

    def test_manual_draft_returns_null_for_new_fields(self, client):
        """Manual draft without ai_provider/prompt_profile returns null
        for both fields."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.post(
            "/api/v1/message-drafts",
            json={
                "opportunity_id": str(opp_id),
                "body": "Test body content",
                "generated_by": "manual",
            },
        )
        assert resp.status_code == 201
        data = resp.json()

        assert data["generated_by"] == "manual"
        assert data["ai_provider"] is None
        assert data["prompt_profile"] is None
        assert data["model_name"] is None
        assert data["prompt_version"] is None

    def test_manual_draft_with_explicit_null(self, client):
        """Explicitly passing null values works the same."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.post(
            "/api/v1/message-drafts",
            json={
                "opportunity_id": str(opp_id),
                "body": "Another test body",
                "generated_by": "manual",
                "ai_provider": None,
                "prompt_profile": None,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["ai_provider"] is None
        assert resp.json()["prompt_profile"] is None


# ---------------------------------------------------------------------------
# TestRuleBasedDraftNullMetadata
# ---------------------------------------------------------------------------


class TestRuleBasedDraftNullMetadata:
    """rule_based generate-draft still returns null for AI metadata."""

    def test_rule_based_draft_returns_null_ai_fields(self, client):
        """Rule-based draft has ai_provider=null and prompt_profile=null."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
        assert resp.status_code == 200
        data = resp.json()

        assert data["generated_by"] == "rule_based"
        assert data["ai_provider"] is None
        assert data["prompt_profile"] is None

    def test_rule_based_regenerate_returns_null_ai_fields(self, client):
        """Regenerated rule-based draft has ai_provider=null and
        prompt_profile=null."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        client.post(f"/api/v1/opportunities/{opp_id}/generate-draft")
        resp = client.post(
            f"/api/v1/opportunities/{opp_id}/regenerate-draft",
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["generated_by"] == "rule_based"
        assert data["ai_provider"] is None
        assert data["prompt_profile"] is None


# ---------------------------------------------------------------------------
# TestListAndGetMessageDraftsIncludeNewFields
# ---------------------------------------------------------------------------


class TestListAndGetMessageDraftsIncludeNewFields:
    """list and get message-drafts include ai_provider and prompt_profile."""

    def test_list_includes_new_fields(self, client):
        """GET /message-drafts returns ai_provider and prompt_profile."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        # Create an AI draft
        client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")

        # List all drafts
        resp = client.get("/api/v1/message-drafts")
        assert resp.status_code == 200
        items = resp.json()["items"]

        assert len(items) >= 1
        for item in items:
            assert "ai_provider" in item
            assert "prompt_profile" in item

        # Find the AI draft
        ai_drafts = [d for d in items if d["generated_by"] == "ai"]
        assert len(ai_drafts) >= 1
        assert ai_drafts[0]["ai_provider"] == "mock_ai"
        assert ai_drafts[0]["prompt_profile"] == "prospecting_fr_v1"

    def test_list_filtered_includes_new_fields(self, client):
        """Filtered list returns new fields."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        client.post(f"/api/v1/opportunities/{opp_id}/generate-ai-draft")

        resp = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] == 1
        assert data["items"][0]["ai_provider"] == "mock_ai"
        assert data["items"][0]["prompt_profile"] == "prospecting_fr_v1"

    def test_get_single_includes_new_fields(self, client):
        """GET /message-drafts/{id} returns ai_provider and prompt_profile."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        draft = client.post(
            f"/api/v1/opportunities/{opp_id}/generate-ai-draft",
        )
        draft_id = draft.json()["id"]

        resp = client.get(f"/api/v1/message-drafts/{draft_id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["ai_provider"] == "mock_ai"
        assert data["prompt_profile"] == "prospecting_fr_v1"


# ---------------------------------------------------------------------------
# TestAiDraftPreviewReadOnly
# ---------------------------------------------------------------------------


class TestAiDraftPreviewReadOnly:
    """ai-draft-preview remains read-only."""

    def test_preview_does_not_create_message_draft(self, client):
        """GET ai-draft-preview does not create a MessageDraft."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        # Verify no drafts exist before
        before = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}")
        assert before.json()["total"] == 0

        # Call preview
        preview = client.get(
            f"/api/v1/opportunities/{opp_id}/ai-draft-preview",
        )
        assert preview.status_code == 200

        # Verify no drafts created
        after = client.get(f"/api/v1/message-drafts?opportunity_id={opp_id}")
        assert after.json()["total"] == 0

    def test_preview_does_not_create_compliance_event(self, client):
        """GET ai-draft-preview does not create a ComplianceEvent."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        events_before = client.get("/api/v1/compliance-events").json()

        client.get(f"/api/v1/opportunities/{opp_id}/ai-draft-preview")

        events_after = client.get("/api/v1/compliance-events").json()
        assert events_after["total"] == events_before["total"]

    def test_preview_does_not_mutate_opportunity(self, client):
        """GET ai-draft-preview does not mutate the opportunity."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(
            client, c_resp.json()["id"],
            status="new", score=None,
        )
        opp_id = o_resp.json()["id"]

        original = client.get(f"/api/v1/opportunities/{opp_id}").json()

        client.get(f"/api/v1/opportunities/{opp_id}/ai-draft-preview")

        after = client.get(f"/api/v1/opportunities/{opp_id}").json()
        assert after == original

    def test_preview_returns_prompt_profile(self, client):
        """GET ai-draft-preview returns prompt_profile field."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.get(
            f"/api/v1/opportunities/{opp_id}/ai-draft-preview",
        )
        assert resp.status_code == 200
        assert resp.json()["prompt_profile"] == "prospecting_fr_v1"

    def test_preview_returns_provider_metadata(self, client):
        """GET ai-draft-preview returns provider, model_name,
        prompt_version."""
        c_resp = _create_company(client)
        o_resp = _create_opportunity(client, c_resp.json()["id"])
        opp_id = o_resp.json()["id"]

        resp = client.get(
            f"/api/v1/opportunities/{opp_id}/ai-draft-preview",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "mock_ai"
        assert data["model_name"] == "mock-soria-v1"
        assert data["prompt_version"] == "ai-draft-v1"
