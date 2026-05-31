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
- [x] SpecAgent (new file: agents/specialized/spec.py)
- [x] Insert SpecAgent as Step 0 in Orchestrator
- [x] Competitive swarm mode for EditorAgent steps
- [x] AgentHooks protocol (pre_step / post_step on Orchestrator)

### Phase 3 — Infrastructure
- [x] graphify integration for FilePickerAgent (AST-based CodeGraph + BFS expansion)
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

### LOW
- [ ] Redis Streams for real-time SSE (replace in-memory async generator)
  - Enables horizontal scaling (multiple workers, same stream)
  - Inspired by: redis.io/docs/streams
- [ ] OpenTelemetry tracing (grafana + prometheus export)
  - One-line spans per step/agent/provider
- [ ] MiroFish swarm simulation mode
  - Multiple agents with different "personalities" argue about the plan
  - Best consensus plan wins — for high-stakes refactors only

---

## Round 3 — Completed

#### 5. Competitive swarm mode (`e204906`) ✅
- `_execute_step_swarm()` runs 2 EditorAgents in parallel (temp 0.10 vs 0.35)
- `ReviewerAgent.score_edits()` picks winner by quality score
- Gated behind `JARVIS_SWARM_MODE=true` env flag (off by default)

#### 6. Graph-based file picker (`0b056aa`) ✅
- `code_graph.py` — AST import graph builder (Python + JS/TS, stdlib only)
- `file_picker.py` — two-phase: LLM seeds → `CodeGraph.reachable(seeds, hops=2)` BFS expansion
- `most_connected()` ranks by hub score; best-effort (failures silently skipped)
- `repo_root` wired into Orchestrator's FilePicker call

#### 7. Hooks system (`988ea01`) ✅
- `pre_step` / `post_step` hooks on Orchestrator instance
- Both sync and async callables supported
- Hook errors are swallowed (won't crash pipeline)
- Usage: `orch.add_hook("pre_step", fn)` / `orch.add_hook("post_step", fn)`

---

## Research Round 4 — AI Agent + Skills System (30 repos)

### Repos analyzed
LangGraph, AutoGen, CrewAI, MetaGPT, OpenDevin, Open-Interpreter, AutoGPT, BabyAGI

---

### KEY FINDINGS — steal these patterns

#### 1. LangGraph — StateGraph / Checkpointing ⭐
```python
# Pattern: typed state dict + nodes + conditional edges
class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

workflow = StateGraph(State)
workflow.add_node("call_model", call_model)
workflow.add_conditional_edges("call_model", should_continue)
graph = workflow.compile()
```
- **What Jarvis lacks**: typed State object — our Orchestrator passes raw dicts
- **Steal**: wrap pipeline state in a TypedDict; makes debugging/serialization trivial
- **Also**: LangGraph supports **durable execution** — resume from checkpoint after crash
- **Also**: `RetryPolicy` + `CachePolicy` per node — aligns with our retry work

#### 2. AutoGen — `on_messages_stream` + cancellation token ⭐
```python
async def on_messages_stream(
    self, messages, cancellation_token: CancellationToken
) -> AsyncGenerator[...]:
```
- **What Jarvis lacks**: no CancellationToken — user can't abort mid-run
- **Steal**: pass cancellation event through Orchestrator → agents
- **Also**: `AssistantAgentConfig` — declarative agent config via Pydantic, serializable

#### 3. MetaGPT — ActionNode (structured LLM output) ⭐⭐
- Every action has typed input/output schema in Pydantic
- LLM is asked to fill a structured template — reduces JSON parse errors
- `action_graph.py` — actions form a DAG (like our steps, but first-class)
- `Planner` in role decides WHICH action to take next (vs our hardcoded pipeline)
- **Priority**: HIGH — our agents parse LLM output with regex; ActionNode style = more reliable

#### 4. OpenDevin — Skill-as-markdown with YAML frontmatter ⭐
```yaml
---
name: fix_bug
triggers: ["/fix", "fix bug", "debug"]
type: task
---
# Fix Bug Skill
...instructions for the agent...
```
- Skills stored as `.md` files with YAML frontmatter — human-readable, git-diffable
- `KeywordTrigger` vs `TaskTrigger` — keyword = chat command, task = slash command
- Skill loader is a thin proxy → agent-server `/api/skills` (decoupled from main app)
- **Jarvis has**: `skill_service.py` with DB-stored LLM-generated skills
- **Gap**: no trigger system — skills are never auto-invoked based on user message
- **Steal**: add `triggers: list[str]` to Skill model + IntentRouter matches triggers → dispatches skill

#### 5. BabyAGI `functionz` — Function Registry with DB persistence ⭐⭐
```python
@python_func.register_function(
    metadata={"description": "..."},
    imports=["httpx"],
    dependencies=["other_fn"],
    triggers=["search the web"],
    key_dependencies=["OPENAI_API_KEY"]
)
async def web_search(query: str) -> dict:
    ...
```
- Functions stored in DB with: code, metadata, imports, dependencies, triggers, versions
- **Dependency graph** between functions (like our CodeGraph but for skills!)
- **Triggers**: when another function is added/updated → auto-fires trigger
- **key_dependencies**: declares which API keys a function needs
- `function_added_or_updated` hook — reactive to registry changes
- **Jarvis has**: `skill_service.py` — very similar! But missing: dependency graph, triggers, reactive hooks
- **Steal**: add `dependencies: list[str]` + `triggers: list[str]` to Skill model

#### 6. AutoGPT — Tool output size management ⭐
```python
_LARGE_OUTPUT_THRESHOLD = 80_000  # persist to workspace if >80KB
_PREVIEW_CHARS = 95_000           # middle-out preview for LLM context
```
- Large tool outputs saved to file; LLM gets a preview + "retrieve full output" instruction
- Prevents context overflow from big tool results
- **Jarvis has**: `SKILL_OUTPUT_LIMIT = 50_000` truncation — but no middle-out preview
- **Steal**: middle-out preview pattern for large skill outputs

#### 7. CrewAI — Role-based agent with `goal` + `backstory` ⭐
- Each agent has: role, goal, backstory, tools list, memory flag
- Crew = team of agents with a `process` (sequential or hierarchical)
- Task has `expected_output` field → reviewer knows what "done" means
- **Jarvis gap**: agents have no explicit goal/backstory — harder to tune behavior

---

### COMMON PATTERN ACROSS ALL REPOS

```
User Input
    ↓
Intent Router / Skill Selector
    ↓
Skill Registry (trigger match → pick skill/tool)
    ↓
Agent Executor (LLM with structured output)
    ↓
Memory (vector DB + state checkpoint)
    ↓
Tool Execution Layer (sandboxed)
    ↓
Feedback / Quality loop (retry + crystallize)
```

**Jarvis covers**: Agent Executor ✅, Memory ✅, Tool sandbox ✅, Retry ✅, Crystallize ✅
**Jarvis missing**: Intent Router ❌, Trigger-based skill dispatch ❌, State checkpoint ❌, CancellationToken ❌

---

## IMPLEMENTATION CHECKLIST — Round 4

### HIGH priority
- [x] **Trigger-based skill dispatch** (`IntentRouter`) ✅ `round4-impl`
  - Added `triggers_json` + `dependencies_json` columns to Skill model + SQLite migration
  - `IntentRouter.match(user_message)` — keyword (substring) + slash prefix matching, quality_score ranked
  - Hooked into `chat.py` before LLM call — zero-latency skill dispatch
  - Pattern: OpenDevin KeywordTrigger + BabyAGI functionz triggers

- [x] **Structured agent output** (ActionNode-style) ✅ `round4-impl`
  - `BaseAgent.output_schema: type[BaseModel] | None` class variable
  - `_chat()` injects JSON schema into system message; validates response with `model_validate_json()`
  - Falls back to raw text on validation failure — zero regression risk
  - Output schemas added: `PlannerAgent._PlannerOutput`, `EditorAgent._EditorOutput`,
    `ReviewerAgent._ReviewerOutput`, `SpecAgent._SpecOutput`, `FilePickerAgent._FilePickerOutput`
  - Pattern: MetaGPT ActionNode

### MEDIUM priority
- [x] **CancellationToken in Orchestrator** ✅ `round4-impl`
  - `asyncio.Event cancel_event` passed to `Orchestrator.run(cancel_event=...)` (optional, auto-created if not provided)
  - Checked at every phase boundary: compress, spec, file_picker, planner, execute loop
  - Yields `{"event": "cancelled", "data": {"phase": "..."}}` then returns cleanly
  - Pattern: AutoGen CancellationToken

- [x] **Typed State in Orchestrator** ✅ `round4-impl`
  - `PipelineState` TypedDict declared — all pipeline locals typed
  - `state` dict built incrementally throughout `run()` for observability
  - Pattern: LangGraph StateGraph

- [x] **Middle-out preview for large skill outputs** ✅ `round4-impl`
  - Threshold lowered to `_SKILL_OUTPUT_LIMIT = 50_000` (existing) — now returns head+tail not just head
  - Preview: first 2000 chars + last 500 chars + total_bytes + note with file path
  - Full output saved to `/tmp/jarvis_skill_outputs/skill_output_{ts}.json`
  - Pattern: AutoGPT tool output management

- [x] **Skill dependency graph** ✅ `round4-impl`
  - `dependencies_json TEXT DEFAULT '[]'` column added to Skill model + DB
  - `_to_dict()` serialises both `triggers` and `dependencies` in all API responses
  - Reactive notification not yet implemented (dependency tracking stored, not acted on)

### LOW priority
- [ ] Role + goal + backstory on BaseAgent
  - Makes agent behavior tunable without touching code
  - Pattern: CrewAI role-based agents

- [ ] LangGraph durable execution (checkpoint/resume)
  - Serialize PipelineState to DB after each step
  - Resume if process dies mid-run
  - Only needed for very long tasks

---

## Round 4 Implementation Log

| Commit | What |
|--------|------|
| `round4-impl` | IntentRouter, structured output schemas, CancellationToken, PipelineState TypedDict, middle-out preview, Skill triggers+dependencies columns |

---

## Research Round 5 — Skill OS / Marketplace Architecture

### Vision
Jarvis = OS. Skills = apps. Marketplace = app store. Registry = package manager. GitHub importer = package installer.

### Gap analysis vs current state
| Feature | Current | Need |
|---------|---------|------|
| Skill CRUD | ✅ basic | ✅ |
| Skill execution + sandbox | ✅ | ✅ |
| Self-scoring (quality_score) | ✅ | ✅ |
| GitHub importer | ❌ | Build |
| Marketplace UI | ❌ | Build |
| Skill registry metadata (repo_url, hash, trust_score, latency) | ❌ | Add to model |
| Install/uninstall/rate/publish endpoints | ❌ | Build |
| Skill search by tag/category | ❌ | Build |
| Self-growing loop (detect missing → generate → validate → deploy) | ❌ partial | Wire fully |
| Skill evolution loop (failure → patch → new version) | ❌ | Wire fully |
| Score formula (success*0.5 + usage*0.2 + speed*0.2 + feedback*0.1) | partial | Wire |

---

## IMPLEMENTATION CHECKLIST — Round 5 (Skill OS)

### BACKEND

#### 1. Skill model extended fields
- [ ] Add `repo_url`, `hash_sha`, `trust_score`, `latency_ms_avg`, `tags_json`, `installed_at`, `publisher` to Skill model

#### 2. Skill Registry Service (`skill_registry.py`)
- [ ] `compute_score(skill)` — weighted formula: success*0.5 + freq*0.2 + speed*0.2 + feedback*0.1
- [ ] `update_registry_after_execution(skill_id, success, latency_ms)` — post-exec scoring
- [ ] `rank_skills(category?)` — return ranked list
- [ ] `auto_disable_bad_skills()` — disable skills with trust_score < 0.2 after 5+ runs
- [ ] `detect_missing_capability(user_message)` — returns True if no skill matches + no LLM handled it

#### 3. GitHub Importer (`github_importer.py`)
- [ ] `import_from_github(url)` — clone → detect manifest → wrap → sandbox test → register
- [ ] `detect_skill_manifest(repo_path)` — look for skill.json, tool.py, agent.yaml, plugin manifest
- [ ] `llm_generate_manifest(repo_path)` — LLM scans repo → extracts callable + builds manifest
- [ ] `wrap_to_jarvis_format(manifest, repo_path)` → generates `async def run(**kwargs)` wrapper
- [ ] `validate_and_register(manifest, source_code)` — syntax check + dry-run + DB insert

#### 4. Marketplace API endpoints (`routers/marketplace.py`)
- [ ] `GET /marketplace/skills` — list with search/filter/sort
- [ ] `GET /marketplace/skills/{id}` — detail + stats
- [ ] `POST /marketplace/install` — install by skill_id or GitHub URL
- [ ] `POST /marketplace/uninstall/{skill_id}` — soft disable + cleanup
- [ ] `POST /marketplace/rate/{skill_id}` — user rating (1-5), updates trust_score
- [ ] `POST /marketplace/publish` — publish a local skill to marketplace registry
- [ ] `GET /marketplace/trending` — top by trust_score * usage_count
- [ ] `GET /marketplace/search?q=&tags=&category=` — semantic + keyword search

#### 5. Skill Evolution Loop (`skill_evolution.py`)
- [ ] `run_evolution_cycle(db)` — scan all skills, find failures, trigger patch
- [ ] `patch_skill(db, skill_id, error_context)` — LLM rewrites code, bumps version
- [ ] `deprecate_old_version(db, skill_id)` — mark old as deprecated, activate new
- [ ] Background task: scheduled every 10min via APScheduler

#### 6. Self-Growing Capability Detection
- [ ] Hook into chat.py: after IntentRouter miss + LLM response → check if LLM says "I can't do X"
- [ ] If missing capability detected: auto-trigger `generate_and_store()` for that capability
- [ ] Emit SSE event `skill_generated` with new skill metadata

### FRONTEND

#### 7. Skill Marketplace UI (`features/skillMarketplace/`)
- [ ] `SkillMarketplacePage.tsx` — main page with search bar + tabs (All / Installed / Trending)
- [ ] `SkillCard.tsx` — card: name, description, tags, trust_score stars, install button
- [ ] `SkillDetailModal.tsx` — full detail: source code preview, stats, version history, rate
- [ ] `GitHubImportModal.tsx` — URL input → import progress → result
- [ ] `SkillRegistryStats.tsx` — dashboard widget: total skills, avg score, top categories
- [ ] Add route `/skills` or tab in sidebar

#### 8. Score formula wiring
- [ ] Replace current naive `quality_score` update with full weighted formula
- [ ] `latency_ms_avg` tracked per-execution (rolling avg)
- [ ] `user_feedback` from marketplace rating endpoint feeds into score

