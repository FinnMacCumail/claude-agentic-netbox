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


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for chat streaming.

    Maintains a Claude Agent session for the duration of the connection.
    Streams responses back to client in real-time. Handles continuous
    conversation with context preservation.

    Protocol:
        Client sends: {"message": "user message text"}
        Server sends: StreamChunk JSON objects with type, content, completed fields

    Args:
        websocket: WebSocket connection from client.
    """
    # PATTERN: Accept WebSocket connection
    await websocket.accept()
    logger.info(f"WebSocket connection accepted from {websocket.client}")

    # Create and start agent session for this WebSocket
    agent = ChatAgent(config)

    try:
        # CRITICAL: Start session before processing queries
        await agent.start_session()
        logger.info("Agent session started for WebSocket")

        # Send connection success message
        connection_chunk = StreamChunk(
            type="connected",
            content="Connected to Netbox chatbox. Ask me about your Netbox infrastructure!",
            completed=False,
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
