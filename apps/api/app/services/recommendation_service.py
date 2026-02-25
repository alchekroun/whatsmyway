from datetime import timedelta

from app.services.travel_service import estimate_travel_minutes
from app.services.time_service import to_naive_utc


# Office hours used for fallback candidate window generation.
DAY_START_HOUR = 8
DAY_END_HOUR = 19


def _overlap(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def _build_candidate_windows(date_start, date_end, events):
    windows = []
    cursor = to_naive_utc(date_start)

    sorted_events = sorted(events, key=lambda e: e.start_at)

    for event in sorted_events:
        event_start = to_naive_utc(event.start_at)
        event_end = to_naive_utc(event.end_at)
        if cursor < event_start:
            windows.append((cursor, event_start))
        if cursor < event_end:
            cursor = event_end

    normalized_end = to_naive_utc(date_end)
    if cursor < normalized_end:
        windows.append((cursor, normalized_end))

    trimmed = []
    for start, end in windows:
        day_start = start.replace(hour=DAY_START_HOUR, minute=0, second=0, microsecond=0)
        day_end = start.replace(hour=DAY_END_HOUR, minute=0, second=0, microsecond=0)
        bounded_start = max(start, day_start)
        bounded_end = min(end, day_end)
        if bounded_start < bounded_end:
            trimmed.append((bounded_start, bounded_end))

    return trimmed


def _neighbors_for_slot(events, slot_start, slot_end):
    previous_event = None
    next_event = None

    for event in events:
        event_start = to_naive_utc(event.start_at)
        event_end = to_naive_utc(event.end_at)
        if event_end <= slot_start:
            previous_event = event
        if next_event is None and event_start >= slot_end:
            next_event = event

    return previous_event, next_event


def recommend_slots(date_start, date_end, events, new_event, duration_minutes, buffer_minutes):
    duration = timedelta(minutes=duration_minutes)
    buffer = timedelta(minutes=buffer_minutes)
    suggestions = []
    windows = _build_candidate_windows(date_start, date_end, events)

    for window_start, window_end in windows:
        candidate_start = window_start + buffer
        candidate_end = candidate_start + duration
        if candidate_end + buffer > window_end:
            continue

        previous_event, next_event = _neighbors_for_slot(events, candidate_start, candidate_end)

        prev_to_new = 0.0
        new_to_next = 0.0
        prev_to_next = 0.0

        if previous_event:
            prev_to_new = estimate_travel_minutes(
                {"lat": previous_event.lat, "lng": previous_event.lng},
                {"lat": new_event["lat"], "lng": new_event["lng"]},
            )

        if next_event:
            new_to_next = estimate_travel_minutes(
                {"lat": new_event["lat"], "lng": new_event["lng"]},
                {"lat": next_event.lat, "lng": next_event.lng},
            )

        if previous_event and next_event:
            prev_to_next = estimate_travel_minutes(
                {"lat": previous_event.lat, "lng": previous_event.lng},
                {"lat": next_event.lat, "lng": next_event.lng},
            )

        added_travel = round(max(prev_to_new + new_to_next - prev_to_next, 0), 1)
        total_travel = round(prev_to_new + new_to_next, 1)

        explanation = (
            f"Inserted between {previous_event.id if previous_event else 'START'} "
            f"and {next_event.id if next_event else 'END'} with +{added_travel} min travel"
        )

        suggestions.append(
            {
                "start_at": candidate_start.isoformat(),
                "end_at": candidate_end.isoformat(),
                "before_event_id": previous_event.id if previous_event else None,
                "after_event_id": next_event.id if next_event else None,
                "added_travel_min": added_travel,
                "total_travel_min": total_travel,
                "explanation": explanation,
            }
        )

    return sorted(
        suggestions,
        key=lambda x: (x["added_travel_min"], x["start_at"]),
    )[:10]
