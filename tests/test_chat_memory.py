import pytest

from open_endurance_coach.chat.memory import update_memory
from open_endurance_coach.clients.llm import LlmMessage
from open_endurance_coach.tokens import estimate_text_tokens


def turn(text: str, role: str = "user") -> LlmMessage:
    return LlmMessage(role=role, content=text)  # type: ignore[arg-type]


def test_below_the_first_threshold_stays_quiet() -> None:
    turns = [turn("hi")]
    report = update_memory(turns, cap=10, notified=set())
    assert report.notices == []
    assert report.dropped_exchanges == 0
    assert turns == [turn("hi")]


def test_crossing_50_and_75_warns_once_each() -> None:
    notified: set[float] = set()
    first = update_memory([turn("x" * 150)], cap=100, notified=notified)
    assert len(first.notices) == 1
    assert "50%" in first.notices[0]
    assert update_memory([turn("x" * 150)], cap=100, notified=notified).notices == []
    second = update_memory([turn("x" * 225)], cap=100, notified=notified)
    assert len(second.notices) == 1
    assert "75%" in second.notices[0]


def exchanges(count: int, *, chars: int = 156) -> list[LlmMessage]:
    turns: list[LlmMessage] = []
    for index in range(count):
        turns.append(LlmMessage(role="user", content=f"u{index}" + "x" * chars))
        turns.append(LlmMessage(role="assistant", content=f"a{index}" + "x" * chars))
    return turns


def test_relief_drops_the_oldest_and_keeps_the_newest() -> None:
    notified: set[float] = {0.50, 0.75}
    turns = exchanges(10)
    report = update_memory(turns, cap=1300, notified=notified)
    assert report.dropped_exchanges == 4
    assert "dropped 4 old exchanges" in report.notices[-1]
    assert turns[-1].content.startswith("a9")
    assert not turns[0].content.startswith("u0")
    assert sum(estimate_text_tokens(item.content) for item in turns) <= int(0.5 * 1300)


def test_relief_never_truncates_the_newest_exchange() -> None:
    turns = [
        turn("x" * 300),
        turn("y" * 300, role="assistant"),
        turn("z" * 1800),
        turn("w" * 1800, role="assistant"),
    ]
    report = update_memory(turns, cap=1000, notified=set())
    assert turns[-2].content == "z" * 1800
    assert turns[-1].content == "w" * 1800
    assert report.dropped_exchanges == 1


def test_relief_reports_only_one_notice() -> None:
    turns = exchanges(10)
    report = update_memory(turns, cap=1300, notified=set())
    assert len(report.notices) == 1
    assert "was full" in report.notices[0]


def test_update_memory_rejects_non_positive_cap() -> None:
    with pytest.raises(ValueError, match="cap"):
        update_memory([], cap=0, notified=set())


def test_two_thresholds_crossed_in_one_turn_warn_once() -> None:
    report = update_memory([turn("x" * 240)], cap=100, notified=set())
    filling = [note for note in report.notices if "conversation memory is" in note]
    assert len(filling) == 1


def test_relief_does_not_report_exchanges_without_a_reply() -> None:
    turns = [turn("x" * 150) for _ in range(20)]
    report = update_memory(turns, cap=1000, notified=set())
    assert report.dropped_exchanges == 0
    assert all("dropped" not in note for note in report.notices)
    assert "trimmed the oldest messages" in report.notices[-1]
    assert len(turns) == 10


def test_trimming_only_reply_less_turns_does_not_claim_an_exchange() -> None:
    turns = [turn("x" * 300) for _ in range(11)] + [turn("y" * 300, role="assistant")]
    report = update_memory(turns, cap=1200, notified=set())
    assert report.dropped_exchanges == 0
    assert all("dropped" not in note for note in report.notices)
    assert "trimmed the oldest messages" in report.notices[-1]


def test_relief_does_not_repeat_when_nothing_is_dropped() -> None:
    notified: set[float] = set()
    turns = [turn("short")]
    first = update_memory(turns, cap=1, notified=notified)
    assert first.dropped_exchanges == 0
    second = update_memory(turns, cap=1, notified=notified)
    assert second.notices == []


def test_thresholds_fire_again_after_relief() -> None:
    notified: set[float] = set()
    turns = exchanges(10)
    update_memory(turns, cap=1300, notified=notified)
    remaining = sum(estimate_text_tokens(item.content) for item in turns)
    assert remaining / 1300 < 0.5
    assert 0.50 not in notified
