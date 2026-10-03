from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUPPORTED_PROVIDERS = {
    "openai",
    "custom",
    "gemini",
    "anthropic",
    "ollama",
    "openrouter",
}


@dataclass
class ProviderConfig:
    """Configuration shared by all supported chat-model providers."""

    provider: str
    model_name: str
    temperature: float = 0.0
    api_key: str | None = None
    base_url: str | None = None


def normalize_provider(value: str) -> str:
    """Return a canonical provider name or raise a useful error."""

    normalized = value.strip().lower().replace("_", "-").replace(" ", "-")
    aliases = {
        "open-ai": "openai",
        "openai-compatible": "custom",
        "openai-compat": "custom",
        "compatible": "custom",
        "google": "gemini",
        "google-genai": "gemini",
        "google-generative-ai": "gemini",
        "claude": "anthropic",
        "anthorpic": "anthropic",
        "open-router": "openrouter",
        "local": "ollama",
    }
    normalized = aliases.get(normalized, normalized)

    if normalized not in SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise ValueError(f"Unsupported provider {value!r}. Expected one of: {supported}.")
    return normalized


def _without_none(values: dict[str, Any]) -> dict[str, Any]:
    """Avoid passing optional keyword arguments unsupported by some SDK versions."""

    return {key: value for key, value in values.items() if value is not None}



def build_chat_model(config: ProviderConfig):
    """Instantiate a LangChain chat model for the selected provider.

    Imports stay local so offline mode can run even when an optional provider
    package is not installed. MWAPI and similar gateways should use the
    ``custom`` provider because they expose an OpenAI-compatible endpoint.
    """

    provider = normalize_provider(config.provider)
    common = {"model": config.model_name, "temperature": config.temperature}

    if provider in {"openai", "custom"}:
        from langchain_openai import ChatOpenAI

        if provider == "custom" and not config.base_url:
            raise ValueError("The custom provider requires an OpenAI-compatible base_url.")
        return ChatOpenAI(
            **common,
            **_without_none({"api_key": config.api_key, "base_url": config.base_url}),
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            **common,
            **_without_none({"google_api_key": config.api_key}),
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            **common,
            **_without_none({"anthropic_api_key": config.api_key}),
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            **common,
            **_without_none({"base_url": config.base_url}),
        )

    if provider == "openrouter":
        from langchain_openrouter import ChatOpenRouter

        return ChatOpenRouter(
            **common,
            **_without_none({"api_key": config.api_key}),
        )

    # normalize_provider already validates this; this line protects future edits.
    raise AssertionError(f"Unhandled provider: {provider}")
