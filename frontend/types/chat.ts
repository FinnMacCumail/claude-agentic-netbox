/**
 * TypeScript type definitions for the Netbox Chatbox frontend.
 * These types match the backend Pydantic models.
 */

/**
 * Represents a single chat message from user or assistant.
 */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

/**
 * User request to send a message.
 */
export interface ChatRequest {
  message: string
  session_id?: string
}

/**
 * Response from assistant.
 */
export interface ChatResponse {
  message: string
  session_id: string
  completed: boolean
}

/**
 * Streaming response chunk from the WebSocket.
 */
export interface StreamChunk {
  type: 'text' | 'tool_use' | 'tool_result' | 'thinking' | 'error' | 'connected' | 'reset_complete' | 'model_changed'
  content: string
  completed: boolean
  metadata?: {
    model?: ModelInfo | any
    archived_messages?: ChatMessage[]
  }
}

/**
 * Error response from the server.
 */
export interface ErrorResponse {
  error: string
  details?: string
}

/**
 * WebSocket connection state.
 */
export interface ConnectionState {
  connected: boolean
  connecting: boolean
  error: string | null
  reconnectAttempts: number
}

/**
 * Health check response.
 */
export interface HealthResponse {
  status: 'healthy' | 'unhealthy'
  service: string
  version: string
  timestamp?: string
}

/**
 * Message to send via WebSocket.
 */
export interface WebSocketMessage {
  message?: string
  type?: 'message' | 'reset' | 'model_change'
  model?: string
}

/**
 * Model information from the API.
 */
export interface ModelInfo {
  id: string
  name: string
  provider: string
  available: boolean
}

/**
 * Model selection state.
 */
export interface ModelSelectionState {
  selectedModel: string
  availableModels: ModelInfo[]
  isLoading: boolean
  error: string | null
}