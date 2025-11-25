"""
Unit tests for Netbox CLI tool.

Tests the CLI functions and modes without requiring a live backend server.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import CLI functions
import sys
from pathlib import Path

# Add parent dir to path to import netbox_cli
sys.path.insert(0, str(Path(__file__).parent.parent))

import netbox_cli


class TestColors:
    """Test color formatting functions."""

    def test_colored_with_color(self) -> None:
        """Test colored() applies ANSI codes when use_color=True."""
        result = netbox_cli.colored("test", netbox_cli.Colors.RED, use_color=True)
        assert result == f"{netbox_cli.Colors.RED}test{netbox_cli.Colors.RESET}"

    def test_colored_without_color(self) -> None:
        """Test colored() returns plain text when use_color=False."""
        result = netbox_cli.colored("test", netbox_cli.Colors.RED, use_color=False)
        assert result == "test"

    def test_colored_empty_string(self) -> None:
        """Test colored() handles empty strings."""
        result = netbox_cli.colored("", netbox_cli.Colors.GREEN)
        assert result == f"{netbox_cli.Colors.GREEN}{netbox_cli.Colors.RESET}"


class TestConnectWebsocket:
    """Test WebSocket connection function."""

    @pytest.mark.asyncio
    async def test_successful_connection(self) -> None:
        """Test successful WebSocket connection."""
        mock_ws = AsyncMock()

        # Make connect return an awaitable
        async def mock_connect(*args: tuple, **kwargs: dict) -> AsyncMock:
            return mock_ws

        with patch("websockets.connect", side_effect=mock_connect):
            result = await netbox_cli.connect_websocket("ws://localhost:8001/ws/chat")
            assert result == mock_ws

    @pytest.mark.asyncio
    async def test_connection_timeout(self) -> None:
        """Test connection timeout handling."""
        async def slow_connect(*args: tuple, **kwargs: dict) -> None:
            await asyncio.sleep(10)

        with patch("websockets.connect", side_effect=slow_connect):
            with pytest.raises(ConnectionError, match="Connection timeout"):
                await netbox_cli.connect_websocket(
                    "ws://localhost:8001/ws/chat", timeout=0.1
                )

    @pytest.mark.asyncio
    async def test_connection_refused(self) -> None:
        """Test handling of connection refused."""
        with patch("websockets.connect", side_effect=ConnectionRefusedError("Refused")):
            with pytest.raises(ConnectionError, match="Failed to connect"):
                await netbox_cli.connect_websocket("ws://localhost:8001/ws/chat")


class TestSendQuery:
    """Test query sending and response handling."""

    @pytest.mark.asyncio
    async def test_simple_text_response(self, capsys: pytest.CaptureFixture) -> None:
        """Test handling of simple text response."""
        mock_ws = AsyncMock()
        responses = [
            json.dumps({"type": "text", "content": "Hello", "completed": False}),
            json.dumps({"type": "text", "content": " World", "completed": False}),
            json.dumps({"type": "text", "content": "", "completed": True}),
        ]
        mock_ws.recv = AsyncMock(side_effect=responses)
        mock_ws.send = AsyncMock()

        response, success = await netbox_cli.send_query(
            mock_ws, "test query", use_color=False
        )

        assert response == "Hello World"
        assert success is True
        captured = capsys.readouterr()
        assert "Hello World" in captured.out

    @pytest.mark.asyncio
    async def test_tool_use_verbose(self, capsys: pytest.CaptureFixture) -> None:
        """Test tool usage display in verbose mode."""
        mock_ws = AsyncMock()
        responses = [
            json.dumps(
                {"type": "tool_use", "content": "Using tool: netbox_get_objects", "completed": False}
            ),
            json.dumps({"type": "text", "content": "Found 5 sites", "completed": False}),
            json.dumps({"type": "text", "content": "", "completed": True}),
        ]
        mock_ws.recv = AsyncMock(side_effect=responses)
        mock_ws.send = AsyncMock()

        response, success = await netbox_cli.send_query(
            mock_ws, "test query", verbose=True, use_color=False
        )

        assert "Found 5 sites" in response
        assert success is True
        captured = capsys.readouterr()
        assert "netbox_get_objects" in captured.out

    @pytest.mark.asyncio
    async def test_error_response(self, capsys: pytest.CaptureFixture) -> None:
        """Test error response handling."""
        mock_ws = AsyncMock()
        responses = [
            json.dumps(
                {"type": "error", "content": "Something went wrong", "completed": True}
            ),
        ]
        mock_ws.recv = AsyncMock(side_effect=responses)
        mock_ws.send = AsyncMock()

        response, success = await netbox_cli.send_query(
            mock_ws, "test query", use_color=False
        )

        assert success is False
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "Something went wrong" in captured.out

    @pytest.mark.asyncio
    async def test_json_output_mode(self, capsys: pytest.CaptureFixture) -> None:
        """Test JSON output mode."""
        mock_ws = AsyncMock()
        chunk1 = {"type": "text", "content": "Hello", "completed": False}
        chunk2 = {"type": "text", "content": "", "completed": True}
        responses = [json.dumps(chunk1), json.dumps(chunk2)]
        mock_ws.recv = AsyncMock(side_effect=responses)
        mock_ws.send = AsyncMock()

        response, success = await netbox_cli.send_query(
            mock_ws, "test query", json_output=True
        )

        captured = capsys.readouterr()
        # Should output raw JSON
        assert json.dumps(chunk1) in captured.out
        assert json.dumps(chunk2) in captured.out

    @pytest.mark.asyncio
    async def test_query_timeout(self, capsys: pytest.CaptureFixture) -> None:
        """Test query timeout handling."""
        mock_ws = AsyncMock()

        async def slow_recv() -> str:
            await asyncio.sleep(10)
            return json.dumps({"type": "text", "content": "slow", "completed": False})

        mock_ws.recv = AsyncMock(side_effect=slow_recv)
        mock_ws.send = AsyncMock()

        response, success = await netbox_cli.send_query(
            mock_ws, "test query", timeout=0.1, use_color=False
        )

        assert success is False
        captured = capsys.readouterr()
        # Either "timeout" or "No response" message is acceptable
        assert ("timeout" in captured.out.lower() or "no response" in captured.out.lower())

    @pytest.mark.asyncio
    async def test_connection_closed(self) -> None:
        """Test handling of unexpected connection closure."""
        from websockets.exceptions import ConnectionClosed as WSConnectionClosed

        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=WSConnectionClosed(None, None))
        mock_ws.send = AsyncMock()

        response, success = await netbox_cli.send_query(
            mock_ws, "test query", use_color=False
        )

        assert success is False


class TestSingleQueryMode:
    """Test single query mode."""

    @pytest.mark.asyncio
    async def test_successful_query(self, capsys: pytest.CaptureFixture) -> None:
        """Test successful single query."""
        mock_ws = AsyncMock()
        responses = [
            json.dumps({"type": "text", "content": "Result", "completed": False}),
            json.dumps({"type": "text", "content": "", "completed": True}),
        ]
        mock_ws.recv = AsyncMock(side_effect=responses)
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()

        with patch("netbox_cli.connect_websocket", return_value=mock_ws):
            exit_code = await netbox_cli.single_query_mode(
                "ws://test", "test query", use_color=False
            )

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Result" in captured.out

    @pytest.mark.asyncio
    async def test_connection_failure(self, capsys: pytest.CaptureFixture) -> None:
        """Test handling of connection failure."""
        with patch(
            "netbox_cli.connect_websocket",
            side_effect=ConnectionError("Failed to connect"),
        ):
            exit_code = await netbox_cli.single_query_mode(
                "ws://test", "test query", use_color=False
            )

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "ERROR" in captured.out

    @pytest.mark.asyncio
    async def test_json_output(self, capsys: pytest.CaptureFixture) -> None:
        """Test JSON output in single query mode."""
        mock_ws = AsyncMock()
        chunk = {"type": "text", "content": "Test", "completed": True}
        responses = [json.dumps(chunk)]
        mock_ws.recv = AsyncMock(side_effect=responses)
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()

        with patch("netbox_cli.connect_websocket", return_value=mock_ws):
            exit_code = await netbox_cli.single_query_mode(
                "ws://test", "test query", json_output=True
            )

        assert exit_code == 0
        captured = capsys.readouterr()
        assert json.dumps(chunk) in captured.out


class TestInteractiveMode:
    """Test interactive mode."""

    @pytest.mark.asyncio
    async def test_exit_command(self, capsys: pytest.CaptureFixture) -> None:
        """Test exiting interactive mode with 'exit' command."""
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        # Mock the welcome message
        welcome_msg = json.dumps({"type": "connected", "content": "Welcome", "completed": False})
        mock_ws.recv = AsyncMock(return_value=welcome_msg)

        # Mock input to return "exit"
        with patch("netbox_cli.connect_websocket", return_value=mock_ws):
            with patch("builtins.input", return_value="exit"):
                exit_code = await netbox_cli.interactive_mode(
                    "ws://test", use_color=False
                )

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Goodbye" in captured.out

    @pytest.mark.asyncio
    async def test_quit_command(self) -> None:
        """Test exiting with 'quit' command."""
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        # Mock the welcome message
        welcome_msg = json.dumps({"type": "connected", "content": "Welcome", "completed": False})
        mock_ws.recv = AsyncMock(return_value=welcome_msg)

        with patch("netbox_cli.connect_websocket", return_value=mock_ws):
            with patch("builtins.input", return_value="quit"):
                exit_code = await netbox_cli.interactive_mode("ws://test")

        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_eof(self) -> None:
        """Test exiting with EOF (Ctrl+D)."""
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        # Mock the welcome message
        welcome_msg = json.dumps({"type": "connected", "content": "Welcome", "completed": False})
        mock_ws.recv = AsyncMock(return_value=welcome_msg)

        with patch("netbox_cli.connect_websocket", return_value=mock_ws):
            with patch("builtins.input", side_effect=EOFError()):
                exit_code = await netbox_cli.interactive_mode("ws://test")

        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_connection_failure(self) -> None:
        """Test handling connection failure in interactive mode."""
        with patch(
            "netbox_cli.connect_websocket",
            side_effect=ConnectionError("Failed"),
        ):
            exit_code = await netbox_cli.interactive_mode("ws://test")

        assert exit_code == 1


class TestMain:
    """Test main() function and argument parsing."""

    def test_help_output(self, capsys: pytest.CaptureFixture) -> None:
        """Test --help flag."""
        with patch("sys.argv", ["netbox_cli.py", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                netbox_cli.main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Netbox Chatbox CLI" in captured.out

    def test_no_query_no_interactive(self, capsys: pytest.CaptureFixture) -> None:
        """Test error when neither query nor --interactive provided."""
        with patch("sys.argv", ["netbox_cli.py"]):
            exit_code = netbox_cli.main()

        assert exit_code == 1

    def test_query_and_interactive_conflict(self, capsys: pytest.CaptureFixture) -> None:
        """Test error when both query and --interactive provided."""
        with patch("sys.argv", ["netbox_cli.py", "--interactive", "test query"]):
            exit_code = netbox_cli.main()

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "ERROR" in captured.out

    def test_single_query_mode_invocation(self) -> None:
        """Test that single query mode is invoked correctly."""
        with patch("sys.argv", ["netbox_cli.py", "test query"]):
            with patch("netbox_cli.asyncio.run") as mock_run:
                mock_run.return_value = 0
                exit_code = netbox_cli.main()

        assert exit_code == 0
        assert mock_run.called

    def test_interactive_mode_invocation(self) -> None:
        """Test that interactive mode is invoked correctly."""
        with patch("sys.argv", ["netbox_cli.py", "--interactive"]):
            with patch("netbox_cli.asyncio.run") as mock_run:
                mock_run.return_value = 0
                exit_code = netbox_cli.main()

        assert exit_code == 0
        assert mock_run.called
