import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from core.shared_helpers import get_master_logger

NO_LOCATION = "api-key n/a"


@dataclass
class CallTiming:
    attempts: int = 0
    retries: int = 0
    call_ms: int = 0
    wait_ms: int = 0
    failures: list[dict] = field(default_factory=list)
    wasted_input_tokens: int = 0
    wasted_output_tokens: int = 0
    wasted_thinking_tokens: int = 0

    def record_failure(self, kind: str, ms: int) -> None:
        self.failures.append({"kind": kind, "ms": ms})

    def record_wasted(self, response) -> None:
        prompt, completion, thinking, _ = extract_usage(response)
        self.wasted_input_tokens += prompt or 0
        self.wasted_output_tokens += completion or 0
        self.wasted_thinking_tokens += thinking or 0


@dataclass(frozen=True)
class CallRecord:
    index: int
    timestamp: str
    caller: str
    model: str
    location: str
    response_model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    thinking_tokens: int | None
    total_tokens: int | None
    duration_ms: int
    call_ms: int
    wait_ms: int
    attempts: int
    retries: int
    failures: list[dict]
    wasted_input_tokens: int
    wasted_output_tokens: int
    wasted_thinking_tokens: int


class APIRecordManager:

    def __init__(self):
        self._records: list[CallRecord] = []
        self._log_path = _make_log_path()

        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._total_thinking_tokens: int = 0
        self._total_api_tokens: int = 0
        self._total_retries: int = 0
        self._total_wait_ms: int = 0
        self._total_wasted_tokens: int = 0
        self._call_index = 0

        self._lock = threading.Lock()

    def log_call(self, caller, api_model, response_model, response, start, timing=None, location=NO_LOCATION):
        prompt, completion, thinking, total = self._extract_usage(response)
        timing = timing or CallTiming(attempts=1)

        with self._lock:
            record = CallRecord(
                index=self._call_index,
                timestamp=datetime.now(timezone.utc).isoformat(),
                caller=caller,
                model=api_model,
                location=location,
                response_model=getattr(response_model, "__name__", str(response_model)),
                prompt_tokens=prompt,
                completion_tokens=completion,
                thinking_tokens=thinking,
                total_tokens=total,
                duration_ms=int((time.monotonic() - start) * 1000),
                call_ms=timing.call_ms,
                wait_ms=timing.wait_ms,
                attempts=timing.attempts,
                retries=timing.retries,
                failures=list(timing.failures),
                wasted_input_tokens=timing.wasted_input_tokens,
                wasted_output_tokens=timing.wasted_output_tokens,
                wasted_thinking_tokens=timing.wasted_thinking_tokens,
            )
            self._call_index += 1
            self._records.append(record)
            self._total_input_tokens += prompt or 0
            self._total_output_tokens += completion or 0
            self._total_thinking_tokens += thinking or 0
            self._total_api_tokens += total or 0
            self._total_retries += timing.retries
            self._total_wait_ms += timing.wait_ms
            self._total_wasted_tokens += (
                timing.wasted_input_tokens + timing.wasted_output_tokens + timing.wasted_thinking_tokens
            )

        _write(self._log_path, record)
        return record

    def usage_totals(self) -> dict:
        with self._lock:
            sum_total = self._total_input_tokens + self._total_output_tokens + self._total_thinking_tokens
            return {
                "input": self._total_input_tokens,
                "output": self._total_output_tokens,
                "thinking": self._total_thinking_tokens,
                "sum_total": sum_total,
                "api_total": self._total_api_tokens,
                "total": max(sum_total, self._total_api_tokens),
            }

    @staticmethod
    def _extract_usage(response) -> tuple[int | None, int | None, int | None, int | None]:
        return extract_usage(response)



#----------------------------------------#
    def summary(self) -> dict:
        with self._lock:
            records = list(self._records)
            total_input = self._total_input_tokens
            total_output = self._total_output_tokens
            total_thinking = self._total_thinking_tokens
            api_total = self._total_api_tokens
            total_retries = self._total_retries
            total_wait_ms = self._total_wait_ms
            total_wasted = self._total_wasted_tokens
        sum_total = total_input + total_output + total_thinking
        by_caller: dict[str, dict] = {}
        by_model: dict[str, dict] = {}
        for r in records:
            _accumulate(by_caller, r.caller, r)
            _accumulate(by_model, f"{r.model} @ {r.location}", r)
        return {
            "total_calls": len(records),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_thinking_tokens": total_thinking,
            "sum_total_tokens": sum_total,
            "api_total_tokens": api_total,
            "total_retries": total_retries,
            "total_wait_ms": total_wait_ms,
            "total_wasted_tokens": total_wasted,
            "by_caller": by_caller,
            "by_model": by_model,
        }

    def print_and_write_summary(self, game_id=None) -> None:
        s = self.summary()
        w = 80
        print(f"\n{'─' * w}")
        print(f"  API — {s['total_calls']} calls · "
              f"{s['total_input_tokens']:,} in · "
              f"{s['total_output_tokens']:,} out · "
              f"{s['total_thinking_tokens']:,} thinking · "
              f"sum {s['sum_total_tokens']:,} · api {s['api_total_tokens']:,}")
        print(f"  {s['total_retries']:,} retries · "
              f"{s['total_wait_ms'] / 1000:,.1f}s backoff wait · "
              f"{s['total_wasted_tokens']:,} tokens wasted on retries")
        print(f"{'─' * w}")
        for caller, stats in s["by_caller"].items():
            print(f"  {caller:<40}  {_format_stats(stats)}")
        print(f"{'─' * w}")
        for model, stats in s["by_model"].items():
            print(f"  {model:<40}  {_format_stats(stats)}")
        print(f"{'─' * w}\n")

        if game_id is None:
            game_id = os.path.splitext(os.path.basename(self._log_path))[0] if self._log_path else None
        entry = {
            "game_id": game_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **s,
        }
        get_master_logger("api_summary", "api_summary_log").info(json.dumps(entry, ensure_ascii=False))


#------------------------------


def _first_present(usage, *names: str) -> int | None:
    for name in names:
        value = getattr(usage, name, None)
        if value is not None:
            return value
    return None


def extract_usage(response) -> tuple[int | None, int | None, int | None, int | None]:
    usage = getattr(response, "usage_metadata", None) or getattr(response, "usage", None)
    if usage is None:
        return None, None, None, None

    prompt = _first_present(usage, "prompt_token_count", "prompt_tokens")
    completion = _first_present(usage, "candidates_token_count", "completion_tokens")
    thinking = _first_present(usage, "thoughts_token_count", "thinking_tokens")
    api_total = _first_present(usage, "total_token_count", "total_tokens")
    return prompt, completion, thinking, api_total


def _accumulate(bucket: dict[str, dict], key: str, r: CallRecord) -> None:
    s = bucket.setdefault(key, {
        "calls": 0, "input": 0, "output": 0, "thinking": 0, "ms": 0,
        "call_ms": 0, "wait_ms": 0, "retries": 0, "wasted": 0, "failures": {},
    })
    s["calls"] += 1
    s["input"] += r.prompt_tokens or 0
    s["output"] += r.completion_tokens or 0
    s["thinking"] += r.thinking_tokens or 0
    s["ms"] += r.duration_ms
    s["call_ms"] += r.call_ms
    s["wait_ms"] += r.wait_ms
    s["retries"] += r.retries
    s["wasted"] += r.wasted_input_tokens + r.wasted_output_tokens + r.wasted_thinking_tokens
    for failure in r.failures:
        s["failures"][failure["kind"]] = s["failures"].get(failure["kind"], 0) + 1


def _format_stats(stats: dict) -> str:
    line = (f"{stats['calls']:3d} calls  "
            f"{stats['input']:>7,} in  {stats['output']:>7,} out  "
            f"{stats['thinking']:>7,} think  "
            f"{stats['ms']:>7}ms  "
            f"{stats['retries']:>3} retries")
    if stats["wait_ms"]:
        line += f"  {stats['wait_ms'] / 1000:,.1f}s wait"
    if stats["wasted"]:
        line += f"  {stats['wasted']:,} wasted"
    if stats["failures"]:
        line += "  " + " ".join(f"{kind}x{count}" for kind, count in sorted(stats["failures"].items()))
    return line


def _write(path: str | None, record: CallRecord) -> None:
    if path is None:
        return
    line = json.dumps(asdict(record)) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def _make_log_path() -> str:
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs", "api_logs")
    os.makedirs(log_dir, exist_ok=True)
    _prune_logs(log_dir, keep=50)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return os.path.join(log_dir, f"api_calls_{ts}_{suffix}.jsonl")


def _prune_logs(log_dir: str, keep: int) -> None:
    logs = sorted(os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".jsonl"))
    for old in logs[:-keep]:
        os.remove(old)
