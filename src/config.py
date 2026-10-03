from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from model_provider import ProviderConfig, normalize_provider


@dataclass
class LabConfig:
    """Shared paths, memory settings, and model configuration for the lab."""

    base_dir: Path
    data_dir: Path
    state_dir: Path
    compact_threshold_tokens: int
    compact_keep_messages: int
    model: ProviderConfig
    judge_model: ProviderConfig


def load_config(base_dir: Path | None = None) -> LabConfig:
    """Load ``.env`` values and return a complete lab configuration."""

    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()
    try:
        from dotenv import load_dotenv

        load_dotenv(root / ".env", override=False)
    except ImportError:
        # Offline mode does not require python-dotenv.
        pass

    data_dir = root / "data"
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    mwapi_key = _optional_env("MWAPI_API_KEY")
    mwapi_base_url = _optional_env("MWAPI_BASE_URL") or "https://api.mwapi.dev/v1"

    # This lab defaults to the user's OpenAI-compatible MWAPI gateway. Direct
    # providers remain available by setting LLM_PROVIDER/JUDGE_PROVIDER.
    model_provider = normalize_provider(os.getenv("LLM_PROVIDER", "custom"))
    judge_provider = normalize_provider(os.getenv("JUDGE_PROVIDER", model_provider))

    model = ProviderConfig(
        provider=model_provider,
        model_name=os.getenv(
            "LLM_MODEL",
            os.getenv("MWAPI_GEMINI_MODEL", "gemini-2.5-flash"),
        ),
        temperature=_float_env("LLM_TEMPERATURE", 0.0),
        api_key=_provider_api_key(model_provider, "LLM", mwapi_key),
        base_url=_provider_base_url(model_provider, "LLM", mwapi_base_url),
    )
    judge_model = ProviderConfig(
        provider=judge_provider,
        model_name=os.getenv(
            "JUDGE_MODEL",
            os.getenv("MWAPI_ANTHROPIC_MODEL", "claude-sonnet-4-5"),
        ),
        temperature=_float_env("JUDGE_TEMPERATURE", 0.0),
        api_key=_provider_api_key(judge_provider, "JUDGE", mwapi_key),
        base_url=_provider_base_url(judge_provider, "JUDGE", mwapi_base_url),
    )

    return LabConfig(
        base_dir=root,
        data_dir=data_dir,
        state_dir=state_dir,
        compact_threshold_tokens=_positive_int_env("COMPACT_THRESHOLD_TOKENS", 1_200),
        compact_keep_messages=_positive_int_env("COMPACT_KEEP_MESSAGES", 6),
        model=model,
        judge_model=judge_model,
    )


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _float_env(name: str, default: float) -> float:
    raw = _optional_env(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}.") from exc


def _positive_int_env(name: str, default: int) -> int:
    raw = _optional_env(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}.") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")
    return value


def _provider_api_key(provider: str, prefix: str, mwapi_key: str | None) -> str | None:
    explicit = _optional_env(f"{prefix}_API_KEY")
    if explicit:
        return explicit
    names = {
        "openai": ("OPENAI_API_KEY",),
        "custom": ("CUSTOM_API_KEY", "MWAPI_API_KEY"),
        "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "anthropic": ("ANTHROPIC_API_KEY",),
        "openrouter": ("OPENROUTER_API_KEY",),
        "ollama": (),
    }
    for name in names[provider]:
        value = _optional_env(name)
        if value:
            return value
    return mwapi_key if provider == "custom" else None


def _provider_base_url(provider: str, prefix: str, mwapi_base_url: str) -> str | None:
    explicit = _optional_env(f"{prefix}_BASE_URL")
    if explicit:
        return explicit
    if provider == "custom":
        return _optional_env("CUSTOM_BASE_URL") or mwapi_base_url
    if provider == "ollama":
        return _optional_env("OLLAMA_BASE_URL")
    return None
