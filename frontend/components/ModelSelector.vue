<template>
  <div class="model-selector">
    <!-- Model Indicator Button -->
    <button
      @click="showModal = true"
      :disabled="!canSwitchModels"
      class="model-selector-button"
      :class="{ 'disabled': !canSwitchModels }"
      :title="canSwitchModels ? 'Switch model' : 'Model switching not available'"
    >
      <div class="model-info">
        <span class="model-label">Model:</span>
        <span class="model-name">{{ getModelDisplayName }}</span>
      </div>
      <svg v-if="canSwitchModels" class="chevron-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <!-- Model Selection Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showModal" class="modal-overlay" @click="closeModal">
          <div class="modal-content" @click.stop>
            <div class="modal-header">
              <h2>Select Model</h2>
              <button @click="closeModal" class="close-button" aria-label="Close">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M15 5L5 15M5 5l10 10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </button>
            </div>

            <div class="modal-body">
              <!-- Warning message -->
              <div v-if="selectedModel !== pendingModel" class="warning-message">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M8 1l7 13H1L8 1z" stroke="currentColor" stroke-width="1.5" fill="none"/>
                  <circle cx="8" cy="11" r="0.5" fill="currentColor"/>
                  <path d="M8 5v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
                <span>Switching models will reset your conversation context</span>
              </div>

              <!-- Loading state -->
              <div v-if="isLoading" class="loading-state">
                <LoadingSpinner />
                <span>Loading available models...</span>
              </div>

              <!-- Error state -->
              <div v-else-if="error" class="error-state">
                <span>{{ error }}</span>
                <button @click="fetchModels" class="retry-button">Retry</button>
              </div>

              <!-- Models list -->
              <div v-else class="models-list">
                <div
                  v-for="model in availableModels"
                  :key="model.id"
                  class="model-option"
                  :class="{
                    'selected': model.id === selectedModel,
                    'pending': model.id === pendingModel && model.id !== selectedModel,
                    'unavailable': !model.available
                  }"
                  @click="model.available && selectModelOption(model.id)"
                >
                  <div class="model-option-info">
                    <div class="model-option-name">{{ model.name }}</div>
                    <div class="model-option-meta">
                      <span class="model-provider">{{ model.provider }}</span>
                      <span v-if="!model.available" class="unavailable-badge">Unavailable</span>
                    </div>
                  </div>
                  <div v-if="model.id === selectedModel" class="check-icon">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                      <path d="M4 10l4 4L16 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </div>
                </div>
              </div>

              <!-- Action buttons -->
              <div class="modal-actions">
                <button @click="closeModal" class="cancel-button">Cancel</button>
                <button
                  @click="confirmModelSwitch"
                  :disabled="pendingModel === selectedModel || !pendingModel"
                  class="confirm-button"
                  :class="{ 'disabled': pendingModel === selectedModel || !pendingModel }"
                >
                  Switch Model
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { useModelSelection } from '~/composables/useModelSelection'

// Props
interface Props {
  onModelSwitch?: (modelId: string) => void
}

const props = defineProps<Props>()

// Emit events
const emit = defineEmits<{
  'model-switch': [modelId: string]
}>()

// Use model selection composable
const {
  selectedModel,
  availableModels,
  isLoading,
  error,
  getModelDisplayName,
  canSwitchModels,
  fetchModels,
  selectModel
} = useModelSelection()

// Local state for modal
const showModal = ref(false)
const pendingModel = ref<string | null>(null)

// Watch for selected model changes
watch(selectedModel, (newModel) => {
  pendingModel.value = newModel
})

// Modal actions
const closeModal = () => {
  showModal.value = false
  pendingModel.value = selectedModel.value
}

const selectModelOption = (modelId: string) => {
  pendingModel.value = modelId
}

const confirmModelSwitch = () => {
  if (pendingModel.value && pendingModel.value !== selectedModel.value) {
    selectModel(pendingModel.value)
    emit('model-switch', pendingModel.value)
    props.onModelSwitch?.(pendingModel.value)
  }
  showModal.value = false
}

// Initialize pending model
onMounted(() => {
  pendingModel.value = selectedModel.value
})
</script>

<style scoped>
.model-selector {
  display: inline-block;
}

.model-selector-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  color: inherit;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.model-selector-button:hover:not(.disabled) {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.model-selector-button.disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.model-info {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.model-label {
  opacity: 0.7;
}

.model-name {
  font-weight: 500;
}

.chevron-icon {
  opacity: 0.6;
  transition: transform 0.2s;
}

.model-selector-button:hover .chevron-icon {
  transform: translateY(1px);
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.modal-content {
  background: #2a2a2a;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 1rem;
  max-width: 500px;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.15);
  background: #333333;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #ffffff;
}

.close-button {
  padding: 0.25rem;
  background: none;
  border: none;
  color: #ffffff;
  cursor: pointer;
  opacity: 0.8;
  transition: all 0.2s;
  border-radius: 0.25rem;
}

.close-button:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.1);
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
}

.warning-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(255, 200, 0, 0.1);
  border: 1px solid rgba(255, 200, 0, 0.2);
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  color: #ffc800;
  font-size: 0.875rem;
}

.loading-state,
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  color: rgba(255, 255, 255, 0.6);
}

.retry-button {
  padding: 0.25rem 0.75rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.375rem;
  color: inherit;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-button:hover {
  background: rgba(255, 255, 255, 0.15);
}

.models-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.model-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: #3a3a3a;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  color: #ffffff;
}

.model-option:hover:not(.unavailable) {
  background: #454545;
  border-color: rgba(255, 255, 255, 0.25);
}

.model-option.selected {
  background: rgba(100, 200, 255, 0.2);
  border-color: rgba(100, 200, 255, 0.5);
  color: #ffffff;
}

.model-option.pending {
  background: rgba(255, 200, 0, 0.15);
  border-color: rgba(255, 200, 0, 0.4);
}

.model-option.unavailable {
  opacity: 0.5;
  cursor: not-allowed;
}

.model-option-info {
  flex: 1;
}

.model-option-name {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.model-option-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  opacity: 0.7;
}

.model-provider {
  text-transform: capitalize;
}

.unavailable-badge {
  padding: 0.125rem 0.375rem;
  background: rgba(255, 0, 0, 0.1);
  border: 1px solid rgba(255, 0, 0, 0.2);
  border-radius: 0.25rem;
  color: #ff6b6b;
}

.check-icon {
  color: #64c8ff;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  padding: 1rem 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.cancel-button,
.confirm-button {
  padding: 0.5rem 1.25rem;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-button {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
}

.cancel-button:hover {
  background: rgba(255, 255, 255, 0.1);
}

.confirm-button {
  background: #64c8ff;
  border: 1px solid #64c8ff;
  color: #000;
}

.confirm-button:hover:not(.disabled) {
  background: #4db8ff;
  border-color: #4db8ff;
}

.confirm-button.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal transition */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-content,
.modal-leave-to .modal-content {
  transform: scale(0.9);
}
</style>