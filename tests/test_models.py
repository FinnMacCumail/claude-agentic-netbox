"""
Tests for Pydantic models.

Tests data validation and serialization for API models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.models import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
    StreamChunk,
)


def test_chat_message_valid() -> None:
    """
    Test that ChatMessage accepts valid data.
    """
    message = ChatMessage(role="user", content="Hello")

    assert message.role == "user"
    assert message.content == "Hello"
    assert isinstance(message.timestamp, datetime)


def test_chat_message_rejects_empty_content() -> None:
    """
    Test that ChatMessage rejects empty content.
    """
    with pytest.raises(ValidationError):
        ChatMessage(role="user", content="")


def test_chat_message_strips_whitespace() -> None:
    """
    Test that ChatMessage strips whitespace from content.
    """
    message = ChatMessage(role="user", content="  Hello  ")
    assert message.content == "Hello"


def test_chat_message_rejects_invalid_role() -> None:
    """
    Test that ChatMessage rejects invalid role.
    """
    with pytest.raises(ValidationError):
        ChatMessage(role="invalid", content="Hello")  # type: ignore


def test_chat_request_valid() -> None:
    """
    Test that ChatRequest accepts valid data.
    """
    request = ChatRequest(message="What devices do I have?")

    assert request.message == "What devices do I have?"
    assert request.session_id is None


def test_chat_request_with_session_id() -> None:
    """
    Test that ChatRequest accepts session_id.
    """
    request = ChatRequest(message="Follow up question", session_id="abc123")

    assert request.session_id == "abc123"


def test_chat_request_rejects_empty_message() -> None:
    """
    Test that ChatRequest rejects empty message.
    """
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_request_strips_whitespace() -> None:
    """
    Test that ChatRequest strips whitespace from message.
    """
    request = ChatRequest(message="  Hello  ")
    assert request.message == "Hello"


def test_chat_response_valid() -> None:
    """
    Test that ChatResponse accepts valid data.
    """
    response = ChatResponse(message="I found 5 devices", session_id="abc123", completed=True)

    assert response.message == "I found 5 devices"
    assert response.session_id == "abc123"
    assert response.completed is True


def test_stream_chunk_text_type() -> None:
    """
    Test that StreamChunk accepts text type.
    """
    chunk = StreamChunk(type="text", content="Hello", completed=False)

    assert chunk.type == "text"
    assert chunk.content == "Hello"
    assert chunk.completed is False


def test_stream_chunk_all_types() -> None:
    """
    Test that StreamChunk accepts all valid types.
    """
    valid_types = ["text", "tool_use", "tool_result", "thinking", "error", "connected"]

    for chunk_type in valid_types:
        chunk = StreamChunk(type=chunk_type, content="test", completed=False)  # type: ignore
        assert chunk.type == chunk_type


def test_stream_chunk_rejects_invalid_type() -> None:
    """
    Test that StreamChunk rejects invalid type.
    """
    with pytest.raises(ValidationError):
        StreamChunk(type="invalid", content="test", completed=False)  # type: ignore


def test_stream_chunk_default_completed() -> None:
    """
    Test that StreamChunk defaults completed to False.
    """
    chunk = StreamChunk(type="text", content="test")
    assert chunk.completed is False


def test_stream_chunk_serialization() -> None:
    """
    Test that StreamChunk serializes correctly.
    """
    chunk = StreamChunk(type="text", content="Hello", completed=True)
    data = chunk.model_dump()

    assert data["type"] == "text"
    assert data["content"] == "Hello"
    assert data["completed"] is True


def test_error_response_valid() -> None:
    """
    Test that ErrorResponse accepts valid data.
    """
    error = ErrorResponse(error="Something went wrong", details="Connection timeout")

    assert error.error == "Something went wrong"
    assert error.details == "Connection timeout"


def test_error_response_without_details() -> None:
    """
    Test that ErrorResponse works without details.
    """
    error = ErrorResponse(error="Something went wrong")

    assert error.error == "Something went wrong"
    assert error.details is None


def test_health_response_valid() -> None:
    """
    Test that HealthResponse accepts valid data.
    """
    health = HealthResponse(status="healthy", service="test-service", version="1.0.0")

    assert health.status == "healthy"
    assert health.service == "test-service"
    assert health.version == "1.0.0"


def test_health_response_rejects_invalid_status() -> None:
    """
    Test that HealthResponse rejects invalid status.
    """
    with pytest.raises(ValidationError):
        HealthResponse(status="invalid", service="test")  # type: ignore


def test_health_response_without_version() -> None:
    """
    Test that HealthResponse works without version.
    """
    health = HealthResponse(status="healthy", service="test-service")

    assert health.status == "healthy"
    assert health.version is None
