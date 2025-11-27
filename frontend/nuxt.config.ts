// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  // Module configuration
  modules: [
    '@nuxtjs/tailwindcss'
  ],

  // CSS files
  css: ['~/assets/css/main.css'],

  // Runtime configuration
  runtimeConfig: {
    public: {
      wsUrl: process.env.NUXT_PUBLIC_WS_URL || 'ws://localhost:8002/ws/chat',
      apiUrl: process.env.NUXT_PUBLIC_API_URL || 'http://localhost:8002'
    }
  },

  // Typescript strict mode
  typescript: {
    strict: true,
    typeCheck: false  // Disabled temporarily due to vue-tsc issues
  },

  // Enable experimental WebSocket support
  nitro: {
    experimental: {
      websocket: true
    }
  },

  // Tailwind CSS configuration (handled by @nuxtjs/tailwindcss module)
  // css: ['~/assets/css/main.css'],

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
