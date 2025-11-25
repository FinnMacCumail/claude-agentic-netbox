"""
Claude Agent logic for Netbox chatbox.

Manages Claude SDK sessions and message processing for continuous conversations.
"""

import logging
from collections.abc import AsyncIterator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

from backend.config import Config

from backend.mcp_config import get_allowed_netbox_tools, get_netbox_mcp_config
from backend.models import StreamChunk

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    Manages Claude Agent sessions for Netbox queries.

    Uses ClaudeSDKClient for continuous conversation support across multiple
    message exchanges. Each ChatAgent instance maintains a single conversation
    session with context preservation.

    Attributes:
        options: Claude Agent configuration options.
        client: Claude SDK client instance (active during session).
        session_active: Whether a session is currently active.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize agent with configuration.

        Args:
            config: Application configuration with Netbox credentials.

        Example:
            >>> config = Config()
            >>> agent = ChatAgent(config)
            >>> await agent.start_session()
        """
        # PATTERN: Configure ClaudeAgentOptions with MCP servers
        self.options = ClaudeAgentOptions(
            mcp_servers=get_netbox_mcp_config(config),
            allowed_tools=get_allowed_netbox_tools(),
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": (
                    "You are a Netbox infrastructure assistant. "
                    "Help users query and understand their Netbox data. "
                    "Use the Netbox MCP tools to retrieve information. "
                    "Be concise and focus on answering the user's specific question. "
                    "When showing data, format it clearly using markdown tables or lists."
                ),
            },
            permission_mode="acceptEdits",
            include_partial_messages=False,  # Only complete messages
        )
        self.client: ClaudeSDKClient | None = None
        self.session_active = False

    async def start_session(self) -> None:
        """
        Start a new Claude Agent session.

        CRITICAL: Uses async context manager pattern for proper resource management.
        The session remains active until close_session() is called.

        Raises:
            RuntimeError: If a session is already active.
            ValueError: If MCP server configuration is invalid.
        """
        if self.session_active:
            raise RuntimeError("Session already active. Call close_session() first.")

        try:
            # PATTERN: ClaudeSDKClient as async context manager
            # CRITICAL: Manual context entry for long-lived session
            self.client = ClaudeSDKClient(options=self.options)
            await self.client.__aenter__()
            self.session_active = True
            logger.info("Claude Agent session started successfully")
        except Exception as e:
            logger.error(f"Failed to start Claude Agent session: {e}", exc_info=True)
            self.session_active = False
            self.client = None
            raise

    async def query(self, message: str) -> AsyncIterator[StreamChunk]:
        """
        Send query to Claude and stream responses.

        The query is sent to the active session, maintaining conversation context
        from previous queries. Responses are streamed as StreamChunk objects for
        real-time display.

        Args:
            message: User's natural language query about Netbox data.

        Yields:
            StreamChunk: Response chunks with type, content, and completion status.

        Raises:
            RuntimeError: If no active session (call start_session() first).

        Example:
            >>> async for chunk in agent.query("List all sites"):
            ...     print(f"{chunk.type}: {chunk.content}")
        """
        if not self.session_active or not self.client:
            raise RuntimeError("Session not active. Call start_session() first.")

        try:
            # Send query to Claude
            logger.debug(f"Sending query: {message[:100]}...")
            await self.client.query(message)

            # PATTERN: Type-safe message processing
            # CRITICAL: Don't use break, let iteration complete naturally
            found_result = False
            async for msg in self.client.receive_response():
                if isinstance(msg, AssistantMessage):
                    # Process assistant response
                    logger.debug(f"Received AssistantMessage with {len(msg.content)} blocks")
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            # Stream text content
                            if block.text:  # Only yield non-empty text
                                yield StreamChunk(type="text", content=block.text, completed=False)
                        elif isinstance(block, ToolUseBlock):
                            # Tool being used
                            logger.debug(f"Tool use: {block.name}")
                            yield StreamChunk(
                                type="tool_use",
                                content=f"Using tool: {block.name}",
                                completed=False,
                            )
                        elif isinstance(block, ToolResultBlock):
                            # Tool result available
                            if block.content:
                                result_text = (
                                    block.content
                                    if isinstance(block.content, str)
                                    else str(block.content)
                                )
                                logger.debug(
                                    f"Tool result: {result_text[:100]}..."
                                    if len(result_text) > 100
                                    else f"Tool result: {result_text}"
                                )
                                # Don't stream tool results to user, Claude will process them
                                # yield StreamChunk(
                                #     type="tool_result",
                                #     content=result_text,
                                #     completed=False
                                # )

                elif isinstance(msg, ResultMessage):
                    # Final result - conversation turn complete
                    found_result = True
                    logger.info(
                        f"Query completed in {msg.duration_ms}ms, " f"{msg.num_turns} turns"
                    )
                    yield StreamChunk(type="text", content="", completed=True)

                # CRITICAL: Let iteration complete naturally
                if found_result:
                    continue

        except Exception as e:
            # PATTERN: Graceful error handling
            logger.error(f"Query error: {e}", exc_info=True)
            yield StreamChunk(type="error", content=f"Error: {str(e)}", completed=True)

    async def close_session(self) -> None:
        """
        Close the Claude Agent session and cleanup resources.

        CRITICAL: Always call this to properly cleanup the async context manager.
        This should be called when the WebSocket connection closes.
        """
        if self.client and self.session_active:
            try:
                await self.client.__aexit__(None, None, None)  # Manual context exit
                logger.info("Claude Agent session closed successfully")
            except Exception as e:
                logger.error(f"Error closing session: {e}", exc_info=True)
            finally:
                self.session_active = False
                self.client = None
        else:
            logger.debug("No active session to close")
