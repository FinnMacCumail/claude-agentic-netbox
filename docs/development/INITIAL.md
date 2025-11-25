## FEATURE:

- Netbox chatbox built using the the claude agent SDK
- The Chatbox will be able to handle all netbox related queries
- The claude agent SDK uses the Netbox mcp server tools
- The ClaudeSDKClient will be utilised to allow for Continuous Conversation and Follow-up questions
- The application will be organised into frontend and backend directories
- The backend will contain the logic for anthropic authentication and all the logic for dealing with the netbox query
- The Frontend UI will be built using Nuxt.js

## EXAMPLES:

- The examples`examples/` folder contains information regarding the clause code sdk.
- This directory contains the Netbox mcp server that the application will utilise - /home/ola/dev/rnd/mcp/testmcp/netbox-mcp-server/


## DOCUMENTATION:

- This github repo is for the claude agentic SDK - https://github.com/anthropics/claude-agent-sdk-python
- Agent SDK overview - https://platform.claude.com/docs/en/agent-sdk/overview
- Nuxt.js - https://nuxt.com/docs/4.x/getting-started/introduction


## OTHER CONSIDERATIONS:

Do not use the python SDK query() but use ClaudeSDKClient
