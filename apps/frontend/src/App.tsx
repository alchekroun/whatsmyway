import { useEffect, useMemo, useState } from "react";
import type {
  EventInput,
  Recommendation,
  RecommendationRequest,
  SalesEvent
} from "@whatsmyway/shared-types";
import {
  createEvent,
  deleteEvent,
  listEvents,
  recommend,
  suggestAddresses,
  validateAddress
} from "./services/apiClient";

type EventDraft = {
  title: string;
  address: string;
  start_at: string;
  duration_min: number;
  time_zone?: string;
};

function toLocalInputValue(date: Date): string {
  const adjusted = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return adjusted.toISOString().slice(0, 16);
}

function startOfTodayInput(): string {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return toLocalInputValue(now);
}

function daysFromNowInput(days: number): string {
  const now = new Date();
  now.setDate(now.getDate() + days);
  now.setHours(23, 59, 0, 0);
  return toLocalInputValue(now);
}

function nowLocalDateTime(): string {
  return toLocalInputValue(new Date());
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

function computeEndFromStart(startAt: string, durationMin: number): string {
  const start = new Date(startAt);
  start.setMinutes(start.getMinutes() + durationMin);
  return toLocalInputValue(start);
}

function isValidDateInput(value: string): boolean {
  return !Number.isNaN(new Date(value).getTime());
}

function recommendationKey(item: Recommendation): string {
  return `${item.start_at}__${item.end_at}__${item.new_event_address}`;
}

export default function App() {
  const [salesRepId, setSalesRepId] = useState<string>("rep-001");
  const [rangeStart, setRangeStart] = useState<string>(startOfTodayInput());
  const [rangeEnd, setRangeEnd] = useState<string>(daysFromNowInput(7));
  const [events, setEvents] = useState<SalesEvent[]>([]);
  const [suggestions, setSuggestions] = useState<Recommendation[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [eventForm, setEventForm] = useState<EventDraft>({
    title: "",
    address: "",
    start_at: nowLocalDateTime(),
    duration_min: 60,
    time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone
  });

  const [recommendForm, setRecommendForm] = useState<RecommendationRequest>({
    date_start: rangeStart,
    date_end: rangeEnd,
    sales_rep_id: salesRepId,
    new_event_duration_min: 45,
    new_event_address: "",
    buffer_min: 10
  });

  const [eventAddressSuggestions, setEventAddressSuggestions] = useState<string[]>([]);
  const [recommendAddressSuggestions, setRecommendAddressSuggestions] = useState<string[]>([]);
  const [eventAddressValidated, setEventAddressValidated] = useState<boolean>(false);
  const [recommendAddressValidated, setRecommendAddressValidated] = useState<boolean>(false);
  const [eventAddressMessage, setEventAddressMessage] = useState<string | null>(null);
  const [recommendAddressMessage, setRecommendAddressMessage] = useState<string | null>(null);

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

  const projectedEnd = useMemo(() => {
    if (!isValidDateInput(eventForm.start_at) || eventForm.duration_min <= 0) {
      return "";
    }
    return computeEndFromStart(eventForm.start_at, eventForm.duration_min);
  }, [eventForm.start_at, eventForm.duration_min]);

  async function validateEventAddressInput(address: string): Promise<boolean> {
    if (!address.trim()) {
      setEventAddressValidated(false);
      setEventAddressMessage("Address is required.");
      return false;
    }

    try {
      const response = await validateAddress(address);
      setEventForm((prev) => ({ ...prev, address: response.normalized_address }));
      setEventAddressValidated(true);
      setEventAddressMessage("Address validated.");
      setEventAddressSuggestions([]);
      return true;
    } catch (err) {
      setEventAddressValidated(false);
      setEventAddressMessage((err as Error).message);
      return false;
    }
  }

  async function validateRecommendAddressInput(address: string): Promise<boolean> {
    if (!address.trim()) {
      setRecommendAddressValidated(false);
      setRecommendAddressMessage("Address is required.");
      return false;
    }

    try {
      const response = await validateAddress(address);
      setRecommendForm((prev) => ({ ...prev, new_event_address: response.normalized_address }));
      setRecommendAddressValidated(true);
      setRecommendAddressMessage("Address validated.");
      setRecommendAddressSuggestions([]);
      return true;
    } catch (err) {
      setRecommendAddressValidated(false);
      setRecommendAddressMessage((err as Error).message);
      return false;
    }
  }

  function validateRangeInputs(): string | null {
    if (!isValidDateInput(rangeStart) || !isValidDateInput(rangeEnd)) {
      return "Date range values are invalid.";
    }

    if (new Date(rangeEnd) <= new Date(rangeStart)) {
      return "Date range end must be after date range start.";
    }

    return null;
  }

  function validateEventForm(): string | null {
    if (!eventForm.title.trim()) {
      return "Event title is required.";
    }
    if (!eventForm.address.trim()) {
      return "Event address is required.";
    }
    if (!eventAddressValidated) {
      return "Event address must be validated from provider.";
    }
    if (!isValidDateInput(eventForm.start_at)) {
      return "Event start datetime is invalid.";
    }
    if (!Number.isFinite(eventForm.duration_min) || eventForm.duration_min <= 0) {
      return "Event duration must be a positive number.";
    }

    return null;
  }

  function validateRecommendationForm(): string | null {
    if (!recommendForm.new_event_address.trim()) {
      return "Recommendation event address is required.";
    }
    if (!recommendAddressValidated) {
      return "Recommendation address must be validated from provider.";
    }
    if (!Number.isFinite(recommendForm.new_event_duration_min) || recommendForm.new_event_duration_min <= 0) {
      return "Recommendation duration must be positive.";
    }
    if (!Number.isFinite(recommendForm.buffer_min ?? 0) || (recommendForm.buffer_min ?? 0) < 0) {
      return "Buffer must be zero or a positive number.";
    }

    return null;
  }

  async function loadEvents(): Promise<void> {
    const rangeError = validateRangeInputs();
    if (rangeError) {
      setError(rangeError);
      return;
    }

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
    const rangeError = validateRangeInputs();
    if (rangeError) {
      setError(rangeError);
      return;
    }

    const formError = validateEventForm();
    if (formError) {
      setError(formError);
      return;
    }

    setError(null);
    try {
      const endAt = computeEndFromStart(eventForm.start_at, eventForm.duration_min);
      const payload: EventInput = {
        title: eventForm.title.trim(),
        address: eventForm.address.trim(),
        start_at: eventForm.start_at,
        end_at: endAt,
        sales_rep_id: salesRepId,
        time_zone: eventForm.time_zone
      };
      await createEvent(payload);
      await loadEvents();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleDeleteEvent(eventId: string): Promise<void> {
    setError(null);
    try {
      await deleteEvent(eventId);
      await loadEvents();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function dismissRecommendation(item: Recommendation): void {
    const key = recommendationKey(item);
    setSuggestions((prev) => prev.filter((candidate) => recommendationKey(candidate) !== key));
  }

  async function addRecommendationAsEvent(item: Recommendation): Promise<void> {
    const suggestedTitle = `Visit - ${item.new_event_address}`;
    const enteredTitle = window.prompt("Event name", suggestedTitle);
    if (!enteredTitle) {
      return;
    }

    const title = enteredTitle.trim();
    if (!title) {
      setError("Event name cannot be empty.");
      return;
    }

    setError(null);
    try {
      const payload: EventInput = {
        title,
        address: item.new_event_address,
        start_at: item.start_at,
        end_at: item.end_at,
        sales_rep_id: salesRepId,
        time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone
      };
      await createEvent(payload);
      dismissRecommendation(item);
      await loadEvents();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function submitRecommendation(): Promise<void> {
    const rangeError = validateRangeInputs();
    if (rangeError) {
      setError(rangeError);
      return;
    }

    const formError = validateRecommendationForm();
    if (formError) {
      setError(formError);
      return;
    }

    setError(null);
    try {
      const payload: RecommendationRequest = {
        ...recommendForm,
        new_event_address: recommendForm.new_event_address.trim(),
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

  useEffect(() => {
    if (eventForm.address.trim().length < 3) {
      setEventAddressSuggestions([]);
      return;
    }

    const timeout = setTimeout(async () => {
      try {
        const data = await suggestAddresses(eventForm.address.trim());
        setEventAddressSuggestions(data.suggestions);
      } catch {
        setEventAddressSuggestions([]);
      }
    }, 250);

    return () => clearTimeout(timeout);
  }, [eventForm.address]);

  useEffect(() => {
    if (recommendForm.new_event_address.trim().length < 3) {
      setRecommendAddressSuggestions([]);
      return;
    }

    const timeout = setTimeout(async () => {
      try {
        const data = await suggestAddresses(recommendForm.new_event_address.trim());
        setRecommendAddressSuggestions(data.suggestions);
      } catch {
        setRecommendAddressSuggestions([]);
      }
    }, 250);

    return () => clearTimeout(timeout);
  }, [recommendForm.new_event_address]);

  useEffect(() => {
    void loadEvents();
  }, []);

  return (
    <main className="app-shell">
      <h1>WhatsMyWay</h1>
      <p className="subtitle">Sales calendar planner with travel-optimized slot recommendations.</p>

      <section className="workspace">
        <aside className="panel side-panel">
          <h2>Create Event</h2>
          <label>
            Title *
            <input
              required
              value={eventForm.title}
              onChange={(e) => setEventForm({ ...eventForm, title: e.target.value })}
            />
          </label>
          <label>
            Address *
            <input
              required
              value={eventForm.address}
              onChange={(e) => {
                setEventForm({ ...eventForm, address: e.target.value });
                setEventAddressValidated(false);
                setEventAddressMessage(null);
              }}
              onBlur={() => {
                void validateEventAddressInput(eventForm.address);
              }}
            />
            {eventAddressSuggestions.length > 0 ? (
              <div className="address-suggestions">
                {eventAddressSuggestions.map((candidate) => (
                  <button
                    key={candidate}
                    type="button"
                    className="address-suggestion"
                    onClick={() => {
                      setEventForm((prev) => ({ ...prev, address: candidate }));
                      void validateEventAddressInput(candidate);
                    }}
                  >
                    {candidate}
                  </button>
                ))}
              </div>
            ) : null}
            {eventAddressMessage ? <div className="address-status">{eventAddressMessage}</div> : null}
          </label>
          <div className="inline">
            <label>
              Start *
              <input
                required
                type="datetime-local"
                value={eventForm.start_at}
                onChange={(e) => setEventForm({ ...eventForm, start_at: e.target.value })}
              />
            </label>
            <label>
              Duration (min) *
              <input
                required
                min={1}
                type="number"
                value={eventForm.duration_min}
                onChange={(e) =>
                  setEventForm({ ...eventForm, duration_min: Number(e.target.value) })
                }
              />
            </label>
          </div>
          <p className="hint">Ends at: {projectedEnd ? new Date(projectedEnd).toLocaleString() : "-"}</p>
          <button onClick={submitEvent}>Save event</button>
        </aside>

        <section className="calendar-zone">
          <div className="panel controls-panel">
            <div className="controls-row">
              <label>
                Sales rep id *
                <input required value={salesRepId} onChange={(e) => setSalesRepId(e.target.value)} />
              </label>
              <label>
                Date range start *
                <input
                  required
                  type="datetime-local"
                  value={rangeStart}
                  onChange={(e) => setRangeStart(e.target.value)}
                />
              </label>
              <label>
                Date range end *
                <input
                  required
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
                          <button
                            className="event-delete"
                            aria-label={`Delete ${event.title}`}
                            onClick={() => {
                              void handleDeleteEvent(event.id);
                            }}
                          >
                            ×
                          </button>
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
            New event address *
            <input
              required
              value={recommendForm.new_event_address}
              onChange={(e) => {
                setRecommendForm({ ...recommendForm, new_event_address: e.target.value });
                setRecommendAddressValidated(false);
                setRecommendAddressMessage(null);
              }}
              onBlur={() => {
                void validateRecommendAddressInput(recommendForm.new_event_address);
              }}
            />
            {recommendAddressSuggestions.length > 0 ? (
              <div className="address-suggestions">
                {recommendAddressSuggestions.map((candidate) => (
                  <button
                    key={candidate}
                    type="button"
                    className="address-suggestion"
                    onClick={() => {
                      setRecommendForm((prev) => ({ ...prev, new_event_address: candidate }));
                      void validateRecommendAddressInput(candidate);
                    }}
                  >
                    {candidate}
                  </button>
                ))}
              </div>
            ) : null}
            {recommendAddressMessage ? (
              <div className="address-status">{recommendAddressMessage}</div>
            ) : null}
          </label>
          <div className="inline">
            <label>
              Duration (min) *
              <input
                required
                min={1}
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
              Buffer (min) *
              <input
                required
                min={0}
                type="number"
                value={recommendForm.buffer_min}
                onChange={(e) => setRecommendForm({ ...recommendForm, buffer_min: Number(e.target.value) })}
              />
            </label>
          </div>
          <button onClick={submitRecommendation}>Get recommendations</button>
          <ul>
            {suggestions.map((slot) => (
              <li key={recommendationKey(slot)} className="recommendation-item">
                <strong>{formatTimeWindow(slot.start_at, slot.end_at)}</strong>
                <div>{new Date(slot.start_at).toLocaleDateString()}</div>
                <div>
                  Travel from previous event:{" "}
                  {slot.travel_from_previous_min === null ? "N/A" : `${slot.travel_from_previous_min} min`}
                </div>
                <div>
                  Travel to next event:{" "}
                  {slot.travel_to_next_min === null ? "N/A" : `${slot.travel_to_next_min} min`}
                </div>
                <div className="recommendation-actions">
                  <button type="button" onClick={() => dismissRecommendation(slot)}>
                    Dismiss
                  </button>
                  <button type="button" onClick={() => void addRecommendationAsEvent(slot)}>
                    Add as event
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </aside>
      </section>

      {error ? <div className="error">{error}</div> : null}
    </main>
  );
}
