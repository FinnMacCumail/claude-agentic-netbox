"""
Tests for utility functions.

Tests helper functions for message formatting and data processing.
"""

import pytest

from backend.models import StreamChunk
from backend.utils import (
    create_stream_chunk,
    sanitize_error_message,
    truncate_text,
)


def test_create_stream_chunk_text() -> None:
    """
    Test creating a text stream chunk.
    """
    chunk = create_stream_chunk("text", "Hello", completed=False)

    assert isinstance(chunk, StreamChunk)
    assert chunk.type == "text"
    assert chunk.content == "Hello"
    assert chunk.completed is False


def test_create_stream_chunk_all_types() -> None:
    """
    Test creating stream chunks of all valid types.
    """
    valid_types = ["text", "tool_use", "tool_result", "thinking", "error", "connected"]

    for chunk_type in valid_types:
        chunk = create_stream_chunk(chunk_type, "test content")
        assert chunk.type == chunk_type
        assert chunk.content == "test content"


def test_create_stream_chunk_invalid_type() -> None:
    """
    Test that create_stream_chunk raises error for invalid type.
    """
    with pytest.raises(ValueError) as exc_info:
        create_stream_chunk("invalid_type", "test")

    assert "Invalid chunk type" in str(exc_info.value)


def test_create_stream_chunk_completed() -> None:
    """
    Test creating a completed stream chunk.
    """
    chunk = create_stream_chunk("text", "Done", completed=True)
    assert chunk.completed is True


def test_truncate_text_short() -> None:
    """
    Test that truncate_text doesn't truncate short text.
    """
    text = "Short text"
    truncated = truncate_text(text, max_length=100)
    assert truncated == text


def test_truncate_text_long() -> None:
    """
    Test that truncate_text truncates long text.
    """
    text = "A" * 150
    truncated = truncate_text(text, max_length=50)

    assert len(truncated) == 53  # 50 + len("...")
    assert truncated.endswith("...")
    assert truncated.startswith("AAA")


def test_truncate_text_exact_length() -> None:
    """
    Test that truncate_text handles exact length.
    """
    text = "A" * 100
    truncated = truncate_text(text, max_length=100)
    assert truncated == text


def test_truncate_text_custom_suffix() -> None:
    """
    Test that truncate_text uses custom suffix.
    """
    text = "A" * 150
    truncated = truncate_text(text, max_length=50, suffix="[...]")

    assert truncated.endswith("[...]")
    assert len(truncated) == 55  # 50 + len("[...]")


def test_sanitize_error_message_removes_api_key() -> None:
    """
    Test that sanitize_error_message removes API keys.
    """
    error = ValueError("Failed with key: sk-ant-1234567890abcdefghijklmnopqrstuvwxyz01")
    sanitized = sanitize_error_message(error)

    assert "sk-ant-" not in sanitized or "sk-ant-***" in sanitized
    assert "1234567890abcdefghijklmnopqrstuvwxyz01" not in sanitized


def test_sanitize_error_message_removes_tokens() -> None:
    """
    Test that sanitize_error_message removes tokens.
    """
    error = ValueError("Token: abcdef1234567890abcdef1234567890abcdef12")
    sanitized = sanitize_error_message(error)

    assert "abcdef1234567890abcdef1234567890abcdef12" not in sanitized
    assert "***" in sanitized


def test_sanitize_error_message_removes_paths() -> None:
    """
    Test that sanitize_error_message removes user paths.
    """
    error = ValueError("File not found: /home/username/secret/file.txt")
    sanitized = sanitize_error_message(error)

    assert "username" not in sanitized
    assert "/home/***/" in sanitized


def test_sanitize_error_message_keeps_safe_content() -> None:
    """
    Test that sanitize_error_message keeps safe content.
    """
    error = ValueError("Connection failed: timeout")
    sanitized = sanitize_error_message(error)

    assert "Connection failed" in sanitized
    assert "timeout" in sanitized


def test_sanitize_error_message_handles_multiple_secrets() -> None:
    """
    Test that sanitize_error_message handles multiple secrets.
    """
    error = ValueError(
        "Error with key sk-ant-abcd1234567890abcdef1234567890abcdef12 "
        "and token ef0123456789abcdef0123456789abcdef012345"
    )
    sanitized = sanitize_error_message(error)

    assert "sk-ant-abcd" not in sanitized
    assert "ef0123456789" not in sanitized
    assert "***" in sanitized
