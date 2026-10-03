from __future__ import annotations

from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import LabConfig
from memory_store import UserProfileStore
from model_provider import ProviderConfig, normalize_provider


def make_config(tmp_path: Path) -> LabConfig:
    """Build a fully offline config whose state is isolated per test."""

    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    offline_model = ProviderConfig(
        provider="custom",
        model_name="offline-test-model",
        api_key=None,
        base_url="https://api.invalid/v1",
    )
    return LabConfig(
        base_dir=tmp_path,
        data_dir=tmp_path / "data",
        state_dir=state_dir,
        compact_threshold_tokens=80,
        compact_keep_messages=2,
        model=offline_model,
        judge_model=offline_model,
    )


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    store = UserProfileStore(tmp_path / "profiles")
    path = store.write_text("dungct", "# User Profile\n\n- location: Đà Nẵng")

    assert path.exists()
    assert "Đà Nẵng" in store.read_text("dungct")
    assert store.edit_text("dungct", "Đà Nẵng", "Huế") is True
    assert store.edit_text("dungct", "Không tồn tại", "X") is False
    assert store.facts("dungct")["location"] == "Huế"
    assert store.file_size("dungct") > 0


def test_compact_trigger(tmp_path: Path) -> None:
    agent = AdvancedAgent(make_config(tmp_path), force_offline=True)
    for index in range(8):
        agent.reply("user", "long-thread", f"Lượt {index}: " + "ngữ cảnh dài " * 35)

    context = agent.compact_memory.context("long-thread")
    assert agent.compaction_count("long-thread") > 0
    assert context["summary"]
    assert len(context["messages"]) <= 2


def test_cross_session_recall(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)

    fact = "Chào bạn, mình tên là DũngCT."
    baseline.reply("dungct", "train", fact)
    advanced.reply("dungct", "train", fact)

    baseline_answer = baseline.reply("dungct", "fresh", "Mình tên gì?")["content"]
    advanced_answer = advanced.reply("dungct", "fresh", "Mình tên gì?")["content"]

    assert "DũngCT" not in baseline_answer
    assert "DũngCT" in advanced_answer


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)

    for index in range(24):
        message = f"Lượt {index}: " + "Thông tin vận hành dài để đo prompt context. " * 12
        baseline.reply("stress", "thread", message)
        advanced.reply("stress", "thread", message)

    assert advanced.compaction_count("thread") > 0
    assert advanced.prompt_token_usage("thread") < baseline.prompt_token_usage("thread")


def test_corrections_and_noise_do_not_replace_current_facts(tmp_path: Path) -> None:
    agent = AdvancedAgent(make_config(tmp_path), force_offline=True)
    messages = [
        "Mình ở Đà Nẵng và đang làm backend engineer cho startup AI.",
        "Giờ mình đang ở Huế chứ không còn ở Đà Nẵng nữa.",
        "Mình không còn làm backend engineer nữa, giờ chuyển sang MLOps engineer.",
        "Mình nuôi một bé corgi tên Bơ.",
        "Có lúc mình đùa rằng hay là chuyển sang product manager, nhưng đó chỉ là câu đùa.",
        "Hà Nội chỉ là nơi mình đi họp hai ngày chứ không phải nơi ở hiện tại.",
    ]
    for message in messages:
        agent.reply("dungct", "facts", message)
    agent.reply(
        "dungct",
        "recall",
        "Nhắc lại giúp mình: tên, món ăn yêu thích và mình nuôi con gì.",
    )

    facts = agent.profile_store.facts("dungct")
    assert facts["location"] == "Huế"
    assert facts["profession"] == "MLOps engineer"
    assert facts["pet"] == "corgi tên Bơ"


def test_user_id_is_sanitized(tmp_path: Path) -> None:
    store = UserProfileStore(tmp_path / "profiles")
    path = store.path_for("../../outside")
    assert path.parent.parent.resolve() == (tmp_path / "profiles").resolve()


def test_provider_alias_is_normalized() -> None:
    assert normalize_provider("anthorpic") == "anthropic"
    assert normalize_provider("google-genai") == "gemini"
