from __future__ import annotations

import inspect
import json
import os
import random
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal, get_args, get_origin
import google.genai.types as types


@dataclass(frozen=True)
class CallRecord:
    index: int
    timestamp: str
    caller: str
    model: str
    response_model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    duration_ms: int

class APIClient:
    def __init__(self) -> None:
        self._client = None
        self._records: list[CallRecord] = []
        self._lock = threading.Lock()
        self._index = 0
        self._log_path: str | None = None
        self._mock_output = False

    def init(self, client, model: str) -> None:
        self._client = client
        self._default_model = model
        self._log_path = _make_log_path()
        
    def _mock_response(self, response_model):
        long_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\n Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, \n \n sunt in culpa qui officia deserunt mollit anim id est laborum."
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
            else:
                values[name] = f"{long_text}  [{name}]"
        return response_model(**values)

    def _make_call(self, messages, api_model, response_model):
        system_content = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_content = next((m["content"] for m in messages if m["role"] == "user"), None)
        max_429_retries = 5
        backoff = 2
        for attempt in range(max_429_retries):
            try: 
                response = self._client.models.generate_content(
                    model=api_model,
                    contents=user_content,  # just the user message string
                    config=types.GenerateContentConfig(
                        system_instruction=system_content,
                        response_mime_type="application/json",
                        response_schema=response_model,
                        thinking_config=types.ThinkingConfig(#thinking_budget=512, 
                                                            include_thoughts=False,),
                        temperature=1.5,
                        #top_p=0.99,
                        #top_k=64
                    ),
                )
                break
            except Exception as e:
                if attempt < max_429_retries - 1 and _is_rate_limit(e):
                    wait = backoff * (2 ** attempt)
                    print(f"[api_client] 429 rate limit — waiting {wait}s before retry {attempt + 1}/{max_429_retries - 1}")
                    time.sleep(wait)
                else:
                    raise
        result = response_model(**json.loads(response.text))
        return response, result
    
    def create(self, response_model, messages: list, model: str | None = None):
        if self._client is None:
            raise RuntimeError("APIClient not initialized — call init() first")

        if self._mock_output:
            return self._mock_response(response_model)
        api_model = model or self._default_model
        caller = _caller()
        start = time.monotonic()
        response, result = self._make_call(messages, api_model, response_model)
        prompt, completion, total = _extract_usage(response)
        with self._lock:
            record = CallRecord(
                index=self._index,
                timestamp=datetime.now(timezone.utc).isoformat(),
                caller=caller,
                model=api_model,
                response_model=getattr(response_model, "__name__", str(response_model)),
                prompt_tokens=prompt,
                completion_tokens=completion,
                total_tokens=total,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
            self._index += 1
            self._records.append(record)

        _write(self._log_path, record)
        return result

    def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/webm", model: str | None = None, hints: list[str] | None = None) -> str:
        hint_text = ""
        if hints:
            hint_text = f"\nThe following names and terms may appear: {', '.join(hints)}."
            
        api_model = model or self._default_model
        response = self._client.models.generate_content(
            model=api_model,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                f"Transcribe this audio exactly. Return only the spoken words, nothing else. {hint_text}",
            ],
        )
        return response.text.strip()
        
    def summary(self) -> dict:
        with self._lock:
            records = list(self._records)
        by_caller: dict[str, dict] = {}
        for r in records:
            s = by_caller.setdefault(r.caller, {"calls": 0, "tokens": 0, "ms": 0})
            s["calls"] += 1
            s["tokens"] += r.total_tokens or 0
            s["ms"] += r.duration_ms
        return {
            "total_calls": len(records),
            "total_tokens": sum(r.total_tokens or 0 for r in records),
            "by_caller": by_caller,
        }

    def print_summary(self) -> None:
        s = self.summary()
        w = 60
        print(f"\n{'─' * w}")
        print(f"  API — {s['total_calls']} calls · {s['total_tokens']:,} tokens")
        print(f"{'─' * w}")
        for caller, stats in s["by_caller"].items():
            print(f"  {caller:<40}  {stats['calls']:3d} calls  {stats['tokens']:>7,} tok  {stats['ms']:>5}ms")
        print(f"{'─' * w}\n")
        if self._log_path:
            summary_path = self._log_path.replace(".jsonl", "_summary.json")
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(s, f, indent=2)

# ── module-level singleton ───────────────────────────────────────────────────
api_client = APIClient()


# ── helpers ──────────────────────────────────────────────────────────────────

_SKIP = {"core.api_client", "agents.base_agent"}


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg


def _caller() -> str:
    for frame in inspect.stack():
        module = frame.frame.f_globals.get("__name__", "")
        if any(module.startswith(s) for s in _SKIP):
            continue
        cls = frame.frame.f_locals.get("self")
        cls_name = type(cls).__name__ if cls else ""
        return f"{cls_name}.{frame.function}" if cls_name else frame.function
    return "unknown"


def _extract_usage(response) -> tuple[int | None, int | None, int | None]:
    usage = getattr(response, "usage_metadata", None) or getattr(response, "usage", None)
    if usage is None:
        return None, None, None
    prompt = getattr(usage, "prompt_token_count", None) or getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "candidates_token_count", None) or getattr(usage, "completion_tokens", None)
    total = getattr(usage, "total_token_count", None) or getattr(usage, "total_tokens", None)
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion
    return prompt, completion, total


def _write(path: str | None, record: CallRecord) -> None:
    if path is None:
        return
    line = json.dumps(asdict(record)) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def _make_log_path() -> str:
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "api_logs")
    os.makedirs(log_dir, exist_ok=True)
    _prune_logs(log_dir, keep=25)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return os.path.join(log_dir, f"api_calls_{ts}.jsonl")


def _prune_logs(log_dir: str, keep: int) -> None:
    logs = sorted(os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".jsonl"))
    for old in logs[:-keep]:
        os.remove(old)
