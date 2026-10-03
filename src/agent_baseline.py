from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import (
    estimate_tokens,
    extract_profile_updates,
    render_profile_answer,
    requested_profile_keys,
)
from model_provider import build_chat_model


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    """Agent A: full within-thread history with no persistent memory."""

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}
        self.langchain_agent = None if force_offline else self._maybe_build_langchain_agent()

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Reply using a real model when configured, otherwise deterministic offline mode."""

        del user_id  # Baseline deliberately does not share state by user.
        if self.langchain_agent is not None:
            return self._reply_live(thread_id, message)
        return self._reply_offline(thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).token_usage

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).prompt_tokens_processed

    def compaction_count(self, thread_id: str) -> int:
        # Baseline has no compact memory.
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        """Use only facts present in this thread to create a stable response."""

        session = self.sessions.setdefault(thread_id, SessionState())
        session.messages.append({"role": "user", "content": message})
        prompt_tokens = _message_tokens(session.messages)
        session.prompt_tokens_processed += prompt_tokens

        requested = requested_profile_keys(message)
        if requested:
            response = render_profile_answer(_session_facts(session.messages), requested)
        else:
            response = "Đã ghi nhận trong thread hiện tại."

        response_tokens = estimate_tokens(response)
        session.messages.append({"role": "assistant", "content": response})
        session.token_usage += response_tokens
        return {
            "content": response,
            "tokens": response_tokens,
            "prompt_tokens": prompt_tokens,
            "thread_id": thread_id,
            "mode": "offline",
        }

    def _maybe_build_langchain_agent(self):
        """Build the configured chat model when credentials are available."""

        provider = self.config.model.provider
        if provider != "ollama" and not self.config.model.api_key:
            return None
        return build_chat_model(self.config.model)

    def _reply_live(self, thread_id: str, message: str) -> dict[str, Any]:
        session = self.sessions.setdefault(thread_id, SessionState())
        session.messages.append({"role": "user", "content": message})
        prompt_tokens = _message_tokens(session.messages)
        session.prompt_tokens_processed += prompt_tokens

        result = self.langchain_agent.invoke(session.messages)
        response = _model_content(result)
        response_tokens = estimate_tokens(response)
        session.messages.append({"role": "assistant", "content": response})
        session.token_usage += response_tokens
        return {
            "content": response,
            "tokens": response_tokens,
            "prompt_tokens": prompt_tokens,
            "thread_id": thread_id,
            "mode": "live",
        }


def _session_facts(messages: list[dict[str, str]]) -> dict[str, str]:
    facts: dict[str, str] = {}
    for item in messages:
        if item.get("role") != "user":
            continue
        updates = extract_profile_updates(item.get("content", ""))
        for key, value in updates.items():
            if key == "technical_interests" and facts.get(key):
                existing = [part.strip() for part in facts[key].split(",")]
                additions = [part.strip() for part in value.split(",")]
                facts[key] = ", ".join(dict.fromkeys(existing + additions))
            else:
                facts[key] = value
    return facts


def _message_tokens(messages: list[dict[str, str]]) -> int:
    text = "\n".join(f"{item['role']}: {item['content']}" for item in messages)
    return estimate_tokens(text)


def _model_content(result: Any) -> str:
    content = getattr(result, "content", result)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "\n".join(parts)
    return str(content)
