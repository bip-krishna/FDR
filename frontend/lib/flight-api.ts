export type FlightSearchInput = {
  origin: string;
  destination: string;
  departure_date: string;
  travel_class: string;
  currency: string;
  adults: number;
  include_nearby_airports: boolean;
};

export type FlightSegment = {
  airline: string | null;
  flight_number: string | null;
  departure_airport: string | null;
  departure_code: string | null;
  departure_local_time: string | null;
  departure_at_utc?: string | null;
  arrival_airport: string | null;
  arrival_code: string | null;
  arrival_local_time: string | null;
  arrival_at_utc?: string | null;
  duration_minutes: number | null;
  aircraft: string | null;
  travel_class: string | null;
};

export type FlightOffer = {
  id: string;
  origin_airport: string | null;
  origin_code: string | null;
  destination_airport: string | null;
  destination_code: string | null;
  segments: FlightSegment[];
  stops: number;
  layovers: { name?: string; id?: string; duration?: number; overnight?: boolean }[];
  total_duration_minutes: number | null;
  price: number | null;
  currency: string;
  airlines: string[];
  booking_url: string | null;
  source: string;
  status: "live" | "cached";
  retrieved_at: string;
  provider_created_at: string | null;
  fare_note: string;
};

export type FlightSearchResponse = {
  status: "live" | "cached" | "unavailable" | "blocked" | "error";
  reason: string | null;
  message: string;
  results: FlightOffer[];
  airport_pairs_searched: { origin: string; destination: string }[];
  airport_pairs_failed: { origin: string; destination: string; reason: string }[];
  airport_pairs_not_searched: { origin: string; destination: string }[];
  calls_used: number;
  calls_allowed: number;
  source: string;
  retrieved_at: string | null;
};

export type TransferEstimate = {
  status: "ready" | "unavailable" | "blocked" | "error";
  reason?: string;
  message?: string;
  origin?: { latitude: number; longitude: number; formatted_address: string };
  destination?: { latitude: number; longitude: number; formatted_address: string };
  distance_meters?: number;
  duration_seconds?: number;
  static_duration_seconds?: number;
  encoded_polyline?: string;
  departure_time?: string;
  arrival_time_estimate?: string;
  traffic_delay_seconds?: number;
  traffic_mode?: "current_traffic" | "future_prediction";
  traffic_label?: string;
  provider?: string;
  retrieved_at?: string;
  ranking_duration_minutes?: number;
  calls_used?: number;
};

export type GroundAccessEstimate = {
  status: "ready" | "infeasible" | "partial" | "unavailable" | "blocked" | "error";
  reason?: string;
  message?: string;
  legs?: { kind: string; distance_meters: number; duration_seconds: number; static_duration_seconds: number; encoded_polyline: string; retrieved_at: string; departure_time?: string; provider?: string; traffic_mode?: "current_traffic" | "future_prediction" }[];
  origin_ground_minutes?: number;
  destination_ground_minutes?: number;
  airport_checkin_buffer_minutes?: number;
  estimated_wait_at_departure_airport_minutes?: number;
  estimated_total_minutes?: number;
  scheduled_flight_elapsed_minutes?: number;
  estimated_total_known_cost?: number | null;
  unpriced_components?: string[];
  risks?: string[];
  calls_used?: number;
};

const requestCache = new Map<string, Promise<FlightSearchResponse>>();

export function searchFlights(apiBaseUrl: string, input: FlightSearchInput): Promise<FlightSearchResponse> {
  const baseUrl = apiBaseUrl.replace(/\/$/, "");
  const cacheKey = `${baseUrl}:${JSON.stringify(input)}`;
  const existing = requestCache.get(cacheKey);
  if (existing) return existing;

  const request = fetch(`${baseUrl}/api/flights/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }).then(async (response) => {
    const payload = await response.json();
    if (!response.ok) throw new Error("The flight search request could not be completed.");
    return payload as FlightSearchResponse;
  }).catch((error: unknown) => {
    requestCache.delete(cacheKey);
    throw error;
  });

  requestCache.set(cacheKey, request);
  void request.then(() => requestCache.delete(cacheKey), () => requestCache.delete(cacheKey));
  return request;
}

export async function estimateTransfer(apiBaseUrl: string, input: {
  origin: string; destination: string; departure_time: string;
}): Promise<TransferEstimate> {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/api/transfers/estimate`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error("The transfer service could not complete this request.");
  return response.json() as Promise<TransferEstimate>;
}

export async function estimateGroundAccess(apiBaseUrl: string, input: {
  origin: string; destination: string; departure_airport_code: string; arrival_airport_code: string;
  departure_local_time: string; arrival_local_time: string; flight_duration_minutes: number;
}): Promise<GroundAccessEstimate> {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/api/journeys/ground-access`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error("The ground access estimate could not be completed.");
  return response.json() as Promise<GroundAccessEstimate>;
}

export type OptimizationSegment = {
  segment_id: string;
  mode: "flight" | "train" | "ground";
  origin: string;
  destination: string;
  departure_at: string;
  arrival_at: string;
  provider: string;
  data_status: "live" | "cached" | "estimated" | "static";
  estimate_departure_at?: string | null;
  fare_amount: number | null;
  currency: string | null;
  ticket_group_id: string | null;
  booking_url: string | null;
};

export type OptimizedRoute = {
  segment_ids: string[];
  segments: (Omit<OptimizationSegment, "fare_amount"> & { id: string; fare_amount: string | null })[];
  departure_at: string;
  arrival_at: string;
  duration_minutes: number;
  fare_amount: string | null;
  known_fare_amount: string | null;
  known_fare_currency: string | null;
  currency: string | null;
  fare_complete: boolean;
  confirmed_bookable: false;
  pareto_efficient: boolean;
  risks: string[];
};

export type OptimizationResponse = {
  status: "ready" | "unavailable";
  reason: string | null;
  message: string;
  origin: string;
  destination: string;
  routes: OptimizedRoute[];
  routes_considered: number;
  pareto_routes: number;
  search_truncated: boolean;
  search_states_expanded: number;
};

export async function optimizeJourneys(apiBaseUrl: string, input: {
  origin: string; destination: string; segments: OptimizationSegment[];
}): Promise<OptimizationResponse> {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/api/journeys/optimize`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Journey optimization could not be completed.");
  return payload as OptimizationResponse;
}

export type LayoverEvaluation = {
  status: "ready";
  layover_minutes: number;
  long_layover: boolean;
  exploration_eligible_by_duration: boolean;
  exit_eligibility: "verified_yes" | "verified_no" | "unknown";
  airport_exit_authorized: false;
  exploration_start_at: string;
  latest_recommended_airport_return_at: string;
  available_exploration_minutes: number;
  airport_return_buffer_minutes: number;
  terminal_transfer_buffer_minutes: number;
  weather_status: string;
  route_traffic_status: string;
  places_status: string;
  warnings: string[];
  feasible_candidates: { place_id: string; name: string }[];
  rejected_candidates: { place_id: string; name: string; reason: string }[];
  places_message: string;
  route_message: string;
  weather_message: string;
  disclaimer: string;
};

export async function evaluateLayover(apiBaseUrl: string, input: {
  arrival_at: string; departure_at: string;
  exit_eligibility: "verified_yes" | "verified_no" | "unknown";
  baggage_recheck_required: boolean;
}): Promise<LayoverEvaluation> {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/api/layovers/evaluate`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Layover evaluation could not be completed.");
  return payload as LayoverEvaluation;
}

export type LayoverPlanResult = {
  status: "ready" | "unavailable" | "blocked" | "rejected" | "error";
  reason?: string;
  message?: string;
  groq_called: boolean;
  places?: { candidate_id: string; name: string; source: string; source_status: string;
    arrive_place_at: string; finish_visit_at: string; return_to_airport_at: string;
    known_cost_amount: number | null; known_cost_currency: string | null; explanation: string }[];
  warnings?: string[];
  latest_recommended_airport_return_at?: string;
  disclaimer?: string;
};

export async function planLayover(apiBaseUrl: string, input: {
  arrival_at: string; departure_at: string; exit_eligibility: "verified_yes" | "verified_no" | "unknown";
  baggage_recheck_required: boolean; disclaimer_acknowledged: boolean; interests: string[];
}): Promise<LayoverPlanResult> {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/api/layovers/plan`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Layover planning could not be completed.");
  return payload as LayoverPlanResult;
}
