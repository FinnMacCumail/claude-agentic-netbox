<template>
  <div class="chat-message" :class="messageClass">
    <div class="message-header">
      <span class="message-role">{{ roleLabel }}</span>
      <span class="message-time">{{ formattedTime }}</span>
    </div>
    <div class="message-content" v-html="formattedContent"></div>
  </div>
</template>

<script setup lang="ts">
import type { ChatMessage } from '~/types/chat'
import { formatTime, formatMarkdown } from '~/utils/formatters'

interface Props {
  message: ChatMessage
}

const props = defineProps<Props>()

const messageClass = computed(() => ({
  'user-message': props.message.role === 'user',
  'assistant-message': props.message.role === 'assistant'
}))

const roleLabel = computed(() =>
  props.message.role === 'user' ? 'You' : 'Netbox Assistant'
)

const formattedTime = computed(() =>
  formatTime(props.message.timestamp)
)

const formattedContent = computed(() => {
  if (props.message.role === 'assistant') {
    // Format markdown for assistant messages
    return formatMarkdown(props.message.content)
  }
  // Escape HTML for user messages
  return props.message.content.replace(/</g, '&lt;').replace(/>/g, '&gt;')
})
</script>

<style scoped>
.chat-message {
  @apply mb-4 p-4 rounded-lg;
}

.user-message {
  @apply bg-blue-50 dark:bg-blue-900/20 ml-8;
}

.assistant-message {
  @apply bg-gray-50 dark:bg-gray-800/50 mr-8;
}

.message-header {
  @apply flex justify-between items-center mb-2 text-sm;
}

.message-role {
  @apply font-semibold text-gray-700 dark:text-gray-300;
}

.message-time {
  @apply text-gray-500 dark:text-gray-400;
}

.message-content {
  @apply text-gray-800 dark:text-gray-200;
}

/* Style markdown content */
.message-content :deep(h1) {
  @apply text-xl font-bold mt-4 mb-2;
}

.message-content :deep(h2) {
  @apply text-lg font-semibold mt-3 mb-2;
}

.message-content :deep(h3) {
  @apply text-base font-semibold mt-2 mb-1;
}

.message-content :deep(p) {
  @apply mb-2;
}

.message-content :deep(ul) {
  @apply list-disc list-inside mb-2 ml-4;
}

.message-content :deep(ol) {
  @apply list-decimal list-inside mb-2 ml-4;
}

.message-content :deep(code) {
  @apply bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm;
}

.message-content :deep(pre) {
  @apply bg-gray-100 dark:bg-gray-800 p-3 rounded-md overflow-x-auto mb-2;
}

.message-content :deep(pre code) {
  @apply bg-transparent p-0;
}

.message-content :deep(blockquote) {
  @apply border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic my-2;
}

.message-content :deep(a) {
  @apply text-blue-600 dark:text-blue-400 underline hover:text-blue-800 dark:hover:text-blue-300;
}

.message-content :deep(table) {
  @apply w-full border-collapse my-2;
}

.message-content :deep(th) {
  @apply bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 px-2 py-1 text-left;
}

.message-content :deep(td) {
  @apply border border-gray-300 dark:border-gray-600 px-2 py-1;
}
</style>