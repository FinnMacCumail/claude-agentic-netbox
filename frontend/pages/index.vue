<template>
  <div class="app-container">
    <!-- Conversation Sidebar -->
    <ConversationSidebar
      :is-open="sidebarOpen"
      @close="sidebarOpen = false"
    />

    <!-- Main Content Area -->
    <div class="main-content">
      <!-- Header -->
      <header class="chat-header">
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-3">
            <!-- Mobile menu button -->
            <button
              class="mobile-menu-button md:hidden"
              @click="sidebarOpen = !sidebarOpen"
              title="Toggle sidebar"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            <div>
              <h1 class="chat-title">{{ activeConversation?.title || 'Netbox Chatbox' }}</h1>
              <p class="chat-subtitle">Natural language interface for your infrastructure</p>
            </div>
          </div>

          <div class="flex items-center gap-4">
            <ConnectionStatus
              :connection-state="connectionState"
              @reconnect="handleReconnect"
            />
          </div>
        </div>
      </header>

      <!-- Main chat area -->
      <main class="chat-main">
        <ChatHistory
          :messages="displayMessages"
          :is-processing="isProcessing"
          :partial-message="partialMessage"
          @edit="handleEditMessage"
          @regenerate="handleRegenerateMessage"
        />

        <ChatInput
          :disabled="!connectionState.connected"
          :is-processing="isProcessing"
          @send="handleSendMessage"
        />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage } from '~/types/chat'

// Load debug utilities (makes window.dumpConversations() available)
if (process.client) {
  import('~/utils/debug')
}

// Chat socket composable
const {
  messages,
  allMessages,
  partialMessage,
  connectionState,
  isProcessing,
  connect,
  disconnect,
  sendMessage,
  clearMessages,
  loadMessages
} = useChatSocket()

// Conversations composable
const {
  conversations,
  activeConversationId,
  activeConversation,
  createConversation,
  updateConversation,
  startNewConversation,
  clearAllConversations
} = useConversations()

// Sidebar state (mobile)
const sidebarOpen = ref(false)

// Loading state to prevent watch conflicts
const isLoadingMessages = ref(false)

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

/**
 * Display messages - always show current WebSocket messages.
 * Conversations are synced with WebSocket messages via watch.
 */
const displayMessages = computed(() => allMessages.value)

/**
 * Watch messages and sync with active conversation.
 * Only sync when messages are NEW from WebSocket, not when loading from storage.
 */
watch(
  () => allMessages.value,
  (newMessages) => {
    // Skip if we're loading messages from storage (not new messages)
    if (isLoadingMessages.value) {
      console.log('⏭️ Skipping conversation update - loading from storage')
      return
    }

    if (activeConversationId.value && newMessages.length > 0) {
      console.log('💾 Syncing messages to conversation:', activeConversationId.value, newMessages.length, 'messages')
      // Update active conversation with latest messages
      updateConversation(activeConversationId.value, [...newMessages])
    }
  },
  { deep: true }
)

/**
 * Watch active conversation changes and load its messages.
 */
watch(
  () => activeConversationId.value,
  async (newId, oldId) => {
    console.log('⚡ Watch triggered - oldId:', oldId, 'newId:', newId, 'activeConv exists:', !!activeConversation.value)

    // Don't process if IDs are the same (shouldn't happen but just in case)
    if (newId === oldId) {
      console.log('⏭️ Skipping - same conversation ID')
      return
    }

    // Need a valid new ID
    if (!newId) {
      console.log('⏭️ Skipping - no new conversation ID')
      return
    }

    // Get the conversation
    const conv = activeConversation.value
    if (!conv) {
      console.warn('⚠️ Active conversation not found for ID:', newId)
      return
    }

    console.log('🔄 Switching to conversation:', newId, 'Title:', conv.title, 'Messages:', conv.messages.length)

    // Set loading flag to prevent sync watch from triggering
    isLoadingMessages.value = true

    // Load conversation's messages into the chat
    if (conv.messages.length > 0) {
      loadMessages(conv.messages)
      console.log('📥 Loaded', conv.messages.length, 'messages from conversation')
    } else {
      // New empty conversation - clear the chat
      clearMessages()
      console.log('🆕 Empty conversation - cleared chat')
    }

    // Reset loading flag after next tick
    await nextTick()
    isLoadingMessages.value = false
  }
)

/**
 * Handle sending messages.
 */
const handleSendMessage = (message: string) => {
  // Create conversation only if there's no active conversation at all
  if (!activeConversationId.value) {
    console.log('📝 Creating new conversation for first message')
    createConversation()
  }

  console.log('📤 Sending message:', message.substring(0, 50) + '...')

  // Send message via WebSocket (this will add the message to messages via sendMessage)
  if (!sendMessage(message)) {
    console.error('❌ Failed to send message')
  }

  // Close sidebar on mobile after sending
  sidebarOpen.value = false
}

/**
 * Handle reconnection.
 */
const handleReconnect = () => {
  connect()
}

/**
 * Handle edit message action.
 */
const handleEditMessage = (message: ChatMessage) => {
  // TODO: Implement edit functionality
  // This would populate the input with the message content for editing
  console.log('Edit message:', message)
}

/**
 * Handle regenerate message action.
 */
const handleRegenerateMessage = (message: ChatMessage) => {
  // TODO: Implement regenerate functionality
  // This would resend the user message to get a new response
  console.log('Regenerate response for:', message)

  // For now, just resend the message
  if (sendMessage(message.content)) {
    console.log('Regenerating response...')
  }
}

/**
 * Clear localStorage and reset (for testing/debugging).
 */
const handleResetStorage = () => {
  if (confirm('⚠️ Clear all conversation history from localStorage?\n\nThis will delete all saved conversations and cannot be undone.')) {
    console.log('🗑️ Clearing localStorage...')
    clearAllConversations()
    clearMessages()
    console.log('✅ localStorage cleared')
    // Page will auto-create a new conversation
    location.reload()
  }
}

/**
 * Keyboard shortcuts.
 */
const handleKeyboardShortcuts = (event: KeyboardEvent) => {
  // Ctrl+B or Cmd+B to toggle sidebar
  if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
    event.preventDefault()
    sidebarOpen.value = !sidebarOpen.value
  }

  // Ctrl+N or Cmd+N to start new conversation
  if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
    event.preventDefault()
    console.log('⌨️ Keyboard shortcut - New conversation')
    const newConv = startNewConversation()
    // Watch will trigger and clear messages automatically
  }

  // Ctrl+Shift+Delete to reset localStorage (for debugging)
  if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'Delete') {
    event.preventDefault()
    handleResetStorage()
  }
}

// Setup keyboard listeners and initial conversation load
onMounted(async () => {
  window.addEventListener('keydown', handleKeyboardShortcuts)

  // Load initial conversation if one is already active
  // This handles page refresh where useConversations sets active conversation on mount
  await nextTick() // Wait for useConversations to mount and set activeConversationId

  if (activeConversationId.value && activeConversation.value) {
    console.log('🚀 Initial load - Loading active conversation:', activeConversationId.value)

    if (activeConversation.value.messages.length > 0) {
      // Set loading flag
      isLoadingMessages.value = true

      // Load the conversation's messages
      loadMessages(activeConversation.value.messages)
      console.log('📥 Initial load - Loaded', activeConversation.value.messages.length, 'messages')

      // Reset flag
      await nextTick()
      isLoadingMessages.value = false
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyboardShortcuts)
})
</script>

<style scoped>
.app-container {
  @apply h-screen flex bg-white dark:bg-gray-900;
  @apply overflow-hidden;
}

.main-content {
  @apply flex-1 flex flex-col min-w-0;
}

.chat-header {
  @apply px-4 md:px-6 py-4;
  @apply bg-white dark:bg-gray-800;
  @apply border-b border-gray-200 dark:border-gray-700;
  @apply shadow-sm;
}

.mobile-menu-button {
  @apply p-2 rounded-lg;
  @apply text-gray-600 dark:text-gray-400;
  @apply hover:bg-gray-100 dark:hover:bg-gray-700;
  @apply transition-colors;
}

.chat-title {
  @apply text-lg md:text-xl font-semibold;
  @apply text-gray-900 dark:text-gray-100;
  @apply truncate;
}

.chat-subtitle {
  @apply text-xs md:text-sm text-gray-600 dark:text-gray-400;
}

.chat-main {
  @apply flex-1 flex flex-col min-h-0;
}
</style>
