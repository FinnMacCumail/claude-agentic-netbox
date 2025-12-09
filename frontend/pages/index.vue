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
            <ModelSelector
              :on-model-switch="handleModelSwitch"
            />
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
        />

        <ChatInput
          :disabled="!connectionState.connected"
          :is-processing="isProcessing"
          :edit-mode="editingMessageIndex !== null"
          :initial-value="editingContent"
          @send="handleSendMessage"
          @update="handleUpdateMessage"
          @cancel="handleCancelEdit"
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
  currentModel,
  archivedMessages,
  connect,
  disconnect,
  sendMessage,
  sendMessageOnly,
  clearMessages,
  loadMessages,
  resetSession,
  switchModel
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

// Edit mode state
const editingMessageIndex = ref<number | null>(null)
const editingContent = ref('')

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
 * Handle model switching.
 */
const handleModelSwitch = (modelId: string) => {
  console.log('🔄 Switching to model:', modelId)

  // Switch model via WebSocket
  if (!switchModel(modelId)) {
    console.error('❌ Failed to switch model')
    return
  }

  // The backend will handle the context reset and send model_changed message
  // which will trigger clearMessages() and archive the old messages
}

/**
 * Handle starting a new conversation with backend reset.
 */
const handleNewConversation = () => {
  console.log('🆕 Starting new conversation with backend reset')

  // Reset backend session (clears Claude's context)
  if (resetSession()) {
    console.log('✅ Backend reset request sent')
    // Backend will send reset_complete message which triggers clearMessages()
  } else {
    console.error('❌ Failed to send backend reset request')
    // Still create new conversation even if reset fails
  }

  // Create new frontend conversation
  const newConv = startNewConversation()
  console.log('📝 Created new conversation:', newConv.id)
}

/**
 * Handle edit message action.
 */
const handleEditMessage = (message: ChatMessage) => {
  console.log('📝 Editing message:', message.content.substring(0, 50))

  // Find the message index in the messages array
  const index = allMessages.value.findIndex(
    m => m.timestamp === message.timestamp && m.role === 'user'
  )

  if (index === -1) {
    console.error('❌ Message not found for editing')
    return
  }

  // Set editing state
  editingMessageIndex.value = index
  editingContent.value = message.content
  console.log('✅ Edit mode activated for message at index:', index)
}

/**
 * Handle updating an edited message.
 */
const handleUpdateMessage = (newContent: string) => {
  if (editingMessageIndex.value === null) {
    console.error('❌ No message being edited')
    return
  }

  console.log('💾 Updating message at index:', editingMessageIndex.value)

  // Create a copy of messages and update the edited message
  const updatedMessages = [...messages.value]
  updatedMessages[editingMessageIndex.value] = {
    ...updatedMessages[editingMessageIndex.value],
    content: newContent
  }

  // Remove all messages after the edited one (context has changed)
  const messagesToKeep = updatedMessages.slice(0, editingMessageIndex.value + 1)

  // Update the messages in the composable
  loadMessages(messagesToKeep)

  // Update conversation storage
  if (activeConversationId.value) {
    updateConversation(activeConversationId.value, messagesToKeep)
    console.log('✅ Conversation updated with edited message')
  }

  // Send the edited message to get a new response (without adding to array again)
  sendMessageOnly(newContent)

  // Clear editing state
  editingMessageIndex.value = null
  editingContent.value = ''
  console.log('✅ Edit mode deactivated')
}

/**
 * Handle canceling an edit.
 */
const handleCancelEdit = () => {
  console.log('🚫 Edit canceled')
  editingMessageIndex.value = null
  editingContent.value = ''
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
    handleNewConversation()
    // Backend reset will clear messages, watch will handle conversation switch
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
