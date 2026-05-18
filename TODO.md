# TODO

## Resolved ✅

- WhisperModel per-request init → module-level `_whisper_cache` dict in `voice.py`
- vision.py direct DeviceManager call → now uses `WorkloadRouter.acquire("vision")` semaphore
- memory_service.py embedder → now uses `WorkloadRouter.acquire("embeddings")` semaphore
- docker-compose.yml default build target `gpu` → changed to `base` (GPU users use `docker-compose.gpu.yml`)
- docker-compose.yml `deploy.resources` NVIDIA block removed from default compose (breaks CPU-only Docker)
- Chat streaming circuit breaker → `AIProxy.Stream()` added; `streamCompletions` now routes through
  it — circuit_open → 503/circuit_open envelope on tripped state (commit c57dd45)

## Remaining known gaps (low priority)

- [ ] **TTS GPU engine**: `pyttsx3` is CPU-only. `tts_gpu_enabled=auto` in config has no effect.
  No GPU TTS engine is wired up. Acceptable until a use case requires low-latency TTS at scale.

- [ ] **GATEWAY_API_KEY rotation**: No dual-key support for zero-downtime key rotation in production.
