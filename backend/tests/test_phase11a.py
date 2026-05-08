"""Phase 11A — Imported Opportunity Review Workflow.

Covers:
- New imported opportunity gets imported_pending_review status
- Duplicate import does not overwrite existing opportunity status
- Manual status update survives duplicate import
- Search endpoints remain read-only (no DB mutation)
- Phase 9B / 10C behavior remains safe
"""

from app.core.enums import OpportunityStatus
from app.models.company import Company
from app.models.opportunity import Opportunity
from app.models.source_record import SourceRecord

# ---------------------------------------------------------------------------
# Sample candidate
# ---------------------------------------------------------------------------

_FT_CANDIDATE = {
    "provider": "france_travail",
    "external_id": "fr-001",
    "source_kind": "job",
    "title": "Ingénieur DevOps",
    "company_name": "TechCorp France",
    "description": "Recherche ingénieur DevOps expérimenté.",
    "location": "Paris",
    "country": "FR",
    "language": "fr",
    "source_url": "https://example.com/fr-001",
    "source_published_at": "2025-06-01T00:00:00+00:00",
    "contract_type": "CDI",
    "remote_type": "hybrid",
    "budget_min": None,
    "budget_max": None,
    "budget_currency": None,
    "tags": ["devops", "cloud", "ci/cd", "kubernetes"],
    "raw_payload": {
        "provider": "france_travail",
        "external_id": "fr-001",
        "title": "Ingénieur DevOps",
    },
}

_ADZUNA_CANDIDATE = {
    "provider": "adzuna_uk",
    "external_id": "uk-001",
    "source_kind": "job",
    "title": "DevOps Engineer",
    "company_name": "CloudBase Ltd",
    "description": "Build and maintain CI/CD pipelines and K8s.",
    "location": "London",
    "country": "GB",
    "language": "en",
    "source_url": "https://example.com/uk-001",
    "source_published_at": "2025-07-01T00:00:00+00:00",
    "contract_type": "permanent",
    "remote_type": "hybrid",
    "budget_min": None,
    "budget_max": None,
    "budget_currency": None,
    "tags": ["devops", "kubernetes", "ci/cd"],
    "raw_payload": {
        "provider": "adzuna_uk",
        "external_id": "uk-001",
        "title": "DevOps Engineer",
    },
}

_FREELANCER_CANDIDATE = {
    "provider": "freelancer",
    "external_id": "fl-001",
    "source_kind": "freelance_project",
    "title": "Kubernetes Cluster Setup and Migration",
    "company_name": "GlobalTech GmbH",
    "description": "Set up a production-grade Kubernetes cluster.",
    "location": "Remote",
    "country": "GLOBAL",
    "language": "en",
    "source_url": "https://example.com/fl-001",
    "source_published_at": "2025-08-01T00:00:00+00:00",
    "contract_type": "project",
    "remote_type": "remote",
    "budget_min": 3000.0,
    "budget_max": 8000.0,
    "budget_currency": "EUR",
    "tags": ["kubernetes", "devops", "migration", "cloud"],
    "raw_payload": {
        "provider": "freelancer",
        "external_id": "fl-001",
        "title": "Kubernetes Cluster Setup",
    },
}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestImportedOpportunityStatus:
    """Newly imported opportunities get imported_pending_review status."""

    def test_france_travail_import_gets_imported_pending_review(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp is not None
        assert opp.status == OpportunityStatus.imported_pending_review

    def test_adzuna_uk_import_gets_imported_pending_review(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_ADZUNA_CANDIDATE,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp.status == OpportunityStatus.imported_pending_review

    def test_freelancer_import_gets_imported_pending_review(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FREELANCER_CANDIDATE,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp.status == OpportunityStatus.imported_pending_review

    def test_status_is_imported_pending_review_not_new(self, client, db_session):
        """Verify that imported opportunities do NOT get 'new' status."""
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp.status != OpportunityStatus.new

    def test_response_contains_status(self, client):
        """Verify the API response includes the new status."""
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["opportunity"]["status"] == "imported_pending_review"


class TestDuplicateImportPreservesStatus:
    """Duplicate import must NOT overwrite the existing opportunity status."""

    def test_duplicate_keeps_existing_status(self, client, db_session):
        # First import
        resp1 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp1.status_code == 200

        opp = db_session.query(Opportunity).first()
        assert opp.status == OpportunityStatus.imported_pending_review

        # Second import (duplicate)
        resp2 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["duplicate_detected"] is True

        # Status must not have been touched
        opp_after = db_session.query(Opportunity).first()
        assert opp_after.status == OpportunityStatus.imported_pending_review

    def test_duplicate_with_manually_changed_status(self, client, db_session):
        """If user changed status after import, duplicate must not revert it."""
        # First import
        resp1 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp1.status_code == 200
        opp = db_session.query(Opportunity).first()

        # Manually change status (simulates human review)
        opp.status = OpportunityStatus.interesting
        db_session.add(opp)
        db_session.commit()

        # Duplicate import
        resp2 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["duplicate_detected"] is True

        # Status must remain interesting (not reverted)
        opp_after = db_session.query(Opportunity).first()
        assert opp_after.status == OpportunityStatus.interesting

    def test_duplicate_does_not_create_new_opportunity(self, client, db_session):
        """Duplicate returns existing opportunity, does not create a new one."""
        resp1 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp1.status_code == 200
        opp1_id = resp1.json()["opportunity"]["id"]

        resp2 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp2.status_code == 200
        opp2_id = resp2.json()["opportunity"]["id"]

        # Same opportunity returned
        assert opp2_id == opp1_id
        assert db_session.query(Opportunity).count() == 1

    def test_duplicate_no_new_source_record(self, client, db_session):
        """Duplicate must not create a new SourceRecord."""
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert db_session.query(SourceRecord).count() == 1

        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert db_session.query(SourceRecord).count() == 1

    def test_duplicate_no_new_company(self, client, db_session):
        """Duplicate must not create a new Company."""
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert db_session.query(Company).count() == 1

        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert db_session.query(Company).count() == 1

    def test_duplicate_flags_no_new_records(self, client, db_session):
        """Duplicate response flags all created_* as False."""
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )

        resp2 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        data2 = resp2.json()
        assert data2["created_source_record"] is False
        assert data2["created_company"] is False
        assert data2["created_opportunity"] is False
        assert data2["duplicate_detected"] is True


class TestPhase9BBehaviorSafe:
    """Phase 9B behavior remains safe after Phase 11A changes."""

    def test_notes_still_contain_provenance(self, client, db_session):
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        opp = db_session.query(Opportunity).first()
        assert opp.notes is not None
        assert "provider=france_travail" in opp.notes
        assert "external_id=fr-001" in opp.notes

    def test_no_side_effects(self, client, db_session):
        from app.models.compliance_event import ComplianceEvent
        from app.models.follow_up import FollowUp
        from app.models.message_draft import MessageDraft

        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert db_session.query(MessageDraft).count() == 0
        assert db_session.query(FollowUp).count() == 0
        assert db_session.query(ComplianceEvent).count() == 0

    def test_unknown_provider_still_returns_400(self, client):
        payload = {**_FT_CANDIDATE, "provider": "non_existent"}
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload,
        )
        assert resp.status_code == 400
        assert "non_existent" in resp.json()["detail"]

    def test_company_reuse_still_works(self, client, db_session):
        payload_2 = {**_FT_CANDIDATE, "external_id": "fr-002", "title": "Architecte Cloud"}
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert db_session.query(Company).count() == 1

        resp2 = client.post(
            "/api/v1/external-sources/import-candidate",
            json=payload_2,
        )
        assert resp2.status_code == 200
        assert db_session.query(Company).count() == 1
        assert resp2.json()["created_company"] is False


class TestPhase10CBehaviorSafe:
    """Phase 10C behavior remains safe after Phase 11A changes."""

    def test_mock_search_still_works(self, client):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_providers_endpoint_still_works(self, client):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200
        assert resp.json()["mock_only"] is True

    def test_combined_search_still_works(self, client):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={"providers": "france_travail,adzuna_uk", "query": "devops"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0


class TestSearchReadOnly:
    """Search endpoints remain read-only (no DB mutation)."""

    def test_providers_no_db_mutation(self, client, db_session):
        resp = client.get("/api/v1/external-sources/providers")
        assert resp.status_code == 200
        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0

    def test_single_search_no_db_mutation(self, client, db_session):
        resp = client.get(
            "/api/v1/external-sources/france_travail/search",
            params={"query": "devops"},
        )
        assert resp.status_code == 200
        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0

    def test_combined_search_no_db_mutation(self, client, db_session):
        resp = client.get(
            "/api/v1/external-sources/search",
            params={"providers": "france_travail,adzuna_uk", "query": "devops"},
        )
        assert resp.status_code == 200
        assert db_session.query(SourceRecord).count() == 0
        assert db_session.query(Company).count() == 0
        assert db_session.query(Opportunity).count() == 0

    def test_opportunity_list_no_mutation(self, client, db_session):
        """The opportunity list endpoint is read-only."""
        resp = client.get("/api/v1/opportunities")
        assert resp.status_code == 200
        assert db_session.query(Opportunity).count() == 0


class TestStatusFiltering:
    """Opportunities can be filtered by status including imported_pending_review."""

    def test_filter_by_imported_pending_review(self, client, db_session):
        # Create an imported opportunity
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )

        # Filter by the new status
        resp = client.get(
            "/api/v1/opportunities",
            params={"status": "imported_pending_review"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "imported_pending_review"

    def test_filter_by_other_status_excludes_imported(self, client, db_session):
        # Create an imported opportunity
        client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )

        # Filter by 'new' — no imported should appear
        resp = client.get(
            "/api/v1/opportunities",
            params={"status": "new"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0


class TestScoringDoesNotAdvanceImported:
    """Scoring an imported_pending_review opportunity does not auto-advance status."""

    def test_score_does_not_change_imported_status(self, client, db_session):
        # Import
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        assert resp.status_code == 200
        opp_id = resp.json()["opportunity"]["id"]

        # Score
        resp = client.post(f"/api/v1/opportunities/{opp_id}/score")
        assert resp.status_code == 200

        # Status must still be imported_pending_review
        # (only 'new' is auto-advanced to 'scored')
        opp = db_session.query(Opportunity).first()
        assert opp.status == OpportunityStatus.imported_pending_review

    def test_score_still_updates_score_field(self, client, db_session):
        """Scoring still computes a score, just doesn't change status."""
        resp = client.post(
            "/api/v1/external-sources/import-candidate",
            json=_FT_CANDIDATE,
        )
        opp_id = resp.json()["opportunity"]["id"]

        resp = client.post(f"/api/v1/opportunities/{opp_id}/score")
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] > 0
