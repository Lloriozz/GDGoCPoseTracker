from __future__ import annotations

import importlib
import json
import sys
import traceback
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_RUNTIME_BINDINGS: dict[str, Any] | None = None


def _reload_app_modules() -> None:
    importlib.invalidate_caches()
    app_module_names = sorted(
        (
            name
            for name in sys.modules
            if name == "app" or name.startswith("app.")
        ),
        reverse=True,
    )
    for module_name in app_module_names:
        sys.modules.pop(module_name, None)


def _load_runtime_bindings(*, force_reload: bool = False) -> dict[str, Any]:
    global _RUNTIME_BINDINGS

    if _RUNTIME_BINDINGS is not None and not force_reload:
        return _RUNTIME_BINDINGS

    if force_reload:
        _reload_app_modules()

    config_module = importlib.import_module("app.core.config")
    orchestrator_module = importlib.import_module("app.core.orchestrator")
    database_module = importlib.import_module("app.db.database")
    factory_module = importlib.import_module("app.llm.factory")
    chat_request_module = importlib.import_module("app.schemas.chat_request")
    user_profile_module = importlib.import_module("app.schemas.user_profile")

    _RUNTIME_BINDINGS = {
        "settings": config_module.settings,
        "FitnessChatOrchestrator": orchestrator_module.FitnessChatOrchestrator,
        "init_db": database_module.init_db,
        "build_llm_backend": factory_module.build_llm_backend,
        "ChatRequest": chat_request_module.ChatRequest,
        "UserProfilePatch": user_profile_module.UserProfilePatch,
    }
    return _RUNTIME_BINDINGS


def _safe_json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _format_response(response: object) -> str:
    try:
        payload = response.model_dump()
    except AttributeError:
        payload = response
    return _safe_json_dumps(payload)


def _coerce_profile_patch(
    profile_patch: dict[str, Any] | None,
    user_profile_patch_cls: type[Any],
) -> Any | None:
    if not profile_patch:
        return None
    return user_profile_patch_cls(**profile_patch)


def _set_setting_if_present(settings: Any, name: str, value: Any) -> None:
    if value is None or not hasattr(settings, name):
        return
    setattr(settings, name, value)


def configure_colab_runtime(
    *,
    llm_backend: str = "gemma_local",
    model_id: str | None = None,
    device: str | None = None,
    dtype: str | None = None,
    quantization: str | None = None,
    max_new_tokens: int | None = None,
    gpu_memory_limit_mb: int | None = None,
    cpu_memory_limit_mb: int | None = None,
    cpu_offload: bool | None = None,
    offload_buffers: bool | None = None,
    wiki_enabled: bool | None = None,
    wiki_path: str | None = None,
    rag_enabled: bool | None = None,
    database_url: str | None = None,
    database_schema: str | None = None,
    reload_backend: bool = True,
) -> dict[str, object]:
    runtime = _load_runtime_bindings(force_reload=reload_backend)
    settings = runtime["settings"]

    settings.llm_backend = llm_backend
    if model_id is not None:
        settings.gemma_model_id = model_id
    if device is not None:
        settings.gemma_device = device
    if dtype is not None:
        settings.gemma_dtype = dtype
    if quantization is not None:
        settings.gemma_quantization = quantization
    if max_new_tokens is not None:
        settings.gemma_max_new_tokens = max_new_tokens
    if gpu_memory_limit_mb is not None:
        settings.gemma_gpu_memory_limit_mb = gpu_memory_limit_mb
    if cpu_memory_limit_mb is not None:
        settings.gemma_cpu_memory_limit_mb = cpu_memory_limit_mb
    if cpu_offload is not None:
        settings.gemma_cpu_offload = cpu_offload
    if offload_buffers is not None:
        settings.gemma_offload_buffers = offload_buffers
    if wiki_enabled is not None:
        settings.wiki_enabled = wiki_enabled
    if wiki_path is not None:
        settings.wiki_path = wiki_path
    if rag_enabled is not None:
        settings.rag_enabled = rag_enabled
    if database_url is not None:
        settings.database_url = database_url
    _set_setting_if_present(settings, "database_schema", database_schema)

    build_llm_backend = runtime["build_llm_backend"]
    if reload_backend and hasattr(build_llm_backend, "cache_clear"):
        build_llm_backend.cache_clear()

    runtime["init_db"]()
    return runtime_summary()


def runtime_summary() -> dict[str, object]:
    runtime = _load_runtime_bindings()
    settings = runtime["settings"]
    summary: dict[str, object] = {
        "backend": settings.llm_backend,
        "model_id": settings.gemma_model_id,
        "device": settings.gemma_device,
        "dtype": settings.gemma_dtype,
        "quantization": settings.gemma_quantization,
        "max_new_tokens": settings.gemma_max_new_tokens,
        "gpu_memory_limit_mb": settings.gemma_gpu_memory_limit_mb,
        "cpu_memory_limit_mb": settings.gemma_cpu_memory_limit_mb,
        "cpu_offload": settings.gemma_cpu_offload,
        "offload_buffers": settings.gemma_offload_buffers,
        "wiki_enabled": settings.wiki_enabled,
        "wiki_path": settings.wiki_path,
        "rag_enabled": settings.rag_enabled,
        "database_url": settings.database_url,
        "project_root": str(PROJECT_ROOT),
        "code_reload_hint": "Pass reload_backend=True or restart the runtime after backend code changes.",
    }
    if hasattr(settings, "database_schema"):
        summary["database_schema"] = settings.database_schema
    return summary


def backend_diagnostics(*, load_model: bool = False) -> dict[str, object]:
    runtime = _load_runtime_bindings()
    build_llm_backend = runtime["build_llm_backend"]
    backend = build_llm_backend()

    if load_model and hasattr(backend, "_ensure_loaded"):
        backend._ensure_loaded()

    model = getattr(backend, "_model", None)
    torch_runtime = getattr(backend, "_torch", None)
    parameter_device = None
    if model is not None:
        try:
            parameter_device = str(next(model.parameters()).device)
        except (StopIteration, AttributeError, TypeError):
            parameter_device = None

    diagnostics: dict[str, object] = {
        "backend_class": type(backend).__name__,
        "model_loaded": model is not None,
        "parameter_device": parameter_device,
        "hf_device_map": getattr(model, "hf_device_map", None),
        "project_root": str(PROJECT_ROOT),
    }

    if torch_runtime is not None and getattr(torch_runtime, "cuda", None) is not None:
        cuda_available = bool(torch_runtime.cuda.is_available())
        diagnostics["cuda_available"] = cuda_available
        if cuda_available:
            diagnostics["cuda_device_count"] = int(torch_runtime.cuda.device_count())
            diagnostics["cuda_device_name"] = str(torch_runtime.cuda.get_device_name(0))
            diagnostics["cuda_memory_allocated_mb"] = round(torch_runtime.cuda.memory_allocated(0) / (1024 * 1024), 2)
            diagnostics["cuda_memory_reserved_mb"] = round(torch_runtime.cuda.memory_reserved(0) / (1024 * 1024), 2)

    return diagnostics


def example_profile_patch() -> dict[str, object]:
    return {
        "age": 24,
        "sex": "male",
        "height_cm": 175,
        "weight_kg": 72,
        "activity_level": "moderate",
        "goal": "muscle_gain",
        "workout_days_per_week": 4,
        "train_location": "gym",
        "experience_level": "beginner",
        "budget_level": "medium",
        "cook_time_preference": "quick",
    }


class ColabGemmaChatSession:
    def __init__(
        self,
        *,
        user_id: str = "colab-user",
        session_id: str | None = None,
        reload_backend: bool = False,
    ) -> None:
        runtime = _load_runtime_bindings(force_reload=reload_backend)
        build_llm_backend = runtime["build_llm_backend"]
        self.user_id = user_id
        self.session_id = session_id or f"colab-chat-{uuid4().hex[:8]}"
        if reload_backend and hasattr(build_llm_backend, "cache_clear"):
            build_llm_backend.cache_clear()
        runtime["init_db"]()
        self._runtime = runtime
        self.orchestrator = runtime["FitnessChatOrchestrator"]()

    def reset_session(self, session_id: str | None = None) -> str:
        self.session_id = session_id or f"colab-chat-{uuid4().hex[:8]}"
        return self.session_id

    def send(
        self,
        message: str,
        profile_patch: dict[str, Any] | None = None,
    ):
        request = self._runtime["ChatRequest"](
            user_id=self.user_id,
            session_id=self.session_id,
            message=message,
            profile_patch=_coerce_profile_patch(profile_patch, self._runtime["UserProfilePatch"]),
        )
        return self.orchestrator.handle_chat(request)


def chat_once(
    *,
    message: str,
    profile_patch: dict[str, Any] | None = None,
    user_id: str = "colab-user",
    session_id: str = "colab-chat",
    reload_backend: bool = False,
):
    session = ColabGemmaChatSession(
        user_id=user_id,
        session_id=session_id,
        reload_backend=reload_backend,
    )
    return session.send(message=message, profile_patch=profile_patch)


def launch_colab_chat(
    *,
    user_id: str = "colab-user",
    session_id: str | None = None,
    default_profile_patch: dict[str, Any] | None = None,
    reload_backend: bool = False,
):
    try:
        try:  # pragma: no cover - notebook-only path
            from google.colab import output as colab_output

            colab_output.enable_custom_widget_manager()
        except Exception:
            pass

        import ipywidgets as widgets
        from IPython.display import display
    except ImportError as exc:  # pragma: no cover - notebook-only path
        raise RuntimeError(
            "ipywidgets is not available in this runtime. "
            "Install it first or use chat_once(...) for single-turn testing."
        ) from exc

    session = ColabGemmaChatSession(
        user_id=user_id,
        session_id=session_id,
        reload_backend=reload_backend,
    )

    profile_value = _safe_json_dumps(default_profile_patch or example_profile_patch())
    summary_value = _safe_json_dumps(runtime_summary())

    header = widgets.HTML(
        value=(
            "<b>Fitness Chatbot (Colab + Gemma)</b><br>"
            f"user_id: <code>{session.user_id}</code> | "
            f"session_id: <code>{session.session_id}</code>"
        )
    )
    runtime_box = widgets.Textarea(
        value=summary_value,
        description="Runtime",
        disabled=True,
        layout=widgets.Layout(width="100%", height="150px"),
    )
    message_box = widgets.Textarea(
        value="",
        placeholder="Nhập tin nhắn ở đây...",
        description="Message",
        layout=widgets.Layout(width="100%", height="110px"),
    )
    profile_box = widgets.Textarea(
        value=profile_value,
        placeholder='{"age": 24, "sex": "male", "height_cm": 175, "weight_kg": 72, "activity_level": "moderate", "goal": "muscle_gain"}',
        description="Profile",
        layout=widgets.Layout(width="100%", height="200px"),
    )
    show_debug = widgets.Checkbox(
        value=False,
        description="Show debug JSON",
        indent=False,
    )
    keep_profile = widgets.Checkbox(
        value=True,
        description="Keep profile for next turns",
        indent=False,
    )
    send_button = widgets.Button(
        description="Send",
        button_style="success",
        icon="paper-plane",
    )
    new_session_button = widgets.Button(
        description="New session",
        button_style="warning",
        icon="refresh",
    )
    clear_profile_button = widgets.Button(
        description="Clear profile JSON",
        button_style="",
        icon="eraser",
    )
    output = widgets.Output(layout=widgets.Layout(border="1px solid #ddd", padding="8px"))

    def _parse_profile_patch() -> dict[str, Any] | None:
        raw = profile_box.value.strip()
        if not raw:
            return None
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Profile JSON must be an object.")
        return parsed

    def _append_chat(role: str, text: str) -> None:
        with output:
            print(f"{role}:")
            print(text)
            print("")

    def _handle_send(_: object) -> None:
        message = message_box.value.strip()
        if not message:
            with output:
                print("Enter a message before sending.\n")
            return

        try:
            profile_patch = _parse_profile_patch()
        except Exception as exc:
            with output:
                print(f"Invalid profile JSON: {exc}\n")
            return

        with output:
            print("[Sending...]")

        try:
            response = session.send(message=message, profile_patch=profile_patch)
        except Exception as exc:
            with output:
                print(f"[ERROR] {type(exc).__name__}: {exc}")
                print(traceback.format_exc())
                print("")
            return

        _append_chat("You", message)
        _append_chat("Bot", response.reply)
        if show_debug.value:
            with output:
                print("[DEBUG RESPONSE]")
                print(_format_response(response))
                print("")
        message_box.value = ""
        if not keep_profile.value:
            profile_box.value = ""

    def _handle_new_session(_: object) -> None:
        new_session_id = session.reset_session()
        header.value = (
            "<b>Fitness Chatbot (Colab + Gemma)</b><br>"
            f"user_id: <code>{session.user_id}</code> | "
            f"session_id: <code>{new_session_id}</code>"
        )
        with output:
            print(f"Created a new session: {new_session_id}\n")

    def _handle_clear_profile(_: object) -> None:
        profile_box.value = ""

    send_button.on_click(_handle_send)
    new_session_button.on_click(_handle_new_session)
    clear_profile_button.on_click(_handle_clear_profile)

    controls = widgets.HBox([send_button, new_session_button, clear_profile_button, show_debug, keep_profile])
    ui = widgets.VBox(
        [
            header,
            runtime_box,
            message_box,
            profile_box,
            controls,
            output,
        ]
    )
    display(ui)
    with output:
        if not reload_backend:
            print(
                "[NOTE] reload_backend=False se dung cac module da import san. "
                "Neu ban vua sua code backend, hay restart runtime hoac launch_colab_chat(reload_backend=True).\n"
            )
        print("Chat UI is ready. Enter a message and click Send.\n")
    return session


def launch_cli_chat(
    *,
    user_id: str = "cli-user",
    session_id: str | None = None,
    reload_backend: bool = False,
) -> None:
    session = ColabGemmaChatSession(
        user_id=user_id,
        session_id=session_id,
        reload_backend=reload_backend,
    )
    print("Runtime:")
    print(_safe_json_dumps(runtime_summary()))
    print("")
    print(f"Chat session: {session.session_id}")
    print("Type /exit to stop or /new to start a new session.")
    print("")

    while True:
        message = input("You: ").strip()
        if not message:
            continue
        if message == "/exit":
            break
        if message == "/new":
            print(f"New session: {session.reset_session()}")
            continue

        response = session.send(message)
        print(f"Bot: {response.reply}")
        print("")


def launch_colab_gemma_chat(
    *,
    user_id: str = "colab-user",
    session_id: str | None = None,
    default_profile_patch: dict[str, Any] | None = None,
    reload_backend: bool = False,
):
    return launch_colab_chat(
        user_id=user_id,
        session_id=session_id,
        default_profile_patch=default_profile_patch,
        reload_backend=reload_backend,
    )


if __name__ == "__main__":
    print(_safe_json_dumps(runtime_summary()))
    launch_cli_chat()
