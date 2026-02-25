import type {
  EventInput,
  RecommendationRequest,
  RecommendationResponse,
  SalesEvent
} from "@whatsmyway/shared-types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5001";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function createEvent(payload: EventInput): Promise<SalesEvent> {
  return request<SalesEvent>("/api/events", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function listEvents(params: {
  salesRepId: string;
  start: string;
  end: string;
}): Promise<SalesEvent[]> {
  const query = new URLSearchParams({
    sales_rep_id: params.salesRepId,
    start: params.start,
    end: params.end
  });

  return request<SalesEvent[]>(`/api/events?${query.toString()}`);
}

export function recommend(payload: RecommendationRequest): Promise<RecommendationResponse> {
  return request<RecommendationResponse>("/api/recommendations", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
