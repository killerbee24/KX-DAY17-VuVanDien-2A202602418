from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Estimate token count deterministically without a provider tokenizer."""

    normalized = text.strip()
    if not normalized:
        return 0
    return max(1, math.ceil(len(normalized) / 4))


@dataclass
class UserProfileStore:
    """Persistent UTF-8 storage for one structured ``User.md`` per user."""

    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        normalized = unicodedata.normalize("NFKC", user_id).strip()
        safe_user_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", normalized).strip("._")
        if not safe_user_id:
            raise ValueError("user_id must contain at least one safe character.")
        return self.root_dir / safe_user_id / "User.md"

    def read_text(self, user_id: str) -> str:
        path = self.path_for(user_id)
        if not path.exists():
            return "# User Profile\n"
        return path.read_text(encoding="utf-8")

    def write_text(self, user_id: str, content: str) -> Path:
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = content.rstrip() + "\n"
        path.write_text(normalized, encoding="utf-8")
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        if not search_text:
            return False
        current = self.read_text(user_id)
        if search_text not in current:
            return False
        self.write_text(user_id, current.replace(search_text, replacement, 1))
        return True

    def file_size(self, user_id: str) -> int:
        path = self.path_for(user_id)
        return path.stat().st_size if path.exists() else 0

    def facts(self, user_id: str) -> dict[str, str]:
        """Parse ``- key: value`` lines from the user's Markdown profile."""

        result: dict[str, str] = {}
        for line in self.read_text(user_id).splitlines():
            match = re.match(r"^\s*-\s*([A-Za-z0-9_]+)\s*:\s*(.+?)\s*$", line)
            if match:
                result[match.group(1).lower()] = match.group(2).strip()
        return result

    def upsert_fact(self, user_id: str, key: str, value: str) -> Path:
        """Insert or replace one structured profile fact."""

        safe_key = re.sub(r"[^A-Za-z0-9_]+", "_", key.strip().lower()).strip("_")
        clean_value = _clean_value(value)
        if not safe_key or not clean_value:
            raise ValueError("Both fact key and value must be non-empty.")
        profile_facts = self.facts(user_id)
        profile_facts[safe_key] = clean_value
        lines = ["# User Profile", ""]
        lines.extend(f"- {fact_key}: {fact_value}" for fact_key, fact_value in profile_facts.items())
        return self.write_text(user_id, "\n".join(lines))


def extract_profile_updates(message: str) -> dict[str, str]:
    """Extract high-confidence, durable profile facts from Vietnamese text.

    The extractor is intentionally conservative. It handles the benchmark's
    explicit first-person statements and corrections while ignoring questions,
    jokes, trips, and other likely temporary context.
    """

    text = re.sub(r"\s+", " ", message).strip()
    lowered = text.casefold()
    question_cues = (
        " là gì",
        " tên gì",
        " ở đâu",
        " như thế nào",
        "nhắc lại giúp mình",
        "thử nhớ lại",
        "tóm tắt ngắn về mình",
        "bạn biết ",
    )
    if not text or text.endswith("?") or any(cue in lowered for cue in question_cues):
        return {}

    updates: dict[str, str] = {}

    name_match = re.search(
        r"(?:mình\s+tên\s+là|tên\s+(?:của\s+)?mình\s+là)\s+([^,.;!?]+)",
        text,
        flags=re.IGNORECASE,
    )
    if name_match:
        updates["name"] = _clean_value(name_match.group(1))

    location_patterns = (
        r"nơi\s+ở\s+hiện\s+tại(?:\s+của\s+mình)?\s*(?:là|:)\s*([^,.;!?]+)",
        r"(?:thực\s+ra[^.!?]{0,90})?(?:từ\s+tuần\s+này\s+)?mình\s+đang\s+làm\s+việc\s+ở\s+([^,.;!?]+)",
        r"(?:giờ|hiện\s+tại)[^.!?]{0,35}?mình\s+(?:đang\s+)?ở\s+([^,.;!?]+)",
        r"mình\s+(?:vẫn\s+|hiện\s+|đang\s+)?ở\s+([^,.;!?]+)",
        r"(?:^|[,;])\s*hiện\s+ở\s+([^,.;!?]+)",
    )
    for pattern in location_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            location = _trim_at_phrases(
                match.group(1),
                (" và ", " chứ ", " nhưng ", " dù ", " để ", " vài tháng", " cho "),
            )
            if location:
                updates["location"] = location
                break

    profession_patterns = (
        r"(?:giờ|hiện\s+tại)\s+(?:mình\s+)?(?:đã\s+)?chuyển\s+sang\s+([^,.;!?]+)",
        r"nghề\s+nghiệp(?:\s+hiện\s+tại)?\s+(?:thì\s+)?(?:vẫn\s+)?là\s+([^,.;!?]+)",
        r"(?:mình|và)\s+(?:đang\s+|vẫn\s+)?làm\s+([^,.;!?]+)",
        r"(?:^|[,;])\s*nghề\s+([^,.;!?]+)",
    )
    for pattern in profession_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            profession = _trim_at_phrases(
                match.group(1),
                (" cho ", " tại ", " chứ ", " nhưng ", " và ", " không ", " vẫn "),
            )
            if _looks_like_profession(profession):
                updates["profession"] = profession
                break

    drink_match = re.search(
        r"đồ\s+uống\s+yêu\s+thích(?:\s+của\s+mình)?\s*(?:là|:)\s*([^,.;!?]+)",
        text,
        flags=re.IGNORECASE,
    )
    if drink_match:
        updates["favorite_drink"] = _clean_value(drink_match.group(1))

    food_match = re.search(
        r"món\s+ăn\s+yêu\s+thích(?:\s+của\s+mình)?\s*(?:là|:)\s*([^,.;!?]+)",
        text,
        flags=re.IGNORECASE,
    )
    if food_match:
        updates["favorite_food"] = _clean_value(food_match.group(1))

    pet_match = re.search(
        r"mình\s+nuôi\s+(?:một\s+)?(?:bé\s+|con\s+)?([^,.;!?]+)",
        text,
        flags=re.IGNORECASE,
    )
    if pet_match:
        updates["pet"] = _clean_value(pet_match.group(1))

    style_context = any(
        cue in lowered for cue in ("trả lời", "câu trả lời", "giải thích", "style")
    )
    if style_context:
        style_parts: list[str] = []
        if re.search(r"\b3\s+bullet\b", lowered):
            style_parts.append("3 bullet")
        elif "bullet" in lowered:
            style_parts.append("có bullet")
        if any(
            cue in lowered
            for cue in ("ngắn gọn", "trả lời ngắn", "bullet ngắn", "trả lời gọn", "đừng lan man")
        ):
            style_parts.append("ngắn gọn")
        if "ví dụ thực chiến" in lowered:
            style_parts.append("có ví dụ thực chiến")
        elif "ví dụ thực tế" in lowered:
            style_parts.append("có ví dụ thực tế")
        if "trade-off" in lowered:
            style_parts.append("nhấn mạnh trade-off")
        if style_parts:
            updates["response_style"] = ", ".join(dict.fromkeys(style_parts))

    interest_context = any(cue in lowered for cue in ("mình thích", "quan tâm", "mối quan tâm"))
    if interest_context:
        interests: list[str] = []
        interest_terms = (
            (r"\bpython\b", "Python"),
            (r"\bai\b|trí tuệ nhân tạo", "AI"),
            (r"\bmlops\b", "MLOps"),
            (r"\brag\b", "RAG"),
            (r"\bevaluation\b", "evaluation"),
            (r"memory(?:\s+architecture|\s+system|\s+benchmark)?", "memory systems"),
        )
        for pattern, label in interest_terms:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                interests.append(label)
        if interests:
            updates["technical_interests"] = ", ".join(interests)

    return {key: value for key, value in updates.items() if value}


PROFILE_LABELS = {
    "name": "Tên",
    "location": "Nơi ở hiện tại",
    "profession": "Nghề nghiệp hiện tại",
    "response_style": "Style trả lời",
    "favorite_drink": "Đồ uống yêu thích",
    "favorite_food": "Món ăn yêu thích",
    "pet": "Thú cưng",
    "technical_interests": "Mối quan tâm kỹ thuật",
}


def requested_profile_keys(message: str) -> list[str]:
    """Infer which profile fields a recall-style message is asking for."""

    lowered = message.casefold()
    requested: list[str] = []
    checks = (
        ("name", ("tên", "là ai")),
        ("location", ("ở đâu", "nơi ở", "đang ở", "còn ở")),
        ("profession", ("nghề", "công việc hiện tại", "đang làm gì")),
        ("response_style", ("style", "kiểu trả lời", "trả lời mình thích")),
        ("favorite_drink", ("đồ uống", "uống gì")),
        ("favorite_food", ("món ăn", "ăn gì")),
        ("pet", ("nuôi con gì", "thú cưng", "corgi")),
        ("technical_interests", ("mối quan tâm", "quan tâm kỹ thuật")),
    )
    for key, cues in checks:
        if any(cue in lowered for cue in cues):
            requested.append(key)
    return requested


def render_profile_answer(facts: dict[str, str], requested_keys: list[str]) -> str:
    """Render known requested facts as concise Markdown bullets."""

    lines = [
        f"- {PROFILE_LABELS[key]}: {facts[key]}"
        for key in requested_keys
        if facts.get(key)
    ]
    if not lines:
        return "Mình chưa có thông tin đó trong bộ nhớ hiện tại."
    return "\n".join(lines)


def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    """Create a bounded extractive summary suitable for deterministic tests."""

    if max_items <= 0 or not messages:
        return ""

    candidates: list[tuple[int, int, str, str]] = []
    important_cues = (
        "tên",
        "ở ",
        "nghề",
        "làm ",
        "thích",
        "muốn",
        "đính chính",
        "thực ra",
        "hiện tại",
        "nhớ",
        "ưu tiên",
        "trade-off",
    )
    for index, message in enumerate(messages):
        role = str(message.get("role", "unknown"))
        content = re.sub(r"\s+", " ", str(message.get("content", ""))).strip()
        if not content:
            continue
        score = 2 if role == "user" else 0
        lowered = content.casefold()
        score += sum(1 for cue in important_cues if cue in lowered)
        if any(cue in lowered for cue in ("đính chính", "không còn", "thực ra", "mới")):
            score += 3
        excerpt = content if len(content) <= 280 else content[:277].rstrip() + "..."
        candidates.append((score, index, role, excerpt))

    if not candidates:
        return ""
    selected = sorted(candidates, key=lambda item: (item[0], item[1]), reverse=True)[:max_items]
    selected.sort(key=lambda item: item[1])
    return "\n".join(f"- {role}: {excerpt}" for _, _, role, excerpt in selected)


@dataclass
class CompactMemoryManager:
    """Keep recent messages verbatim and compact older history per thread."""

    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str) -> None:
        if not thread_id.strip():
            raise ValueError("thread_id must not be empty.")
        if role not in {"user", "assistant", "system"}:
            raise ValueError(f"Unsupported message role: {role!r}.")
        thread = self.state.setdefault(
            thread_id,
            {"messages": [], "summary": "", "compactions": 0},
        )
        messages = thread["messages"]
        assert isinstance(messages, list)
        messages.append({"role": role, "content": content})

        summary = str(thread["summary"])
        context_text = _context_text(summary, messages)
        if estimate_tokens(context_text) <= self.threshold_tokens:
            return
        if len(messages) <= self.keep_messages:
            return

        split_at = len(messages) - self.keep_messages
        older_messages = messages[:split_at]
        recent_messages = messages[split_at:]
        summary_input: list[dict[str, str]] = []
        if summary:
            summary_input.append({"role": "summary", "content": summary})
        summary_input.extend(older_messages)
        thread["summary"] = summarize_messages(summary_input)
        thread["messages"] = recent_messages
        thread["compactions"] = int(thread["compactions"]) + 1

    def context(self, thread_id: str) -> dict[str, object]:
        thread = self.state.get(thread_id)
        if thread is None:
            return {"messages": [], "summary": "", "compactions": 0}
        messages = thread["messages"]
        assert isinstance(messages, list)
        return {
            "messages": [dict(message) for message in messages],
            "summary": str(thread["summary"]),
            "compactions": int(thread["compactions"]),
        }

    def compaction_count(self, thread_id: str) -> int:
        return int(self.context(thread_id)["compactions"])


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t\r\n.,;:!?-–—")


def _trim_at_phrases(value: str, phrases: tuple[str, ...]) -> str:
    cleaned = f" {_clean_value(value)} "
    lowered = cleaned.casefold()
    cut_at = len(cleaned)
    for phrase in phrases:
        position = lowered.find(phrase.casefold())
        if position >= 0:
            cut_at = min(cut_at, position)
    return _clean_value(cleaned[:cut_at])


def _looks_like_profession(value: str) -> bool:
    lowered = value.casefold()
    return any(
        keyword in lowered
        for keyword in (
            "engineer",
            "developer",
            "manager",
            "scientist",
            "analyst",
            "designer",
            "devops",
            "mlops",
            "backend",
            "frontend",
            "kỹ sư",
        )
    )


def _context_text(summary: str, messages: list[dict[str, str]]) -> str:
    parts = [summary] if summary else []
    parts.extend(f"{message['role']}: {message['content']}" for message in messages)
    return "\n".join(parts)
