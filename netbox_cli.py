#!/usr/bin/env python3
"""
Netbox Chatbox CLI - Interactive and single-query modes.

Command-line interface for querying Netbox infrastructure data through
natural language using the Netbox Chatbox backend.
"""

import argparse
import asyncio
import json
import readline
import sys
from typing import Any, Literal

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal formatting."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


def colored(text: str, color: str, use_color: bool = True) -> str:
    """
    Apply ANSI color to text.

    Args:
        text: Text to colorize.
        color: ANSI color code.
        use_color: Whether to apply colors.

    Returns:
        str: Colored text or plain text if use_color is False.
    """
    if not use_color:
        return text
    return f"{color}{text}{Colors.RESET}"


def print_status(
    icon: str, message: str, color: str = Colors.CYAN, use_color: bool = True
) -> None:
    """
    Print a status message with icon and color.

    Args:
        icon: Emoji or symbol to prefix message.
        message: Status message text.
        color: ANSI color code.
        use_color: Whether to use colors.
    """
    print(colored(f"{icon} {message}", color, use_color))


def print_error(message: str, use_color: bool = True) -> None:
    """
    Print an error message.

    Args:
        message: Error message text.
        use_color: Whether to use colors.
    """
    print_status("❌", f"ERROR: {message}", Colors.BRIGHT_RED, use_color)


def print_warning(message: str, use_color: bool = True) -> None:
    """
    Print a warning message.

    Args:
        message: Warning message text.
        use_color: Whether to use colors.
    """
    print_status("⚠️", f"WARNING: {message}", Colors.BRIGHT_YELLOW, use_color)


async def connect_websocket(
    url: str, timeout: float = 10.0
) -> websockets.WebSocketClientProtocol:
    """
    Establish WebSocket connection to backend.

    Args:
        url: WebSocket URL to connect to.
        timeout: Connection timeout in seconds.

    Returns:
        websockets.WebSocketClientProtocol: Connected WebSocket.

    Raises:
        ConnectionError: If connection fails.
    """
    try:
        websocket = await asyncio.wait_for(
            websockets.connect(url, close_timeout=5), timeout=timeout
        )
        return websocket
    except asyncio.TimeoutError:
        raise ConnectionError(
            f"Connection timeout after {timeout}s. Is the server running?"
        )
    except WebSocketException as e:
        raise ConnectionError(f"WebSocket connection failed: {e}")
    except Exception as e:
        raise ConnectionError(f"Failed to connect: {e}")


async def send_query(
    websocket: websockets.WebSocketClientProtocol,
    query: str,
    verbose: bool = False,
    json_output: bool = False,
    use_color: bool = True,
    timeout: float = 60.0,
) -> tuple[str, bool]:
    """
    Send a query and stream the response.

    Args:
        websocket: Connected WebSocket.
        query: User query text.
        verbose: Show verbose output (tool usage, etc.).
        json_output: Output raw JSON chunks.
        use_color: Use colored output.
        timeout: Query timeout in seconds.

    Returns:
        tuple[str, bool]: Full response text and success status.

    Raises:
        asyncio.TimeoutError: If query times out.
        ConnectionClosed: If WebSocket closes unexpectedly.
    """
    # Send query message
    message = {"message": query}
    await websocket.send(json.dumps(message))

    full_response = ""
    success = True
    start_time = asyncio.get_event_loop().time()

    try:
        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                print_error(
                    f"Query timeout after {timeout}s. Response may be incomplete.",
                    use_color,
                )
                success = False
                break

            # Receive with timeout
            try:
                raw_data = await asyncio.wait_for(
                    websocket.recv(), timeout=max(1.0, timeout - elapsed)
                )
            except asyncio.TimeoutError:
                print_error(f"No response received within {timeout}s", use_color)
                success = False
                break

            data = json.loads(raw_data)

            # JSON output mode - just dump the chunk
            if json_output:
                print(json.dumps(data))
                if data.get("completed"):
                    break
                continue

            # Process different chunk types
            chunk_type = data.get("type")
            content = data.get("content", "")
            completed = data.get("completed", False)

            if chunk_type == "connected":
                # Welcome message
                if verbose:
                    print_status("🔌", content, Colors.BRIGHT_CYAN, use_color)

            elif chunk_type == "text":
                # Text content - stream it
                if content:
                    print(content, end="", flush=True)
                    full_response += content

            elif chunk_type == "tool_use":
                # Tool usage indicator
                if verbose:
                    print(
                        colored(
                            f"\n🔧 [Using tool: {content.replace('Using tool: ', '')}]",
                            Colors.BRIGHT_BLUE,
                            use_color,
                        ),
                        flush=True,
                    )

            elif chunk_type == "thinking":
                # Thinking indicator
                if verbose:
                    print(
                        colored(f"\n💭 [Thinking...]", Colors.DIM, use_color),
                        flush=True,
                    )

            elif chunk_type == "tool_result":
                # Tool result (usually not sent to user, but handle it)
                if verbose:
                    print(
                        colored(
                            f"\n📊 [Tool result: {content[:100]}...]",
                            Colors.DIM,
                            use_color,
                        ),
                        flush=True,
                    )

            elif chunk_type == "error":
                # Error message
                print_error(content, use_color)
                success = False

            # Check if response is complete
            if completed:
                if not json_output and full_response:
                    print()  # Final newline
                break

    except ConnectionClosed:
        print_error("Connection closed unexpectedly", use_color)
        success = False

    return full_response, success


async def single_query_mode(
    url: str,
    query: str,
    verbose: bool = False,
    json_output: bool = False,
    use_color: bool = True,
    timeout: float = 60.0,
) -> int:
    """
    Execute a single query and exit.

    Args:
        url: WebSocket URL.
        query: Query text.
        verbose: Show verbose output.
        json_output: Output raw JSON.
        use_color: Use colored output.
        timeout: Query timeout in seconds.

    Returns:
        int: Exit code (0 for success, 1 for error).
    """
    if not json_output:
        print_status("🔌", "Connecting to Netbox Chatbox...", Colors.CYAN, use_color)

    try:
        websocket = await connect_websocket(url, timeout=10.0)

        if not json_output:
            print_status("✅", "Connected!", Colors.GREEN, use_color)
            if verbose:
                print()

        response, success = await send_query(
            websocket, query, verbose, json_output, use_color, timeout
        )

        await websocket.close()

        if not json_output and verbose:
            print_status(
                "✅" if success else "⚠️",
                "Query completed" if success else "Query completed with errors",
                Colors.GREEN if success else Colors.YELLOW,
                use_color,
            )

        return 0 if success else 1

    except ConnectionError as e:
        print_error(str(e), use_color)
        return 1
    except KeyboardInterrupt:
        if not json_output:
            print("\n")
            print_status("👋", "Interrupted by user", Colors.YELLOW, use_color)
        return 130
    except Exception as e:
        print_error(f"Unexpected error: {e}", use_color)
        return 1


async def interactive_mode(
    url: str,
    verbose: bool = False,
    use_color: bool = True,
    timeout: float = 60.0,
) -> int:
    """
    Run interactive REPL mode.

    Args:
        url: WebSocket URL.
        verbose: Show verbose output.
        use_color: Use colored output.
        timeout: Query timeout in seconds.

    Returns:
        int: Exit code (0 for success, 1 for error).
    """
    print_status("🔌", "Connecting to Netbox Chatbox...", Colors.CYAN, use_color)

    try:
        websocket = await connect_websocket(url, timeout=10.0)

        # Consume the initial "connected" message
        try:
            welcome_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            welcome = json.loads(welcome_data)
            if welcome.get("type") == "connected" and verbose:
                print_status("🔌", welcome.get("content", "Connected"), Colors.BRIGHT_CYAN, use_color)
        except asyncio.TimeoutError:
            pass  # No welcome message, that's ok

        print_status(
            "✅", "Connected! Type your query or 'exit' to quit.", Colors.GREEN, use_color
        )
        print()

        # Setup readline for history and editing
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set editing-mode emacs")

        # REPL loop
        while True:
            try:
                # Read input with prompt - run in executor to not block event loop
                loop = asyncio.get_event_loop()
                prompt_text = colored("netbox> ", Colors.BRIGHT_GREEN, use_color)

                # Use run_in_executor to make input() non-blocking
                query = await loop.run_in_executor(
                    None, lambda: input(prompt_text)
                )
                query = query.strip()

                # Handle exit commands
                if query.lower() in ("exit", "quit", "q"):
                    break

                # Skip empty queries
                if not query:
                    continue

                # Send query and get response
                try:
                    response, success = await send_query(
                        websocket, query, verbose, False, use_color, timeout
                    )
                except ConnectionClosed:
                    print_error("Connection closed by server. Reconnecting...", use_color)
                    # Try to reconnect
                    websocket = await connect_websocket(url, timeout=10.0)
                    # Consume welcome message
                    try:
                        await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    except asyncio.TimeoutError:
                        pass
                    print_status("✅", "Reconnected!", Colors.GREEN, use_color)
                    continue

                # Add spacing between queries
                print()

            except EOFError:
                # Ctrl+D pressed
                print()
                break
            except KeyboardInterrupt:
                # Ctrl+C pressed - just go to next prompt
                print()
                continue

        # Cleanup
        await websocket.close()
        print_status("👋", "Goodbye!", Colors.CYAN, use_color)
        return 0

    except ConnectionError as e:
        print_error(str(e), use_color)
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}", use_color)
        return 1


def main() -> int:
    """
    Main entry point for CLI.

    Returns:
        int: Exit code.
    """
    parser = argparse.ArgumentParser(
        description="Netbox Chatbox CLI - Query your Netbox infrastructure using natural language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single query
  %(prog)s "List all sites"

  # Interactive mode
  %(prog)s --interactive
  %(prog)s -i

  # With options
  %(prog)s --verbose "Show devices in DC1"
  %(prog)s --json "List VLANs" | jq .
  %(prog)s --no-color "Find active devices" | grep device
""",
    )

    parser.add_argument(
        "query",
        nargs="?",
        help="Query to execute (omit for interactive mode)",
    )

    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Run in interactive mode (REPL)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose output (tool usage, thinking, etc.)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON chunks (for piping/processing)",
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    parser.add_argument(
        "--url",
        default="ws://localhost:8001/ws/chat",
        help="WebSocket URL (default: ws://localhost:8001/ws/chat)",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Query timeout in seconds (default: 60)",
    )

    args = parser.parse_args()

    # Determine mode
    if args.interactive:
        # Interactive mode
        if args.query:
            print_error(
                "Cannot specify query in interactive mode", not args.no_color
            )
            return 1

        return asyncio.run(
            interactive_mode(
                args.url,
                args.verbose,
                not args.no_color,
                args.timeout,
            )
        )
    else:
        # Single query mode
        if not args.query:
            parser.print_help()
            return 1

        return asyncio.run(
            single_query_mode(
                args.url,
                args.query,
                args.verbose,
                args.json,
                not args.no_color,
                args.timeout,
            )
        )


if __name__ == "__main__":
    sys.exit(main())
