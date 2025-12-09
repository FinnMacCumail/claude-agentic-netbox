/**
 * Composable for managing LLM model selection.
 *
 * Handles fetching available models, tracking selected model,
 * and managing model switching state.
 */

import type { ModelInfo, ModelSelectionState } from '~/types/chat'

// LocalStorage key for persisting model selection
const STORAGE_KEY = 'netbox-selected-model'

export const useModelSelection = () => {
  // Load selected model from localStorage if available
  const savedModel = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null

  // Reactive state
  const state = reactive<ModelSelectionState>({
    selectedModel: savedModel || 'auto',
    availableModels: [],
    isLoading: false,
    error: null
  })

  // API configuration
  const config = useRuntimeConfig()
  const apiUrl = config.public.apiUrl || 'http://localhost:8001'

  /**
   * Fetch available models from the API.
   */
  const fetchModels = async () => {
    state.isLoading = true
    state.error = null

    try {
      const response = await $fetch<ModelInfo[]>(`${apiUrl}/models`)
      state.availableModels = response

      // If current selected model is not available, reset to auto
      if (!response.find(m => m.id === state.selectedModel)) {
        state.selectedModel = 'auto'
      }
    } catch (error) {
      console.error('Failed to fetch models:', error)
      state.error = 'Failed to load available models'
      // Set default models as fallback
      state.availableModels = [
        {
          id: 'auto',
          name: 'Claude (Automatic Selection)',
          provider: 'anthropic',
          available: true
        }
      ]
    } finally {
      state.isLoading = false
    }
  }

  /**
   * Select a model by ID and persist to localStorage.
   */
  const selectModel = (modelId: string) => {
    const model = state.availableModels.find(m => m.id === modelId)
    if (model && model.available) {
      state.selectedModel = modelId
      // Persist selection to localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, modelId)
      }
    } else {
      console.warn(`Model ${modelId} is not available`)
    }
  }

  /**
   * Get the currently selected model info.
   */
  const getSelectedModel = computed(() => {
    return state.availableModels.find(m => m.id === state.selectedModel) || null
  })

  /**
   * Get display name for current model.
   */
  const getModelDisplayName = computed(() => {
    const model = getSelectedModel.value
    if (!model) return 'Unknown Model'

    // Special formatting for automatic mode
    if (model.id === 'auto') {
      return 'Auto (Claude)'
    }

    // Shorten long model names for display
    const name = model.name
    if (name.length > 30) {
      return name.substring(0, 27) + '...'
    }
    return name
  })

  /**
   * Check if model switching is available.
   */
  const canSwitchModels = computed(() => {
    return state.availableModels.length > 1
  })

  // Initialize by fetching models on mount
  onMounted(() => {
    fetchModels()
  })

  // Auto-refresh models every 60 seconds
  let refreshInterval: NodeJS.Timeout | null = null

  onMounted(() => {
    refreshInterval = setInterval(() => {
      fetchModels()
    }, 60000)
  })

  onUnmounted(() => {
    if (refreshInterval) {
      clearInterval(refreshInterval)
    }
  })

  return {
    // State
    selectedModel: computed(() => state.selectedModel),
    availableModels: computed(() => state.availableModels),
    isLoading: computed(() => state.isLoading),
    error: computed(() => state.error),

    // Computed
    getSelectedModel,
    getModelDisplayName,
    canSwitchModels,

    // Actions
    fetchModels,
    selectModel
  }
}