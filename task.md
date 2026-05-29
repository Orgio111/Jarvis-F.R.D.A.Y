# Jarvis — Freebuff/Codebuff Architecture Implementation

## Goal
Codebuff/Freebuff multi-agent architecture Jarvis-д нэмэх.
Ad болон төлбөртэй model ХЭРЭГГҮЙ.

## What exists already
- MacroBrain (orchestrator) ✅
- SmartRouter (complexity routing) ✅
- SectorBrains (coding/devops/research/etc) ✅
- agent_service.py (plan→act→reflect loop) ✅
- code_indexing/ (file crawler, chunker, embedder) ✅
- execution.py (Python/shell sandbox) ✅
- StrategyBrain (task graph) ✅
- OpenRouter provider (DeepSeek, Kimi, Gemini Flash — FREE tier models) ✅

## What's MISSING (Freebuff gap)
1. **Specialized sub-agents** — file_picker, planner, editor, reviewer, terminal
   Currently agent_service.py = single loop, no agent specialization
2. **Parallel agent execution** — steps run sequentially, not parallel
3. **Free model routing** — no explicit free model pool (DeepSeek-free, Gemini-flash-lite, Kimi-free)
4. **Codebase context** — code_indexing exists but NOT wired to agent pipeline
5. **Terminal agent** — execution.py exists but not a real agent with feedback loop
6. **Context compression** — no conversation summary / context pruning between iterations

## Implementation Plan

### File 1: app/agents/base_agent.py [NEW]
BaseAgent class — shared interface for all sub-agents

### File 2: app/agents/specialized/file_picker.py [NEW]
FilePickerAgent — tree-sitter scan + vector search → relevant files list

### File 3: app/agents/specialized/planner.py [NEW]
PlannerAgent — decomposes goal into typed steps with agent assignment

### File 4: app/agents/specialized/editor.py [NEW]
EditorAgent — writes/patches code, uses coding model (DeepSeek-free)

### File 5: app/agents/specialized/reviewer.py [NEW]
ReviewerAgent — reviews code output, finds bugs/issues

### File 6: app/agents/specialized/terminal.py [NEW]
TerminalAgent — executes shell/python, parses output, reports result

### File 7: app/agents/orchestrator.py [NEW]
Orchestrator — parallel agent dispatch, aggregates results
Uses Freebuff pattern: fast parallel map, then reduce

### File 8: app/agents/free_model_pool.py [NEW]
FreeModelPool — explicitly maps task types to free-tier models
  file_scan → gemini/gemini-flash-1.5-8b (free)
  coding → deepseek/deepseek-chat-v3-0324:free (free)
  reasoning → deepseek/deepseek-r1:free (free)
  fast/routing → meta-llama/llama-3.2-3b-instruct:free (free)

### File 9: app/agents/context_compressor.py [NEW]
ContextCompressor — summarize old turns, prune irrelevant context
max_context_tokens=4000, compress older than 3 turns

### File 10: app/routers/orchestrate.py [NEW]
/orchestrate/run endpoint — entry point for full multi-agent pipeline

### File 11: main.py [EDIT]
Register /orchestrate router

## Free models on OpenRouter (no key cost)
- deepseek/deepseek-chat-v3-0324:free
- deepseek/deepseek-r1:free
- google/gemini-flash-1.5-8b (very cheap / free quota)
- meta-llama/llama-3.2-3b-instruct:free
- microsoft/phi-3-mini-128k-instruct:free
- qwen/qwen-2.5-7b-instruct:free

## Done (previous sessions)
- [x] Semantic cache (Redis + Qdrant)
- [x] Smart router in chat.py
- [x] Memory timeout + parallel
- [x] Model resolution cache
- [x] RAG score threshold pruning
