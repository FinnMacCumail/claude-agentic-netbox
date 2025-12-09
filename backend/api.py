"""
FastAPI server with WebSocket support for Netbox Chatbox.

Provides REST API and WebSocket endpoints for real-time chat with Claude Agent.
"""

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend import __version__
from backend.agent import ChatAgent
from backend.config import Config
from backend.models import HealthResponse, StreamChunk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Response models
class ModelInfo(BaseModel):
    """Model information response."""
    id: str
    name: str
    provider: str = "anthropic"
    available: bool = True


# Global config instance
config: Config


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown tasks including configuration validation.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Application runs between startup and shutdown.
    """
    # Startup
    global config
    logger.info("Starting Netbox Chatbox API")
    try:
        config = Config()
        # Set logging level from config
        logging.getLogger().setLevel(config.log_level.upper())
        logger.info(f"Configuration loaded: {config}")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Netbox Chatbox API")


# PATTERN: Initialize FastAPI app with lifespan
app = FastAPI(
    title="Netbox Chatbox API",
    description="Backend API for Netbox chatbox with Claude Agent SDK",
    version=__version__,
    lifespan=lifespan,
)

# PATTERN: CORS middleware for frontend access
# In production, restrict to specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse: Service health status.
    """
    return HealthResponse(
        status="healthy",
        service="netbox-chatbox-api",
        version=__version__,
    )


@app.get("/models", response_model=list[ModelInfo])
async def get_models() -> list[ModelInfo]:
    """
    Get available Claude models.

    Returns:
        list[ModelInfo]: List of available Claude models.
    """
    return [
        ModelInfo(
            id="auto",
            name="Claude (Automatic Selection)",
            provider="anthropic",
            available=True,
        ),
        ModelInfo(
            id="claude-sonnet-4-5-20250929",
            name="Claude Sonnet 4.5",
            provider="anthropic",
            available=True,
        ),
        ModelInfo(
            id="claude-opus-4-20250514",
            name="Claude Opus 4",
            provider="anthropic",
            available=True,
        ),
        ModelInfo(
            id="claude-haiku-4-5-20250925",
            name="Claude Haiku 4.5",
            provider="anthropic",
            available=True,
        ),
    ]


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for chat streaming.

    Maintains a Claude Agent session for the duration of the connection.
    Streams responses back to client in real-time. Handles continuous
    conversation with context preservation.

    Protocol:
        Client sends: {"message": "user message text"}
        Client sends: {"type": "reset"} to reset conversation
        Client sends: {"type": "model_change", "model": "claude-sonnet-4-5-20250929"} to switch models
        Server sends: StreamChunk JSON objects with type, content, completed fields

    Args:
        websocket: WebSocket connection from client.
    """
    # PATTERN: Accept WebSocket connection
    await websocket.accept()
    logger.info(f"WebSocket connection accepted from {websocket.client}")

    # Create agent with automatic model selection initially
    current_model = None  # None = automatic selection
    agent = ChatAgent(config, model=current_model)

    try:
        # CRITICAL: Start session before processing queries
        await agent.start_session()
        logger.info(f"Agent session started for WebSocket (model: {current_model or 'auto'})")

        # Send connection success message with model info
        model_info = agent.get_model_info()
        connection_chunk = StreamChunk(
            type="connected",
            content=f"Connected to Netbox chatbox. Ask me about your Netbox infrastructure!",
            completed=False,
            metadata={"model": model_info}
        )
        await websocket.send_json(connection_chunk.model_dump())

        # Main message loop
        while True:
            # PATTERN: Receive message from client
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received message: {data[:100]}...")
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected by client")
                break

            try:
                message_data = json.loads(data)

                # PATTERN: Handle model change request
                if message_data.get("type") == "model_change":
                    new_model_id = message_data.get("model")
                    logger.info(f"Switching model from {current_model or 'auto'} to {new_model_id}")

                    # Map "auto" to None for SDK
                    model_param = None if new_model_id == "auto" else new_model_id

                    try:
                        # Close current session
                        await agent.close_session()

                        # Create new agent with new model
                        current_model = model_param
                        agent = ChatAgent(config, model=current_model)
                        await agent.start_session()

                        logger.info(f"Model switched successfully")

                        # Send confirmation to client
                        model_info = agent.get_model_info()
                        model_chunk = StreamChunk(
                            type="model_changed",
                            content=f"Switched to {model_info['model_display']}. Context has been reset.",
                            completed=False,
                            metadata={"model": model_info}
                        )
                        await websocket.send_json(model_chunk.model_dump())
                        continue
                    except Exception as model_error:
                        logger.error(f"Error during model switch: {model_error}", exc_info=True)
                        error_chunk = StreamChunk(
                            type="error",
                            content=f"Failed to switch model: {str(model_error)}",
                            completed=True,
                        )
                        await websocket.send_json(error_chunk.model_dump())
                        continue

                # PATTERN: Handle session reset request
                if message_data.get("type") == "reset":
                    logger.info("Received reset request - clearing conversation context")
                    try:
                        # Close current session (clears Claude's conversation memory)
                        await agent.close_session()
                        # Start fresh session (new context, same model)
                        await agent.start_session()
                        logger.info("Session reset complete - new conversation context")

                        # Send confirmation to client
                        reset_chunk = StreamChunk(
                            type="reset_complete",
                            content="Conversation context has been reset. Starting fresh!",
                            completed=True,
                        )
                        await websocket.send_json(reset_chunk.model_dump())
                        continue
                    except Exception as reset_error:
                        logger.error(f"Error during session reset: {reset_error}", exc_info=True)
                        error_chunk = StreamChunk(
                            type="error",
                            content=f"Failed to reset session: {str(reset_error)}",
                            completed=True,
                        )
                        await websocket.send_json(error_chunk.model_dump())
                        continue

                user_message = message_data.get("message", "")

                if not user_message:
                    error_chunk = StreamChunk(
                        type="error",
                        content="Empty message received",
                        completed=True,
                    )
                    await websocket.send_json(error_chunk.model_dump())
                    continue

                # PATTERN: Stream responses from agent
                async for chunk in agent.query(user_message):
                    # Send each chunk to client
                    try:
                        await websocket.send_json(chunk.model_dump())
                    except Exception as e:
                        logger.error(f"Error sending chunk: {e}")
                        break

            except json.JSONDecodeError:
                logger.error("Invalid JSON received from client")
                error_chunk = StreamChunk(
                    type="error",
                    content='Invalid JSON format. Expected: {"message": "your message"}',
                    completed=True,
                )
                try:
                    await websocket.send_json(error_chunk.model_dump())
                except Exception:
                    break
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                error_chunk = StreamChunk(
                    type="error",
                    content=f"Error processing message: {str(e)}",
                    completed=True,
                )
                try:
                    await websocket.send_json(error_chunk.model_dump())
                except Exception:
                    break

    except WebSocketDisconnect:
        # PATTERN: Handle disconnection gracefully
        logger.info("WebSocket disconnected during processing")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # CRITICAL: Always close agent session
        await agent.close_session()
        logger.info("Agent session closed for WebSocket")


if __name__ == "__main__":
    """
    Run the server directly with uvicorn.

    For development: python -m backend.api
    For production: uvicorn backend.api:app --host 0.0.0.0 --port 8000
    """
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
