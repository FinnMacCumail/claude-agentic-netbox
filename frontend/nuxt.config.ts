// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  // Module configuration
  modules: [
    '@nuxt/ui',
    '@nuxtjs/tailwindcss'
  ],

  // Runtime configuration
  runtimeConfig: {
    public: {
      wsUrl: process.env.NUXT_PUBLIC_WS_URL || 'ws://localhost:8001/ws/chat',
      apiUrl: process.env.NUXT_PUBLIC_API_URL || 'http://localhost:8001'
    }
  },

  // Typescript strict mode
  typescript: {
    strict: true,
    typeCheck: true
  },

  // Enable experimental WebSocket support
  nitro: {
    experimental: {
      websocket: true
    }
  },

  // Tailwind CSS configuration
  css: ['~/assets/css/main.css'],

  // App configuration
  app: {
    head: {
      title: 'Netbox Chatbox',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Natural language interface for Netbox infrastructure data' }
      ]
    }
  },

  // Development server configuration
  devServer: {
    port: 3000
  },

  // Auto imports
  imports: {
    dirs: ['types', 'utils']
  }
})
