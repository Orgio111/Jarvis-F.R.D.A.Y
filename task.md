# Jarvis Latency Optimization — Full Production Architecture

## What we're building
Real perceived latency reduction via system design (not just faster API calls).

## Components

### 1. Redis Semantic Cache [NEW FILE]
- `app/cache/semantic_cache.py`
- Exact match (hash) + semantic similarity (Qdrant cosine)
- TTL-based expiry, threshold=0.95
- Cache key: sha256(sorted messages)
- Semantic key: embed(last user msg) → Qdrant "semantic_cache" collection

### 2. Smart Router integration in chat.py [EDIT]
- Before memory enrich: run SmartRouter.analyze_task() → get mode
- Replace body.get("mode") default with SmartRouter result
- Select fast/smart/deep/coding model based on complexity

### 3. RAG context pruning [EDIT memory_service.py]
- top_k=3 → top_k=5 with score threshold (only >0.7 similarity)
- Truncate each chunk: 200 → 400 chars but only if score > 0.8
- Hybrid search: keyword pre-filter + semantic

### 4. Cache check in chat pipeline [EDIT chat.py]
- After model resolve: check cache → return instantly if hit
- After response: store to cache async

### 5. Streaming already done (prev session)

### 6. Response shaping [EDIT chat.py]
- For stream: emit "thinking..." STREAM_META event instantly
  so client can show skeleton

### 7. KV prefix cache hint [EDIT providers]
- Add system prompt caching header for Anthropic
- OpenAI: no change needed (auto)

## Priority order
1. Semantic cache (biggest win — 0ms on repeat queries)
2. Smart router in chat (small→big split)
3. RAG pruning (less tokens = faster inference)
4. Response shaping (UX)
5. Anthropic prefix cache

## Done
- [x] Memory timeout + parallel gather (1.5s)
- [x] Model resolution LRU cache (60s)
- [x] Stream first-token probe
- [x] Provider timeout 45→30s
