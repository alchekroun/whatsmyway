export type EventInput = {
  title: string;
  address: string;
  start_at: string;
  end_at: string;
  sales_rep_id: string;
  time_zone?: string;
};

export type SalesEvent = EventInput & {
  id: string;
};

export type RecommendationRequest = {
  date_start: string;
  date_end: string;
  sales_rep_id: string;
  new_event_duration_min: number;
  new_event_address: string;
  buffer_min?: number;
};

export type Recommendation = {
  start_at: string;
  end_at: string;
  new_event_address: string;
  before_event_id: string | null;
  after_event_id: string | null;
  added_travel_min: number;
  total_travel_min: number;
  travel_from_previous_min: number | null;
  travel_to_next_min: number | null;
  explanation: string;
};

export type RecommendationResponse = {
  suggestions: Recommendation[];
};
