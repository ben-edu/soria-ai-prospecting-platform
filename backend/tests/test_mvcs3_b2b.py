import uuid
from datetime import datetime, timezone

from app.core.enums import CompanyType, ContactType, OpportunityType, SourceType
from app.models.company import Company
from app.models.contact import Contact
from app.models.offer import Offer
from app.models.opportunity import Opportunity
from app.services.ai_prompt_builder import build_prompt_context, infer_draft_type
from app.services.mvcs_b2b import (
    B2B_QUALIFICATION_THRESHOLD,
    DIAGNOSTIC_SLUG,
    INDUSTRIALISATION_SLUG,
    RELIABILITY_SLUG,
    qualify_mvcs_b2b,
    select_mvcs_offer_slug,
)


def _company() -> Company:
    return Company(
        name="Example SaaS",
        website_url="https://example.test",
        domain="example.test",
        company_type=CompanyType.it_company,
        sector="SaaS software platform",
        country="France",
    )


def _opportunity(text: str) -> Opportunity:
    company = _company()
    return Opportunity(
        company_id=company.id,
        title=text,
        opportunity_type=OpportunityType.devops_cloud,
        description=(
            "Signal public observé sur le site de l'entreprise concernant son "
            "évolution plateforme et ses pratiques DevOps."
        ),
        detected_need=(
            "Hypothèse : une capacité ponctuelle peut aider à cadrer le sujet, "
            "sans présumer d'un besoin de prestataire externe."
        ),
        source=SourceType.company_website,
        source_url="https://example.test/engineering/signal",
        source_published_at=datetime.now(timezone.utc),
    )


def _offer(slug: str, name: str) -> Offer:
    return Offer(
        category_id=uuid.uuid4(),
        name=name,
        slug=slug,
        landing_page_url=f"https://soria-ai.fr/solutions/{slug}/",
        is_active=True,
    )


def test_offer_selection_uses_specific_signal_then_safe_diagnostic_default():
    assert select_mvcs_offer_slug(_opportunity("CI/CD release automation")) == INDUSTRIALISATION_SLUG
    assert select_mvcs_offer_slug(_opportunity("SRE production reliability")) == RELIABILITY_SLUG
    assert select_mvcs_offer_slug(_opportunity("Platform capacity evolution")) == DIAGNOSTIC_SLUG


def test_b2b_qualification_reaches_threshold_only_with_auditable_evidence():
    company = _company()
    opportunity = _opportunity("Kubernetes platform evolution")
    opportunity.company_id = company.id
    contact = Contact(
        company_id=company.id,
        full_name="Alex Example",
        role_title="CTO",
        contact_type=ContactType.technical_lead,
        email="alex@example.test",
        linkedin_url="https://www.linkedin.com/in/example",
    )
    offer = _offer(DIAGNOSTIC_SLUG, "Diagnostic déploiement & infrastructure")

    result = qualify_mvcs_b2b(opportunity, company, contact, offer)

    assert result["score"] >= B2B_QUALIFICATION_THRESHOLD
    assert result["qualified"] is True
    assert set(result["breakdown"]) == {
        "icp_fit",
        "public_signal",
        "offer_hypothesis_fit",
        "contactability",
        "evidence_quality",
    }
    assert sum(result["breakdown"].values()) == result["score"]


def test_b2b_prompt_is_soria_first_and_hypothesis_safe_even_for_hiring_signal():
    company = _company()
    opportunity = _opportunity("Recrutement DevOps / Platform Engineer")
    opportunity.company_id = company.id
    offer = _offer(DIAGNOSTIC_SLUG, "Diagnostic déploiement & infrastructure")

    context = build_prompt_context(opportunity, company=company, matched_offer=offer)

    assert infer_draft_type(opportunity) == "prospecting_email"
    assert context["prompt_profile"] == "soria_b2b_prospecting_fr_v1"
    assert context["prompt_version"] == "mvcs3-b2b-v1"
    assert "signal public" in context["system_instructions"].lower()
    assert "prestataire externe" in context["system_instructions"].lower()
    assert "SORIA" in context["profile_context"]
    assert "cv.behnam.fr" not in context["profile_context"]
    assert context["user_context"]["evidence_contract"]["vendor_intent"] == "not_established"


def test_job_mode_keeps_personal_profile():
    company = _company()
    opportunity = Opportunity(
        company_id=company.id,
        title="Administrateur DevOps CDI",
        opportunity_type=OpportunityType.job,
        source=SourceType.manual,
    )

    context = build_prompt_context(opportunity, company=company)

    assert context["draft_type"] == "job_application_email"
    assert "Behnam" in context["profile_context"]
    assert "cv.behnam.fr" in context["profile_context"]
