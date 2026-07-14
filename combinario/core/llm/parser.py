import json
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


class LLMOutputError(ValueError):
    pass


class GeneratedItem(BaseModel):
    emoji: str = Field(..., min_length=1, max_length=12)
    text: str = Field(..., min_length=1, max_length=80)

    @field_validator("emoji")
    @classmethod
    def validate_emoji(cls, value: str) -> str:
        value = value.strip()
        if not value or any(char.isspace() for char in value):
            raise ValueError("emoji must be a single token")
        if value == "❌" or not _looks_like_emoji(value[0]):
            raise ValueError("emoji must look like an emoji")
        return value

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = re.sub(r"\s+", " ", value).strip()
        if not value:
            raise ValueError("text cannot be empty")
        if value.lower() == "failed":
            raise ValueError("LLM returned failure sentinel")
        if any(ord(char) < 32 for char in value):
            raise ValueError("text cannot contain control characters")
        return value


def parse_llm_item(raw: str | None) -> GeneratedItem:
    if raw is None:
        raise LLMOutputError("Empty LLM response")

    cleaned = _clean_response(raw)
    if not cleaned or cleaned.startswith("❌") or cleaned.lower() == "failed":
        raise LLMOutputError("LLM returned failure sentinel")

    if parsed_json := _parse_json_response(cleaned):
        return parsed_json

    first_line = next(
        (line.strip() for line in cleaned.splitlines() if line.strip()), ""
    )
    if "→" in first_line:
        first_line = first_line.rsplit("→", maxsplit=1)[1].strip()

    try:
        emoji, text = first_line.split(maxsplit=1)
    except ValueError:
        emoji, text = _split_leading_emoji(first_line)

    try:
        return GeneratedItem(emoji=emoji, text=text)
    except ValueError as exc:
        raise LLMOutputError(str(exc)) from exc


def _clean_response(raw: str) -> str:
    value = raw.strip().strip('"').strip("'")
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    return value


def _parse_json_response(value: str) -> GeneratedItem | None:
    candidate = value
    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = candidate[start : end + 1]

    try:
        payload: Any = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    try:
        return GeneratedItem.model_validate(payload)
    except ValueError as exc:
        raise LLMOutputError(str(exc)) from exc


def _split_leading_emoji(value: str) -> tuple[str, str]:
    if not value:
        raise LLMOutputError("Empty LLM response")
    if not _looks_like_emoji(value[0]):
        raise LLMOutputError("Response does not start with an emoji")

    index = 1
    while index < len(value) and _is_emoji_modifier(value[index]):
        index += 1

    return value[:index], value[index:].strip()


def _looks_like_emoji(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x1F000 <= codepoint <= 0x1FAFF
        or 0x2600 <= codepoint <= 0x27BF
        or 0x2300 <= codepoint <= 0x23FF
    )


def _is_emoji_modifier(char: str) -> bool:
    codepoint = ord(char)
    return codepoint in {0xFE0E, 0xFE0F, 0x200D} or 0x1F3FB <= codepoint <= 0x1F3FF
