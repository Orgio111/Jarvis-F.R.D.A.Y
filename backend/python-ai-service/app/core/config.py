from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── App ──────────────────────────────────────────────────────────────────
    app_env: str = "development"
    app_name: str = "jarvis-backend"
    app_host: str = "0.0.0.0"
    app_port: int = 8100

    # ─── Upstream / dependencies ──────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    rust_broker_url: str = "http://localhost:8200"

    # ─── Provider keys (empty = provider_unavailable, not a startup failure) ──
    anthropic_api_key: str = ""
    nvidia_nim_api_key: str = ""
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # ─── Provider routing ─────────────────────────────────────────────────────
    ai_provider_primary: str = "nvidia_nim"
    ai_provider_fallback: str = "openrouter"
    ai_provider_routing_mode: Literal["auto", "primary", "fallback"] = "auto"
    ai_provider_timeout_seconds: int = 45
    ai_provider_max_retries: int = 2
    ai_max_tokens: int = 4096
    default_chat_model: str = ""

    # ─── Model discovery ──────────────────────────────────────────────────────
    model_discovery_enabled: bool = True
    model_discovery_refresh_seconds: int = 3600
    model_auto_selection_enabled: bool = True

    # ─── GPU ──────────────────────────────────────────────────────────────────
    gpu_enabled: bool = True
    gpu_required: bool = False
    gpu_provider: str = "nvidia"
    gpu_device: str = "auto"
    gpu_allow_cpu_fallback: bool = True
    gpu_memory_soft_limit_mb: int = 0
    gpu_memory_hard_limit_mb: int = 0
    gpu_prefer_half_precision: bool = True
    gpu_enable_mixed_precision: bool = True

    # ─── Local LLM ────────────────────────────────────────────────────────────
    local_llm_enabled: bool = False
    local_llm_gpu_enabled: bool = True
    local_llm_runtime: str = "auto"
    local_llm_base_url: str = ""
    local_llm_model_cache_dir: str = "./data/models"
    local_llm_max_context_tokens: int = 8192

    # ─── STT ──────────────────────────────────────────────────────────────────
    stt_enabled: bool = True
    stt_engine: str = "faster_whisper"
    stt_gpu_enabled: bool = True
    stt_device: str = "auto"
    stt_compute_type: str = "auto"
    stt_model_size: str = "base"
    stt_batch_size: int = 1

    # ─── TTS ──────────────────────────────────────────────────────────────────
    tts_enabled: bool = True
    tts_engine: str = "auto"
    tts_gpu_enabled: str = "auto"
    tts_device: str = "auto"
    tts_model_cache_dir: str = "./data/tts"

    # ─── Voice ────────────────────────────────────────────────────────────────
    voice_streaming_enabled: bool = True

    # ─── Embeddings ───────────────────────────────────────────────────────────
    embeddings_enabled: bool = True
    embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embeddings_gpu_enabled: bool = True
    embeddings_device: str = "auto"
    embeddings_batch_size: int = 32

    # ─── FAISS ────────────────────────────────────────────────────────────────
    faiss_enabled: bool = True
    faiss_gpu_enabled: bool = False
    faiss_index_path: str = "./data/faiss/index"
    faiss_gpu_device: int = 0

    # ─── Vision ───────────────────────────────────────────────────────────────
    vision_enabled: bool = True
    vision_gpu_enabled: bool = True
    vision_device: str = "auto"
    vision_model_cache_dir: str = "./data/vision"

    # ─── GPU workload flags ───────────────────────────────────────────────────
    rag_gpu_acceleration_enabled: bool = True
    memory_synthesis_gpu_enabled: bool = True
    batch_ai_gpu_enabled: bool = True

    # ─── Search ───────────────────────────────────────────────────────────────
    web_search_enabled: bool = True
    deep_search_enabled: bool = True

    # ─── Semantic cache ───────────────────────────────────────────────────────
    semantic_cache_enabled: bool = True
    semantic_cache_threshold: float = 0.95
    semantic_cache_ttl_seconds: int = 86400

    # ─── Sandbox ──────────────────────────────────────────────────────────────
    sandbox_enabled: bool = True
    sandbox_network_disabled: bool = True
    sandbox_cpu_limit: float = 1.0
    sandbox_memory_limit: str = "512m"
    sandbox_timeout_seconds: int = 30
    sandbox_output_limit_bytes: int = 200000
    sandbox_gpu_enabled: bool = False

    # ─── Local control ────────────────────────────────────────────────────────
    local_pc_control_enabled: bool = True
    local_admin_actions_require_approval: bool = True

    # ─── Self-improvement ─────────────────────────────────────────────────────
    self_improvement_enabled: bool = True
    self_improvement_require_approval: bool = True
    self_versioning_enabled: bool = True

    # ─── Persistent data directory ────────────────────────────────────────────
    data_dir: str = "./data"

    # ─── Agent orchestrator ───────────────────────────────────────────────────
    agent_enabled: bool = True
    agent_max_iterations: int = 5
    agent_auto_skill_creation: bool = True

    # ─── Skill system ─────────────────────────────────────────────────────────
    skills_enabled: bool = True
    skill_execution_timeout: int = 30

    # ─── User profile ─────────────────────────────────────────────────────────
    profile_enabled: bool = True
    profile_llm_update_cooldown: int = 30

    # ─── Scheduler ────────────────────────────────────────────────────────────
    scheduler_enabled: bool = True

    # ─── Observability ────────────────────────────────────────────────────────
    prometheus_enabled: bool = True
    otel_enabled: bool = True
    otel_service_name: str = "jarvis-python-ai-service"
    jaeger_endpoint: str = "http://localhost:14268/api/traces"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
