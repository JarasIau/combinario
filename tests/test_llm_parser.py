import pytest

from core.llm.parser import LLMOutputError, parse_llm_item


def test_parse_json_response() -> None:
    result = parse_llm_item('{"emoji": "💨", "text": "Steam"}')

    assert result.emoji == "💨"
    assert result.text == "Steam"


def test_parse_compact_emoji_response() -> None:
    result = parse_llm_item("💨Steam")

    assert result.emoji == "💨"
    assert result.text == "Steam"


def test_parse_arrow_response_takes_generated_result() -> None:
    result = parse_llm_item("Fire + Water → 💨 Steam")

    assert result.emoji == "💨"
    assert result.text == "Steam"


@pytest.mark.parametrize("raw", ["", "❌ Failed", '{"emoji": "❌", "text": "Failed"}'])
def test_rejects_failed_or_empty_responses(raw: str) -> None:
    with pytest.raises(LLMOutputError):
        parse_llm_item(raw)


def test_rejects_response_without_leading_emoji() -> None:
    with pytest.raises(LLMOutputError):
        parse_llm_item("Steam")
