from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence, TypedDict

from app.models.event import SalesEvent
from app.services.time_service import to_naive_utc
from app.services.travel_service import Location, estimate_travel_minutes

DAY_START_HOUR: int = 8
DAY_END_HOUR: int = 19
MAX_SUGGESTIONS: int = 10


class RecommendationResult(TypedDict):
    start_at: str
    end_at: str
    before_event_id: str | None
    after_event_id: str | None
    added_travel_min: float
    total_travel_min: float
    explanation: str


class CandidateWindow(TypedDict):
    start: datetime
    end: datetime


class NewEventLocation(TypedDict):
    address: str
    lat: float
    lng: float


def _build_candidate_windows(
    date_start: datetime, date_end: datetime, events: Sequence[SalesEvent]
) -> list[CandidateWindow]:
    windows: list[CandidateWindow] = []
    cursor: datetime = to_naive_utc(date_start)
    normalized_end: datetime = to_naive_utc(date_end)

    sorted_events: list[SalesEvent] = sorted(events, key=lambda event: event.start_at)

    for event in sorted_events:
        event_start: datetime = to_naive_utc(event.start_at)
        event_end: datetime = to_naive_utc(event.end_at)
        if cursor < event_start:
            windows.append({"start": cursor, "end": event_start})
        if cursor < event_end:
            cursor = event_end

    if cursor < normalized_end:
        windows.append({"start": cursor, "end": normalized_end})

    trimmed: list[CandidateWindow] = []
    for window in windows:
        start: datetime = window["start"]
        end: datetime = window["end"]
        day_start: datetime = start.replace(hour=DAY_START_HOUR, minute=0, second=0, microsecond=0)
        day_end: datetime = start.replace(hour=DAY_END_HOUR, minute=0, second=0, microsecond=0)
        bounded_start: datetime = max(start, day_start)
        bounded_end: datetime = min(end, day_end)
        if bounded_start < bounded_end:
            trimmed.append({"start": bounded_start, "end": bounded_end})

    return trimmed


def _neighbors_for_slot(
    events: Sequence[SalesEvent], slot_start: datetime, slot_end: datetime
) -> tuple[SalesEvent | None, SalesEvent | None]:
    previous_event: SalesEvent | None = None
    next_event: SalesEvent | None = None

    for event in events:
        event_start: datetime = to_naive_utc(event.start_at)
        event_end: datetime = to_naive_utc(event.end_at)
        if event_end <= slot_start:
            previous_event = event
        if next_event is None and event_start >= slot_end:
            next_event = event

    return previous_event, next_event


def recommend_slots(
    date_start: datetime,
    date_end: datetime,
    events: Sequence[SalesEvent],
    new_event: NewEventLocation,
    duration_minutes: int,
    buffer_minutes: int,
) -> list[RecommendationResult]:
    duration: timedelta = timedelta(minutes=duration_minutes)
    buffer: timedelta = timedelta(minutes=buffer_minutes)
    suggestions: list[RecommendationResult] = []
    windows: list[CandidateWindow] = _build_candidate_windows(date_start, date_end, events)

    for window in windows:
        window_start: datetime = window["start"]
        window_end: datetime = window["end"]
        candidate_start: datetime = window_start + buffer
        candidate_end: datetime = candidate_start + duration

        if candidate_end + buffer > window_end:
            continue

        previous_event, next_event = _neighbors_for_slot(events, candidate_start, candidate_end)

        prev_to_new: float = 0.0
        new_to_next: float = 0.0
        prev_to_next: float = 0.0
        new_location: Location = {"lat": new_event["lat"], "lng": new_event["lng"]}

        if previous_event is not None:
            previous_location: Location = {"lat": previous_event.lat, "lng": previous_event.lng}
            prev_to_new = estimate_travel_minutes(previous_location, new_location)

        if next_event is not None:
            next_location: Location = {"lat": next_event.lat, "lng": next_event.lng}
            new_to_next = estimate_travel_minutes(new_location, next_location)

        if previous_event is not None and next_event is not None:
            previous_location = {"lat": previous_event.lat, "lng": previous_event.lng}
            next_location = {"lat": next_event.lat, "lng": next_event.lng}
            prev_to_next = estimate_travel_minutes(previous_location, next_location)

        added_travel: float = round(max(prev_to_new + new_to_next - prev_to_next, 0.0), 1)
        total_travel: float = round(prev_to_new + new_to_next, 1)
        before_event_id: str | None = previous_event.id if previous_event is not None else None
        after_event_id: str | None = next_event.id if next_event is not None else None

        explanation: str = (
            f"Inserted between {before_event_id if before_event_id else 'START'} "
            f"and {after_event_id if after_event_id else 'END'} with +{added_travel} min travel"
        )

        suggestions.append(
            {
                "start_at": candidate_start.isoformat(),
                "end_at": candidate_end.isoformat(),
                "before_event_id": before_event_id,
                "after_event_id": after_event_id,
                "added_travel_min": added_travel,
                "total_travel_min": total_travel,
                "explanation": explanation,
            }
        )

    ranked: list[RecommendationResult] = sorted(
        suggestions,
        key=lambda item: (item["added_travel_min"], item["start_at"]),
    )
    return ranked[:MAX_SUGGESTIONS]
