from dataclasses import dataclass
import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "fitness-chatbot")
    environment: str = os.getenv("APP_ENV", "dev")
    llm_backend: str = os.getenv("LLM_BACKEND", "mock-gemma")
    max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))
    rag_enabled: bool = _env_bool("RAG_ENABLED", True)
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "3"))
    rag_min_score: int = int(os.getenv("RAG_MIN_SCORE", "2"))
    gemma_model_id: str = os.getenv("GEMMA_MODEL_ID", "google/gemma-4-E4B-it")
    gemma_device: str = os.getenv("GEMMA_DEVICE", "cuda")
    gemma_dtype: str = os.getenv("GEMMA_DTYPE", "bfloat16")
    gemma_quantization: str = os.getenv("GEMMA_QUANTIZATION", "4bit")
    gemma_max_new_tokens: int = int(os.getenv("GEMMA_MAX_NEW_TOKENS", "512"))
    gemma_temperature: float = float(os.getenv("GEMMA_TEMPERATURE", "0.3"))
    gemma_top_p: float = float(os.getenv("GEMMA_TOP_P", "0.95"))
    gemma_do_sample: bool = _env_bool("GEMMA_DO_SAMPLE", False)
    gemma_trust_remote_code: bool = _env_bool("GEMMA_TRUST_REMOTE_CODE", False)
    gemma_cpu_offload: bool = _env_bool("GEMMA_CPU_OFFLOAD", True)
    gemma_offload_buffers: bool = _env_bool("GEMMA_OFFLOAD_BUFFERS", True)
    gemma_gpu_memory_limit_mb: int = int(os.getenv("GEMMA_GPU_MEMORY_LIMIT_MB", "3500"))
    gemma_cpu_memory_limit_mb: int = int(os.getenv("GEMMA_CPU_MEMORY_LIMIT_MB", "16384"))
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:Duy1805@localhost:5432/PoseTracker",
    )
    kb_path: str = os.getenv(
        "KB_PATH",
        str(Path("data") / "kb" / "fitness_knowledge.json"),
    )
    nutrition_catalog_path: str = os.getenv(
        "NUTRITION_CATALOG_PATH",
        str(Path("data") / "nutrition" / "catalog.json"),
    )


settings = Settings()
