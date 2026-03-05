from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class NormalizedEvent:
    type: str
    phase: int
    round: int | None
    turn: int | None
    actor: str | None
    text: str | None
    summary: str | None
    scores: dict[str, int] | None
    payload: dict[str, Any]


class EventParseError(ValueError):
    pass


def load_raw_events(path: str | Path) -> list[dict[str, Any]]:
    event_path = Path(path)
    if not event_path.exists():
        raise EventParseError(f"Input file not found: {event_path}")

    suffix = event_path.suffix.lower()
    if suffix == ".jsonl":
        events: list[dict[str, Any]] = []
        with event_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise EventParseError(
                        f"Invalid JSON on line {line_no} in {event_path}: {exc.msg}"
                    ) from exc
                if not isinstance(obj, dict):
                    raise EventParseError(
                        f"Expected JSON object on line {line_no} in {event_path}."
                    )
                events.append(obj)
        if not events:
            raise EventParseError(f"No events found in JSONL file: {event_path}")
        return events

    if suffix == ".json":
        try:
            with event_path.open("r", encoding="utf-8") as handle:
                obj = json.load(handle)
        except json.JSONDecodeError as exc:
            raise EventParseError(f"Invalid JSON in {event_path}: {exc.msg}") from exc

        if not isinstance(obj, list):
            raise EventParseError(f"Expected a JSON array in {event_path}.")
        if not obj:
            raise EventParseError(f"No events found in JSON file: {event_path}")
        if not all(isinstance(item, dict) for item in obj):
            raise EventParseError(f"All items in {event_path} must be JSON objects.")
        return obj

    raise EventParseError(
        f"Unsupported file extension '{suffix or '(none)'}'. Use .jsonl or .json."
    )


def normalize_events(raw_events: list[dict[str, Any]]) -> list[NormalizedEvent]:
    normalized: list[NormalizedEvent] = []
    current_phase = 0

    for index, raw in enumerate(raw_events, start=1):
        event_type = _extract_event_type(raw)
        if not event_type:
            raise EventParseError(f"Event #{index} is missing a 'type' field.")

        phase_value = _extract_phase(raw, current_phase)
        if event_type == "on_phase_header" and phase_value > current_phase:
            current_phase = phase_value
        elif phase_value > current_phase:
            current_phase = phase_value

        normalized.append(
            NormalizedEvent(
                type=event_type,
                phase=phase_value,
                round=_to_int(raw.get("round") or raw.get("round_number")),
                turn=_to_int(raw.get("turn") or raw.get("turn_number")),
                actor=_as_str(raw.get("actor") or raw.get("speaker")),
                text=_as_str(raw.get("text") or raw.get("message") or raw.get("host_text")),
                summary=_as_str(raw.get("summary") or raw.get("summary_text")),
                scores=_extract_scores(raw),
                payload=raw,
            )
        )

    return normalized


def phase_numbers(events: list[NormalizedEvent]) -> list[int]:
    numbers = sorted({event.phase for event in events})
    return numbers or [0]


def events_for_phase(events: list[NormalizedEvent], phase: int) -> list[NormalizedEvent]:
    return [event for event in events if event.phase == phase]


def _extract_event_type(raw: dict[str, Any]) -> str:
    for key in ("type", "event_type", "event"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_phase(raw: dict[str, Any], current_phase: int) -> int:
    value = raw.get("phase")
    if value is None:
        value = raw.get("phase_number")
    parsed = _to_int(value)
    return parsed if parsed is not None else current_phase


def _extract_scores(raw: dict[str, Any]) -> dict[str, int] | None:
    value = raw.get("scores")
    if not isinstance(value, dict):
        return None

    scores: dict[str, int] = {}
    for key, score in value.items():
        if isinstance(key, str):
            int_score = _to_int(score)
            if int_score is not None:
                scores[key] = int_score
    return scores or None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)
