"""
Helper utilities for Netbox Chatbox backend.

Provides utility functions for message formatting, logging, and data processing.
"""

import logging
from typing import Any

from claude_agent_sdk import AssistantMessage, TextBlock, ToolResultBlock, ToolUseBlock

from backend.models import StreamChunk

logger = logging.getLogger(__name__)


def format_message_for_display(message: Any) -> str:
    """
    Format a Claude SDK message for display.

    Extracts text content from various message types and formats them
    for human-readable display.

    Args:
        message: Message object from Claude SDK (AssistantMessage, etc.).

    Returns:
        str: Formatted message text.

    Example:
        >>> message = AssistantMessage(content=[TextBlock(text="Hello")])
        >>> formatted = format_message_for_display(message)
        >>> print(formatted)  # "Hello"
    """
    if isinstance(message, AssistantMessage):
        parts = []
        for block in message.content:
            if isinstance(block, TextBlock):
                parts.append(block.text)
            elif isinstance(block, ToolUseBlock):
                parts.append(f"[Using tool: {block.name}]")
            elif isinstance(block, ToolResultBlock):
                if block.content:
                    content_str = (
                        block.content if isinstance(block.content, str) else str(block.content)
                    )
                    parts.append(f"[Tool result: {content_str[:100]}...]")
        return "\n".join(parts)
    else:
        return str(message)


def extract_text_from_blocks(blocks: list[Any]) -> str:
    """
    Extract text content from a list of content blocks.

    Args:
        blocks: List of content blocks from Claude SDK message.

    Returns:
        str: Concatenated text from all TextBlock instances.

    Example:
        >>> blocks = [
        ...     TextBlock(text="Hello"),
        ...     ToolUseBlock(name="test", input={}),
        ...     TextBlock(text="World")
        ... ]
        >>> text = extract_text_from_blocks(blocks)
        >>> print(text)  # "Hello World"
    """
    text_parts = []
    for block in blocks:
        if isinstance(block, TextBlock) and block.text:
            text_parts.append(block.text)
    return " ".join(text_parts)


def create_stream_chunk(
    chunk_type: str,
    content: str,
    completed: bool = False,
) -> StreamChunk:
    """
    Create a StreamChunk object with validation.

    Helper function to create StreamChunk instances with proper type checking
    and validation.

    Args:
        chunk_type: Type of chunk (text, tool_use, tool_result, thinking, error, connected).
        content: Chunk content.
        completed: Whether this is the final chunk.

    Returns:
        StreamChunk: Validated stream chunk object.

    Raises:
        ValueError: If chunk_type is invalid.

    Example:
        >>> chunk = create_stream_chunk("text", "Hello", completed=False)
        >>> print(chunk.type, chunk.content, chunk.completed)
        text Hello False
    """
    valid_types = {"text", "tool_use", "tool_result", "thinking", "error", "connected"}
    if chunk_type not in valid_types:
        raise ValueError(
            f"Invalid chunk type: {chunk_type}. Must be one of: {', '.join(valid_types)}"
        )

    return StreamChunk(
        type=chunk_type,  # type: ignore
        content=content,
        completed=completed,
    )


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure application logging.

    Sets up logging format, level, and handlers for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Example:
        >>> setup_logging("DEBUG")
        >>> logger.debug("This will be logged")
    """
    # Configure root logger
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    logger.info(f"Logging configured with level: {log_level}")


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: Text to truncate.
        max_length: Maximum length before truncation.
        suffix: Suffix to add when text is truncated.

    Returns:
        str: Truncated text with suffix if needed.

    Example:
        >>> long_text = "A" * 150
        >>> truncated = truncate_text(long_text, max_length=50)
        >>> len(truncated)  # 53 (50 + len("..."))
        53
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error message for user display.

    Removes sensitive information from error messages before displaying to users.

    Args:
        error: Exception object.

    Returns:
        str: Sanitized error message safe for user display.

    Example:
        >>> error = ValueError("Invalid API key: sk-ant-xxxxx")
        >>> sanitized = sanitize_error_message(error)
        >>> print(sanitized)  # Removes sensitive key
        Invalid API key: sk-ant-***
    """
    error_msg = str(error)

    # Remove API keys
    import re

    error_msg = re.sub(r"sk-ant-[a-zA-Z0-9]+", "sk-ant-***", error_msg)

    # Remove tokens (40 hex chars)
    error_msg = re.sub(r"\b[a-f0-9]{40}\b", "***", error_msg)

    # Remove paths that might contain usernames
    error_msg = re.sub(r"/home/[^/]+/", "/home/***/", error_msg)

    return error_msg
