from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.orchestrator import FitnessChatOrchestrator
from app.db.database import init_db
from app.llm.factory import build_llm_backend
from app.schemas.chat_request import ChatRequest
from app.schemas.user_profile import UserProfilePatch


def _safe_json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _format_debug_response(response: object) -> str:
    try:
        payload = response.model_dump()
    except AttributeError:
        payload = response
    return _safe_json_dumps(payload)


def _coerce_profile_patch(profile_patch: dict[str, Any] | None) -> UserProfilePatch | None:
    if not profile_patch:
        return None
    return UserProfilePatch(**profile_patch)


class ColabChatSession:
    def __init__(
        self,
        user_id: str = "colab-user",
        session_id: str | None = None,
        reload_backend: bool = False,
    ) -> None:
        self.user_id = user_id
        self.session_id = session_id or f"colab-chat-{uuid4().hex[:8]}"
        if reload_backend:
            build_llm_backend.cache_clear()
        init_db()
        self.orchestrator = FitnessChatOrchestrator()

    def reset_session(self, session_id: str | None = None) -> str:
        self.session_id = session_id or f"colab-chat-{uuid4().hex[:8]}"
        return self.session_id

    def send(self, message: str, profile_patch: dict[str, Any] | None = None):
        request = ChatRequest(
            user_id=self.user_id,
            session_id=self.session_id,
            message=message,
            profile_patch=_coerce_profile_patch(profile_patch),
        )
        return self.orchestrator.handle_chat(request)


def chat_once(
    message: str,
    profile_patch: dict[str, Any] | None = None,
    user_id: str = "colab-user",
    session_id: str = "colab-chat",
    reload_backend: bool = False,
):
    session = ColabChatSession(
        user_id=user_id,
        session_id=session_id,
        reload_backend=reload_backend,
    )
    return session.send(message=message, profile_patch=profile_patch)


def launch_colab_chat(
    user_id: str = "colab-user",
    session_id: str | None = None,
    default_profile_patch: dict[str, Any] | None = None,
    reload_backend: bool = False,
):
    try:
        import ipywidgets as widgets
        from IPython.display import display
    except ImportError as exc:  # pragma: no cover - notebook-only path
        raise RuntimeError(
            "Không tìm thấy ipywidgets trong runtime này. Bạn có thể cài bằng `pip install ipywidgets` "
            "hoặc dùng `chat_once(...)` để chat từng lượt."
        ) from exc

    session = ColabChatSession(
        user_id=user_id,
        session_id=session_id,
        reload_backend=reload_backend,
    )

    profile_value = ""
    if default_profile_patch:
        profile_value = _safe_json_dumps(default_profile_patch)

    header = widgets.HTML(
        value=(
            "<b>Chatbot Notebook UI</b><br>"
            f"user_id: <code>{session.user_id}</code> | "
            f"session_id: <code>{session.session_id}</code>"
        )
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
        layout=widgets.Layout(width="100%", height="160px"),
    )
    show_debug = widgets.Checkbox(
        value=False,
        description="Hiện debug JSON",
        indent=False,
    )
    send_button = widgets.Button(
        description="Gửi",
        button_style="success",
        icon="paper-plane",
    )
    new_session_button = widgets.Button(
        description="Session mới",
        button_style="warning",
        icon="refresh",
    )
    clear_profile_button = widgets.Button(
        description="Xóa profile JSON",
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
            raise ValueError("Profile JSON phải là object.")
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
                print("Nhập message trước khi gửi nhé.\n")
            return

        try:
            profile_patch = _parse_profile_patch()
        except Exception as exc:
            with output:
                print(f"Profile JSON chưa hợp lệ: {exc}\n")
            return

        response = session.send(message=message, profile_patch=profile_patch)
        _append_chat("Bạn", message)
        _append_chat("Bot", response.reply)
        if show_debug.value:
            with output:
                print("[DEBUG RESPONSE]")
                print(_format_debug_response(response))
                print("")
        message_box.value = ""

    def _handle_new_session(_: object) -> None:
        new_session_id = session.reset_session()
        header.value = (
            "<b>Chatbot Notebook UI</b><br>"
            f"user_id: <code>{session.user_id}</code> | "
            f"session_id: <code>{new_session_id}</code>"
        )
        with output:
            print(f"Đã tạo session mới: {new_session_id}\n")

    def _handle_clear_profile(_: object) -> None:
        profile_box.value = ""

    send_button.on_click(_handle_send)
    new_session_button.on_click(_handle_new_session)
    clear_profile_button.on_click(_handle_clear_profile)

    controls = widgets.HBox([send_button, new_session_button, clear_profile_button, show_debug])
    ui = widgets.VBox(
        [
            header,
            message_box,
            profile_box,
            controls,
            output,
        ]
    )
    display(ui)
    with output:
        print("UI đã sẵn sàng. Bạn nhập message rồi bấm Gửi là chat được.\n")
    return session


def launch_cli_chat(
    user_id: str = "cli-user",
    session_id: str | None = None,
    reload_backend: bool = False,
) -> None:
    session = ColabChatSession(
        user_id=user_id,
        session_id=session_id,
        reload_backend=reload_backend,
    )
    print(f"Chat session: {session.session_id}")
    print("Gõ /exit để thoát, /new để tạo session mới.")
    print("")

    while True:
        message = input("Bạn: ").strip()
        if not message:
            continue
        if message == "/exit":
            break
        if message == "/new":
            print(f"Session mới: {session.reset_session()}")
            continue

        response = session.send(message)
        print(f"Bot: {response.reply}")
        print("")


if __name__ == "__main__":
    launch_cli_chat()
