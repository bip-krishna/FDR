"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AlertCircle, ArrowLeft, ArrowRight, CalendarDays, Clock3, MapPin, Users, Plane, ExternalLink } from "lucide-react";
import { AppShell, PageIntro } from "../components/app-shell";
import { FlightOffer, FlightSearchResponse, searchFlights } from "../../lib/flight-api";

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
  const apiBaseUrl = process.env.NEXT_PUBLIC_FDR_API_URL?.trim();
  const currentFlightRun = flightRun?.key === searchInputKey ? flightRun : null;
  const flightResponse = currentFlightRun?.response ?? null;
  const flightError = currentFlightRun?.error ?? null;
  const loadingFlights = currentFlightRun?.loading ?? false;

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
                    <div className="flight-results">
                      {flightResponse.results.map((offer) => <FlightResultCard key={offer.id} offer={offer} />)}
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
                <p className="coverage-disclaimer">Prices and availability can change before booking. Nearby alternatives are limited by your configured request cap. Ground and rail legs are not included.</p>
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

function FlightResultCard({ offer }: { offer: FlightOffer }) {
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
