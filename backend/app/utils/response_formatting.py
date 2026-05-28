import re
from enum import Enum
from typing import List


class QueryIntent(str, Enum):
    SUMMARY = "summary"
    LIST = "list"
    COMPARE = "compare"
    DEFINITION = "definition"
    EXPLAIN = "explain"
    KEY_POINTS = "key_points"
    OTHER = "other"


_COLD_PREAMBLE_PATTERNS = [
    re.compile(r"^based on (the )?provided context[:,\-]?\s*", re.IGNORECASE),
    re.compile(r"^based on (the )?context[:,\-]?\s*", re.IGNORECASE),
    re.compile(r"^here is (a )?(summary|overview)[:,\-]?\s*", re.IGNORECASE),
    re.compile(r"^in summary[:,\-]?\s*", re.IGNORECASE),
    re.compile(r"^summary[:,\-]?\s*", re.IGNORECASE),
]


def detect_query_intent(question: str) -> QueryIntent:
    if not question:
        return QueryIntent.OTHER

    normalized = question.strip().lower()

    if normalized.startswith("summarize") or "summary" in normalized:
        return QueryIntent.SUMMARY

    if normalized.startswith("what is") or normalized.startswith("who is"):
        return QueryIntent.DEFINITION

    if normalized.startswith("define ") or "definition" in normalized:
        return QueryIntent.DEFINITION

    if "compare" in normalized or "difference between" in normalized or " vs " in normalized:
        return QueryIntent.COMPARE

    if normalized.startswith("list") or "list all" in normalized or "show all" in normalized:
        return QueryIntent.LIST

    if "key points" in normalized or "exam" in normalized or "study guide" in normalized:
        return QueryIntent.KEY_POINTS

    if normalized.startswith("explain") or "explain" in normalized or "how does" in normalized:
        return QueryIntent.EXPLAIN

    return QueryIntent.OTHER


def format_response(raw_answer: str, intent: QueryIntent) -> str:
    if not raw_answer:
        return raw_answer

    text = raw_answer.strip()

    text = _strip_cold_preamble(text)
    text = _strip_redundant_header(text)

    if intent != QueryIntent.LIST:
        normalized = _collapse_bullets_if_short(text)
        if normalized:
            text = normalized

    return text.strip()


def _strip_cold_preamble(text: str) -> str:
    for pattern in _COLD_PREAMBLE_PATTERNS:
        text = pattern.sub("", text).lstrip()
    return text


def _strip_redundant_header(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    if not lines:
        return text

    non_empty = [line for line in lines if line.strip()]
    if len(non_empty) <= 3 and non_empty[0].endswith(":"):
        header = non_empty[0]
        return text.replace(header, "", 1).lstrip()

    return text


def _collapse_bullets_if_short(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return text

    if not all(_is_bullet_line(line) for line in lines):
        return text

    items = [_strip_bullet_prefix(line) for line in lines]
    items = [item for item in items if item]

    if not items:
        return text

    if len(items) < 5:
        return _items_to_sentence(items)

    return " ".join(items)


def _is_bullet_line(line: str) -> bool:
    return bool(re.match(r"^(?:[-*•]|\d+\.)\s+", line))


def _strip_bullet_prefix(line: str) -> str:
    return re.sub(r"^(?:[-*•]|\d+\.)\s+", "", line).strip()


def _items_to_sentence(items: List[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"There are two main items: {items[0]} and {items[1]}."

    body = ", ".join(items[:-1]) + f", and {items[-1]}"
    return f"There are {len(items)} main items: {body}."
