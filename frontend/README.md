# Netbox Chatbox Frontend

A Nuxt 3 frontend application providing a natural language chat interface for querying Netbox infrastructure data.

## Features

- 🚀 Real-time WebSocket communication with backend
- 💬 Natural language chat interface
- 🔄 Live streaming responses from Claude AI
- 🎨 Modern UI with Tailwind CSS and Nuxt UI
- 🌗 Dark mode support
- 📱 Responsive design
- ⚡ TypeScript for type safety

## Prerequisites

- Node.js 18+ (Nuxt 3 works with Node 18, despite warnings)
- npm or yarn
- Backend server running on port 8001

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your backend URL if needed
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

   The application will be available at http://localhost:3000

## Project Structure

```
frontend/
├── app/                    # Nuxt app directory
│   └── app.vue            # Root component
├── assets/                 # Static assets
│   └── css/
│       └── main.css       # Global styles with Tailwind
├── components/            # Vue components
│   ├── ChatHistory.vue    # Message history display
│   ├── ChatInput.vue      # Message input field
│   ├── ChatMessage.vue    # Individual message display
│   └── ConnectionStatus.vue # WebSocket status indicator
├── composables/           # Vue composables
│   └── useChatSocket.ts   # WebSocket connection logic
├── pages/                 # Application pages
│   └── index.vue          # Main chat page
├── types/                 # TypeScript type definitions
│   └── chat.ts           # Chat-related types
├── utils/                 # Utility functions
│   └── formatters.ts     # Text formatting utilities
├── nuxt.config.ts        # Nuxt configuration
└── package.json          # Dependencies

```

## Development

### Running Tests

```bash
npm run test        # Run tests (to be implemented)
npm run typecheck   # Check TypeScript types
```

### Building for Production

```bash
npm run build       # Build for production
npm run preview     # Preview production build
```

## Usage

1. **Start the backend server** first:
   ```bash
   cd .. && ./start_server.sh
   ```

2. **Start the frontend**:
   ```bash
   npm run dev
   ```

3. **Open your browser** to http://localhost:3000

4. **Start chatting!** Ask questions about your Netbox infrastructure:
   - "What devices are in the datacenter?"
   - "Show me all virtual machines"
   - "List recent changes"
   - "What IP addresses are assigned to server1?"

## WebSocket Protocol

The frontend communicates with the backend via WebSocket using the following protocol:

### Sending Messages
```json
{
  "message": "Your question here"
}
```

### Receiving Responses
```json
{
  "type": "text|tool_use|tool_result|thinking|error",
  "content": "Response content",
  "completed": false
}
```

## Customization

### Styling
- Global styles: `assets/css/main.css`
- Component styles: Scoped styles in each `.vue` file
- Tailwind config: `tailwind.config.ts` (auto-configured by @nuxtjs/tailwindcss)

### Configuration
- Nuxt config: `nuxt.config.ts`
- Environment variables: `.env`
- TypeScript: `tsconfig.json`

## Troubleshooting

### Connection Issues
- Ensure the backend is running on port 8001
- Check WebSocket URL in `.env`
- Look for connection status in the UI header
- Check browser console for errors

### Node Version Warnings
The warnings about Node version requirements can be safely ignored. Nuxt 3.14 works fine with Node 18.

### Building Issues
If you encounter build issues:
1. Delete `node_modules` and `package-lock.json`
2. Run `npm install` again
3. Clear Nuxt cache: `npx nuxi cleanup`

## License

Part of the Netbox Chatbox project.