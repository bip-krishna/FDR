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
