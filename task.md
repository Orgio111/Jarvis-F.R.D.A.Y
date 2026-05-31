# Jarvis-F.R.D.A.Y — Unified Improvement Task List

## Goal
Improve the repo into a cleaner, more reliable, and more production-ready multi-model AI agent system.

## Keep / Add

### 1) Docs cleanup
- Sync README with actual implementation
- Clarify architecture, services, and startup steps
- Add env variable documentation
- Add concise quickstart and troubleshooting section

### 2) Architecture hardening
- Define clear boundaries between:
  - orchestrator
  - model router
  - tools registry
  - memory store
  - UI
- Reduce duplicated logic across services
- Ensure agent state has a single source of truth
- Standardize API contracts and response envelopes

### 3) Frontend UX improvements
- Build a task-centric cockpit dashboard
- Add sections for:
  - chat
  - agent state
  - tool execution
  - memory
  - logs
- Improve loading states, errors, and empty states
- Make the UI easier to navigate and faster to understand

### 4) Error handling and reliability
- Add better API timeout handling
- Add retries and fallback behavior where needed
- Standardize errors across services
- Handle provider/model failures gracefully
- Validate config before startup

### 5) Testing
- Add smoke tests
- Add endpoint/integration tests
- Add frontend build/lint checks
- Add workflow tests for key agent paths

### 6) DevOps and deployment
- Split docker compose clearly for CPU / GPU / production use cases
- Make env setup safer and simpler
- Add CI for lint, test, and build
- Improve release versioning and changelog flow

### 7) Agent and feature upgrades
- Agent dashboard with live status
- Workflow builder / visual flow editor
- Tool marketplace / plugin-style extension support
- Memory system split into short-term / long-term / project memory
- Prompt library with reusable templates and versioning
- Session replay for previous conversations/workflows
- User approval gates for critical actions
- Model router that picks the best model per task
- Fallback chain for model/provider failure
- Voice mode with wake word, STT, and TTS
- Desktop tray app support
- Search/RAG over repo, docs, and web

## Excluded
- Cost tracker
- Audit log

## Priority Order
1. Docs cleanup
2. Architecture hardening
3. Frontend UX improvements
4. Error handling and reliability
5. Testing
6. DevOps and deployment
7. Agent and feature upgrades

## Suggested next step
Turn this into GitHub issues and implement in small PRs.
