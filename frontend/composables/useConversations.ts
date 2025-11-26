/**
 * Composable for managing chat conversations with localStorage persistence.
 * Provides CRUD operations and state management for conversation history.
 *
 * IMPORTANT: This composable uses shared state (singleton pattern) so that
 * all components that call useConversations() share the same state.
 */
import type { ChatMessage } from '~/types/chat'

export interface Conversation {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: string
  updatedAt: string
}

const STORAGE_KEY = 'netbox-conversations'
const MAX_TITLE_LENGTH = 60

/**
 * Generate a title from the first user message.
 */
const generateTitle = (messages: ChatMessage[]): string => {
  const firstUserMessage = messages.find(m => m.role === 'user')
  if (!firstUserMessage) return 'New Conversation'

  const content = firstUserMessage.content.trim()
  if (content.length <= MAX_TITLE_LENGTH) return content

  return content.substring(0, MAX_TITLE_LENGTH - 3) + '...'
}

/**
 * Generate a unique conversation ID.
 */
const generateId = (): string => {
  return `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// SHARED STATE - These refs are created once at module level
// so all components share the same state
const conversations = ref<Conversation[]>([])
const activeConversationId = ref<string | null>(null)
let isInitialized = false

export const useConversations = () => {

  /**
   * Load conversations from localStorage.
   */
  const loadConversations = () => {
    conversations.value = getItem<Conversation[]>(STORAGE_KEY, [])

    // Sort by updatedAt descending (most recent first)
    conversations.value.sort((a, b) =>
      new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )
  }

  /**
   * Save conversations to localStorage.
   */
  const saveConversations = () => {
    setItem(STORAGE_KEY, conversations.value)
  }

  /**
   * Get the currently active conversation.
   */
  const activeConversation = computed(() => {
    if (!activeConversationId.value) return null
    return conversations.value.find(c => c.id === activeConversationId.value) || null
  })

  /**
   * Create a new conversation.
   */
  const createConversation = (initialMessage?: ChatMessage): Conversation => {
    const now = new Date().toISOString()
    const messages = initialMessage ? [initialMessage] : []

    const conversation: Conversation = {
      id: generateId(),
      title: initialMessage ? generateTitle([initialMessage]) : 'New Conversation',
      messages,
      createdAt: now,
      updatedAt: now
    }

    conversations.value.unshift(conversation)
    activeConversationId.value = conversation.id
    saveConversations()

    console.log('➕ Created conversation:', conversation.id, 'Title:', conversation.title)
    return conversation
  }

  /**
   * Update conversation messages and auto-generate title if needed.
   */
  const updateConversation = (conversationId: string, messages: ChatMessage[]) => {
    const conversation = conversations.value.find(c => c.id === conversationId)
    if (!conversation) {
      console.warn('⚠️ updateConversation: Conversation not found:', conversationId)
      return
    }

    const oldTitle = conversation.title
    conversation.messages = messages
    conversation.updatedAt = new Date().toISOString()

    // Auto-generate title from first user message if still default
    if (conversation.title === 'New Conversation' && messages.length > 0) {
      conversation.title = generateTitle(messages)
      console.log('✨ Generated title:', conversation.title)
    }

    // Move to top of list
    const index = conversations.value.findIndex(c => c.id === conversationId)
    if (index > 0) {
      conversations.value.splice(index, 1)
      conversations.value.unshift(conversation)
      console.log('📌 Moved conversation to top of list')
    }

    saveConversations()
    console.log('💾 Conversation updated and saved:', conversationId, 'Messages:', messages.length)
  }

  /**
   * Rename a conversation.
   */
  const renameConversation = (conversationId: string, newTitle: string) => {
    const conversation = conversations.value.find(c => c.id === conversationId)
    if (!conversation) return false

    conversation.title = newTitle.trim() || 'Untitled Conversation'
    conversation.updatedAt = new Date().toISOString()
    saveConversations()

    return true
  }

  /**
   * Delete a conversation.
   */
  const deleteConversation = (conversationId: string): boolean => {
    const index = conversations.value.findIndex(c => c.id === conversationId)
    if (index === -1) return false

    conversations.value.splice(index, 1)

    // If deleted conversation was active, switch to most recent or null
    if (activeConversationId.value === conversationId) {
      activeConversationId.value = conversations.value.length > 0
        ? conversations.value[0].id
        : null
    }

    saveConversations()
    return true
  }

  /**
   * Set the active conversation.
   */
  const setActiveConversation = (conversationId: string | null) => {
    if (conversationId && !conversations.value.find(c => c.id === conversationId)) {
      console.warn(`⚠️ Conversation ${conversationId} not found in shared state`)
      console.log('Available conversations:', conversations.value.map(c => c.id))
      return false
    }

    const conv = conversationId ? conversations.value.find(c => c.id === conversationId) : null
    console.log('👉 Setting active conversation:', conversationId, 'Title:', conv?.title || 'None')
    activeConversationId.value = conversationId
    return true
  }

  /**
   * Start a new conversation (create and set as active).
   */
  const startNewConversation = () => {
    const conversation = createConversation()
    return conversation
  }

  /**
   * Clear all conversations.
   */
  const clearAllConversations = () => {
    conversations.value = []
    activeConversationId.value = null
    saveConversations()
  }

  /**
   * Get conversation by ID.
   */
  const getConversation = (conversationId: string): Conversation | null => {
    return conversations.value.find(c => c.id === conversationId) || null
  }

  // Initialize on first mount only (singleton pattern)
  onMounted(() => {
    if (!isInitialized) {
      isInitialized = true
      console.log('🔧 Initializing useConversations (singleton)')

      loadConversations()
      console.log('📚 Loaded conversations from localStorage:', conversations.value.length)

      // If no conversations exist, create initial one
      if (conversations.value.length === 0) {
        console.log('🆕 No conversations found - creating initial one')
        startNewConversation()
      } else {
        // Set most recent as active
        activeConversationId.value = conversations.value[0].id
        console.log('👉 Set most recent conversation as active:', activeConversationId.value)
      }
    } else {
      console.log('✅ useConversations already initialized (reusing shared state)')
    }
  })

  return {
    conversations: readonly(conversations),
    activeConversationId: readonly(activeConversationId),
    activeConversation,
    createConversation,
    updateConversation,
    renameConversation,
    deleteConversation,
    setActiveConversation,
    startNewConversation,
    clearAllConversations,
    getConversation
  }
}
