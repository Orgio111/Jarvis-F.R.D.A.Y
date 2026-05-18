# TODO

## Resolved ✅

- WhisperModel per-request init → module-level `_whisper_cache` dict in `voice.py`
- vision.py direct DeviceManager call → now uses `WorkloadRouter.acquire("vision")` semaphore
- memory_service.py embedder → now uses `WorkloadRouter.acquire("embeddings")` semaphore
- docker-compose.yml default build target `gpu` → changed to `base` (GPU users use `docker-compose.gpu.yml`)
- docker-compose.yml `deploy.resources` NVIDIA block removed from default compose (breaks CPU-only Docker)

## Remaining known gaps (low priority)

- [ ] **Chat streaming circuit breaker**: `streamCompletions` in `go-gateway/internal/http/handlers/chat.go`
  bypasses `AIProxy.Post` and makes a raw HTTP call → 5xx from python-ai-service returns 503 with no
  `circuit_open` error code. Consider refactoring to use a shared transport so the circuit breaker
  covers streaming too. Impact is cosmetic (client gets 503 either way).

- [ ] **TTS GPU engine**: `pyttsx3` is CPU-only. `tts_gpu_enabled=auto` in config has no effect.
  No GPU TTS engine is wired up. Acceptable until a use case requires low-latency TTS at scale.

- [ ] **GATEWAY_API_KEY rotation**: No dual-key support for zero-downtime key rotation in production.
