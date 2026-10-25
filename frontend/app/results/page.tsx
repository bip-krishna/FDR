"use client";

import { Suspense, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AlertCircle, ArrowLeft, ArrowRight, CalendarDays, Clock3, MapPin, Users, Plane, ExternalLink } from "lucide-react";
import { AppShell, PageIntro } from "../components/app-shell";
import { FlightOffer, FlightSearchResponse, GroundAccessEstimate, TransferEstimate, estimateGroundAccess, estimateTransfer, searchFlights } from "../../lib/flight-api";
import { JourneyRanking, rankJourneyOffers, journeyRankingNote } from "../../lib/journey-ranking";

type SearchDetails = {
  origin: string;
  destination: string;
  departure: string;
  returnDate?: string;
  passengers: string;
  travelClass: string;
  tripType: string;
  nearbyAirports: boolean;
  includeRail: boolean;
  budget?: string;
  maxDuration?: string;
};

function formatDate(value?: string) {
  if (!value) return "";
  return new Date(value + "T00:00:00").toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function ResultsContent() {
  const params = useSearchParams();
  const origin = params.get("origin");
  const destination = params.get("destination");
  const departure = params.get("departure");
  const details: SearchDetails | null = origin && destination && departure ? {
      origin,
      destination,
      departure,
      returnDate: params.get("return") ?? undefined,
      passengers: params.get("passengers") ?? "1",
      travelClass: params.get("travelClass") ?? "economy",
      tripType: params.get("tripType") ?? "one-way",
      nearbyAirports: params.get("nearbyAirports") === "true",
      includeRail: params.get("includeRail") === "true",
      budget: params.get("budget") ?? undefined,
      maxDuration: params.get("maxDuration") ?? undefined,
    } : null;

  const classLabel = details?.travelClass.replace("-", " ");
  const passengerCount = Number(details?.passengers ?? 1);
  const searchInputKey = details ? JSON.stringify({
    trip_type: details.tripType,
    origin: details.origin,
    destination: details.destination,
    departure_date: details.departure,
    travel_class: details.travelClass,
    currency: "INR",
    adults: passengerCount,
    include_nearby_airports: details.nearbyAirports,
  }) : "";
  const [flightRun, setFlightRun] = useState<{
    key: string; loading: boolean; response?: FlightSearchResponse; error?: string;
  } | null>(null);
  const [ranking, setRanking] = useState<JourneyRanking>("best");
  const [groundAccessByOffer, setGroundAccessByOffer] = useState<Record<string, GroundAccessEstimate>>({});
  const [groundAccessPending, setGroundAccessPending] = useState<Record<string, boolean>>({});
  const apiBaseUrl = process.env.NEXT_PUBLIC_FDR_API_URL?.trim();
  const currentFlightRun = flightRun?.key === searchInputKey ? flightRun : null;
  const flightResponse = currentFlightRun?.response ?? null;
  const flightError = currentFlightRun?.error ?? null;
  const loadingFlights = currentFlightRun?.loading ?? false;
  const scopedAccess: Record<string, GroundAccessEstimate> = {};
  flightResponse?.results.forEach((offer) => {
    const estimate = groundAccessByOffer[`${searchInputKey}:${offer.id}`];
    if (estimate) scopedAccess[offer.id] = estimate;
  });
  const rankedOffers = flightResponse ? rankJourneyOffers(flightResponse.results, scopedAccess, ranking) : [];

  async function requestGroundAccess(offer: FlightOffer) {
    if (!apiBaseUrl) return;
    const key = `${searchInputKey}:${offer.id}`;
    const first = offer.segments[0], last = offer.segments.at(-1);
    if (!offer.origin_code || !offer.destination_code || !first?.departure_local_time || !last?.arrival_local_time || offer.total_duration_minutes == null) {
      setGroundAccessByOffer((previous) => ({ ...previous, [key]: {
        status: "unavailable", message: "The flight provider did not return airport times and duration needed for door-to-door timing.",
      } }));
      return;
    }
    setGroundAccessPending((previous) => ({ ...previous, [key]: true }));
    try {
      const estimate = await estimateGroundAccess(apiBaseUrl, {
        origin: details?.origin ?? "", destination: details?.destination ?? "",
        departure_airport_code: offer.origin_code, arrival_airport_code: offer.destination_code,
        departure_local_time: first.departure_local_time, arrival_local_time: last.arrival_local_time,
        flight_duration_minutes: offer.total_duration_minutes,
      });
      setGroundAccessByOffer((previous) => ({ ...previous, [key]: estimate }));
    } catch {
      setGroundAccessByOffer((previous) => ({ ...previous, [key]: {
        status: "error", message: "The ground access service could not be reached. No estimate is available.",
      } }));
    } finally {
      setGroundAccessPending((previous) => ({ ...previous, [key]: false }));
    }
  }

  useEffect(() => {
    if (!searchInputKey) return;
    const parsedInput = JSON.parse(searchInputKey) as {
      trip_type: string;
      origin: string; destination: string; departure_date: string; travel_class: string;
      currency: string; adults: number; include_nearby_airports: boolean;
    };
    if (parsedInput.trip_type === "round" || !apiBaseUrl) return;
    const input = {
      origin: parsedInput.origin,
      destination: parsedInput.destination,
      departure_date: parsedInput.departure_date,
      travel_class: parsedInput.travel_class,
      currency: parsedInput.currency,
      adults: parsedInput.adults,
      include_nearby_airports: parsedInput.include_nearby_airports,
    };
    let active = true;
    const timer = window.setTimeout(() => {
      if (!active) return;
      setFlightRun({ key: searchInputKey, loading: true });
      searchFlights(apiBaseUrl, input).then((response) => {
        if (active) setFlightRun({ key: searchInputKey, loading: false, response });
      }).catch(() => {
        if (active) setFlightRun({ key: searchInputKey, loading: false,
          error: "FDR could not reach the flight-search service. No fare information is available." });
      });
    }, 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [searchInputKey, apiBaseUrl]);

  const responseStatus = flightResponse?.status;
  const resultStatusLabel = loadingFlights ? "Searching provider" :
    responseStatus === "live" ? "Provider results" :
    responseStatus === "cached" ? "Cached provider results" :
    responseStatus === "blocked" ? "Search blocked" :
    responseStatus === "error" ? "Provider unavailable" : "No provider search";

  return (
    <AppShell>
      <main className="page-content">
        <PageIntro
          eyebrow="Flight & multimodal results"
          title={details ? `${details.origin} to ${details.destination}.` : "Journey results."}
          description="Compare available options by total journey time, transfers, and known costs. Search coverage will always reflect the providers actually checked."
        />

        {details ? (
          <>
            <section className="surface results-query" aria-label="Search details">
              <div className="query-route">
                <div><span className="query-label">From</span><strong>{details.origin}</strong></div>
                <ArrowRight className="query-arrow" aria-hidden="true" />
                <div><span className="query-label">To</span><strong>{details.destination}</strong></div>
              </div>
              <div className="query-meta">
                <span><CalendarDays aria-hidden="true" />{formatDate(details.departure)}{details.returnDate ? ` – ${formatDate(details.returnDate)}` : ""}</span>
                <span><Users aria-hidden="true" />{passengerCount} {passengerCount === 1 ? "traveller" : "travellers"}</span>
                <span className="capitalize">{classLabel}</span>
                {details.nearbyAirports && <span>Nearby airports</span>}
                {details.includeRail && <span>Rail requested</span>}
                {details.budget && <span>Budget ₹{Number(details.budget).toLocaleString("en-IN")}</span>}
                {details.maxDuration && <span>Up to {details.maxDuration} hours</span>}
              </div>
            </section>

            <div className="results-grid">
              <section className="surface result-list" aria-labelledby="available-routes">
                <div className="result-list-heading">
                  <div><h2 id="available-routes">Available journeys</h2><p>Ranked with the information returned by each provider.</p></div>
                  <span className={`stage-label ${responseStatus === "live" ? "stage-label-live" : ""}`}>
                    <Clock3 aria-hidden="true" />{resultStatusLabel}
                  </span>
                </div>
                {loadingFlights ? (
                  <div className="empty-results results-empty" role="status" aria-live="polite">
                    <span className="empty-icon"><Plane aria-hidden="true" /></span>
                    <div><h3>Checking SerpApi for this route</h3><p>This searches the requested airport pair. Nearby airport combinations are included only when enabled and remain within your configured request cap.</p></div>
                  </div>
                ) : flightError ? (
                  <div className="empty-results results-empty" role="alert"><span className="empty-icon"><AlertCircle aria-hidden="true" /></span><div><h3>Search could not connect</h3><p>{flightError}</p></div></div>
                ) : details?.tripType === "round" ? (
                  <div className="empty-results results-empty"><span className="empty-icon"><AlertCircle aria-hidden="true" /></span><div><h3>Round-trip flight search is not available yet</h3><p>Stage 3 currently connects one-way live search. No provider request was made for this round trip.</p></div></div>
                ) : !apiBaseUrl ? (
                  <div className="empty-results results-empty"><span className="empty-icon"><AlertCircle aria-hidden="true" /></span><div><h3>Flight-search service is not connected</h3><p>Configure NEXT_PUBLIC_FDR_API_URL for this frontend deployment. FDR has not returned or created any sample fares.</p></div></div>
                ) : flightResponse?.results.length ? (
                  <>
                    <p className="flight-search-message" role="status">{flightResponse.message} {flightResponse.calls_used > 0 ? `${flightResponse.calls_used} provider request${flightResponse.calls_used === 1 ? "" : "s"} used.` : ""}</p>
                    <div className="journey-ranking" aria-label="Rank journeys">
                      {(["best", "cheapest", "fastest", "fewest-transfers"] as JourneyRanking[]).map((mode) => <button key={mode} type="button" aria-pressed={ranking === mode} onClick={() => setRanking(mode)}>
                        {mode === "best" ? "Best overall" : mode === "cheapest" ? "Lowest known fare" : mode === "fastest" ? "Fastest" : "Fewest transfers"}
                      </button>)}
                    </div>
                    <p className="journey-ranking-note">{journeyRankingNote(ranking, Object.values(scopedAccess).some((entry) => entry.status === "ready"))}</p>
                    <div className="flight-results">
                      {rankedOffers.map((offer) => {
                        const key = `${searchInputKey}:${offer.id}`;
                        return <FlightResultCard key={offer.id} offer={offer} access={groundAccessByOffer[key]}
                          accessPending={groundAccessPending[key] ?? false} onEstimateAccess={() => requestGroundAccess(offer)} />;
                      })}
                    </div>
                  </>
                ) : (
                  <div className="empty-results results-empty"><span className="empty-icon"><AlertCircle aria-hidden="true" /></span><div>
                    <h3>{flightResponse?.status === "live" || flightResponse?.status === "cached" ? "No flights returned for this search" : "Live flight search is unavailable"}</h3>
                    <p>{flightResponse?.message ?? "FDR has not received flight results. No example fares are shown."}</p>
                  </div></div>
                )}
              </section>

              <aside className="surface results-side">
                <h2>Search coverage</h2>
                <p>Only airport pairs returned by the configured provider search are listed here.</p>
                <div className="coverage-status"><span className="provider-dot" aria-hidden="true" />
                  {loadingFlights ? "Contacting SerpApi" : flightResponse?.status === "unavailable" ? "SerpApi unavailable" : flightResponse?.status === "blocked" ? "Blocked by usage limits" : flightResponse?.airport_pairs_searched.length ? "SerpApi checked" : "No provider search made"}
                </div>
                {flightResponse?.airport_pairs_searched.map((pair) => <div className="airport-pair-line" key={`${pair.origin}-${pair.destination}`}><span>{pair.origin} → {pair.destination}</span><small>searched</small></div>)}
                {flightResponse?.airport_pairs_failed.map((pair) => <div className="airport-pair-line airport-pair-muted" key={`${pair.origin}-${pair.destination}`}><span>{pair.origin} → {pair.destination}</span><small>provider error</small></div>)}
                {flightResponse?.airport_pairs_not_searched.map((pair) => <div className="airport-pair-line airport-pair-muted" key={`${pair.origin}-${pair.destination}`}><span>{pair.origin} → {pair.destination}</span><small>not searched</small></div>)}
                {flightResponse?.retrieved_at && <p className="coverage-foot">Retrieved {new Date(flightResponse.retrieved_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })} · source: SerpApi</p>}
                <p className="coverage-disclaimer">Prices can change before booking. Ground transfer time is included only after an estimate; ground fares and rail are unavailable.</p>
                <TransferExplorer key={`${details.origin}:${details.destination}:${details.departure}`} apiBaseUrl={apiBaseUrl} details={details} />
              </aside>
            </div>

            <Link className="back-to-search" href="/"><ArrowLeft aria-hidden="true" />Change search</Link>
          </>
        ) : (
          <section className="surface results-query results-invalid">
            <span className="empty-icon"><MapPin aria-hidden="true" /></span>
            <div><h2>Search details are missing</h2><p>Start with a valid origin, destination, and departure date.</p><Link href="/">Return to search <ArrowRight aria-hidden="true" /></Link></div>
          </section>
        )}
      </main>
    </AppShell>
  );
}

function TransferExplorer({ apiBaseUrl, details }: {
  apiBaseUrl?: string; details: SearchDetails;
}) {
  const [origin, setOrigin] = useState(details.origin);
  const [destination, setDestination] = useState(details.destination);
  const [state, setState] = useState<{ loading: boolean; result?: TransferEstimate; error?: string }>({ loading: false });
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiBaseUrl) return;
    setState({ loading: true });
    try {
      const requestedMorning = new Date(`${details.departure}T09:00:00`);
      const departure = requestedMorning.getTime() > Date.now() ? requestedMorning : new Date();
      const result = await estimateTransfer(apiBaseUrl, {
        origin, destination, departure_time: departure.toISOString(),
      });
      setState({ loading: false, result });
    } catch {
      setState({ loading: false, error: "The transfer service could not be reached. No estimate is available." });
    }
  }
  const points = state.result?.encoded_polyline ? decodePolyline(state.result.encoded_polyline) : [];
  const svgPoints = toSvgPolyline(points);
  const svgCoords = svgPoints.split(" ").map((point) => point.split(","));
  return <section className="transfer-explorer" aria-labelledby="transfer-title">
    <div className="transfer-title-row"><span className="transfer-mark"><MapPin aria-hidden="true" /></span><div><h3 id="transfer-title">Ground transfer</h3><p>Check a city, station, or airport connection.</p></div></div>
    <form className="transfer-form" onSubmit={submit}>
      <label>From<input value={origin} onChange={(event) => setOrigin(event.target.value)} maxLength={160} required /></label>
      <label>To<input value={destination} onChange={(event) => setDestination(event.target.value)} maxLength={160} required /></label>
      <button type="submit" disabled={state.loading || !apiBaseUrl}>{state.loading ? "Calculating…" : "Get route"}<ArrowRight aria-hidden="true" /></button>
    </form>
    {!apiBaseUrl && <p className="transfer-note">The hosted travel service is not connected.</p>}
    {state.error && <p className="transfer-note" role="alert">{state.error}</p>}
    {state.result?.status !== undefined && state.result.status !== "ready" && <p className="transfer-note" role="status">{state.result.message}</p>}
    {state.result?.status === "ready" && <div className="transfer-result" aria-live="polite">
      <div className="transfer-stats"><strong>{Math.round((state.result.distance_meters ?? 0) / 1000).toLocaleString("en-IN")} km</strong><strong>{Math.ceil((state.result.duration_seconds ?? 0) / 60)} min</strong></div>
      {svgPoints && <svg className="transfer-map" viewBox="0 0 320 150" role="img" aria-label={`Google route from ${state.result.origin?.formatted_address} to ${state.result.destination?.formatted_address}`}>
        <path className="transfer-map-grid" d="M0 38H320M0 75H320M0 112H320M80 0V150M160 0V150M240 0V150" />
        <polyline points={svgPoints} /><circle cx={svgCoords[0]?.[0]} cy={svgCoords[0]?.[1]} r="4" /><circle cx={svgCoords.at(-1)?.[0]} cy={svgCoords.at(-1)?.[1]} r="4" />
      </svg>}
      <p className="transfer-traffic"><span className="provider-dot" aria-hidden="true" />{state.result.traffic_label} · {Math.ceil((state.result.static_duration_seconds ?? 0) / 60)} min without live traffic</p>
      <p className="transfer-note">Estimated arrival {state.result.arrival_time_estimate ? new Date(state.result.arrival_time_estimate).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" }) : "unavailable"}. Traffic adds about {Math.ceil((state.result.traffic_delay_seconds ?? 0) / 60)} min to the static estimate.</p>
      <p className="transfer-note">Route geometry and duration from Google Maps. {state.result.traffic_mode === "future_prediction" ? "Future traffic is a prediction based on available traffic patterns." : "Traffic can change before travel."}</p>
    </div>}
  </section>;
}

function decodePolyline(encoded: string): [number, number][] {
  const coords: [number, number][] = [];
  let index = 0, lat = 0, lng = 0;
  while (index < encoded.length) {
    const values: number[] = [];
    for (let axis = 0; axis < 2; axis++) {
      let result = 0, shift = 0, byte: number;
      do { byte = encoded.charCodeAt(index++) - 63; result |= (byte & 31) << shift; shift += 5; } while (byte >= 32 && index < encoded.length);
      values.push((result & 1) ? ~(result >> 1) : result >> 1);
    }
    lat += values[0]; lng += values[1]; coords.push([lng / 1e5, lat / 1e5]);
  }
  return coords;
}

function toSvgPolyline(points: [number, number][]): string {
  if (points.length < 2) return "";
  const lons = points.map(([lon]) => lon), lats = points.map(([, lat]) => lat);
  const minLon = Math.min(...lons), maxLon = Math.max(...lons), minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const width = maxLon - minLon || 1e-6, height = maxLat - minLat || 1e-6;
  return points.map(([lon, lat]) => `${12 + ((lon - minLon) / width) * 296},${138 - ((lat - minLat) / height) * 126}`).join(" ");
}

function FlightResultCard({ offer, access, accessPending, onEstimateAccess }: {
  offer: FlightOffer; access?: GroundAccessEstimate; accessPending: boolean; onEstimateAccess: () => void;
}) {
  const duration = offer.total_duration_minutes == null ? "Duration unavailable" :
    `${Math.floor(offer.total_duration_minutes / 60)}h ${offer.total_duration_minutes % 60}m`;
  const price = offer.price == null ? "Fare not provided" : new Intl.NumberFormat("en-IN", {
    style: "currency", currency: offer.currency, maximumFractionDigits: 0,
  }).format(offer.price);
  const first = offer.segments[0];
  const last = offer.segments[offer.segments.length - 1];
  return (
    <article className="flight-card">
      <div className="flight-card-top">
        <div className="flight-airlines">{offer.airlines.join(" · ") || "Airline unavailable"}<span>{offer.status === "cached" ? "Cached result" : "Provider result"}</span></div>
        <div className="flight-price">{price}<small>Provider fare</small></div>
      </div>
      <div className="flight-route-line">
        <div className="flight-time"><strong>{first?.departure_local_time?.slice(-5) ?? "—"}</strong><span>{offer.origin_code ?? "—"}</span></div>
        <div className="flight-duration"><span>{duration}</span><div className="flight-duration-rule" /><small>{offer.stops === 0 ? "Nonstop" : `${offer.stops} stop${offer.stops === 1 ? "" : "s"}`}</small></div>
        <div className="flight-time flight-time-end"><strong>{last?.arrival_local_time?.slice(-5) ?? "—"}</strong><span>{offer.destination_code ?? "—"}</span></div>
      </div>
      {offer.segments.length > 1 && <div className="flight-connections">{offer.segments.map((segment, index) => <span key={`${segment.flight_number ?? index}-${segment.departure_code}`}>{segment.flight_number ?? segment.airline ?? "Flight"}{index < offer.segments.length - 1 ? ` · ${offer.layovers[index]?.name ?? "connection"}` : ""}</span>)}</div>}
      <div className="journey-detail">
        {access?.status === "ready" ? <>
          <div className="journey-access-line"><span>Origin → {offer.origin_code}</span><strong>{access.origin_ground_minutes} min</strong></div>
          <div className="journey-access-line"><span>{offer.destination_code} → destination</span><strong>{access.destination_ground_minutes} min</strong></div>
          <div className="journey-total"><span>Estimated door-to-door time</span><strong>{Math.floor((access.estimated_total_minutes ?? 0) / 60)}h {(access.estimated_total_minutes ?? 0) % 60}m</strong></div>
          <p className="journey-risk">Known total cost: {price}; ground transfer fares are not sourced. Includes a {access.airport_checkin_buffer_minutes}-minute airport buffer.</p>
          {access.risks?.map((risk) => <p className="journey-risk" key={risk}>{risk}</p>)}
          <p className="journey-risk">Ground route estimates use Google Maps. Retrieved {access.legs?.at(-1)?.retrieved_at ? new Date(access.legs.at(-1)!.retrieved_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "time unavailable"}.</p>
        </> : <>
          {access?.message && <p className="journey-risk" role="status">{access.message}</p>}
          <p className="journey-risk">Ground access time and cost are unknown; displayed flight duration excludes airport transfers.</p>
          <button className="journey-estimate-button" type="button" onClick={onEstimateAccess} disabled={accessPending}>
            {accessPending ? "Estimating access…" : access ? "Try access estimate again" : "Estimate airport access"}
          </button>
        </>}
      </div>
      <div className="flight-card-footer">
        <span>{offer.origin_airport ?? offer.origin_code} → {offer.destination_airport ?? offer.destination_code}</span>
        {offer.booking_url ? <a href={offer.booking_url} target="_blank" rel="noreferrer">View on Google Flights <ExternalLink aria-hidden="true" /></a> : <span>Provider link unavailable</span>}
      </div>
      <p className="flight-fare-note">{offer.fare_note} Retrieved {new Date(offer.retrieved_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}.</p>
    </article>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<AppShell><main className="page-content"><p className="page-subtitle">Loading search details…</p></main></AppShell>}>
      <ResultsContent />
    </Suspense>
  );
}
