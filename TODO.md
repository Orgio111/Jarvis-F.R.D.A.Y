# TODO

## Resolved ✅

- WhisperModel per-request init → module-level `_whisper_cache` dict in `voice.py`
- vision.py direct DeviceManager call → now uses `WorkloadRouter.acquire("vision")` semaphore
- memory_service.py embedder → now uses `WorkloadRouter.acquire("embeddings")` semaphore
- docker-compose.yml default build target `gpu` → changed to `base` (GPU users use `docker-compose.gpu.yml`)
- docker-compose.yml `deploy.resources` NVIDIA block removed from default compose (breaks CPU-only Docker)
- Chat streaming circuit breaker → `AIProxy.Stream()` added; `streamCompletions` now routes through
  it — circuit_open → 503/circuit_open envelope on tripped state (commit c57dd45)

- TTS GPU engine → Coqui TTS (TTS>=0.22.0) added to gpu-cuda extras and Dockerfile;
  voice.py tries CoquiTTS on cuda first, falls back to pyttsx3 CPU, then 204 (commit b40dcea)
- GATEWAY_API_KEY rotation → apikey.go now accepts GATEWAY_API_KEY / _KEY_1 / _KEY_2;
  deploy new key as _KEY_2 while _KEY_1 is live, remove _KEY_1 after migration (commit b40dcea)

## Remaining known gaps

None — all known gaps resolved.
