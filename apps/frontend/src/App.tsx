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

export default function App() {
  const [salesRepId, setSalesRepId] = useState("rep-001");
  const [rangeStart, setRangeStart] = useState(nowLocalDateTime());
  const [rangeEnd, setRangeEnd] = useState(minutesFromNow(60 * 24 * 5));
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

  async function loadEvents() {
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

  async function submitEvent() {
    setError(null);
    try {
      const payload = { ...eventForm, sales_rep_id: salesRepId };
      await createEvent(payload);
      await loadEvents();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function submitRecommendation() {
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
      <h1>WhatsMyWay - Sales Calendar Optimizer</h1>
      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="inline">
          <label>
            Sales rep id
            <input value={salesRepId} onChange={(e) => setSalesRepId(e.target.value)} />
          </label>
          <label>
            Date range start
            <input type="datetime-local" value={rangeStart} onChange={(e) => setRangeStart(e.target.value)} />
          </label>
          <label>
            Date range end
            <input type="datetime-local" value={rangeEnd} onChange={(e) => setRangeEnd(e.target.value)} />
          </label>
        </div>
        <button onClick={loadEvents}>Load Events</button>
      </div>

      <section className="grid">
        <div className="panel">
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
        </div>

        <div className="panel">
          <h2>Best Slot Recommendation</h2>
          <label>
            New event address
            <input
              value={recommendForm.new_event_address}
              onChange={(e) =>
                setRecommendForm({ ...recommendForm, new_event_address: e.target.value })
              }
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
                onChange={(e) =>
                  setRecommendForm({ ...recommendForm, new_event_lat: Number(e.target.value) })
                }
              />
            </label>
            <label>
              Longitude
              <input
                type="number"
                value={recommendForm.new_event_lng}
                onChange={(e) =>
                  setRecommendForm({ ...recommendForm, new_event_lng: Number(e.target.value) })
                }
              />
            </label>
          </div>
          <button onClick={submitRecommendation}>Get recommendations</button>
          <ul>
            {suggestions.map((slot) => (
              <li key={`${slot.start_at}-${slot.end_at}`}>
                <strong>
                  {new Date(slot.start_at).toLocaleString()} - {new Date(slot.end_at).toLocaleString()}
                </strong>
                <div>Added travel: {slot.added_travel_min} min</div>
                <div>{slot.explanation}</div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="panel" style={{ marginTop: 18 }}>
        <h2>Events in range</h2>
        <ul>
          {sortedEvents.map((event) => (
            <li key={event.id}>
              <strong>{event.title || "Untitled"}</strong> ({event.address})<br />
              {new Date(event.start_at).toLocaleString()} - {new Date(event.end_at).toLocaleString()}
            </li>
          ))}
        </ul>
      </section>

      {error ? <div className="error">{error}</div> : null}
    </main>
  );
}
