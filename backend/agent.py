"""
Claude Agent logic for Netbox chatbox.

Manages Claude SDK sessions and message processing for continuous conversations.
"""

import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path

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
from backend.anonymization.mapping_service import MappingService
from backend.anonymization.query_anonymizer import QueryAnonymizer
from backend.anonymization.response_restorer import ResponseRestorer
from backend.mcp_config import get_allowed_netbox_tools, get_netbox_mcp_config
from backend.models import StreamChunk

logger = logging.getLogger(__name__)

# Configure LangSmith tracing if enabled
# Reason: LangSmith integration must be configured before creating Claude SDK client
_langsmith_configured = False


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
        model: Optional explicit model selection.
    """

    def __init__(self, config: Config, model: str | None = None) -> None:
        """
        Initialize agent with configuration and optional model specification.

        Args:
            config: Application configuration with Netbox credentials.
            model: Optional explicit model (e.g., "claude-sonnet-4-5-20250929").
                   If None, SDK uses automatic routing (Haiku/Sonnet/Opus).

        Example:
            >>> config = Config()
            >>> # Automatic routing (recommended)
            >>> agent = ChatAgent(config, model=None)
            >>> # Explicit model
            >>> agent = ChatAgent(config, model="claude-sonnet-4-5-20250929")
            >>> await agent.start_session()
        """
        self.model = model
        self.config = config

        # Initialize anonymization services if enabled
        self.query_anonymizer = None
        self.response_restorer = None

        if config.anonymization_enabled and config.anonymization_mode == "greenmask":
            try:
                mappings_file = Path("backend/anonymization/mappings/mappings_latest.json")
                if mappings_file.exists():
                    logger.info(f"Loading anonymization mappings from {mappings_file}")
                    mapping_service = MappingService(str(mappings_file))
                    mapping_service.load_mappings()

                    self.query_anonymizer = QueryAnonymizer(mapping_service)
                    self.response_restorer = ResponseRestorer(mapping_service)

                    stats = mapping_service.get_stats()
                    logger.info(f"Anonymization enabled: {stats['mappings_count']} mappings loaded")
                else:
                    logger.warning(f"Anonymization enabled but mapping file not found: {mappings_file}")
            except Exception as e:
                logger.error(f"Failed to initialize anonymization: {e}", exc_info=True)

        # Configure LangSmith tracing if enabled
        # Reason: One-time configuration per process, must happen before creating SDK client
        global _langsmith_configured
        if config.langchain_tracing_v2 and not _langsmith_configured:
            try:
                from langsmith.integrations.claude_agent_sdk import configure_claude_agent_sdk

                # Set environment variables for LangSmith
                if config.langchain_api_key:
                    os.environ["LANGCHAIN_API_KEY"] = config.langchain_api_key
                os.environ["LANGCHAIN_PROJECT"] = config.langchain_project

                configure_claude_agent_sdk()
                _langsmith_configured = True
                logger.info(
                    f"LangSmith tracing enabled for project '{config.langchain_project}'"
                )
            except ImportError:
                logger.warning(
                    "LangSmith tracing requested but langsmith package not installed. "
                    "Install with: pip install 'langsmith[claude-agent-sdk]'"
                )
            except Exception as e:
                logger.warning(f"Failed to configure LangSmith tracing: {e}")
        elif config.langchain_tracing_v2 and _langsmith_configured:
            logger.debug("LangSmith tracing already configured")

        # PATTERN: Configure ClaudeAgentOptions with MCP servers and model
        self.options = ClaudeAgentOptions(
            model=model,  # KEY: Explicit model or None for automatic
            fallback_model=None,  # No fallback for explicit model selection
            mcp_servers=get_netbox_mcp_config(config),
            allowed_tools=get_allowed_netbox_tools(),
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": (
                    "You are a NetBox infrastructure assistant with semantic understanding of network relationships. "

                    "## CRITICAL OPTIMIZATION RULES:\n"
                    "1. ALWAYS use the 'fields' parameter to minimize token usage (90% reduction possible)\n"
                    "2. NEVER request all fields unless explicitly asked for complete objects\n"
                    "3. Start with 'brief=true' for overview queries, then drill down with specific fields\n"
                    "4. Use 'netbox_search_objects' for global queries when object type is unknown\n"
                    "5. Use 'netbox_get_objects' when you know the specific object type\n\n"

                    "## COMMON FIELD PATTERNS:\n"
                    "- Devices: fields=['id', 'name', 'status', 'device_type', 'site', 'primary_ip4']\n"
                    "- IP Addresses: fields=['id', 'address', 'status', 'dns_name', 'description', 'vrf']\n"
                    "- Sites: fields=['id', 'name', 'status', 'region', 'description', 'facility']\n"
                    "- Interfaces: fields=['id', 'name', 'type', 'enabled', 'device']\n"
                    "- VLANs: fields=['id', 'vid', 'name', 'status', 'site', 'description']\n"
                    "- Racks: fields=['id', 'name', 'site', 'status', 'u_height', 'facility_id']\n"
                    "- Circuits: fields=['id', 'cid', 'provider', 'type', 'status', 'description']\n"
                    "- Virtual Machines: fields=['id', 'name', 'status', 'cluster', 'vcpus', 'memory']\n\n"

                    "## QUERY OPTIMIZATION WORKFLOW:\n"
                    "1. Analyze user question to determine required data\n"
                    "2. Select minimal field set that answers the question\n"
                    "3. Use pagination (limit/offset) for large datasets\n"
                    "4. Leverage ordering to get most relevant results first\n"
                    "5. For counting: use fields=['id'] only\n\n"

                    "## SEMANTIC INFRASTRUCTURE UNDERSTANDING:\n"
                    "- Understand NetBox object relationships: Device → Site → Region\n"
                    "- Interface → Device, IP Address → Interface → Device\n"
                    "- VLAN → Site, Circuit → Provider\n"
                    "- Use two-step queries for cross-relationship filtering\n"
                    "- Remember: Multi-hop filters like 'device__site_id' are NOT supported\n\n"

                    "## OUTPUT FORMATTING:\n"
                    "- Present results as concise markdown tables\n"
                    "- Highlight key information relevant to user's question\n"
                    "- Include summary statistics when appropriate\n"
                    "- For large result sets, show sample + summary (e.g., 'Showing 10 of 247 total')\n"
                    "- Always mention if results are paginated and how to get more\n\n"

                    "Your goal: Provide accurate, efficient answers using minimal tokens while maintaining clarity."
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
            # Anonymize query if enabled
            query_to_send = message
            if self.query_anonymizer:
                anonymization_result = self.query_anonymizer.anonymize(message)
                if anonymization_result.mappings_applied:
                    logger.info(f"Anonymized {anonymization_result.entities_found} entities in query")
                    for orig, anon in anonymization_result.mappings_applied.items():
                        logger.debug(f"  {orig} -> {anon[:16]}...")
                    query_to_send = anonymization_result.anonymized_query
                else:
                    logger.debug("No entities to anonymize in query")

            # Send query to Claude
            logger.debug(f"Sending query: {query_to_send[:100]}...")
            await self.client.query(query_to_send)

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
                                # Restore anonymized values if enabled
                                text_to_send = block.text
                                if self.response_restorer:
                                    restoration_result = self.response_restorer.restore(block.text)
                                    if restoration_result.restorations_applied:
                                        logger.debug(f"Restored {len(restoration_result.restorations_applied)} values in response")
                                        text_to_send = restoration_result.restored_response
                                yield StreamChunk(type="text", content=text_to_send, completed=False)
                        elif isinstance(block, ToolUseBlock):
                            # Tool being used
                            logger.debug(f"Tool use: {block.name}")
                            # Restore any anonymized values in tool use display
                            tool_msg = f"Using tool: {block.name}"
                            if self.response_restorer:
                                restoration_result = self.response_restorer.restore(tool_msg)
                                if restoration_result.restorations_applied:
                                    tool_msg = restoration_result.restored_response
                            yield StreamChunk(
                                type="tool_use",
                                content=tool_msg,
                                completed=False,
                            )
                        elif isinstance(block, ToolResultBlock):
                            # Tool result available - for display purposes (Claude synthesizes these)
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

    def get_model_info(self) -> dict:
        """
        Get information about the current model.

        Returns:
            dict: Model information including name and routing mode
        """
        return {
            "model": self.model if self.model else "automatic",
            "model_display": self.model if self.model else "Claude (Automatic Selection)",
            "is_automatic": self.model is None,
        }
