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
  arrival_airport: string | null;
  arrival_code: string | null;
  arrival_local_time: string | null;
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
  status: "ready" | "partial" | "unavailable" | "blocked" | "error";
  reason?: string;
  message?: string;
  legs?: { kind: string; distance_meters: number; duration_seconds: number; static_duration_seconds: number; encoded_polyline: string; retrieved_at: string }[];
  origin_ground_minutes?: number;
  destination_ground_minutes?: number;
  airport_checkin_buffer_minutes?: number;
  estimated_wait_at_departure_airport_minutes?: number;
  estimated_total_minutes?: number;
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
