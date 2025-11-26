<template>
  <div class="connection-status" :class="statusClass">
    <div class="status-indicator">
      <span class="status-dot" :class="dotClass"></span>
      <span class="status-text">{{ statusText }}</span>
    </div>
    <div v-if="showError" class="status-error">
      {{ connectionState.error }}
    </div>
    <button
      v-if="showReconnect"
      @click="$emit('reconnect')"
      class="reconnect-button"
    >
      Reconnect
    </button>
  </div>
</template>

<script setup lang="ts">
import type { ConnectionState } from '~/types/chat'

interface Props {
  connectionState: ConnectionState
}

interface Emits {
  (e: 'reconnect'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const statusClass = computed(() => ({
  'status-connected': props.connectionState.connected,
  'status-connecting': props.connectionState.connecting,
  'status-disconnected': !props.connectionState.connected && !props.connectionState.connecting,
  'status-error': props.connectionState.error !== null
}))

const dotClass = computed(() => ({
  'dot-connected': props.connectionState.connected,
  'dot-connecting': props.connectionState.connecting,
  'dot-disconnected': !props.connectionState.connected && !props.connectionState.connecting
}))

const statusText = computed(() => {
  if (props.connectionState.connected) {
    return 'Connected'
  }
  if (props.connectionState.connecting) {
    return `Connecting${props.connectionState.reconnectAttempts > 0
      ? ` (attempt ${props.connectionState.reconnectAttempts})`
      : ''}...`
  }
  if (props.connectionState.error) {
    return 'Connection Error'
  }
  return 'Disconnected'
})

const showError = computed<boolean>(() =>
  props.connectionState.error !== null && !props.connectionState.connecting
)

const showReconnect = computed<boolean>(() =>
  !props.connectionState.connected &&
  !props.connectionState.connecting &&
  props.connectionState.reconnectAttempts >= 5
)
</script>

<style scoped>
.connection-status {
  @apply flex items-center gap-3 px-4 py-2;
  @apply bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700;
  @apply transition-colors duration-200;
}

.status-indicator {
  @apply flex items-center gap-2;
}

.status-dot {
  @apply w-2 h-2 rounded-full transition-colors duration-200;
}

.dot-connected {
  @apply bg-green-500;
  animation: pulse 2s ease-in-out infinite;
}

.dot-connecting {
  @apply bg-yellow-500;
  animation: pulse 1s ease-in-out infinite;
}

.dot-disconnected {
  @apply bg-red-500;
}

.status-text {
  @apply text-sm font-medium text-gray-700 dark:text-gray-300;
}

.status-error {
  @apply text-sm text-red-600 dark:text-red-400;
}

.reconnect-button {
  @apply px-3 py-1 text-sm font-medium;
  @apply bg-blue-600 hover:bg-blue-700 text-white rounded;
  @apply transition-colors duration-200;
  @apply focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2;
}

/* Status-specific backgrounds */
.status-connected {
  @apply bg-green-50 dark:bg-green-900/10;
}

.status-connecting {
  @apply bg-yellow-50 dark:bg-yellow-900/10;
}

.status-disconnected {
  @apply bg-red-50 dark:bg-red-900/10;
}

.status-error {
  @apply bg-red-50 dark:bg-red-900/10;
}

/* Pulse animation */
@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
  100% {
    opacity: 1;
  }
}
</style>