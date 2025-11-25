<template>
  <div class="chat-input-container">
    <form @submit.prevent="handleSubmit" class="chat-input-form">
      <textarea
        v-model="message"
        @keydown="handleKeyDown"
        :disabled="disabled"
        :placeholder="placeholder"
        class="chat-textarea"
        rows="3"
        ref="textareaRef"
      ></textarea>
      <div class="chat-input-actions">
        <span class="input-hint">{{ hint }}</span>
        <button
          type="submit"
          :disabled="!canSend"
          class="send-button"
          :class="{ 'send-button-disabled': !canSend }"
        >
          <span v-if="isProcessing">Sending...</span>
          <span v-else>Send</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
interface Props {
  disabled?: boolean
  isProcessing?: boolean
  placeholder?: string
}

interface Emits {
  (e: 'send', message: string): void
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  isProcessing: false,
  placeholder: 'Ask about your Netbox infrastructure...'
})

const emit = defineEmits<Emits>()

const message = ref('')
const textareaRef = ref<HTMLTextAreaElement>()

const canSend = computed(() =>
  !props.disabled &&
  !props.isProcessing &&
  message.value.trim().length > 0
)

const hint = computed(() => {
  if (props.isProcessing) {
    return 'Processing your message...'
  }
  if (props.disabled) {
    return 'Chat is disabled'
  }
  return 'Press Enter to send, Shift+Enter for new line'
})

const handleSubmit = () => {
  if (canSend.value) {
    emit('send', message.value.trim())
    message.value = ''
    // Focus textarea after sending
    nextTick(() => {
      textareaRef.value?.focus()
    })
  }
}

const handleKeyDown = (event: KeyboardEvent) => {
  // Send on Enter, unless Shift is held
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSubmit()
  }
}

// Auto-focus on mount
onMounted(() => {
  textareaRef.value?.focus()
})
</script>

<style scoped>
.chat-input-container {
  @apply border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4;
}

.chat-input-form {
  @apply space-y-2;
}

.chat-textarea {
  @apply w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg;
  @apply bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100;
  @apply focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent;
  @apply resize-none transition-colors;
  @apply placeholder-gray-500 dark:placeholder-gray-400;
}

.chat-textarea:disabled {
  @apply bg-gray-100 dark:bg-gray-800 cursor-not-allowed opacity-60;
}

.chat-input-actions {
  @apply flex justify-between items-center;
}

.input-hint {
  @apply text-sm text-gray-500 dark:text-gray-400;
}

.send-button {
  @apply px-4 py-2 bg-blue-600 text-white rounded-lg font-medium;
  @apply hover:bg-blue-700 active:bg-blue-800 transition-colors;
  @apply focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2;
}

.send-button-disabled {
  @apply bg-gray-400 dark:bg-gray-600 cursor-not-allowed;
  @apply hover:bg-gray-400 dark:hover:bg-gray-600;
}
</style>