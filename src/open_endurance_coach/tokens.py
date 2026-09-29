import json
from typing import Any

# Calibrated 2026-09-15 against DeepSeek (deepseek-flash): a representative analysis
# prompt of 12,380 chars used 4,039 prompt tokens (3.07 chars/token). The previous
# chars/4 heuristic under-counted by ~23%, so 3 gives a small safety margin.
CHARS_PER_TOKEN = 3

# Fraction of a model's window held back from the derived input budget. It must stay
# larger than the tokenizer drift between providers (the same prompt costs Qwen about
# 14% more tokens than DeepSeek). Adjust here in code.
BUDGET_SAFETY_MARGIN = 0.2


def estimate_text_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def estimate_payload_tokens(payload: Any) -> int:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    return max(1, len(serialized) // CHARS_PER_TOKEN)
