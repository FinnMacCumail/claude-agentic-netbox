<template>
  <div class="chat-container">
    <!-- Header -->
    <header class="chat-header">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="chat-title">Netbox Chatbox</h1>
          <p class="chat-subtitle">Natural language interface for your infrastructure</p>
        </div>
        <div class="flex items-center gap-4">
          <button
            v-if="messages.length > 0"
            @click="handleClearChat"
            class="clear-button"
          >
            Clear Chat
          </button>
        </div>
      </div>
    </header>

    <!-- Connection Status -->
    <ConnectionStatus
      :connection-state="connectionState"
      @reconnect="handleReconnect"
    />

    <!-- Main chat area -->
    <main class="chat-main">
      <ChatHistory
        :messages="allMessages"
        :is-processing="isProcessing"
        :partial-message="partialMessage"
      />

      <ChatInput
        :disabled="!connectionState.connected"
        :is-processing="isProcessing"
        @send="handleSendMessage"
      />
    </main>
  </div>
</template>

<script setup lang="ts">
// Use the chat socket composable
const {
  messages,
  allMessages,
  partialMessage,
  connectionState,
  isProcessing,
  connect,
  disconnect,
  sendMessage,
  clearMessages
} = useChatSocket()

// SEO metadata
useHead({
  title: 'Netbox Chatbox - Natural Language Infrastructure Interface',
  meta: [
    {
      name: 'description',
      content: 'Query your Netbox infrastructure using natural language powered by Claude AI'
    }
  ]
})

// Handle sending messages
const handleSendMessage = (message: string) => {
  if (!sendMessage(message)) {
    // Could show an error toast here
    console.error('Failed to send message')
  }
}

// Handle reconnection
const handleReconnect = () => {
  connect()
}

// Handle clearing chat
const handleClearChat = () => {
  if (confirm('Are you sure you want to clear the chat history?')) {
    clearMessages()
  }
}

// Keyboard shortcuts
const handleKeyboardShortcuts = (event: KeyboardEvent) => {
  // Ctrl+K or Cmd+K to clear chat
  if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
    event.preventDefault()
    if (messages.value.length > 0) {
      handleClearChat()
    }
  }
}

// Setup keyboard listeners
onMounted(() => {
  window.addEventListener('keydown', handleKeyboardShortcuts)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyboardShortcuts)
})
</script>

<style scoped>
.clear-button {
  @apply px-3 py-1.5 text-sm font-medium;
  @apply text-gray-700 dark:text-gray-300;
  @apply bg-gray-100 dark:bg-gray-700;
  @apply hover:bg-gray-200 dark:hover:bg-gray-600;
  @apply rounded-lg transition-colors;
  @apply focus:outline-none focus:ring-2 focus:ring-gray-500;
}
</style>