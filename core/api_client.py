from __future__ import annotations

import inspect
import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


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

    def init(self, client, model: str) -> None:
        self._client = client
        self._default_model = model
        self._log_path = _make_log_path()

    def create(self, response_model, messages: list, model: str | None = None, **kwargs):
        if self._client is None:
            raise RuntimeError("APIClient not initialized — call init() first")

        api_model = model or self._default_model
        caller = _caller()
        start = time.monotonic()

        max_429_retries = 5
        backoff = 2
        for attempt in range(max_429_retries):
            try:
                response, raw = self._client.create_with_completion(
                    model=api_model,
                    response_model=response_model,
                    messages=messages,
                    **kwargs,
                )
                break
            except Exception as e:
                if attempt < max_429_retries - 1 and _is_rate_limit(e):
                    wait = backoff * (2 ** attempt)
                    print(f"[api_client] 429 rate limit — waiting {wait}s before retry {attempt + 1}/{max_429_retries - 1}")
                    time.sleep(wait)
                else:
                    raise

        prompt, completion, total = _extract_usage(raw)
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
        return response

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
