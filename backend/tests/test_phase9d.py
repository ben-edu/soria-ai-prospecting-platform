"""Phase 9D — SourceRecord / Import Provenance UX.

Tests for:
- list empty
- get invalid UUID returns 400
- get missing UUID returns 404
- list after importing candidate through Phase 9B endpoint
- filter by source_name
- filter by source_type
- filter by external_id
- filter by processed
- search by external_id
- search by processing_notes
- raw_payload is returned
- linked_company_id is extracted
- linked_opportunity_id is extracted
- source-record endpoints are read-only
- no MessageDraft, FollowUp, ComplianceEvent is created by source-record endpoints
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session

from app.models.compliance_event import ComplianceEvent
from app.models.follow_up import FollowUp
from app.models.message_draft import MessageDraft
from app.models.source_record import SourceRecord

# ---------------------------------------------------------------------------
# Helper
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

_FT_CANDIDATE_2 = {
    **_FT_CANDIDATE,
    "external_id": "fr-002",
    "title": "Architecte Cloud",
    "raw_payload": {
        "provider": "france_travail",
        "external_id": "fr-002",
        "title": "Architecte Cloud",
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


def _count(db: Session, model) -> int:
    return len(db.query(model).all())


def _import_candidate(client, candidate: dict):
    return client.post(
        "/api/v1/external-sources/import-candidate",
        json=candidate,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListEmpty:
    """List source-records when none exist."""

    def test_list_empty(self, client):
        resp = client.get("/api/v1/source-records")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["skip"] == 0
        assert data["limit"] == 50


class TestGetErrors:
    """Error cases for get by ID."""

    def test_invalid_uuid_returns_400(self, client):
        resp = client.get("/api/v1/source-records/not-a-uuid")
        assert resp.status_code == 400
        assert "Invalid" in resp.json()["detail"]

    def test_missing_uuid_returns_404(self, client):
        resp = client.get(
            "/api/v1/source-records/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]


class TestAfterImport:
    """List and get after importing a candidate through the Phase 9B endpoint."""

    def test_list_after_import(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        resp = client.get("/api/v1/source-records")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["source_name"] == "france_travail"
        assert item["external_id"] == "fr-001"
        assert item["processed"] is True
        assert item["source_type"] == "france_travail"

    def test_get_by_id(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        list_resp = client.get("/api/v1/source-records")
        sr_id = list_resp.json()["items"][0]["id"]

        resp = client.get(f"/api/v1/source-records/{sr_id}")
        assert resp.status_code == 200
        item = resp.json()
        assert item["id"] == sr_id
        assert item["source_name"] == "france_travail"
        assert item["external_id"] == "fr-001"

    def test_raw_payload_is_returned(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        list_resp = client.get("/api/v1/source-records")
        item = list_resp.json()["items"][0]
        assert item["raw_payload"] is not None
        assert item["raw_payload"]["provider"] == "france_travail"
        assert item["raw_payload"]["external_id"] == "fr-001"
        assert "Ingénieur" in item["raw_payload"]["title"]


class TestFilters:
    """Filtering source-records by various criteria."""

    def test_filter_by_source_name(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        _import_candidate(client, _ADZUNA_CANDIDATE)

        resp = client.get("/api/v1/source-records?source_name=france_travail")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["source_name"] == "france_travail"

    def test_filter_by_source_type(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        _import_candidate(client, _ADZUNA_CANDIDATE)

        resp = client.get("/api/v1/source-records?source_type=france_travail")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["source_type"] == "france_travail"

    def test_filter_by_external_id(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        _import_candidate(client, _FT_CANDIDATE_2)

        resp = client.get("/api/v1/source-records?external_id=fr-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["external_id"] == "fr-001"

    def test_filter_by_processed_true(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)

        # Add an unprocessed SourceRecord manually
        sr = SourceRecord(
            source_name="manual_test",
            external_id="manual-001",
            source_type="manual",
            imported_at=datetime.now(timezone.utc),
            processed=False,
        )
        db_session.add(sr)
        db_session.commit()

        resp = client.get("/api/v1/source-records?processed=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        for item in data["items"]:
            assert item["processed"] is True

    def test_filter_by_processed_false(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)

        sr = SourceRecord(
            source_name="manual_test",
            external_id="manual-001",
            source_type="manual",
            imported_at=datetime.now(timezone.utc),
            processed=False,
        )
        db_session.add(sr)
        db_session.commit()

        resp = client.get("/api/v1/source-records?processed=false")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["external_id"] == "manual-001"
        assert data["items"][0]["processed"] is False


class TestSearch:
    """Global search across source-record fields."""

    def test_search_by_external_id(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        _import_candidate(client, _ADZUNA_CANDIDATE)

        resp = client.get("/api/v1/source-records?search=fr-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["external_id"] == "fr-001"

    def test_search_by_processing_notes(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        _import_candidate(client, _ADZUNA_CANDIDATE)

        # Search for "Company" which appears in all processing_notes
        resp = client.get("/api/v1/source-records?search=Company")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_search_by_source_url(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)

        resp = client.get("/api/v1/source-records?search=example.com/fr-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["source_url"] == "https://example.com/fr-001"


class TestLinkedIds:
    """linked_company_id and linked_opportunity_id extraction."""

    def test_linked_company_id_extracted(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        list_resp = client.get("/api/v1/source-records")
        item = list_resp.json()["items"][0]
        assert item["linked_company_id"] is not None
        # Should be a valid UUID string
        UUID(item["linked_company_id"])

    def test_linked_opportunity_id_extracted(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        list_resp = client.get("/api/v1/source-records")
        item = list_resp.json()["items"][0]
        assert item["linked_opportunity_id"] is not None
        UUID(item["linked_opportunity_id"])

    def test_linked_ids_in_get(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        list_resp = client.get("/api/v1/source-records")
        sr_id = list_resp.json()["items"][0]["id"]

        resp = client.get(f"/api/v1/source-records/{sr_id}")
        item = resp.json()
        assert item["linked_company_id"] is not None
        assert item["linked_opportunity_id"] is not None
        UUID(item["linked_company_id"])
        UUID(item["linked_opportunity_id"])

    def test_linked_ids_null_without_processing_notes(self, client, db_session):
        """SourceRecords without processing_notes should have null linked_ids."""
        sr = SourceRecord(
            source_name="manual",
            source_type="manual",
            imported_at=datetime.now(timezone.utc),
            processing_notes=None,
        )
        db_session.add(sr)
        db_session.commit()

        list_resp = client.get("/api/v1/source-records")
        # The manual one has most recent imported_at, so it should be first
        item = list_resp.json()["items"][0]
        assert item["linked_company_id"] is None
        assert item["linked_opportunity_id"] is None


class TestReadOnly:
    """Source-record endpoints must not create any side-effect records."""

    def test_list_is_read_only(self, client, db_session):
        resp = client.get("/api/v1/source-records")
        assert resp.status_code == 200
        assert _count(db_session, MessageDraft) == 0
        assert _count(db_session, FollowUp) == 0
        assert _count(db_session, ComplianceEvent) == 0

    def test_get_is_read_only(self, client, db_session):
        _import_candidate(client, _FT_CANDIDATE)
        list_resp = client.get("/api/v1/source-records")
        sr_id = list_resp.json()["items"][0]["id"]

        msg_count_before = _count(db_session, MessageDraft)
        fu_count_before = _count(db_session, FollowUp)
        ce_count_before = _count(db_session, ComplianceEvent)

        resp = client.get(f"/api/v1/source-records/{sr_id}")
        assert resp.status_code == 200

        assert _count(db_session, MessageDraft) == msg_count_before
        assert _count(db_session, FollowUp) == fu_count_before
        assert _count(db_session, ComplianceEvent) == ce_count_before

    def test_no_write_endpoints(self, client):
        """POST, PATCH, DELETE should not exist for source-records."""
        resp = client.post("/api/v1/source-records", json={})
        assert resp.status_code in (405, 404)

        resp = client.patch(
            "/api/v1/source-records/00000000-0000-0000-0000-000000000000",
            json={},
        )
        assert resp.status_code in (405, 404)

        resp = client.delete(
            "/api/v1/source-records/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code in (405, 404)
