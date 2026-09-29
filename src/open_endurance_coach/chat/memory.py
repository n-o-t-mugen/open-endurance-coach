from dataclasses import dataclass, field

from open_endurance_coach.chat.history import count_exchanges, trim_history
from open_endurance_coach.clients.llm import LlmMessage
from open_endurance_coach.tokens import estimate_text_tokens

# Ratios of the in-session history cap at which the session warns, then relieves pressure.
NOTICE_RATIOS = (0.50, 0.75)
RELIEF_RATIO = 0.80
# Relief shrinks the transcript to this fraction of the cap, never below the newest exchange:
# it only ever drops whole old turns, always frees enough headroom that it does not fire again
# on the next turn, and scales down on small models.
RELIEF_TARGET_RATIO = 0.50


@dataclass(frozen=True)
class MemoryReport:
    notices: list[str] = field(default_factory=list)
    dropped_exchanges: int = 0


def _tokens(turns: list[LlmMessage]) -> int:
    return sum(estimate_text_tokens(turn.content) for turn in turns)


def _filling_notice(ratio: float, used: int, cap: int) -> str:
    return (
        f"conversation memory is {int(ratio * 100)}% full (~{used}/{cap} tokens); /forget clears it"
    )


def _exchanges_label(count: int) -> str:
    return "exchange" if count == 1 else "exchanges"


def _relief_notice(dropped: int, kept: int, used: int, cap: int) -> str:
    return (
        f"conversation memory was full: dropped {dropped} old {_exchanges_label(dropped)}"
        f" and kept the last {kept}; it is now ~{used}/{cap} tokens ({int(100 * used / cap)}%)"
    )


def _trim_notice(used: int, cap: int) -> str:
    return (
        f"conversation memory was full: trimmed the oldest messages; it is now"
        f" ~{used}/{cap} tokens ({int(100 * used / cap)}%)"
    )


def _newest_exchange(turns: list[LlmMessage]) -> list[LlmMessage]:
    if len(turns) >= 2 and turns[-1].role == "assistant":
        return turns[-2:]
    return turns[-1:]


def _relieve(turns: list[LlmMessage], *, cap: int, notified: set[float]) -> MemoryReport | None:
    before = count_exchanges(turns)
    target = max(1, int(RELIEF_TARGET_RATIO * cap), _tokens(_newest_exchange(turns)) + 1)
    trimmed = trim_history(turns, target)
    while trimmed and trimmed[0].role == "assistant":
        trimmed.pop(0)
    if len(trimmed) == len(turns):
        return None
    turns[:] = trimmed
    post_used = _tokens(turns)
    post_ratio = post_used / cap
    notified.clear()
    notified.update(threshold for threshold in NOTICE_RATIOS if post_ratio >= threshold)
    kept = count_exchanges(turns)
    dropped = before - kept
    if dropped < 1:
        return MemoryReport(notices=[_trim_notice(post_used, cap)])
    return MemoryReport(
        notices=[_relief_notice(dropped, kept, post_used, cap)], dropped_exchanges=dropped
    )


def update_memory(
    turns: list[LlmMessage],
    *,
    cap: int,
    notified: set[float],
) -> MemoryReport:
    """Warn as the conversation fills, then drop the oldest turns at ``RELIEF_RATIO``.

    Pressure is measured on the transcript alone (``turns`` against ``cap``), not on the
    whole request: the athlete data is re-fetched every turn and must not mask or fake
    memory pressure. ``turns`` is trimmed in place; ``notified`` tracks the ratios already
    reported and is rebuilt after relief so the warnings fire again as the transcript
    refills. At most one notice is returned per call.
    """
    if cap < 1:
        raise ValueError(f"cap must be positive: {cap}")
    used = _tokens(turns)
    ratio = used / cap
    if ratio >= RELIEF_RATIO:
        relief = _relieve(turns, cap=cap, notified=notified)
        if relief is not None:
            return relief
    crossed = [
        threshold for threshold in NOTICE_RATIOS if ratio >= threshold and threshold not in notified
    ]
    if crossed:
        notified.update(crossed)
        return MemoryReport(notices=[_filling_notice(ratio, used, cap)])
    return MemoryReport()
