import { useMemo, useState } from "react";
import type {
  EventInput,
  Recommendation,
  RecommendationRequest,
  SalesEvent
} from "@whatsmyway/shared-types";
import { createEvent, listEvents, recommend } from "./services/apiClient";

function nowLocalDateTime(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

function minutesFromNow(minutes: number): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() + minutes - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
}

function buildDayHeaders(rangeStart: string, rangeEnd: string): Date[] {
  const startDate = startOfDay(new Date(rangeStart));
  const endDate = startOfDay(new Date(rangeEnd));
  const result: Date[] = [];
  const cursor = new Date(startDate);

  while (cursor <= endDate && result.length < 14) {
    result.push(new Date(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }

  return result;
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function formatTimeWindow(startAt: string, endAt: string): string {
  const start = new Date(startAt);
  const end = new Date(endAt);
  return `${start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} - ${end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

export default function App() {
  const [salesRepId, setSalesRepId] = useState<string>("rep-001");
  const [rangeStart, setRangeStart] = useState<string>(nowLocalDateTime());
  const [rangeEnd, setRangeEnd] = useState<string>(minutesFromNow(60 * 24 * 5));
  const [events, setEvents] = useState<SalesEvent[]>([]);
  const [suggestions, setSuggestions] = useState<Recommendation[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [eventForm, setEventForm] = useState<EventInput>({
    title: "",
    address: "",
    start_at: nowLocalDateTime(),
    end_at: minutesFromNow(60),
    lat: 40.7128,
    lng: -74.006,
    sales_rep_id: salesRepId,
    time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone
  });

  const [recommendForm, setRecommendForm] = useState<RecommendationRequest>({
    date_start: rangeStart,
    date_end: rangeEnd,
    sales_rep_id: salesRepId,
    new_event_duration_min: 45,
    new_event_address: "",
    new_event_lat: 40.73061,
    new_event_lng: -73.935242,
    buffer_min: 10
  });

  const sortedEvents = useMemo(
    () => [...events].sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime()),
    [events]
  );

  const calendarDays = useMemo(() => buildDayHeaders(rangeStart, rangeEnd), [rangeStart, rangeEnd]);

  const eventsByDay = useMemo(() => {
    return calendarDays.map((day) => {
      const dayEvents = sortedEvents.filter((event) => isSameDay(new Date(event.start_at), day));
      return {
        day,
        events: dayEvents
      };
    });
  }, [calendarDays, sortedEvents]);

  async function loadEvents(): Promise<void> {
    setError(null);
    try {
      const data = await listEvents({
        salesRepId,
        start: rangeStart,
        end: rangeEnd
      });
      setEvents(data);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function submitEvent(): Promise<void> {
    setError(null);
    try {
      const payload = { ...eventForm, sales_rep_id: salesRepId };
      await createEvent(payload);
      await loadEvents();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function submitRecommendation(): Promise<void> {
    setError(null);
    try {
      const payload = {
        ...recommendForm,
        sales_rep_id: salesRepId,
        date_start: rangeStart,
        date_end: rangeEnd
      };
      const data = await recommend(payload);
      setSuggestions(data.suggestions);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <main className="app-shell">
      <h1>WhatsMyWay</h1>
      <p className="subtitle">Sales calendar planner with travel-optimized slot recommendations.</p>

      <section className="workspace">
        <aside className="panel side-panel">
          <h2>Create Event</h2>
          <label>
            Title
            <input
              value={eventForm.title}
              onChange={(e) => setEventForm({ ...eventForm, title: e.target.value })}
            />
          </label>
          <label>
            Address
            <input
              value={eventForm.address}
              onChange={(e) => setEventForm({ ...eventForm, address: e.target.value })}
            />
          </label>
          <div className="inline">
            <label>
              Start
              <input
                type="datetime-local"
                value={eventForm.start_at}
                onChange={(e) => setEventForm({ ...eventForm, start_at: e.target.value })}
              />
            </label>
            <label>
              End
              <input
                type="datetime-local"
                value={eventForm.end_at}
                onChange={(e) => setEventForm({ ...eventForm, end_at: e.target.value })}
              />
            </label>
            <label>
              Latitude
              <input
                type="number"
                value={eventForm.lat}
                onChange={(e) => setEventForm({ ...eventForm, lat: Number(e.target.value) })}
              />
            </label>
            <label>
              Longitude
              <input
                type="number"
                value={eventForm.lng}
                onChange={(e) => setEventForm({ ...eventForm, lng: Number(e.target.value) })}
              />
            </label>
          </div>
          <button onClick={submitEvent}>Save event</button>
        </aside>

        <section className="calendar-zone">
          <div className="panel controls-panel">
            <div className="controls-row">
              <label>
                Sales rep id
                <input value={salesRepId} onChange={(e) => setSalesRepId(e.target.value)} />
              </label>
              <label>
                Date range start
                <input
                  type="datetime-local"
                  value={rangeStart}
                  onChange={(e) => setRangeStart(e.target.value)}
                />
              </label>
              <label>
                Date range end
                <input
                  type="datetime-local"
                  value={rangeEnd}
                  onChange={(e) => setRangeEnd(e.target.value)}
                />
              </label>
              <button onClick={loadEvents}>Refresh</button>
            </div>
          </div>

          <div className="panel calendar-panel">
            <div className="calendar-header">Calendar</div>
            <div className="calendar-grid">
              {eventsByDay.map((entry) => (
                <article key={entry.day.toISOString()} className="day-column">
                  <header>
                    <span className="day-name">
                      {entry.day.toLocaleDateString([], { weekday: "short" })}
                    </span>
                    <strong>{entry.day.toLocaleDateString([], { month: "short", day: "numeric" })}</strong>
                  </header>
                  <div className="day-events">
                    {entry.events.length === 0 ? (
                      <p className="empty-day">No events</p>
                    ) : (
                      entry.events.map((event) => (
                        <div key={event.id} className="event-chip">
                          <strong>{event.title || "Untitled"}</strong>
                          <span>{formatTimeWindow(event.start_at, event.end_at)}</span>
                          <span>{event.address}</span>
                        </div>
                      ))
                    )}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <aside className="panel side-panel">
          <h2>Best Slot Recommendation</h2>
          <label>
            New event address
            <input
              value={recommendForm.new_event_address}
              onChange={(e) => setRecommendForm({ ...recommendForm, new_event_address: e.target.value })}
            />
          </label>
          <div className="inline">
            <label>
              Duration (min)
              <input
                type="number"
                value={recommendForm.new_event_duration_min}
                onChange={(e) =>
                  setRecommendForm({
                    ...recommendForm,
                    new_event_duration_min: Number(e.target.value)
                  })
                }
              />
            </label>
            <label>
              Buffer (min)
              <input
                type="number"
                value={recommendForm.buffer_min}
                onChange={(e) => setRecommendForm({ ...recommendForm, buffer_min: Number(e.target.value) })}
              />
            </label>
            <label>
              Latitude
              <input
                type="number"
                value={recommendForm.new_event_lat}
                onChange={(e) => setRecommendForm({ ...recommendForm, new_event_lat: Number(e.target.value) })}
              />
            </label>
            <label>
              Longitude
              <input
                type="number"
                value={recommendForm.new_event_lng}
                onChange={(e) => setRecommendForm({ ...recommendForm, new_event_lng: Number(e.target.value) })}
              />
            </label>
          </div>
          <button onClick={submitRecommendation}>Get recommendations</button>
          <ul>
            {suggestions.map((slot) => (
              <li key={`${slot.start_at}-${slot.end_at}`}>
                <strong>{formatTimeWindow(slot.start_at, slot.end_at)}</strong>
                <div>{new Date(slot.start_at).toLocaleDateString()}</div>
                <div>Added travel: {slot.added_travel_min} min</div>
                <div>{slot.explanation}</div>
              </li>
            ))}
          </ul>
        </aside>
      </section>

      {error ? <div className="error">{error}</div> : null}
    </main>
  );
}
