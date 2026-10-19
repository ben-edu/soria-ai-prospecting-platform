import uuid

from app.models.offer import Offer
from app.scripts.import_mvcs3c_shortlist import (
    APPROVED_SHORTLIST,
    IMPORT_BATCH,
    build_candidate_models,
)
from app.services.mvcs_b2b import (
    B2B_QUALIFICATION_THRESHOLD,
    DIAGNOSTIC_SLUG,
    INDUSTRIALISATION_SLUG,
    RELIABILITY_SLUG,
    qualify_mvcs_b2b,
    select_mvcs_offer_slug,
)

EXPECTED_ROUTES = {
    "mvcs3c-shotgun": RELIABILITY_SLUG,
    "mvcs3c-parallel": RELIABILITY_SLUG,
    "mvcs3c-amo": RELIABILITY_SLUG,
    "mvcs3c-my-job-glasses": RELIABILITY_SLUG,
    "mvcs3c-xxii-group": INDUSTRIALISATION_SLUG,
    "mvcs3c-modulotech": RELIABILITY_SLUG,
    "mvcs3c-implicity": RELIABILITY_SLUG,
    "mvcs3c-trustbuilder": INDUSTRIALISATION_SLUG,
    "mvcs3c-adlin-science": RELIABILITY_SLUG,
    "mvcs3c-stoik": DIAGNOSTIC_SLUG,
}


def _offer(slug: str) -> Offer:
    return Offer(
        category_id=uuid.uuid4(),
        name=slug,
        slug=slug,
        landing_page_url=f"https://soria-ai.fr/solutions/{slug}/",
        is_active=True,
    )


def test_approved_shortlist_is_exactly_ten_unique_human_approved_candidates():
    assert len(APPROVED_SHORTLIST) == 10
    assert len({item["slug"] for item in APPROVED_SHORTLIST}) == 10
    assert len({item["source_url"] for item in APPROVED_SHORTLIST}) == 10
    assert IMPORT_BATCH == "mvcs3c-approved-2026-10-18"


def test_every_approved_candidate_routes_and_qualifies_without_contact_points():
    for candidate in APPROVED_SHORTLIST:
        company, opportunity = build_candidate_models(candidate)
        route = select_mvcs_offer_slug(opportunity)

        assert route == EXPECTED_ROUTES[candidate["slug"]]

        result = qualify_mvcs_b2b(
            opportunity,
            company,
            contact=None,
            matched_offer=_offer(route),
        )

        assert result["qualified"] is True
        assert result["score"] >= B2B_QUALIFICATION_THRESHOLD
        assert result["breakdown"]["icp_fit"] == 35
        assert result["breakdown"]["offer_hypothesis_fit"] == 20
        assert result["breakdown"]["contactability"] == 0
        assert "hypoth" in opportunity.detected_need.lower()
        assert "vendor intent is not established" in opportunity.detected_need.lower()
        assert opportunity.source_url


def test_undated_conservative_scores_match_the_production_arithmetic():
    expected = {
        "mvcs3c-shotgun": 81,
        "mvcs3c-parallel": 81,
        "mvcs3c-amo": 81,
        "mvcs3c-xxii-group": 81,
        "mvcs3c-modulotech": 81,
        "mvcs3c-trustbuilder": 81,
        "mvcs3c-adlin-science": 82,
        "mvcs3c-stoik": 81,
    }

    for candidate in APPROVED_SHORTLIST:
        if candidate["slug"] not in expected:
            continue

        company, opportunity = build_candidate_models(candidate)
        route = select_mvcs_offer_slug(opportunity)
        result = qualify_mvcs_b2b(opportunity, company, None, _offer(route))

        assert opportunity.source_published_at is None
        assert result["score"] == expected[candidate["slug"]]
