from __future__ import annotations

import inspect
import json
import os
import random
import time
from typing import TYPE_CHECKING, Literal, get_args, get_origin
from pydantic import BaseModel
import google.genai.types as types

MAX_TOKENS_PER_GAME_CAP = int(os.environ.get("MAX_TOKENS_PER_GAME", 1500000))

from core.sinks.game_sink import NoopGameSink
from core.api_client.api_record_manager import APIRecordManager, CallTiming, NO_LOCATION
from core.api_client.model_registry import MODEL_2

if TYPE_CHECKING:
    from core.sinks.game_sink import GameEventSink

class BudgetExceeded(Exception):
    pass

class APIClient:
    def __init__(self, client, model: str, higher_model_name: str, sink: GameEventSink = None,
                 token_budget: int = None, european_client=None) -> None:
        if token_budget is None:
            raise ValueError("token_budget is required")
        self._mock_output = False
        self._min_mock_time = 1
        self._max_mock_time = 1
        self._client = client
        self.default_model = model
        self.higher_model = higher_model_name
        if not sink:
            self.sink = NoopGameSink()
        else:
            self.sink = sink
        self._record_manager = APIRecordManager()
        self.token_budget = min(token_budget, MAX_TOKENS_PER_GAME_CAP)
        self.game_id = None
        
        self.european_client = european_client
        
    def _mock_response(self, response_model):
        long_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\n Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, \n \n sunt in culpa qui officia deserunt mollit anim id est laborum."
        short_text = "Lorem ipsum dolor sit amet"
        values = {}
        for name, field_info in response_model.model_fields.items():
            annotation = field_info.annotation
            if get_origin(annotation) is Literal:
                values[name] = random.choice(get_args(annotation))
            elif get_origin(annotation) is list:
                inner = get_args(annotation)[0] if get_args(annotation) else str
                if get_origin(inner) is Literal:
                    values[name] = [random.choice(get_args(inner))]
                else:
                    values[name] = [f"test [{name}]"]
            elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
                values[name] = self._mock_response(annotation)
            elif annotation is bool:
                values[name] = random.choice([True, False])
            elif annotation is int:
                values[name] = 2
            elif annotation is float:
                values[name] = 0.0
            else:
                values[name] = f"{short_text}  [{name}]"
        return response_model(**values)

    def _make_call(self, messages, api_model, response_model, thinking=False):
        
        if thinking:
            thinking_config = types.ThinkingConfig(thinking_budget=512, include_thoughts=True)
        else:
            thinking_config = types.ThinkingConfig(thinking_budget=0, include_thoughts=False)
        system_content = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_content = next((m["content"] for m in messages if m["role"] == "user"), None)
        max_429_retries = 16
        backoff = 2
        
        if api_model == MODEL_2 and self.european_client is not None:
            client = self.european_client
        else:
            client = self._client

        location = getattr(getattr(client, "_api_client", None), "location", None) or NO_LOCATION
        timing = CallTiming()

        for attempt in range(max_429_retries):
            timing.attempts += 1
            attempt_start = time.monotonic()
            try:
                response = client.models.generate_content(
                    model=api_model,
                    contents=user_content,  # just the user message string
                    config=types.GenerateContentConfig(
                        system_instruction=system_content,
                        response_mime_type="application/json",
                        response_schema=response_model,
                        thinking_config=thinking_config,
                        temperature=1.4,
                        #top_p=0.99,
                        #top_k=64
                    ),
                )
                result = response_model(**json.loads(response.text))
                timing.call_ms = _elapsed_ms(attempt_start)
                break
            except json.JSONDecodeError:
                timing.record_failure("malformed_json", _elapsed_ms(attempt_start))
                timing.record_wasted(response)
                if attempt < max_429_retries - 1:
                    timing.retries += 1
                    print(f"malformed JSON response — retrying ({attempt + 1}/{max_429_retries - 1})")
                    continue
                raise
            except Exception as e:
                is_rate_limit = _is_rate_limit(e)
                kind = "rate_limit" if is_rate_limit else "server_error" if _is_transient_server_error(e) else "other"
                timing.record_failure(kind, _elapsed_ms(attempt_start))
                if attempt < max_429_retries - 1 and kind != "other":
                    timing.retries += 1
                    wait = backoff * (2 ** attempt)
                    reason = f"{location} - {api_model} - 429 rate limit" if is_rate_limit else "5xx server error"
                    error_message = (f"server {reason} — waiting {wait}s before retry {attempt + 1}/{max_429_retries - 1}")
                    print(error_message)
                    if attempt > 1:
                        self.sink.system_private(error_message)
                    time.sleep(wait)
                    timing.wait_ms += wait * 1000
                else:
                    raise

        return response, result, timing, location
    
    def create(self, response_model, messages: list, thinking=False, agent_api_model=None, use_higher_model = False, span=None):
        if self._mock_output:
            time.sleep(random.uniform(self._min_mock_time, self._max_mock_time))
            return self._mock_response(response_model)
        if self._record_manager._total_api_tokens > self.token_budget:
            raise BudgetExceeded(f"Token budget of {self.token_budget} exceeded")

        if use_higher_model:
            api_model = self.higher_model
        elif agent_api_model:
            api_model = agent_api_model
        
        else:
            api_model = self.default_model


        caller = _caller()
        start = time.monotonic()
        response, result, timing, location = self._make_call(messages, api_model, response_model, thinking=thinking)
        record = self._record_manager.log_call(
            caller=caller,
            api_model=api_model,
            response_model=response_model,
            response=response,
            start=start,
            timing=timing,
            location=location,
        )
        if span is not None:
            _tag_span(span, record, thinking=thinking, game_id=self.game_id)
        return result

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm", model: str | None = None, hints: list[str] | None = None) -> str:
        hint_text = ""
        if hints:
            hint_text = f"\nThe following names and terms may appear: {', '.join(hints)}."
            
        api_model = model or self.default_model
        response = self._client.models.generate_content(
            model=api_model,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                f"Transcribe this audio exactly. Return only the spoken words, nothing else. {hint_text}",
            ],
        )
        return response.text.strip()

    def summary(self) -> dict:
        return self._record_manager.summary()

    def print_and_write_summary(self) -> None:
        self._record_manager.print_and_write_summary(self.game_id)

    def usage_totals(self) -> dict:
        return self._record_manager.usage_totals()


# ── helpers ──────────────────────────────────────────────────────────────────

_SKIP = {"core.api_client", "agents.base_agent"}


def _tag_span(span, record, thinking: bool, game_id=None) -> None:
    if game_id is not None:
        span.set_attribute("game.id", game_id)
    span.set_attribute("llm.model", record.model)
    span.set_attribute("llm.caller", record.caller)
    span.set_attribute("llm.thinking", thinking)
    span.set_attribute("llm.location", record.location)
    span.set_attribute("llm.duration_ms", record.duration_ms)
    span.set_attribute("llm.call_ms", record.call_ms)
    span.set_attribute("llm.wait_ms", record.wait_ms)
    span.set_attribute("llm.retries", record.retries)
    for name, value in (
        ("llm.tokens.prompt", record.prompt_tokens),
        ("llm.tokens.completion", record.completion_tokens),
        ("llm.tokens.thinking", record.thinking_tokens),
        ("llm.tokens.total", record.total_tokens),
    ):
        if value is not None:
            span.set_attribute(name, value)


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg


def _is_transient_server_error(exc: Exception) -> bool:
    msg = str(exc)
    return any(code in msg for code in ("500", "502", "503", "504"))


def _caller() -> str:
    for frame in inspect.stack():
        module = frame.frame.f_globals.get("__name__", "")
        if any(module.startswith(s) for s in _SKIP):
            continue
        cls = frame.frame.f_locals.get("self")
        cls_name = type(cls).__name__ if cls else ""
        return f"{cls_name}.{frame.function}" if cls_name else frame.function
    return "unknown"



