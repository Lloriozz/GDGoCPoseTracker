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
        self._fallback_backend = MockGemmaInferencer()

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

        return self._fallback_backend.generate(prompt)

    def _ensure_loaded(self) -> None:
        if self._model is not None and self._processor is not None:
            return

        try:
            import torch
            from transformers import AutoConfig, AutoModelForCausalLM, AutoProcessor, Gemma4ForConditionalGeneration
        except ImportError as exc:
            raise RuntimeError(
                "Local Gemma backend requires a Transformers build that includes Gemma 4 support, "
                "along with `torch`. Install a newer/main Transformers build before using "
                "`LLM_BACKEND=local-transformers`."
            ) from exc

        self._torch = torch
        self._validate_runtime(torch)

        pretrained_kwargs = self._build_pretrained_kwargs()
        processor_kwargs = {"trust_remote_code": self.trust_remote_code, **pretrained_kwargs}
        model_kwargs = self._build_model_kwargs(torch)

        try:
            config = AutoConfig.from_pretrained(
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
        self._processor = AutoProcessor.from_pretrained(self.model_id, **processor_kwargs)

        if getattr(config, "model_type", "") == "gemma4":
            model_cls = Gemma4ForConditionalGeneration
        else:
            model_cls = AutoModelForCausalLM

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

        if self.quantization.strip().lower() == "none" and self.device not in {"auto", "cuda"}:
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

    def _build_model_kwargs(self, torch: Any) -> dict[str, Any]:
        quantization_mode = self.quantization.strip().lower()
        model_kwargs: dict[str, Any] = {
            "trust_remote_code": self.trust_remote_code,
            "use_safetensors": True,
            **self._build_pretrained_kwargs(),
        }

        if quantization_mode == "none":
            model_kwargs["torch_dtype"] = self._resolve_torch_dtype(torch)
            if self.device in {"auto", "cuda"}:
                model_kwargs["device_map"] = "auto"
                model_kwargs["max_memory"] = self._build_max_memory()
                if self.offload_buffers:
                    model_kwargs["offload_buffers"] = True
            return model_kwargs

        try:
            from transformers import BitsAndBytesConfig
        except ImportError as exc:
            raise RuntimeError(
                "Quantized Gemma inference requires `bitsandbytes` in addition to `transformers` and `torch`."
            ) from exc

        if quantization_mode == "4bit":
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=self._resolve_torch_dtype(torch),
                llm_int8_enable_fp32_cpu_offload=self.cpu_offload,
            )
            model_kwargs["device_map"] = "auto"
            model_kwargs["max_memory"] = self._build_max_memory()
            if self.offload_buffers:
                model_kwargs["offload_buffers"] = True
            return model_kwargs

        if quantization_mode == "8bit":
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_enable_fp32_cpu_offload=self.cpu_offload,
            )
            model_kwargs["device_map"] = "auto"
            model_kwargs["max_memory"] = self._build_max_memory()
            if self.offload_buffers:
                model_kwargs["offload_buffers"] = True
            return model_kwargs

        raise ValueError(f"Unsupported GEMMA_QUANTIZATION mode: {self.quantization}")

    def _build_pretrained_kwargs(self) -> dict[str, Any]:
        if self._is_local_path():
            return {"local_files_only": True}
        return {}

    def _is_local_path(self) -> bool:
        return Path(self.model_id).exists()

    def _build_max_memory(self) -> dict[Any, str]:
        if self.device.strip().lower() not in {"cuda", "auto"}:
            return {"cpu": f"{self.cpu_memory_limit_mb}MiB"}

        gpu_index: Any = 0
        return {
            gpu_index: f"{self.gpu_memory_limit_mb}MiB",
            "cpu": f"{self.cpu_memory_limit_mb}MiB",
        }

    def _validate_runtime(self, torch: Any) -> None:
        device = self.device.strip().lower()
        quantization_mode = self.quantization.strip().lower()

        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "GEMMA_DEVICE is set to `cuda` but CUDA is not available in this environment."
            )

        if quantization_mode in {"4bit", "8bit"} and device not in {"cuda", "auto"}:
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
            "Không được lặp lại user message. "
            "Không được xuất markdown code fence. "
            "Không được viết các nhãn như Final Answer. "
            "Không được nhắc đến tên trường nội bộ như TOOL_RESULTS, TOOL_SETTINGS, RESPONSE_RULES, INTENT hay SAFETY CASE. "
            "Nếu có số trong tool results thì phải dùng đúng các số đó, không tự làm tròn."
        )
        if intent == "nutrition_llm_fallback":
            persona_rules = (
                "Bạn đang đóng vai một trợ lý hữu ích nói tiếng Việt, chuyên ước lượng dinh dưỡng thực dụng. "
                "Hãy trả lời ngắn gọn, tự nhiên, và nêu rất rõ đây chỉ là ước lượng low-confidence khi catalog chưa có dữ liệu."
            )
        elif intent == "general_fitness_qa":
            persona_rules = (
                "Bạn đang đóng vai một trợ lý hữu ích nói tiếng Việt. "
                "Hãy trả lời trực tiếp, tự nhiên, thực tế và không cố lái câu trả lời về fitness nếu câu hỏi không liên quan. "
                "Nếu có dữ liệu tool hoặc knowledge context thật sự liên quan thì dùng chúng để trả lời chắc hơn."
            )
        else:
            persona_rules = (
                "Bạn đang đóng vai một trợ lý fitness nói tiếng Việt. "
                "Hãy đưa ra câu trả lời trực tiếp, tự nhiên, hữu ích và bám sát tool results nếu đã có."
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
                    "Phần đã tính bằng catalog hiện có:\n"
                    f"- {known_totals.get('calories', 0)} kcal | "
                    f"{known_totals.get('protein_g', 0)}g protein | "
                    f"{known_totals.get('carb_g', 0)}g carb | "
                    f"{known_totals.get('fat_g', 0)}g fat"
                )
            parts = [
                f"Yêu cầu gốc của user: {message}",
                f"Các mục chưa có trong catalog:\n{rendered_items}" if rendered_items else "",
                known_totals_text,
                f"Nhiệm vụ trả lời: {answer_brief}" if answer_brief else "",
            ]
            return "\n\n".join(part for part in parts if part)

        if intent == "general_fitness_qa":
            parts = [
                f"Cau hoi hien tai: {message}",
                f"Ngữ cảnh trước đó:\n{history}" if history else "",
                f"Goi y lien quan:\n{kb_context}" if kb_context else "",
                f"Nhiem vu tra loi: {answer_brief}" if answer_brief else "",
            ]
            return "\n\n".join(part for part in parts if part)

        parts = [
            "Đây là dữ liệu để trả lời cho user.",
            f"Intent: {intent}",
            f"Profile: {profile_summary}" if profile_summary else "",
            f"Personalization: {personalization_summary}" if personalization_summary else "",
            f"History:\n{history}" if history else "",
            f"Tool results:\n{tool_results}" if tool_results not in ("", "{}", "[]") else "",
            f"Knowledge context:\n{kb_context}" if kb_context else "",
            f"Yêu cầu hiện tại của user: {message}",
            f"Nhiệm vụ trả lời: {answer_brief}" if answer_brief else "",
        ]
        return "\n\n".join(part for part in parts if part)

    def _build_answer_brief(self, prompt: dict[str, object]) -> str:
        intent = str(prompt.get("intent", "general_fitness_qa"))
        briefs = {
            "request_tdee_macro": (
                "Tóm tắt ngắn gọn calories mục tiêu và macro theo đúng số trong dữ liệu."
            ),
            "request_meal_guidance": (
                "Tạo khung 3-5 bữa ăn rõ ràng, mỗi bữa có ví dụ món ngắn gọn và dễ hiểu."
            ),
            "request_workout_plan": (
                "Viết 1 đoạn ngắn câu theo kiểu coach, tóm tắt split, số buổi, lý do chọn lịch và 1-2 lưu ý quan trọng nếu có chấn thương. "
                "Không liệt kê toàn bộ bài tập từng ngày trừ khi user hỏi."
            ),
            "general_fitness_qa": (
                "Trả lời trực tiếp câu hỏi hiện tại một cách hữu ích và tự nhiên, không nhắc đến dữ liệu hay quy tắc nội bộ."
            ),
            "nutrition_llm_fallback": (
                "Ước lượng sơ bộ cho từng mục chưa có trong catalog; nếu cần thì đưa ra khoảng kcal thay vì một con số cứng. "
                "Phải nói rõ đây là ước lượng low-confidence và khuyên user nhập tên cụ thể hơn hoặc gram nếu muốn sát hơn."
            ),
        }
        return briefs.get(intent, "Trả lời trực tiếp và hữu ích cho user.")

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
        for item in kb_context[:2]:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category", ""))
            if not category.startswith(("workout", "recovery")):
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
            f"Số buổi: {len(days)}" if isinstance(days, list) and days else "",
            f"Mục tiêu: {goal}" if goal else "",
            f"Nơi tập: {train_location}" if train_location else "",
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
                    segment = f"{segment}. Bài chính: {exercise_text}." if segment else f"- Bài chính: {exercise_text}."
                if segment:
                    day_summaries.append(segment)

        notes_summary = ""
        if isinstance(notes, list) and notes:
            kept_notes = [str(note).strip() for note in notes[:2] if str(note).strip()]
            if kept_notes:
                notes_summary = "Lưu ý chính: " + "; ".join(kept_notes) + "."

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

        try:
            return next(self._model.parameters()).device
        except (StopIteration, AttributeError, TypeError):
            return None

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

        if self._looks_like_echo(cleaned, normalized_user):
            return self._fallback_backend.generate(prompt)

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
                    return self._fallback_backend.generate(prompt)
        if intent == "request_meal_guidance":
            if (
                self._contains_internal_meta(text)
                or self._contains_meal_planning_meta(text)
                or not self._looks_like_meal_guidance(text)
            ):
                return self._fallback_backend.generate(prompt)
        if intent == "request_workout_plan":
            if (
                self._contains_internal_meta(text)
                or self._contains_generation_noise(text)
                or self._contains_workout_planning_meta(text)
                or not self._looks_like_workout_guidance(text, prompt)
            ):
                return self._fallback_backend.generate(prompt)
        if intent == "general_fitness_qa":
            if self._looks_invalid_general_response(text):
                return self._fallback_backend.generate(prompt)
        if intent == "nutrition_llm_fallback":
            if self._looks_invalid_nutrition_fallback_response(text):
                return self._fallback_backend.generate(prompt)
        return text

    def _contains_internal_meta(self, text: str) -> bool:
        normalized = normalize_text(text)
        forbidden_markers = [
            "tool_results",
            "tool settings",
            "tool_settings",
            "response_rules",
            "kb_context",
            "knowledge base",
            "knowledge context",
            "intent:",
            "profile:",
            "history:",
            "safety case",
            "quy tac noi bo",
            "quy tac sau",
            "hay chi tra loi",
            "hay chi su dung",
            "dua vao tool_results",
            "su dung cac con so trong tool_results",
            "xac dinh muc tieu chung",
        ]
        return any(marker in normalized for marker in forbidden_markers)

    def _contains_meal_planning_meta(self, text: str) -> bool:
        normalized = normalize_text(text)
        forbidden_markers = [
            "luu y quan trong khi tao phan hoi",
            "vi ban khong the biet",
            "day la huong dan chi tiet",
            "hay su dung cac con",
            "xac dinh muc tieu chung",
            "chia nho theo",
            "ke hoach chia nho de xuat",
            "xay dung ke hoach bua an hop ly",
            "de ban tham khao",
        ]
        if any(marker in normalized for marker in forbidden_markers):
            return True
        if text.count("...") >= 2:
            return True
        if len(text.splitlines()) > 10:
            return True
        return False

    def _contains_workout_planning_meta(self, text: str) -> bool:
        normalized = normalize_text(text)
        forbidden_markers = [
            "nhac den dieu chinh dac biet",
            "neu co tool_settings",
            "du lieu dung hon",
            "hay chi tra tra loi",
            "theo cac quy tac",
            "lich tap nay duoc tao tu",
            "giai thich chi tiet ve ke hoach tap cho tung ngay",
        ]
        if any(marker in normalized for marker in forbidden_markers):
            return True
        if text.count("...") >= 2:
            return True
        if len(text) > 1400:
            return True
        if len([line for line in text.splitlines() if line.strip()]) > 10:
            return True
        return False

    def _looks_like_meal_guidance(self, text: str) -> bool:
        normalized = normalize_text(text)
        meal_markers = [
            "bua sang",
            "bua trua",
            "bua phu",
            "bua toi",
        ]
        marker_hits = sum(1 for marker in meal_markers if marker in normalized)
        bullet_hits = sum(
            1 for line in text.splitlines()
            if line.strip().startswith("-") and "bua" in normalize_text(line)
        )
        if marker_hits >= 2 or bullet_hits >= 2:
            return True
        return False

    def _looks_like_workout_guidance(self, text: str, prompt: dict[str, object]) -> bool:
        normalized = normalize_text(text)
        tool_results = prompt.get("tool_results", {})
        workout_plan = tool_results.get("workout_plan", {}) if isinstance(tool_results, dict) else {}
        non_empty_lines = [line for line in text.splitlines() if line.strip()]

        if len(non_empty_lines) > 8 or len(text) > 900:
            return False

        markers = ["lich tap", "split", "buoi", "day 1", "upper", "lower", "dau goi"]
        marker_hits = sum(1 for marker in markers if marker in normalized)

        if isinstance(workout_plan, dict) and workout_plan:
            split = normalize_text(str(workout_plan.get("split", "")))
            day_count = len(workout_plan.get("days", [])) if isinstance(workout_plan.get("days", []), list) else 0
            if split and split in normalized:
                return True
            if day_count and f"{day_count} buoi" in normalized:
                return True

        return marker_hits >= 2

    def _contains_generation_noise(self, text: str) -> bool:
        normalized = normalize_text(text)
        if any(marker in normalized for marker in ["channel|", "turn|", "<channel|", "<turn|"]):
            return True

        noise_char_count = len(NON_LATIN_NOISE_PATTERN.findall(text))
        if noise_char_count >= 6:
            return True

        return False

    def _looks_invalid_general_response(self, text: str) -> bool:
        normalized = normalize_text(text)
        invalid_markers = [
            "turn|",
            "channel",
            "assistant",
            "final output",
            "final answer",
            "response:",
            "tool_results",
            "tool_settings",
            "safety case",
            "quy tac",
            "hay chi",
            "khong vi thieu tool",
            "tra loi theo",
            "du lieu",
            "nhiem vu tra loi",
            "yeu cau hien tai cua user",
            "profile:",
            "personalization:",
            "knowledge context",
        ]
        if any(marker in normalized for marker in invalid_markers):
            return True
        if self._contains_generation_noise(text):
            return True
        if len(text.strip()) < 20:
            return True
        return False

    def _looks_invalid_nutrition_fallback_response(self, text: str) -> bool:
        normalized = normalize_text(text)
        invalid_markers = [
            "tool_results",
            "response_rules",
            "intent:",
            "profile:",
            "history:",
            "knowledge context",
            "safety case",
            "channel|",
            "turn|",
        ]
        if any(marker in normalized for marker in invalid_markers):
            return True
        if self._contains_generation_noise(text):
            return True
        return len(text.strip()) < 24

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
