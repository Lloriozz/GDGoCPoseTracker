from functools import lru_cache

from app.core.config import settings
from app.llm.base import BaseLLMBackend
from app.llm.gemma_local_runtime import LocalGemmaInferencer
from app.llm.mock_gemma import MockGemmaInferencer


@lru_cache(maxsize=1)
def build_llm_backend() -> BaseLLMBackend:
    backend = settings.llm_backend.strip().lower()

    if backend in {"mock", "mock-gemma"}:
        return MockGemmaInferencer()

    if backend in {"local", "local-gemma", "local-transformers"}:
        return LocalGemmaInferencer(
            model_id=settings.gemma_model_id,
            device=settings.gemma_device,
            dtype=settings.gemma_dtype,
            quantization=settings.gemma_quantization,
            max_new_tokens=settings.gemma_max_new_tokens,
            temperature=settings.gemma_temperature,
            top_p=settings.gemma_top_p,
            do_sample=settings.gemma_do_sample,
            trust_remote_code=settings.gemma_trust_remote_code,
            cpu_offload=settings.gemma_cpu_offload,
            offload_buffers=settings.gemma_offload_buffers,
            gpu_memory_limit_mb=settings.gemma_gpu_memory_limit_mb,
            cpu_memory_limit_mb=settings.gemma_cpu_memory_limit_mb,
        )

    raise ValueError(f"Unsupported LLM_BACKEND: {settings.llm_backend}")
