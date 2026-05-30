# Jarvis Improvement Plan — Research Synthesis

## Research Summary (30+ repos analyzed)

### Key findings by category

---

## FREE LLM PROVIDERS (immediate value — no infrastructure needed)

### Already implemented
- NIM (nvidia) — primary, 44 free models, 40 req/min
- OpenRouter — fallback, 50 req/day free / 1000 with $10 topup
- ProviderRouter — ultimate fallback

### TO ADD (confirmed free, OpenAI-compatible)

| Provider | Base URL | Free limits | Best models |
|----------|----------|-------------|-------------|
| **Cerebras** | `https://api.cerebras.ai/v1` | 1M tokens/day, 14400 req/day | gpt-oss-120b, llama-3.1-8b — EXTREMELY fast inference |
| **Groq** | `https://api.groq.com/openai/v1` | 14400 req/day (llama-3.1-8b), 1000/day (llama-3.3-70b) | Best for low-latency terminal/routing tasks |
| **Google AI Studio** | `https://generativelanguage.googleapis.com/v1beta/openai` | 500 req/day (gemini flash lite), 14400/day gemma | Gemini 2.5 Flash, Gemma 3 27B |
| **Mistral La Plateforme** | `https://api.mistral.ai/v1` | 1B tokens/month (free tier) | codestral for code, mistral-nemo-12b for chat |
| **Cloudflare Workers AI** | `https://api.cloudflare.com/client/v4/accounts/{acct}/ai/v1` | 10k neurons/day | kimi-k2.6, gemma-4, nemotron-120b |
| **GitHub Models** | `https://models.inference.ai.azure.com` | Copilot-tier limits | gpt-5, gpt-4o, deepseek-r1, llama-4 |

**Provider priority order (updated):**
```
NIM → Cerebras → Groq → OpenRouter → Google AI Studio → Mistral → ProviderRouter
```

---

## ARCHITECTURE PATTERNS (steal these)

### 1. SpecAgent — Spec-before-code (spec-kit)
- **What**: Write a spec/PRD BEFORE PlannerAgent runs
- **Why**: Reduces hallucination, gives planner concrete acceptance criteria
- **How**: Insert as Step 0 in Orchestrator: `SpecAgent → FilePicker → Planner → Execute → Review`
- **Priority**: HIGH — low effort, big quality gain

### 2. Competitive swarm mode (MEGA_JARVIS_UNIVERSE_3D)
- **What**: Run 2 EditorAgents in parallel on same step, ReviewerAgent picks best
- **Why**: Better output quality, natural redundancy
- **How**: In `_execute_step()`, for EDITOR steps, spawn 2 EditorAgent tasks → compare → return winner
- **Priority**: MEDIUM — needs careful token budget mgmt

### 3. Retry-on-failure in agentic loop (Temporal.io / agent-lightning pattern)
- **What**: Each step retries up to 3x before marking failed
- **Why**: LLM calls fail transiently; rate limits, network, etc.
- **How**: Wrap `_execute_step()` in exponential backoff retry
- **Priority**: HIGH — easy win, prevents cascade failures

### 4. Knowledge graph indexing (graphify / cocoindex-code)
- **What**: AST-based semantic search for FilePickerAgent
- **Why**: Saves ~70% tokens by finding truly relevant files (not just keyword match)
- **How**: `graphify .` maps codebase → `graph.json` → FilePicker queries graph
- **Priority**: MEDIUM — needs integration work

### 5. Parallel agent teams with subgraph isolation (openpencil / ruflo)
- **What**: Each parallel step batch runs in an isolated subgraph context
- **Why**: Prevents context bleeding between parallel agent tasks
- **How**: Pass only step-relevant file_contents to each parallel task (already partially done)
- **Priority**: LOW — already partially implemented

### 6. Hooks system (ruflo / claude-flow)
- **What**: Pre/post hooks on every agent action (log, validate, transform)
- **Why**: Observability, guard rails, custom transforms without touching agent code
- **How**: `AgentHooks.pre_run(agent, input)` / `AgentHooks.post_run(agent, result)` protocol
- **Priority**: MEDIUM

### 7. Multi-model prompt adaptation (openpencil)
- **What**: Different prompt strategies per model capability tier
- **Why**: Smaller models need simpler prompts; reasoning models need "think step by step"
- **How**: ModelCapabilityRouter → assigns prompt template based on model family
- **Priority**: MEDIUM

---

## INFERENCE INFRASTRUCTURE (future/self-hosted)

| Project | What | When to use |
|---------|------|-------------|
| **vLLM** | PagedAttention, continuous batching, 200+ HF models | When self-hosting on GPU |
| **SGLang** | RadixAttention (prefix cache), 25x speedup on GB300 | Self-host, production scale |
| **llama.cpp** | CPU inference, quantized | Edge/local dev without GPU |
| **lucebox-hub** | Custom CUDA kernels, speculative prefill, 5.6x speedup | Self-host Qwen/Gemma |
| **Sana** | High-res image/video generation (NVIDIA) | Image tasks |

---

## OBSERVABILITY (future)

- **Prometheus + Grafana**: Metrics per agent, per model, per step latency
- **OpenTelemetry**: Distributed tracing across agent calls
- **Redis Streams**: Real-time SSE event bus (replace current direct yield)

---

## VECTOR SEARCH / MEMORY (future)

- **Weaviate** or **Milvus**: Persistent agent memory, semantic search over past tasks
- **Kafka**: Event streaming for multi-instance Jarvis coordination

---

## MISC INTERESTING FINDS

- **MiroFish**: Swarm simulation engine — "parallel universes" approach to prediction. Interesting for agent-based hypothesis generation.
- **sniffnet**: Rust network monitor — not directly relevant but shows good CLI UX patterns
- **graphify**: `/graphify .` → graph.html + GRAPH_REPORT.md + graph.json. Drop-in codebase mapper. USE THIS.
- **Groq compound/compound-mini**: Multi-step agentic model (250 req/day) — could replace PlannerAgent model
- **Mistral Codestral**: 2000 req/day free, code-specialized. Better than generic models for EditorAgent.

---

## IMPLEMENTATION CHECKLIST (ordered by priority)

### Phase 1 — Do now (no API keys needed for structure)
- [x] Research complete
- [ ] Add Cerebras provider to free_model_pool.py
- [ ] Add Groq provider to free_model_pool.py  
- [ ] Add Google AI Studio provider to free_model_pool.py
- [ ] Add Mistral provider to free_model_pool.py
- [ ] Add retry-on-failure to orchestrator._execute_step()
- [ ] Update provider priority in _chat() / ProviderRouter

### Phase 2 — Architecture improvements
- [ ] SpecAgent (new file: agents/specialized/spec.py)
- [ ] Insert SpecAgent as Step 0 in Orchestrator
- [ ] Competitive swarm mode for EditorAgent steps
- [ ] AgentHooks protocol

### Phase 3 — Infrastructure
- [ ] graphify integration for FilePickerAgent
- [ ] Prometheus metrics endpoint
- [ ] Redis Streams event bus

---

## UPDATED PROVIDER PRIORITY (to implement in code)

```python
# _chat() priority order:
# 1. NIM (nvidia) — best quality, 44 models, 40 req/min
# 2. Cerebras — fastest inference, 1M tokens/day
# 3. Groq — ultra-low latency, 14400 req/day for small models
# 4. Google AI Studio — gemini flash, 500 req/day
# 5. Mistral — codestral for editor, 2000/day
# 6. OpenRouter — broad model selection, 50 req/day free
# 7. ProviderRouter — ultimate fallback
```

---

## IMPLEMENTATION LOG

### Round 2 — Completed

#### 1. SpecAgent (`app/agents/specialized/spec_agent.py`) ✅
- New agent: writes spec/PRD with acceptance criteria before Planner runs
- Uses PLANNER model pool (reasoning-strong)
- Output: `spec` (markdown), `scope`, `out_of_scope`, `constraints`

#### 2. Orchestrator updates (`app/agents/orchestrator.py`) ✅
- Pipeline now: `Compress → Spec → FilePicker → Load → Plan → Execute → Review`
- Spec + constraints fed into Planner prompt
- `_execute_step_with_retry()` wraps all step execution
  - 3 retries, exponential backoff (2s → 4s → 8s)
  - Works for both parallel and sequential steps
  - Raises on final failure so orchestrator emits `step_error`

#### 3. Multi-provider free chain (`app/agents/free_model_pool.py`) ✅
- Added Cerebras (1M tokens/day, ultra-fast — llama-4-scout, llama-3.3-70b)
- Added Groq (14400 req/day — llama-3.1-8b-instant, llama-4-scout)
- Added Google AI Studio (gemini-2.5-flash-lite, gemma-3-27b)
- `provider_chain(role)` returns ordered list for `_chat()` to walk
- `base_agent._chat()` now iterates chain: NIM → Cerebras → Groq → Google → OpenRouter → ProviderRouter

#### 4. Config + env.example ✅
- Added `cerebras_api_key`, `groq_api_key`, `google_ai_api_key` to Settings
- Added to `.env.example` with doc links

---

## REMAINING (not yet implemented)

### HIGH
- [ ] Competitive swarm mode for EditorAgent
  - Run 2 EditorAgents in parallel on same step (asyncio.gather)
  - ReviewerAgent scores both, picks winner
  - Gated behind config flag `JARVIS_SWARM_MODE=true`

### MEDIUM
- [ ] graphify-style knowledge graph for file picking
  - Parse imports/exports to build a dependency graph
  - FilePickerAgent uses graph traversal instead of pure LLM guess
  - Inspired by: graphify (safishamsi), cocoindex-code (AST semantic search)
- [ ] Hooks system (ruflo/claude-flow pattern)
  - `pre_step` / `post_step` hooks in Orchestrator
  - Enables: logging, tracing, custom validators without modifying core

### LOW
- [ ] Redis Streams for real-time SSE (replace in-memory async generator)
  - Enables horizontal scaling (multiple workers, same stream)
  - Inspired by: redis.io/docs/streams
- [ ] OpenTelemetry tracing (grafana + prometheus export)
  - One-line spans per step/agent/provider
- [ ] MiroFish swarm simulation mode
  - Multiple agents with different "personalities" argue about the plan
  - Best consensus plan wins — for high-stakes refactors only
