from __future__ import annotations

import gc
import json
import re
from pathlib import Path
from typing import Any

from app.core.text_utils import normalize_text
from app.llm.base import BaseLLMBackend
from app.llm.mock_gemma import MockGemmaInferencer


NON_LATIN_NOISE_PATTERN = re.compile(
    r"[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0C00-\u0C7F\u0E00-\u0E7F\u3040-\u30FF\u3400-\u9FFF\uAC00-\uD7AF]"
)
PROMPT_LEAK_LABEL_PATTERN = re.compile(r"^[A-Z][A-Z0-9_ ]{5,}:")
PROMPT_LEAK_LINE_PREFIXES = (
    "user_context",
    "user_context_final",
    "profile_final",
    "profile hien tai",
    "profile lien quan",
    "cau hoi hien tai",
    "cau hoi cuoi cung",
    "user dang hoi",
    "yeu cau hien tai",
    "ngu canh truoc do",
    "thong tin tham khao neu lien quan",
    "thong tin tham khao lien quan",
    "thongtin tham khao lien quan",
    "khung so lieu hien co",
    "khung lich tap hien co",
    "goi y tap luyen lien quan",
    "goi y nen",
    "cac muc chua co trong catalog",
    "phan da tinh bang catalog hien co",
    "kinh nghiem tap",
    "muc tieu",
    "muc van dong",
    "so buoi tap/tuan",
    "thoi gian nau",
    "ngan sach",
    "mon ua thich",
    "mon khong thich",
)
PROMPT_LEAK_MARKERS = (
    "user_context",
    "user_context_final",
    "profile_final",
    "profile hien tai",
    "profile lien quan",
    "cau hoi hien tai",
    "cau hoi cuoi cung",
    "thong tin tham khao neu lien quan",
    "thong tin tham khao lien quan",
    "thongtin tham khao lien quan",
    "khung so lieu hien co",
    "khung lich tap hien co",
    "goi y tap luyen lien quan",
    "goi y nen",
    "tool_results",
    "response_rules",
    "system_prompt",
    "profile hien dai",
    "profile hieuplan",
)
CUDA_DEVICE_MODES = {"cuda", "auto"}
QUANTIZED_MODES = {"4bit", "8bit"}


class LocalGemmaInferencer(BaseLLMBackend):
    def __init__(
        self,
        model_id: str,
        device: str,
        dtype: str,
        quantization: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float,
        do_sample: bool,
        trust_remote_code: bool,
        cpu_offload: bool,
        offload_buffers: bool,
        gpu_memory_limit_mb: int,
        cpu_memory_limit_mb: int,
    ) -> None:
        self.model_id = model_id
        self.device = device
        self.dtype = dtype
        self.quantization = quantization
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.do_sample = do_sample
        self.trust_remote_code = trust_remote_code
        self.cpu_offload = cpu_offload
        self.offload_buffers = offload_buffers
        self.gpu_memory_limit_mb = gpu_memory_limit_mb
        self.cpu_memory_limit_mb = cpu_memory_limit_mb

        self._processor: Any | None = None
        self._model: Any | None = None
        self._torch: Any | None = None
        self._fallback_backend: MockGemmaInferencer | None = None

    def generate(self, prompt: dict[str, object]) -> str:
        self._ensure_loaded()

        messages = self._build_messages(prompt)
        prompt_text = self._render_messages(messages)
        if isinstance(prompt_text, dict):
            inputs = prompt_text
        else:
            inputs = self._processor(text=prompt_text, return_tensors="pt")
        inputs = self._move_inputs_to_model_device(inputs)

        input_ids = inputs["input_ids"]
        input_length = input_ids.shape[-1]

        generation_kwargs = {
            "max_new_tokens": self.max_new_tokens,
            "pad_token_id": self._get_pad_token_id(),
            "do_sample": self.do_sample,
            "repetition_penalty": 1.1,
            "no_repeat_ngram_size": 4,
        }
        if self.do_sample:
            generation_kwargs["temperature"] = self.temperature
            generation_kwargs["top_p"] = self.top_p

        outputs = self._model.generate(**inputs, **generation_kwargs)
        generated_tokens = outputs[0][input_length:]
        decoded = self._processor.decode(generated_tokens, skip_special_tokens=False)
        parsed = self._parse_response(decoded)
        if parsed:
            cleaned = self._cleanup_response(parsed, prompt)
            if cleaned:
                return self._ground_response(cleaned, prompt)

        fallback = self._processor.decode(generated_tokens, skip_special_tokens=True).strip()
        cleaned_fallback = self._cleanup_response(fallback, prompt)
        if cleaned_fallback:
            return self._ground_response(cleaned_fallback, prompt)

        cleaned_decoded = self._cleanup_response(decoded.strip(), prompt)
        if cleaned_decoded:
            return self._ground_response(cleaned_decoded, prompt)

        return self._fallback_for_prompt(prompt)

    def _ensure_loaded(self) -> None:
        if self._model is not None and self._processor is not None:
            return

        runtime = self._load_transformers_runtime()
        torch = runtime["torch"]
        self._torch = torch
        self._validate_runtime(torch)

        pretrained_kwargs = self._build_pretrained_kwargs()
        config = self._load_model_config(runtime, pretrained_kwargs)
        self._processor = self._load_processor(runtime, pretrained_kwargs)
        model_cls = self._select_model_class(config, runtime)
        model_kwargs = self._build_model_kwargs(runtime)

        try:
            self._model = self._load_model_with_retry(model_cls, model_kwargs)
        except ValueError as exc:
            if "dispatched on the CPU or the disk" in str(exc):
                raise RuntimeError(
                    "GPU RAM is not enough for the current Gemma loading strategy. "
                    "Try one of these: "
                    "1) keep 4bit but enable stronger CPU offload, "
                    "2) lower GEMMA_GPU_MEMORY_LIMIT_MB, "
                    "3) run `run_local_backend.ps1 -Device cpu -Quantization none -DType float32` "
                    "to smoke test the wiring on CPU."
                ) from exc
            raise

        self._move_model_to_explicit_device_if_needed()

    def _load_transformers_runtime(self) -> dict[str, Any]:
        try:
            import torch
            from transformers import AutoConfig, AutoModelForCausalLM, AutoProcessor, Gemma4ForConditionalGeneration
        except ImportError as exc:
            raise RuntimeError(
                "Local Gemma backend requires a Transformers build that includes Gemma 4 support, "
                "along with `torch`. Install a newer/main Transformers build before using "
                "`LLM_BACKEND=local-transformers`."
            ) from exc

        return {
            "torch": torch,
            "AutoConfig": AutoConfig,
            "AutoModelForCausalLM": AutoModelForCausalLM,
            "AutoProcessor": AutoProcessor,
            "Gemma4ForConditionalGeneration": Gemma4ForConditionalGeneration,
        }

    def _load_model_config(self, runtime: dict[str, Any], pretrained_kwargs: dict[str, Any]) -> Any:
        auto_config = runtime["AutoConfig"]
        try:
            return auto_config.from_pretrained(
                self.model_id,
                trust_remote_code=self.trust_remote_code,
                **pretrained_kwargs,
            )
        except ValueError as exc:
            raise RuntimeError(
                "The installed Transformers version does not recognize this Gemma 4 checkpoint yet. "
                "Try installing Transformers from source: "
                "`python -m pip install git+https://github.com/huggingface/transformers`"
            ) from exc

    def _load_processor(self, runtime: dict[str, Any], pretrained_kwargs: dict[str, Any]) -> Any:
        auto_processor = runtime["AutoProcessor"]
        processor_kwargs = {"trust_remote_code": self.trust_remote_code, **pretrained_kwargs}
        return auto_processor.from_pretrained(self.model_id, **processor_kwargs)

    def _select_model_class(self, config: Any, runtime: dict[str, Any]) -> Any:
        if getattr(config, "model_type", "") == "gemma4":
            return runtime["Gemma4ForConditionalGeneration"]
        return runtime["AutoModelForCausalLM"]

    def _move_model_to_explicit_device_if_needed(self) -> None:
        if self._model is None:
            return
        if self.quantization_mode != "none":
            return
        if self.device_mode in CUDA_DEVICE_MODES:
            return
        self._model.to(self.device)

    def _load_model_with_retry(self, model_cls: Any, model_kwargs: dict[str, Any]) -> Any:
        try:
            return model_cls.from_pretrained(self.model_id, **model_kwargs)
        except Exception as exc:
            if not self._should_retry_without_allocator_warmup(exc):
                raise

            from transformers import modeling_utils as transformers_modeling_utils

            original_warmup = transformers_modeling_utils.caching_allocator_warmup
            transformers_modeling_utils.caching_allocator_warmup = lambda *args, **kwargs: None
            try:
                self._clear_cuda_cache()
                return model_cls.from_pretrained(self.model_id, **model_kwargs)
            finally:
                transformers_modeling_utils.caching_allocator_warmup = original_warmup

    def _should_retry_without_allocator_warmup(self, exc: Exception) -> bool:
        if self._torch is None:
            return False
        if self.device.strip().lower() not in {"cuda", "auto"}:
            return False

        oom_error = getattr(self._torch, "OutOfMemoryError", None)
        if oom_error is not None and isinstance(exc, oom_error):
            return True

        return "out of memory" in str(exc).lower()

    def _clear_cuda_cache(self) -> None:
        if self._torch is None or not getattr(self._torch, "cuda", None):
            return
        if not self._torch.cuda.is_available():
            return
        gc.collect()
        self._torch.cuda.empty_cache()

    @property
    def device_mode(self) -> str:
        return self.device.strip().lower()

    @property
    def quantization_mode(self) -> str:
        return self.quantization.strip().lower()

    def _build_model_kwargs(self, runtime: dict[str, Any]) -> dict[str, Any]:
        model_kwargs = self._build_base_model_kwargs()
        if self.quantization_mode == "none":
            return self._build_unquantized_model_kwargs(runtime["torch"], model_kwargs)
        return self._build_quantized_model_kwargs(runtime["torch"], model_kwargs)

    def _build_base_model_kwargs(self) -> dict[str, Any]:
        return {
            "trust_remote_code": self.trust_remote_code,
            "use_safetensors": True,
            **self._build_pretrained_kwargs(),
        }

    def _build_unquantized_model_kwargs(self, torch: Any, model_kwargs: dict[str, Any]) -> dict[str, Any]:
        model_kwargs["torch_dtype"] = self._resolve_torch_dtype(torch)
        if self.device_mode in CUDA_DEVICE_MODES:
            self._apply_auto_device_map(model_kwargs)
        return model_kwargs

    def _build_quantized_model_kwargs(self, torch: Any, model_kwargs: dict[str, Any]) -> dict[str, Any]:
        try:
            from transformers import BitsAndBytesConfig
        except ImportError as exc:
            raise RuntimeError(
                "Quantized Gemma inference requires `bitsandbytes` in addition to `transformers` and `torch`."
            ) from exc

        model_kwargs["quantization_config"] = self._build_quantization_config(torch, BitsAndBytesConfig)
        self._apply_auto_device_map(model_kwargs)
        return model_kwargs

    def _build_quantization_config(self, torch: Any, config_cls: Any) -> Any:
        if self.quantization_mode == "4bit":
            return config_cls(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=self._resolve_torch_dtype(torch),
                llm_int8_enable_fp32_cpu_offload=self.cpu_offload,
            )

        if self.quantization_mode == "8bit":
            return config_cls(
                load_in_8bit=True,
                llm_int8_enable_fp32_cpu_offload=self.cpu_offload,
            )

        raise ValueError(f"Unsupported GEMMA_QUANTIZATION mode: {self.quantization}")

    def _apply_auto_device_map(self, model_kwargs: dict[str, Any]) -> None:
        model_kwargs["device_map"] = "auto"
        model_kwargs["max_memory"] = self._build_max_memory()
        if self.offload_buffers:
            model_kwargs["offload_buffers"] = True

    def _build_pretrained_kwargs(self) -> dict[str, Any]:
        if self._is_local_path():
            return {"local_files_only": True}
        return {}

    def _is_local_path(self) -> bool:
        return Path(self.model_id).exists()

    def _build_max_memory(self) -> dict[Any, str]:
        if self.device_mode not in CUDA_DEVICE_MODES:
            return {"cpu": f"{self.cpu_memory_limit_mb}MiB"}

        gpu_index: Any = 0
        return {
            gpu_index: f"{self.gpu_memory_limit_mb}MiB",
            "cpu": f"{self.cpu_memory_limit_mb}MiB",
        }

    def _validate_runtime(self, torch: Any) -> None:
        if self.device_mode == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "GEMMA_DEVICE is set to `cuda` but CUDA is not available in this environment."
            )

        if self.quantization_mode in QUANTIZED_MODES and self.device_mode not in CUDA_DEVICE_MODES:
            raise RuntimeError(
                "Quantized Gemma inference currently expects GEMMA_DEVICE to be `cuda` or `auto`."
            )

    def _resolve_torch_dtype(self, torch: Any) -> Any:
        mapping = {
            "float32": torch.float32,
            "float16": torch.float16,
            "fp16": torch.float16,
            "bfloat16": torch.bfloat16,
            "bf16": torch.bfloat16,
        }
        key = self.dtype.strip().lower()
        if key not in mapping:
            raise ValueError(f"Unsupported GEMMA_DTYPE: {self.dtype}")
        return mapping[key]

    def _build_messages(self, prompt: dict[str, object]) -> list[dict[str, str]]:
        system_prompt = self._build_system_prompt(prompt)
        user_prompt_payload = dict(prompt)
        user_prompt_payload["system_prompt"] = ""
        user_prompt = self._build_user_prompt(user_prompt_payload).strip()

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _build_system_prompt(self, prompt: dict[str, object]) -> str:
        base_system = str(prompt.get("system_prompt", "")).strip()
        intent = str(prompt.get("intent", "general_fitness_qa"))
        shared_rules = (
            "Tra loi bang tieng Viet tu nhien, khong lap lai cau hoi cua user. "
            "Khong nhac den prompt, tool_results, response_rules, intent, history hay nhan noi bo. "
            "Khong viet cac nhan nhu Final Answer, Response hay Giai dap cuoi cung. "
            "Neu da co so lieu tu tool thi dung dung cac so do."
        )
        if intent == "nutrition_llm_fallback":
            persona_rules = (
                "Ban la tro ly huu ich noi tieng Viet, chuyen uoc luong dinh duong thuc dung. "
                "Hay tra loi ngan gon, than trong, va noi ro day chi la uoc luong low-confidence neu catalog chua co du lieu."
            )
        elif intent == "general_fitness_qa":
            persona_rules = (
                "Ban la tro ly huu ich noi tieng Viet. "
                "Tra loi nhu dang tro chuyen truc tiep voi nguoi dung, "
                "khong dien tiep mau prompt hay liet ke lai cac nhan boi canh. "
                "Chi dua vao knowledge context neu no that su lien quan voi cau hoi hien tai."
            )
        else:
            persona_rules = (
                "Ban la tro ly fitness noi tieng Viet. "
                "Tra loi truc tiep, huu ich, va tong hop tu profile, history, va knowledge context. "
                "Neu da co tool results thi dung chung, neu khong thi khong tu bo sung so lieu tinh toan."
            )
        return "\n".join(part for part in [base_system, persona_rules, shared_rules] if part)

    def _build_user_prompt(self, prompt: dict[str, object]) -> str:
        profile_summary = str(prompt.get("profile_summary", "")).strip()
        personalization_summary = str(prompt.get("personalization_summary", "")).strip()
        tool_results = self._format_tool_context(prompt)
        kb_context = self._format_kb_context_for_prompt(prompt)
        history = self._format_history(prompt.get("history", []))
        message = str(prompt.get("message", "")).strip()
        intent = str(prompt.get("intent", "")).strip()
        answer_brief = self._build_answer_brief(prompt)

        if intent == "nutrition_llm_fallback":
            fallback_items = prompt.get("nutrition_fallback_items", [])
            rendered_items = ""
            if isinstance(fallback_items, list) and fallback_items:
                rendered_items = "\n".join(f"- {str(item)}" for item in fallback_items)
            known_totals = prompt.get("nutrition_known_totals", {})
            known_totals_text = ""
            if isinstance(known_totals, dict) and any(
                float(known_totals.get(key, 0) or 0) > 0 for key in ("calories", "protein_g", "carb_g", "fat_g")
            ):
                known_totals_text = (
                    "Phan da tinh bang catalog hien co:\n"
                    f"- {known_totals.get('calories', 0)} kcal | "
                    f"{known_totals.get('protein_g', 0)}g protein | "
                    f"{known_totals.get('carb_g', 0)}g carb | "
                    f"{known_totals.get('fat_g', 0)}g fat"
                )
            parts = [
                f"Yeu cau hien tai: {message}",
                f"Cac muc chua co trong catalog:\n{rendered_items}" if rendered_items else "",
                known_totals_text,
                answer_brief if answer_brief else "",
            ]
            return "\n\n".join(part for part in parts if part)

        if intent == "general_fitness_qa":
            return self._build_general_user_prompt(
                message=message,
                profile_summary=profile_summary,
                history=history,
                kb_context=kb_context,
            )

        if intent == "request_meal_guidance":
            return self._build_grounded_guidance_prompt(
                message=message,
                profile_summary=profile_summary,
                personalization_summary=personalization_summary,
                history=history,
                tool_context=tool_results,
                tool_context_label="Neu da co khung so lieu lien quan, hay xem day la du lieu uu tien:",
                kb_context=kb_context,
                answer_brief=answer_brief,
                closing_instruction=(
                    "Dua ra khung bua an goi y thuc te, uu tien mon de ap dung, "
                    "va chi nhac den calories/macro neu prompt co san so lieu ro rang."
                ),
            )

        if intent == "request_workout_plan":
            return self._build_grounded_guidance_prompt(
                message=message,
                profile_summary=profile_summary,
                personalization_summary=personalization_summary,
                history=history,
                tool_context=tool_results,
                tool_context_label="Neu da co mot khung lich tap tam thoi, hay xem day la boi canh uu tien:",
                kb_context=kb_context,
                answer_brief=answer_brief,
                closing_instruction=(
                    "Dua ra lich tap hoac split goi y bang ngon ngu coach, "
                    "tap trung vao tinh thuc te va dieu chinh neu co chan thuong hay han che."
                ),
            )

        if intent == "request_tdee_macro":
            parts = [
                f"User dang hoi: {message}",
                f"Profile lien quan: {profile_summary}" if profile_summary else "",
                f"So lieu hien co:\n{tool_results}" if tool_results not in ("", "{}", "[]") else "",
                answer_brief if answer_brief else "",
            ]
            return "\n\n".join(part for part in parts if part)

        parts = [
            f"User dang hoi: {message}",
            f"Profile lien quan: {profile_summary}" if profile_summary else "",
            f"Luu y them: {personalization_summary}" if personalization_summary else "",
            f"Thong tin bo sung:\n{tool_results}" if tool_results not in ("", "{}", "[]") else "",
            f"Context lien quan:\n{kb_context}" if kb_context else "",
            answer_brief if answer_brief else "",
        ]
        return "\n\n".join(part for part in parts if part)

    def _build_general_user_prompt(
        self,
        *,
        message: str,
        profile_summary: str,
        history: str,
        kb_context: str,
    ) -> str:
        parts = [message]

        if profile_summary:
            parts.append(f"Neu can ca nhan hoa, hay dua tren thong tin nay: {profile_summary}.")
        if history:
            parts.append(
                "Neu lien quan, hay noi tiep mach hoi thoai gan day thay vi bat dau lai tu dau:\n"
                f"{history}"
            )
        if kb_context:
            parts.append(
                "Neu mot y nao ben duoi thuc su giup ich, hay dien dat lai bang loi cua ban thay vi chep nguyen van:\n"
                f"{kb_context}"
            )

        parts.append("Tra loi nhu dang tro chuyen binh thuong va tap trung vao dieu nguoi dung dang hoi.")
        return "\n\n".join(part for part in parts if part)

    def _build_grounded_guidance_prompt(
        self,
        *,
        message: str,
        profile_summary: str,
        personalization_summary: str,
        history: str,
        tool_context: str,
        tool_context_label: str,
        kb_context: str,
        answer_brief: str,
        closing_instruction: str,
    ) -> str:
        parts = [message]

        if profile_summary:
            parts.append(f"Thong tin co the dung de ca nhan hoa: {profile_summary}.")
        if personalization_summary:
            parts.append(f"Luu y them neu can: {personalization_summary}.")
        if history:
            parts.append(f"Mach hoi thoai gan day neu lien quan:\n{history}")
        if tool_context not in ("", "{}", "[]"):
            parts.append(f"{tool_context_label}\n{tool_context}")
        if kb_context:
            parts.append(
                "Nhung y tu knowledge context ben duoi co the tham khao. "
                "Hay tong hop lai bang loi cua ban thay vi chep nguyen van:\n"
                f"{kb_context}"
            )
        if answer_brief:
            parts.append(answer_brief)

        parts.append(closing_instruction)
        return "\n\n".join(part for part in parts if part)

    def _build_answer_brief(self, prompt: dict[str, object]) -> str:
        intent = str(prompt.get("intent", "general_fitness_qa"))
        briefs = {
            "request_tdee_macro": "Tom tat ngan gon calories muc tieu va macro theo dung so trong du lieu.",
            "request_meal_guidance": "Tao khung 3-5 bua an ro rang, moi bua co vi du mon ngan gon va de hieu, dua tren profile va knowledge context.",
            "request_workout_plan": "Viet 1 doan ngan kieu coach, goi y split va cach sap buoi tap dua tren profile va knowledge context, khong can JSON.",
            "general_fitness_qa": "",
            "nutrition_llm_fallback": "Uoc luong so bo cho tung muc chua co trong catalog, neu can thi dua ra khoang kcal thay vi mot con so cung. Noi ro day la uoc luong low-confidence.",
        }
        return briefs.get(intent, "")

    def _format_tool_context(self, prompt: dict[str, object]) -> str:
        intent = str(prompt.get("intent", ""))
        tool_results = prompt.get("tool_results", {})

        if intent == "request_workout_plan" and isinstance(tool_results, dict):
            workout_plan = tool_results.get("workout_plan", {})
            summary = self._format_workout_plan_summary(workout_plan)
            if summary:
                return summary

        return self._format_json(tool_results)

    def _format_kb_context_for_prompt(self, prompt: dict[str, object]) -> str:
        intent = str(prompt.get("intent", ""))
        kb_context = prompt.get("kb_context", [])
        formatted = self._format_kb_context(kb_context)
        if intent != "request_workout_plan" or not isinstance(kb_context, list):
            return formatted

        concise_entries: list[str] = []
        for item in kb_context[:3]:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category", ""))
            section = str(item.get("section", ""))
            if not (category.startswith(("workout", "recovery")) or section in {"workout", "recovery"}):
                continue
            title = str(item.get("title", "")).strip()
            content = str(item.get("content", "")).strip()
            first_sentence = content.split(".")[0].strip()
            if title and first_sentence:
                concise_entries.append(f"- {title}: {first_sentence}.")
            elif first_sentence:
                concise_entries.append(f"- {first_sentence}.")
        if concise_entries:
            return "\n".join(concise_entries)
        return formatted

    def _format_workout_plan_summary(self, workout_plan: object) -> str:
        if not isinstance(workout_plan, dict) or not workout_plan:
            return ""

        split = str(workout_plan.get("split", "custom")).strip()
        goal = str(workout_plan.get("goal", "")).strip()
        train_location = str(workout_plan.get("train_location", "")).strip()
        days = workout_plan.get("days", [])
        notes = workout_plan.get("notes", [])

        parts = [
            f"Split: {split}" if split else "",
            f"So buoi: {len(days)}" if isinstance(days, list) and days else "",
            f"Muc tieu: {goal}" if goal else "",
            f"Noi tap: {train_location}" if train_location else "",
        ]

        day_summaries: list[str] = []
        if isinstance(days, list):
            for day in days[:4]:
                if not isinstance(day, dict):
                    continue
                day_name = str(day.get("day", "")).strip()
                focus = str(day.get("focus", "")).strip()
                exercises = day.get("exercises", [])
                main_exercises: list[str] = []
                if isinstance(exercises, list):
                    for exercise in exercises[:3]:
                        if isinstance(exercise, dict):
                            name = str(exercise.get("name", "")).strip()
                            if name:
                                main_exercises.append(name)
                segment = f"- {day_name}: {focus}" if day_name or focus else ""
                if main_exercises:
                    exercise_text = ", ".join(main_exercises)
                    segment = f"{segment}. Bai chinh: {exercise_text}." if segment else f"- Bai chinh: {exercise_text}."
                if segment:
                    day_summaries.append(segment)

        notes_summary = ""
        if isinstance(notes, list) and notes:
            kept_notes = [str(note).strip() for note in notes[:2] if str(note).strip()]
            if kept_notes:
                notes_summary = "Luu y chinh: " + "; ".join(kept_notes) + "."

        sections = [part for part in parts if part]
        if notes_summary:
            sections.append(notes_summary)
        sections.extend(day_summaries)
        return "\n".join(sections)

    def _render_messages(self, messages: list[dict[str, str]]) -> Any:
        if hasattr(self._processor, "apply_chat_template"):
            try:
                return self._processor.apply_chat_template(
                    messages,
                    tokenize=True,
                    return_dict=True,
                    return_tensors="pt",
                    add_generation_prompt=True,
                    enable_thinking=False,
                )
            except TypeError:
                try:
                    return self._processor.apply_chat_template(
                        messages,
                        tokenize=True,
                        return_dict=True,
                        return_tensors="pt",
                        add_generation_prompt=True,
                    )
                except TypeError:
                    pass

        return "\n\n".join(f"{item['role'].upper()}: {item['content']}" for item in messages)

    def _move_inputs_to_model_device(self, inputs: Any) -> Any:
        model_device = self._get_model_device()
        if model_device is None:
            return inputs

        moved_inputs = {}
        for key, value in inputs.items():
            moved_inputs[key] = value.to(model_device) if hasattr(value, "to") else value
        return moved_inputs

    def _get_model_device(self) -> Any | None:
        if self._model is None:
            return None

        mapped_device = self._get_accelerate_input_device()
        if mapped_device is not None:
            return mapped_device

        try:
            return next(self._model.parameters()).device
        except (StopIteration, AttributeError, TypeError):
            return None

    def _get_accelerate_input_device(self) -> Any | None:
        hf_device_map = getattr(self._model, "hf_device_map", None)
        if not isinstance(hf_device_map, dict) or not hf_device_map:
            return None

        fallback_device: Any | None = None
        for raw_device in hf_device_map.values():
            normalized_device = self._normalize_device_spec(raw_device)
            if normalized_device is None:
                continue
            if self._is_cuda_device_spec(normalized_device):
                return normalized_device
            if fallback_device is None:
                fallback_device = normalized_device

        return fallback_device

    def _normalize_device_spec(self, raw_device: Any) -> Any | None:
        if raw_device is None:
            return None
        if isinstance(raw_device, int):
            return f"cuda:{raw_device}"

        device_text = str(raw_device).strip().lower()
        if not device_text or device_text in {"disk", "meta"}:
            return None
        if device_text.isdigit():
            return f"cuda:{device_text}"
        return device_text

    def _is_cuda_device_spec(self, device_spec: Any) -> bool:
        return str(device_spec).strip().lower().startswith("cuda")

    def _get_pad_token_id(self) -> int | None:
        tokenizer = getattr(self._processor, "tokenizer", None)
        if tokenizer is not None and getattr(tokenizer, "pad_token_id", None) is not None:
            return tokenizer.pad_token_id
        if tokenizer is not None and getattr(tokenizer, "eos_token_id", None) is not None:
            return tokenizer.eos_token_id
        return getattr(self._processor, "pad_token_id", None)

    def _parse_response(self, decoded: str) -> str:
        if hasattr(self._processor, "parse_response"):
            parsed = self._processor.parse_response(decoded)
            if isinstance(parsed, str):
                return parsed.strip()
            if isinstance(parsed, dict):
                for key in ("text", "response", "content"):
                    value = parsed.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                return json.dumps(parsed, ensure_ascii=False)
        return ""

    def _cleanup_response(self, text: str, prompt: dict[str, object]) -> str:
        raw = text.strip()
        if not raw:
            return ""

        user_message = str(prompt.get("message", "")).strip()
        normalized_user = normalize_text(user_message)

        lines = [line.strip() for line in raw.splitlines()]
        cleaned_lines: list[str] = []
        for line in lines:
            if not line or line == "```" or self._is_control_line(line):
                continue
            if normalize_text(line) == normalized_user:
                continue
            if cleaned_lines and line == cleaned_lines[-1]:
                continue
            cleaned_lines.append(line)

        cleaned = "\n".join(cleaned_lines).strip()
        if not cleaned:
            return ""

        cleaned = self._strip_prompt_leak_lines(cleaned)
        if self._looks_effectively_empty(cleaned):
            return ""

        if self._looks_like_echo(cleaned, normalized_user):
            return self._fallback_for_prompt(prompt)

        return cleaned

    def _ground_response(self, text: str, prompt: dict[str, object]) -> str:
        intent = str(prompt.get("intent", ""))
        if intent == "request_tdee_macro":
            tool_results = prompt.get("tool_results", {})
            macros = tool_results.get("macros", {}) if isinstance(tool_results, dict) else {}
            if isinstance(macros, dict) and macros:
                expected_values = [
                    str(macros.get("target_calories")),
                    str(macros.get("protein_g")),
                    str(macros.get("fat_g")),
                    str(macros.get("carb_g")),
                ]
                if not all(value in text for value in expected_values):
                    return self._fallback_for_prompt(prompt)
        if self._contains_generation_noise(text):
            return self._fallback_for_prompt(prompt)

        normalized = normalize_text(text)
        if self._looks_like_prompt_leak(text, normalized):
            return self._fallback_for_prompt(prompt)
        if intent == "general_fitness_qa":
            invalid_markers = [
                "neu co thong tin nao can thiet",
                "giai dap cuoi cung",
                "thong tin chi tiet",
                "trang vu",
                "trinh vu",
                "intent:",
                "profile:",
                "tool results",
                "tool_results",
                "history:",
                "ban mock",
                "safety case",
                "tool_settings",
                "hay chi su dung cac quy tac nay",
            ]
            if any(marker in normalized for marker in invalid_markers):
                return self._fallback_for_prompt(prompt)
        if intent == "request_workout_plan":
            if any(marker in normalized for marker in ["bua sang", "bua trua", "bua toi", "thuc don"]):
                return self._fallback_for_prompt(prompt)
        if intent == "nutrition_llm_fallback":
            invalid_markers = [
                "intent:",
                "tool results",
                "tool_results",
                "history:",
                "profile:",
                "ban mock",
            ]
            if any(marker in normalized for marker in invalid_markers):
                return self._fallback_for_prompt(prompt)
        return text

    def _fallback_for_prompt(self, prompt: dict[str, object]) -> str:
        intent = str(prompt.get("intent", "general_fitness_qa"))
        if intent == "general_fitness_qa":
            return self._render_general_fallback(prompt)
        if intent == "nutrition_llm_fallback":
            return self._render_nutrition_fallback(prompt)
        if intent == "request_tdee_macro":
            return self._render_macro_fallback(prompt)
        return self._get_fallback_backend().generate(prompt)

    def _get_fallback_backend(self) -> MockGemmaInferencer:
        if self._fallback_backend is None:
            self._fallback_backend = MockGemmaInferencer()
        return self._fallback_backend

    def _render_macro_fallback(self, prompt: dict[str, object]) -> str:
        tool_results = prompt.get("tool_results", {})
        macros = tool_results.get("macros", {}) if isinstance(tool_results, dict) else {}
        if isinstance(macros, dict) and macros:
            return (
                f"Muc calories muc tieu cua ban hien la {macros.get('target_calories')} kcal/ngay, "
                f"voi {macros.get('protein_g')}g protein, {macros.get('fat_g')}g fat va {macros.get('carb_g')}g carb. "
                "Day la khung co ban de di tiep sang meal plan."
            )
        return self._render_default_fallback(prompt)

    def _render_nutrition_fallback(self, prompt: dict[str, object]) -> str:
        fallback_message = (
            "Minh chi co the uoc luong so bo cho phan chua co trong nutrition catalog. "
            "Neu ban muon tinh sat hon, hay nhap ten cu the hon hoac khoi luong theo gram."
        )

        raw_items = prompt.get("nutrition_fallback_items", [])
        if not isinstance(raw_items, list):
            return fallback_message

        items = [str(item).strip() for item in raw_items if str(item).strip()]
        if not items:
            return fallback_message

        bullet_lines = [
            f"- `{item}`: hien chua co du lieu chuan, nen minh chi co the uoc luong o muc low-confidence."
            for item in items
        ]
        if not bullet_lines:
            return fallback_message
        return (
            "Cac muc duoi day chua co trong nutrition catalog, nen minh chi uoc luong o muc low-confidence:\n"
            + "\n".join(bullet_lines)
            + "\nNeu ban muon tinh sat hon, hay nhap ten cu the hon hoac tach thanh nguyen lieu chinh kem khoi luong theo gram."
        )

    def _render_general_fallback(self, prompt: dict[str, object]) -> str:
        message = str(prompt.get("message", "")).strip()
        kb_note = self._summarize_kb_context(prompt.get("kb_context", []), max_items=2)
        if not message:
            if kb_note:
                return kb_note
            return "Minh co the tra loi ngan gon va thuc te hon neu ban noi ro hon muc tieu hoac dieu ban muon hoi."

        normalized_message = normalize_text(message)
        compact_message = re.sub(r"[^a-z0-9]+", "", normalized_message)
        if any(keyword in compact_message for keyword in ["tapxong", "moitapxong", "sautap"]):
            reply = (
                "Sau tap, ban nen uu tien mot bua co protein ro rang kem carb de hoi phuc tot hon, "
                "vi du com + uc ga, bun + trung, hoac sua chua + chuoi neu can gon nhe."
            )
        elif any(keyword in compact_message for keyword in ["giamcan", "giammo", "fatloss"]):
            reply = (
                "Neu dang giam can, ban nen uu tien bua co protein ro rang, rau de no lau, "
                "va giu phan carb vua du, vi du uc ga + rau + com it hon, trung + salad + khoai, hoac dau hu + rau + com."
            )
        elif (
            any(keyword in compact_message for keyword in ["chiphi", "hetbao", "baonhieu", "tien1ngay"])
            or "chi phi" in normalized_message
            or ("bao" in normalized_message and "1" in normalized_message)
        ):
            reply = (
                "Chi phi moi ngay se phu thuoc vao khau phan va loai thuc pham ban chon, "
                "nhung neu muon toi uu thi co the uu tien trung, dau hu, uc ga, com va rau de vua de bam vua de kiem soat ngan sach."
            )
        elif any(keyword in compact_message for keyword in ["taikhoan", "motaikhoan", "nganhang"]):
            reply = (
                "De mo tai khoan ngan hang, ban co the bat dau bang cach chon ngan hang, chuan bi CCCD hoac giay to tuy than, "
                "roi dang ky tren app hoac ra chi nhanh de xac thuc thong tin theo huong dan cua ngan hang do."
            )
        elif any(keyword in compact_message for keyword in ["tapgym", "conentapgym", "cotaptapgym"]):
            reply = (
                "Neu suc khoe hien tai on va ban muon cai thien the luc, tap gym la mot lua chon rat on "
                "mien la ban bat dau voi muc vua phai, hoc ky thuat tu tu, va duy tri deu."
            )
        else:
            reply = (
                f'Voi cau hoi "{message}", minh se uu tien tra loi gon va thuc te nhat theo thong tin hien co. '
                "Neu ban muon, minh co the di sau hon vao mot muc tieu cu the hon o turn tiep theo."
            )

        if kb_note:
            return f"{reply} {kb_note}"
        return reply

    def _render_default_fallback(self, prompt: dict[str, object]) -> str:
        message = str(prompt.get("message", "")).strip()
        if message:
            return (
                f'Voi cau hoi "{message}", minh se uu tien tra loi gon va thuc te nhat theo thong tin hien co. '
                "Neu ban muon, minh co the di sau hon vao mot muc tieu cu the hon o turn tiep theo."
            )
        return "Minh can them mot chut thong tin de tra loi sat hon."


    def _summarize_kb_context(self, kb_context: object, max_items: int = 2) -> str:
        if not isinstance(kb_context, list):
            return ""

        segments: list[str] = []
        for item in kb_context:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            content = str(item.get("content", "")).strip()
            first_sentence = content.split(".")[0].strip()
            if not first_sentence:
                continue
            if title:
                segments.append(f"{title}: {first_sentence}.")
            else:
                segments.append(f"{first_sentence}.")
            if len(segments) >= max_items:
                break

        if not segments:
            return ""
        return "Goi y lien quan: " + " ".join(segments)

    def _contains_generation_noise(self, text: str) -> bool:
        normalized = normalize_text(text)
        if any(marker in normalized for marker in ["channel|", "turn|", "<channel|", "<turn|"]):
            return True
        noise_char_count = len(NON_LATIN_NOISE_PATTERN.findall(text))
        return noise_char_count >= 6

    def _strip_prompt_leak_lines(self, text: str) -> str:
        kept_lines: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or self._is_prompt_leak_line(line):
                continue
            kept_lines.append(line)
        return "\n".join(kept_lines).strip()

    def _is_prompt_leak_line(self, line: str) -> bool:
        normalized = normalize_text(line).strip(" .:-_;")
        if not normalized:
            return True
        if PROMPT_LEAK_LABEL_PATTERN.match(line):
            return True
        if any(normalized.startswith(prefix) for prefix in PROMPT_LEAK_LINE_PREFIXES):
            return True
        return normalized in {".", ";", ":", "-"}

    def _looks_effectively_empty(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return True
        return not any(char.isalpha() for char in stripped)

    def _looks_like_prompt_leak(self, text: str, normalized: str) -> bool:
        if any(marker in normalized for marker in PROMPT_LEAK_MARKERS):
            return True

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        prompt_leak_lines = sum(1 for line in lines if self._is_prompt_leak_line(line))
        if prompt_leak_lines >= 2:
            return True

        colon_heavy_lines = sum(1 for line in lines if line.count(":") >= 2)
        if colon_heavy_lines >= 2 and any(marker in normalized for marker in ("profile", "context", "muc tieu")):
            return True

        return False

    def _is_control_line(self, line: str) -> bool:
        lowered = line.strip().lower()
        normalized = normalize_text(lowered).strip(" -_`")

        exact_markers = {
            "---",
            "<eos>",
            "<bos>",
            "<end_of_turn>",
            "<start_of_turn>",
            "final output",
        }
        if lowered in exact_markers or normalized in exact_markers:
            return True

        if lowered.startswith("<|") and lowered.endswith(">"):
            return True

        if "turn|" in lowered or "turn|" in normalized:
            return True

        if normalized.startswith("final answer") or normalized.startswith("answer") or normalized.startswith("response"):
            return True

        if normalized in {"channel", "assistant", "user"}:
            return True

        return False

    def _looks_like_echo(self, text: str, normalized_user: str) -> bool:
        normalized_text = normalize_text(text)
        if not normalized_text:
            return True
        if normalized_user and normalized_text.count(normalized_user) >= 2:
            return True

        non_empty_lines = [line for line in text.splitlines() if line.strip()]
        if not non_empty_lines:
            return True

        short_lines = sum(1 for line in non_empty_lines if len(line.strip()) < 12)
        if short_lines == len(non_empty_lines) and len(non_empty_lines) > 3:
            return True

        return False
