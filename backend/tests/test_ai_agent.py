"""_extract_text must handle every content shape different Gemini model versions return -
this is exactly the kind of thing that only breaks in production against a real model."""

from app.services.ai_agent import _extract_text


def test_plain_string_content():
    assert _extract_text("hello") == "hello"


def test_list_of_text_blocks():
    content = [{"type": "text", "text": "hello "}, {"type": "text", "text": "world"}]
    assert _extract_text(content) == "hello world"


def test_list_of_plain_strings():
    assert _extract_text(["hello ", "world"]) == "hello world"


def test_list_ignores_non_text_blocks():
    content = [{"type": "text", "text": "answer"}, {"type": "tool_use", "id": "x"}]
    assert _extract_text(content) == "answer"


def test_empty_list_returns_empty_string():
    assert _extract_text([]) == ""


def test_unexpected_type_returns_empty_string():
    assert _extract_text(None) == ""
