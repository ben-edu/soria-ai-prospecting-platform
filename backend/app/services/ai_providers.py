"""AI provider abstraction layer for SORIA prospecting.

Defines a provider registry, a deterministic MockAIProvider, and a
resolver function. Currently only provides the mock provider —
no external AI APIs are called.
"""

from typing import Optional

# -------------------------------------------------------------------
# Exception hierarchy
# -------------------------------------------------------------------


class AIProviderError(Exception):
    """Base exception for all AI provider errors."""


class UnknownAIProviderError(AIProviderError, ValueError):
    """Raised when the requested provider is not in the registry."""


class AIProviderGenerationError(AIProviderError):
    """Raised when the provider encounters an unexpected runtime error."""


class InvalidAIProviderOutputError(AIProviderError):
    """Raised when the provider returns invalid or incomplete output."""


# -------------------------------------------------------------------
# Registry
# -------------------------------------------------------------------

PROVIDER_REGISTRY: dict[str, type] = {}


def register_provider(name: str):
    """Decorator to register an AI provider implementation."""
    def wrapper(cls):
        PROVIDER_REGISTRY[name] = cls
        return cls
    return wrapper


def get_ai_provider(provider_name: str, model_name: Optional[str] = None):
    """Resolve an AI provider by name, optionally specifying a model.

    Parameters
    ----------
    provider_name
        Registered provider name.
    model_name
        Optional model override passed to the provider constructor.

    Returns
    -------
    An instance of the registered provider class.

    Raises
    ------
    UnknownAIProviderError
        If *provider_name* is not in the registry.
    """
    if provider_name not in PROVIDER_REGISTRY:
        available = ", ".join(sorted(PROVIDER_REGISTRY))
        raise UnknownAIProviderError(
            f"Unknown AI provider: '{provider_name}'. "
            f"Available providers: [{available}]"
        )
    provider_cls = PROVIDER_REGISTRY[provider_name]
    if model_name is not None:
        return provider_cls(model_name=model_name)
    return provider_cls()


def list_available_ai_providers() -> list[str]:
    """Return sorted list of registered AI provider names."""
    return sorted(PROVIDER_REGISTRY)


def get_provider_registry_snapshot() -> dict:
    """Return a diagnostic-friendly snapshot of the provider registry.

    Returns a dict mapping provider name to class qualified name.
    """
    return {
        name: f"{cls.__module__}.{cls.__qualname__}"
        for name, cls in sorted(PROVIDER_REGISTRY.items())
    }


# -------------------------------------------------------------------
# Mock provider
# -------------------------------------------------------------------


@register_provider("mock_ai")
class MockAIProvider:
    """Deterministic mock AI provider for SORIA prospecting drafts.

    Generates structured French prospecting email content from the
    given prompt context without calling any external AI API.
    The output is fully deterministic — the same context always
    produces the same draft.
    """

    provider = "mock_ai"
    model_name = "mock-soria-v1"
    prompt_version = "ai-draft-v1"

    def __init__(self, model_name: Optional[str] = None):
        if model_name is not None:
            self.model_name = model_name

    def generate(self, prompt_context: dict) -> dict:
        """Generate a deterministic draft from *prompt_context*.

        Returns a dict with keys: ``subject``, ``body``, ``provider``,
        ``model_name``, ``prompt_version``, ``safety_note``.
        """
        ctx = prompt_context["user_context"]
        contact_name = ctx["contact"]["full_name"]
        company_name = ctx["company"]["name"]
        opp_title = ctx["opportunity"]["title"]
        opp_description = ctx["opportunity"]["description"]
        detected_need = ctx["opportunity"]["detected_need"]
        landing_page = ctx["opportunity"]["recommended_landing_page"]

        matched_offer = ctx.get("matched_offer")
        matched_resource = ctx.get("matched_resource")

        # ----- Subject -----
        subject = (
            f"Accompagnement sur mesure — {opp_title} — {company_name}"
        )

        # ----- Body -----
        parts: list[str] = []

        # Salutation
        parts.append(f"Bonjour {contact_name},")
        parts.append("")

        # Introduction — contextual
        parts.append(
            f"Nous avons récemment identifié que {company_name} pourrait "
            f"bénéficier d'un accompagnement dans le domaine "
            f"« {opp_title} »."
        )

        if opp_description:
            parts.append(
                f"Au vu du contexte suivant : {opp_description}"
            )

        # Detected need
        if detected_need:
            parts.append("")
            parts.append(f"**Besoins détectés :** {detected_need}")
            parts.append(
                "Notre équipe a analysé ces besoins et propose une réponse "
                "structurée ci-dessous."
            )

        # Matched offer section
        if matched_offer:
            parts.append("")
            parts.append(
                f"**Offre recommandée :** {matched_offer['name']}"
            )
            if matched_offer.get("short_description"):
                parts.append(matched_offer["short_description"])
            if matched_offer.get("landing_page_url"):
                parts.append(
                    f"Page de l'offre : {matched_offer['landing_page_url']}"
                )

        # Matched academy resource section
        if matched_resource:
            parts.append("")
            parts.append(
                f"**Ressource associée :** {matched_resource['title']}"
            )
            if matched_resource.get("short_description"):
                parts.append(matched_resource["short_description"])
            if matched_resource.get("public_url"):
                parts.append(
                    f"En savoir plus : {matched_resource['public_url']}"
                )

        # Recommended landing page
        if landing_page:
            landing_label = "Page dédiée"
            if matched_offer and matched_offer.get("name"):
                landing_label = f"Page dédiée à {matched_offer['name']}"
            parts.append("")
            parts.append(f"{landing_label} : {landing_page}")

        # Closing
        parts.append("")
        parts.append(
            "Je me tiens à votre disposition pour échanger sur ces pistes "
            "et adapter notre proposition à vos besoins spécifiques."
        )
        parts.append("")
        parts.append("Cordialement,")
        parts.append("L'équipe SORIA")

        body = "\n".join(parts)

        return {
            "subject": subject,
            "body": body,
            "provider": self.provider,
            "model_name": self.model_name,
            "prompt_version": prompt_context.get(
                "prompt_version", self.prompt_version
            ),
            "safety_note": prompt_context.get("safety_note", ""),
        }
