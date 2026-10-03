from __future__ import annotations

import json
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Any

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    """Read and minimally validate a UTF-8 benchmark dataset."""

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"Dataset {path} must contain a JSON array.")
    for index, conversation in enumerate(payload):
        if not isinstance(conversation, dict):
            raise ValueError(f"Conversation {index} in {path} must be an object.")
        required = {"id", "user_id", "turns", "recall_questions"}
        missing = required.difference(conversation)
        if missing:
            raise ValueError(f"Conversation {index} is missing: {sorted(missing)}")
    return payload


def recall_points(answer: str, expected: list[str]) -> float:
    """Return 0 for no facts, 0.5 for partial recall, and 1 for all facts."""

    if not expected:
        return 1.0
    normalized_answer = _normalize_for_match(answer)
    matched = sum(
        1 for value in expected if _normalize_for_match(value) in normalized_answer
    )
    if matched == 0:
        return 0.0
    if matched == len(expected):
        return 1.0
    return 0.5


def heuristic_quality(answer: str, expected: list[str]) -> float:
    """Score factual coverage plus basic clarity on a 0–1 scale."""

    stripped = answer.strip()
    if not stripped:
        return 0.0
    normalized_answer = _normalize_for_match(stripped)
    coverage = (
        sum(1 for value in expected if _normalize_for_match(value) in normalized_answer)
        / len(expected)
        if expected
        else 1.0
    )
    word_count = len(stripped.split())
    clarity = 1.0 if 3 <= word_count <= 120 else 0.5
    return round(0.8 * coverage + 0.2 * clarity, 3)


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    """Evaluate one agent with fresh recall threads and no answer leakage."""

    del config
    user_ids = {str(item["user_id"]) for item in conversations}
    initial_memory = sum(_memory_size(agent, user_id) for user_id in user_ids)
    agent_tokens = 0
    prompt_tokens = 0
    recall_scores: list[float] = []
    quality_scores: list[float] = []
    thread_ids: set[str] = set()

    for conversation in conversations:
        conversation_id = str(conversation["id"])
        user_id = str(conversation["user_id"])
        train_thread = f"train:{conversation_id}"
        thread_ids.add(train_thread)
        for turn in conversation["turns"]:
            result = agent.reply(user_id, train_thread, str(turn))
            agent_tokens += int(result.get("tokens", 0))
            prompt_tokens += int(result.get("prompt_tokens", 0))

        for question_index, recall_question in enumerate(conversation["recall_questions"]):
            recall_thread = f"recall:{conversation_id}:{question_index}"
            thread_ids.add(recall_thread)
            result = agent.reply(
                user_id,
                recall_thread,
                str(recall_question["question"]),
            )
            agent_tokens += int(result.get("tokens", 0))
            prompt_tokens += int(result.get("prompt_tokens", 0))
            answer = str(result.get("content", ""))
            expected = [str(value) for value in recall_question["expected_contains"]]
            recall_scores.append(recall_points(answer, expected))
            quality_scores.append(heuristic_quality(answer, expected))

    final_memory = sum(_memory_size(agent, user_id) for user_id in user_ids)
    compactions = sum(agent.compaction_count(thread_id) for thread_id in thread_ids)
    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=agent_tokens,
        prompt_tokens_processed=prompt_tokens,
        recall_score=_average(recall_scores),
        response_quality=_average(quality_scores),
        memory_growth_bytes=max(0, final_memory - initial_memory),
        compactions=compactions,
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    """Format benchmark rows as a readable GitHub-style table."""

    headers = [
        "Agent",
        "Agent tokens only",
        "Prompt tokens processed",
        "Cross-session recall",
        "Response quality",
        "Memory growth (bytes)",
        "Compactions",
    ]
    values = [
        [
            row.agent_name,
            row.agent_tokens_only,
            row.prompt_tokens_processed,
            f"{row.recall_score:.3f}",
            f"{row.response_quality:.3f}",
            row.memory_growth_bytes,
            row.compactions,
        ]
        for row in rows
    ]
    try:
        from tabulate import tabulate

        return tabulate(values, headers=headers, tablefmt="github")
    except ImportError:
        all_rows = [headers, *[[str(value) for value in row] for row in values]]
        widths = [max(len(row[index]) for row in all_rows) for index in range(len(headers))]
        lines = [
            "| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(row)) + " |"
            for row in all_rows
        ]
        separator = "| " + " | ".join("-" * width for width in widths) + " |"
        lines.insert(1, separator)
        return "\n".join(lines)


def main() -> None:
    """Run the standard and stress suites in deterministic offline mode."""

    config = load_config(Path(__file__).resolve().parent.parent)
    suites = (
        ("Standard Benchmark", config.data_dir / "conversations.json"),
        ("Long-Context Stress Benchmark", config.data_dir / "advanced_long_context.json"),
    )

    with tempfile.TemporaryDirectory(
        prefix="memory-agent-benchmark-",
        dir=config.state_dir,
    ) as temporary:
        temporary_root = Path(temporary)
        for suite_index, (title, dataset_path) in enumerate(suites):
            conversations = load_conversations(dataset_path)
            suite_state = temporary_root / f"suite-{suite_index}"
            suite_config = replace(config, state_dir=suite_state)
            rows = [
                run_agent_benchmark(
                    "Baseline",
                    BaselineAgent(suite_config, force_offline=True),
                    conversations,
                    suite_config,
                ),
                run_agent_benchmark(
                    "Advanced",
                    AdvancedAgent(suite_config, force_offline=True),
                    conversations,
                    suite_config,
                ),
            ]
            print(f"\n## {title}\n")
            print(format_rows(rows))


def _normalize_for_match(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", normalized).strip()


def _memory_size(agent: Any, user_id: str) -> int:
    method = getattr(agent, "memory_file_size", None)
    return int(method(user_id)) if callable(method) else 0


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 3) if values else 0.0


if __name__ == "__main__":
    main()
