from __future__ import annotations

from dataclasses import dataclass, field

from core.tui.events import NormalizedEvent


VisibilityMode = str
PUBLIC_ONLY: VisibilityMode = "public"
WITH_THOUGHTS: VisibilityMode = "thoughts"
WITH_INNER: VisibilityMode = "inner"


@dataclass(slots=True)
class PlayerSnapshot:
    active_scores: dict[str, int] = field(default_factory=dict)
    eliminated: list[str] = field(default_factory=list)


def event_visible(event: NormalizedEvent, mode: VisibilityMode) -> bool:
    if event.type == "on_private_thought":
        return mode in (WITH_THOUGHTS, WITH_INNER)
    if event.type == "on_inner_workings":
        return mode == WITH_INNER
    return True


def compute_player_snapshot(events: list[NormalizedEvent], up_to_phase: int) -> PlayerSnapshot:
    active_scores: dict[str, int] = {}
    eliminated: list[str] = []
    previous_names: set[str] | None = None

    for event in events:
        if event.phase > up_to_phase:
            continue

        if event.scores:
            current_names = set(event.scores.keys())
            if previous_names is not None and previous_names:
                dropped = sorted(previous_names - current_names)
                for name in dropped:
                    if name not in eliminated:
                        eliminated.append(name)
            previous_names = current_names
            active_scores = dict(event.scores)

        payload_eliminated = event.payload.get("eliminated")
        if isinstance(payload_eliminated, str):
            if payload_eliminated not in eliminated:
                eliminated.append(payload_eliminated)
            active_scores.pop(payload_eliminated, None)

        if isinstance(payload_eliminated, list):
            for name in payload_eliminated:
                if isinstance(name, str):
                    if name not in eliminated:
                        eliminated.append(name)
                    active_scores.pop(name, None)

    return PlayerSnapshot(active_scores=active_scores, eliminated=eliminated)
