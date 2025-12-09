"""
Pydantic models for API requests and responses.

Defines data structures used in the Netbox Chatbox API.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatMessage(BaseModel):
    """
    Single chat message from user or assistant.

    Attributes:
        role: Message sender role ('user' or 'assistant').
        content: Message text content.
        timestamp: When the message was created (UTC).
    """

    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        """
        Validate that content is not empty.

        Args:
            v: Content value to validate.

        Returns:
            str: Validated content.

        Raises:
            ValueError: If content is empty or only whitespace.
        """
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()


class ChatRequest(BaseModel):
    """
    User request to send a message.

    Attributes:
        message: User's message text.
        session_id: Optional session identifier for conversation continuity.
    """

    message: str
    session_id: str | None = None

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        """
        Validate that message is not empty.

        Args:
            v: Message value to validate.

        Returns:
            str: Validated message.

        Raises:
            ValueError: If message is empty or only whitespace.
        """
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class ChatResponse(BaseModel):
    """
    Response from assistant.

    Attributes:
        message: Assistant's response message.
        session_id: Session identifier for this conversation.
        completed: Whether the response is complete.
    """

    message: str
    session_id: str
    completed: bool


class StreamChunk(BaseModel):
    """
    Streaming response chunk sent over WebSocket.

    Attributes:
        type: Type of chunk (text, tool_use, tool_result, thinking, error, connected, reset_complete, model_changed).
        content: Chunk content (text, status message, error message, etc.).
        completed: Whether this is the final chunk of the response.
        metadata: Optional metadata (model info, etc.).
    """

    type: Literal["text", "tool_use", "tool_result", "thinking", "error", "connected", "reset_complete", "model_changed"]
    content: str
    completed: bool = False
    metadata: dict | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "text",
                    "content": "I found 5 devices in your Netbox instance.",
                    "completed": False,
                },
                {
                    "type": "tool_use",
                    "content": "Using tool: netbox_get_objects",
                    "completed": False,
                },
                {"type": "text", "content": "", "completed": True},
                {
                    "type": "model_changed",
                    "content": "Switched to claude-sonnet-4-5",
                    "completed": False,
                    "metadata": {"model": "claude-sonnet-4-5-20250929"}
                },
            ]
        }
    )


class ErrorResponse(BaseModel):
    """
    Error response.

    Attributes:
        error: Error message.
        details: Optional detailed error information.
    """

    error: str
    details: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": "Invalid message format",
                    "details": "Message cannot be empty",
                },
                {"error": "MCP server connection failed", "details": None},
            ]
        }
    )


class HealthResponse(BaseModel):
    """
    Health check response.

    Attributes:
        status: Health status ('healthy' or 'unhealthy').
        service: Service name.
        version: Optional service version.
    """

    status: Literal["healthy", "unhealthy"]
    service: str
    version: str | None = None
