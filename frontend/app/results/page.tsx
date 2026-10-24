"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AlertCircle, ArrowLeft, ArrowRight, CalendarDays, Clock3, MapPin, Users } from "lucide-react";
import { AppShell, PageIntro } from "../components/app-shell";

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
                  <span className="stage-label"><Clock3 aria-hidden="true" />Live search not connected</span>
                </div>
                <div className="empty-results results-empty">
                  <span className="empty-icon"><AlertCircle aria-hidden="true" /></span>
                  <div><h3>No live journeys to compare yet</h3><p>The search details are ready, but no flight or rail provider is connected. FDR has not created sample fares or itinerary cards. Live flight search is planned for Stage 3.</p></div>
                </div>
              </section>

              <aside className="surface results-side">
                <h2>Search coverage</h2>
                <p>Once providers are connected, this panel will show which sources and airport pairs were checked.</p>
                <div className="coverage-status"><span className="provider-dot" aria-hidden="true" />No sources queried for this search</div>
                <p className="coverage-disclaimer">Cost and duration comparisons will show missing components explicitly. An unknown transfer cost will not be treated as zero.</p>
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

export default function ResultsPage() {
  return (
    <Suspense fallback={<AppShell><main className="page-content"><p className="page-subtitle">Loading search details…</p></main></AppShell>}>
      <ResultsContent />
    </Suspense>
  );
}
