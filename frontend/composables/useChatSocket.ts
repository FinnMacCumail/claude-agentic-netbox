/**
 * WebSocket composable for managing chat connections and messages.
 * Handles connection lifecycle, message sending/receiving, and reconnection logic.
 */

import type { ChatMessage, StreamChunk, ConnectionState, WebSocketMessage } from '~/types/chat'

export const useChatSocket = () => {
  const config = useRuntimeConfig()

  // Reactive state
  const socket = ref<WebSocket | null>(null)
  const messages = ref<ChatMessage[]>([])
  const connectionState = ref<ConnectionState>({
    connected: false,
    connecting: false,
    error: null,
    reconnectAttempts: 0
  })
  const currentAssistantMessage = ref<string>('')
  const isProcessing = ref(false)

  // Configuration
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAY_MS = 2000

  /**
   * Connect to the WebSocket server.
   */
  const connect = () => {
    if (connectionState.value.connecting || connectionState.value.connected) {
      return
    }

    connectionState.value.connecting = true
    connectionState.value.error = null

    try {
      socket.value = new WebSocket(config.public.wsUrl)

      socket.value.onopen = () => {
        console.log('WebSocket connected')
        connectionState.value.connected = true
        connectionState.value.connecting = false
        connectionState.value.reconnectAttempts = 0
        connectionState.value.error = null
      }

      socket.value.onmessage = (event) => {
        try {
          const chunk: StreamChunk = JSON.parse(event.data)
          handleStreamChunk(chunk)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
          connectionState.value.error = 'Failed to parse server message'
        }
      }

      socket.value.onerror = (error) => {
        console.error('WebSocket error:', error)
        connectionState.value.error = 'Connection error occurred'
      }

      socket.value.onclose = () => {
        console.log('WebSocket closed')
        connectionState.value.connected = false
        connectionState.value.connecting = false

        // Attempt to reconnect if not at max attempts
        if (connectionState.value.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
          connectionState.value.reconnectAttempts++
          console.log(`Reconnecting... (attempt ${connectionState.value.reconnectAttempts})`)
          setTimeout(connect, RECONNECT_DELAY_MS)
        } else {
          connectionState.value.error = 'Maximum reconnection attempts reached'
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      connectionState.value.connecting = false
      connectionState.value.error = 'Failed to establish connection'
    }
  }

  /**
   * Handle incoming stream chunks from the WebSocket.
   */
  const handleStreamChunk = (chunk: StreamChunk) => {
    switch (chunk.type) {
      case 'text':
        // Accumulate text content for assistant message
        currentAssistantMessage.value += chunk.content

        // If this chunk completes the message, add it to messages
        if (chunk.completed) {
          if (currentAssistantMessage.value.trim()) {
            messages.value.push({
              role: 'assistant',
              content: currentAssistantMessage.value,
              timestamp: new Date().toISOString()
            })
          }
          currentAssistantMessage.value = ''
          isProcessing.value = false
        }
        break

      case 'tool_use':
        // Show tool usage in a subtle way
        if (!chunk.completed) {
          currentAssistantMessage.value += `\n🔧 Using Netbox tool: ${chunk.content}\n`
        }
        break

      case 'tool_result':
        // Tool results are usually internal, but we can show them if needed
        if (!chunk.completed && chunk.content) {
          currentAssistantMessage.value += `\n📊 Tool result received\n`
        }
        break

      case 'thinking':
        // Optionally show thinking process (usually hidden)
        console.log('Assistant thinking:', chunk.content)
        break

      case 'error':
        // Handle error messages
        console.error('Stream error:', chunk.content)
        messages.value.push({
          role: 'assistant',
          content: `❌ Error: ${chunk.content}`,
          timestamp: new Date().toISOString()
        })
        currentAssistantMessage.value = ''
        isProcessing.value = false
        break
    }
  }

  /**
   * Send a message through the WebSocket.
   */
  const sendMessage = (message: string) => {
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected')
      connectionState.value.error = 'Not connected to server'
      return false
    }

    if (!message.trim()) {
      return false
    }

    try {
      // Add user message to history
      messages.value.push({
        role: 'user',
        content: message,
        timestamp: new Date().toISOString()
      })

      // Send message via WebSocket
      const wsMessage: WebSocketMessage = { message }
      socket.value.send(JSON.stringify(wsMessage))

      // Set processing state
      isProcessing.value = true
      currentAssistantMessage.value = ''

      return true
    } catch (error) {
      console.error('Failed to send message:', error)
      connectionState.value.error = 'Failed to send message'
      isProcessing.value = false
      return false
    }
  }

  /**
   * Disconnect from the WebSocket server.
   */
  const disconnect = () => {
    if (socket.value) {
      socket.value.close()
      socket.value = null
    }
    connectionState.value.connected = false
    connectionState.value.connecting = false
    connectionState.value.reconnectAttempts = 0
  }

  /**
   * Clear all messages.
   */
  const clearMessages = () => {
    messages.value = []
    currentAssistantMessage.value = ''
  }

  /**
   * Get the current partial assistant message (for live streaming display).
   */
  const partialMessage = computed(() => currentAssistantMessage.value)

  /**
   * Get all messages including the current partial message.
   */
  const allMessages = computed(() => {
    const all = [...messages.value]
    if (currentAssistantMessage.value) {
      all.push({
        role: 'assistant',
        content: currentAssistantMessage.value,
        timestamp: new Date().toISOString()
      })
    }
    return all
  })

  // Auto-connect on mount and disconnect on unmount
  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    // State
    messages: readonly(messages),
    allMessages,
    partialMessage,
    connectionState: readonly(connectionState),
    isProcessing: readonly(isProcessing),

    // Actions
    connect,
    disconnect,
    sendMessage,
    clearMessages
  }
}