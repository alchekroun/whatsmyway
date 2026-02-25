from __future__ import annotations

from datetime import datetime, timezone

from app.services.recommendation_service import _build_candidate_windows
from app.services.time_service import to_naive_utc
from app.services.travel_service import estimate_travel_minutes


class StubEvent:
    def __init__(self, start_at: datetime, end_at: datetime):
        self.start_at = start_at
        self.end_at = end_at


def test_to_naive_utc_keeps_naive_and_converts_aware():
    naive = datetime(2026, 3, 10, 12, 0)
    aware = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)

    assert to_naive_utc(naive) == naive
    assert to_naive_utc(aware).tzinfo is None
    assert to_naive_utc(aware) == datetime(2026, 3, 10, 12, 0)


def test_estimate_travel_minutes_has_floor_and_distance_growth():
    short_trip = estimate_travel_minutes({"lat": 48.8566, "lng": 2.3522}, {"lat": 48.8567, "lng": 2.3523})
    longer_trip = estimate_travel_minutes({"lat": 48.8566, "lng": 2.3522}, {"lat": 48.8919, "lng": 2.2384})

    assert short_trip >= 2.0
    assert longer_trip > short_trip


def test_build_candidate_windows_respects_workday_hours():
    events = [
        StubEvent(datetime(2026, 3, 10, 7, 0), datetime(2026, 3, 10, 8, 30)),
        StubEvent(datetime(2026, 3, 10, 10, 0), datetime(2026, 3, 10, 11, 0)),
        StubEvent(datetime(2026, 3, 10, 18, 30), datetime(2026, 3, 10, 20, 0)),
    ]

    windows = _build_candidate_windows(datetime(2026, 3, 10, 6, 0), datetime(2026, 3, 10, 22, 0), events)

    assert windows == [
        {"start": datetime(2026, 3, 10, 8, 30), "end": datetime(2026, 3, 10, 10, 0)},
        {"start": datetime(2026, 3, 10, 11, 0), "end": datetime(2026, 3, 10, 18, 30)},
    ]
