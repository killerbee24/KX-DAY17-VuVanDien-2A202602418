from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from memory_store import (
    PROFILE_LABELS,
    CompactMemoryManager,
    UserProfileStore,
    estimate_tokens,
    extract_profile_updates,
    render_profile_answer,
    requested_profile_keys,
)
from model_provider import build_chat_model


@dataclass
class AgentContext:
    user_id: str
    memory_path: str


class AdvancedAgent:
    """Agent B: persistent profile plus compact per-thread memory."""

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(self.config.state_dir / "profiles")
        self.compact_memory = CompactMemoryManager(
            threshold_tokens=self.config.compact_threshold_tokens,
            keep_messages=self.config.compact_keep_messages,
        )
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}
        self.langchain_agent = None if force_offline else self._maybe_build_langchain_agent()

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Route to deterministic offline mode or the configured live model."""

        if self.langchain_agent is not None:
            return self._reply_live(user_id, thread_id, message)
        return self._reply_offline(user_id, thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Persist profile facts and answer from profile plus compact context."""

        updates = extract_profile_updates(message)
        self._persist_updates(user_id, updates)
        self.compact_memory.append(thread_id, "user", message)

        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        self.thread_prompt_tokens[thread_id] = (
            self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens
        )
        response = self._offline_response(user_id, thread_id, message)
        response_tokens = estimate_tokens(response)
        self.compact_memory.append(thread_id, "assistant", response)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + response_tokens
        return {
            "content": response,
            "tokens": response_tokens,
            "prompt_tokens": prompt_tokens,
            "thread_id": thread_id,
            "memory_path": str(self.profile_store.path_for(user_id)),
            "mode": "offline",
        }

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        """Estimate profile + summary + recent-message context for one turn."""

        context = self.compact_memory.context(thread_id)
        parts = [self.profile_store.read_text(user_id), str(context["summary"])]
        messages = context["messages"]
        assert isinstance(messages, list)
        parts.extend(f"{item['role']}: {item['content']}" for item in messages)
        return estimate_tokens("\n".join(part for part in parts if part))

    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        """Return a deterministic response grounded only in persisted facts."""

        del thread_id
        requested = requested_profile_keys(message)
        if not requested:
            return "Đã cập nhật thông tin quan trọng vào bộ nhớ người dùng."
        facts = self.profile_store.facts(user_id)
        response = render_profile_answer(facts, requested)
        if "3 bullet" in facts.get("response_style", "").casefold():
            response = _force_three_bullets(response, facts, requested)
        return response

    def _maybe_build_langchain_agent(self):
        """Build the configured live model when credentials are available."""

        provider = self.config.model.provider
        if provider != "ollama" and not self.config.model.api_key:
            return None
        return build_chat_model(self.config.model)

    def _persist_updates(self, user_id: str, updates: dict[str, str]) -> None:
        existing = self.profile_store.facts(user_id)
        for key, value in updates.items():
            if key == "technical_interests" and existing.get(key):
                old_values = [part.strip() for part in existing[key].split(",")]
                new_values = [part.strip() for part in value.split(",")]
                value = ", ".join(dict.fromkeys(old_values + new_values))
            self.profile_store.upsert_fact(user_id, key, value)
            existing[key] = value

    def _reply_live(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        updates = extract_profile_updates(message)
        self._persist_updates(user_id, updates)
        self.compact_memory.append(thread_id, "user", message)
        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        self.thread_prompt_tokens[thread_id] = (
            self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens
        )

        context = self.compact_memory.context(thread_id)
        system_prompt = (
            "Bạn là trợ lý có bộ nhớ người dùng. Chỉ sử dụng profile và ngữ cảnh "
            "được cung cấp; ưu tiên fact mới nhất.\n\n"
            f"PROFILE:\n{self.profile_store.read_text(user_id)}\n\n"
            f"SUMMARY:\n{context['summary']}"
        )
        messages = context["messages"]
        assert isinstance(messages, list)
        model_messages = [{"role": "system", "content": system_prompt}, *messages]
        result = self.langchain_agent.invoke(model_messages)
        response = _model_content(result)
        response_tokens = estimate_tokens(response)
        self.compact_memory.append(thread_id, "assistant", response)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + response_tokens
        return {
            "content": response,
            "tokens": response_tokens,
            "prompt_tokens": prompt_tokens,
            "thread_id": thread_id,
            "memory_path": str(self.profile_store.path_for(user_id)),
            "mode": "live",
        }


def _force_three_bullets(
    response: str,
    facts: dict[str, str],
    requested: list[str],
) -> str:
    known = [(PROFILE_LABELS[key], facts[key]) for key in requested if facts.get(key)]
    if not known:
        return response
    groups: list[list[tuple[str, str]]] = [[], [], []]
    for index, item in enumerate(known):
        groups[index % 3].append(item)
    lines: list[str] = []
    for index, group in enumerate(groups):
        if group:
            body = "; ".join(f"{label}: {value}" for label, value in group)
        else:
            body = "Trình bày ngắn gọn theo đúng style đã lưu"
        lines.append(f"- {body}")
    return "\n".join(lines)


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
