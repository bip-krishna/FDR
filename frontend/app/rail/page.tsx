"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ArrowUpRight, CalendarDays, Search, TrainFront } from "lucide-react";
import { AppShell, PageIntro } from "../components/app-shell";

type Station = { name: string; code: string; retrieved_on: string };
type RailSearchResult = {
  status: "unavailable";
  message: string;
  origin: { name: string; code: string };
  destination: { name: string; code: string };
  journey_date: string;
  results: never[];
  availability: "unavailable";
  fare: "unavailable";
  fallbacks: { name: string; url: string }[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_FDR_API_URL?.trim().replace(/\/$/, "");

function StationField({ label, value, onChange, selected, onSelect }: {
  label: string; value: string; onChange: (value: string) => void;
  selected: Station | null; onSelect: (station: Station) => void;
}) {
  const [matches, setMatches] = useState<Station[]>([]);
  const [matchesQuery, setMatchesQuery] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!apiBaseUrl || value.trim().length < 2 || selected?.name === value) {
      return;
    }
    let active = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      fetch(`${apiBaseUrl}/api/rail/stations?q=${encodeURIComponent(value)}&limit=8`)
        .then((response) => response.ok ? response.json() : Promise.reject())
        .then((payload: { results: Station[] }) => { if (active) { setMatches(payload.results); setMatchesQuery(value); } })
        .catch(() => { if (active) { setMatches([]); setMatchesQuery(value); } })
        .finally(() => { if (active) setLoading(false); });
    }, 180);
    return () => { active = false; window.clearTimeout(timer); };
  }, [value, selected?.name]);

  const visibleMatches = matchesQuery === value ? matches : [];

  return (
    <div className="field rail-station-field">
      <label className="field-label" htmlFor={`rail-${label}`}>{label}</label>
      <div className="rail-input-wrap">
        <TrainFront className="field-icon" aria-hidden="true" />
        <input id={`rail-${label}`} className="field-input" autoComplete="off" value={value}
          placeholder="Search station name or code" onChange={(event) => onChange(event.target.value)}
          role="combobox" aria-autocomplete="list" aria-expanded={visibleMatches.length > 0} aria-controls={`rail-options-${label}`} />
        {visibleMatches.length > 0 && <ul id={`rail-options-${label}`} className="rail-suggestions" role="listbox" aria-label={`${label} stations`}>
          {visibleMatches.map((station) => <li key={station.code}>
            <button type="button" role="option" aria-selected={false} onClick={() => { onSelect(station); setMatches([]); }}>
              <span>{station.name}</span><code>{station.code}</code>
            </button>
          </li>)}
        </ul>}
      </div>
      <span className="field-hint">{selected ? `Selected ${selected.code}` : loading ? "Searching station index…" : "Choose a station from the official 2026 index."}</span>
    </div>
  );
}

export default function RailPage() {
  const [originText, setOriginText] = useState("");
  const [destinationText, setDestinationText] = useState("");
  const [origin, setOrigin] = useState<Station | null>(null);
  const [destination, setDestination] = useState<Station | null>(null);
  const [journeyDate, setJourneyDate] = useState("");
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<RailSearchResult | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    if (!origin || !destination) {
      setError("Select both stations from the suggestions so the station codes are verified.");
      return;
    }
    if (!apiBaseUrl) {
      setError("The FDR API is not configured for this deployment.");
      return;
    }
    setSearching(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/rail/search`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ origin_code: origin.code, destination_code: destination.code, journey_date: journeyDate }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Rail enquiry could not be completed.");
      setResult(payload as RailSearchResult);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Rail enquiry could not be completed.");
    } finally {
      setSearching(false);
    }
  }

  return <AppShell>
    <main className="page-content secondary-page rail-page">
      <PageIntro eyebrow="Indian Railways" title="Explore rail routes." description="Find stations from the 2026 official code index, then continue to official railway enquiry for current trains, fares, and availability." />

      <section className="surface rail-search-panel" aria-labelledby="rail-search-heading">
        <div className="card-heading"><h2 className="card-heading-title" id="rail-search-heading">Search a rail journey</h2><span className="card-heading-note">Reference index · 2026</span></div>
        <form className="form-body" onSubmit={submit}>
          <div className="rail-station-grid">
            <StationField label="From station" value={originText} selected={origin}
              onChange={(value) => { setOriginText(value); setOrigin(null); }}
              onSelect={(station) => { setOrigin(station); setOriginText(station.name); }} />
            <StationField label="To station" value={destinationText} selected={destination}
              onChange={(value) => { setDestinationText(value); setDestination(null); }}
              onSelect={(station) => { setDestination(station); setDestinationText(station.name); }} />
          </div>
          <div className="rail-date-field field">
            <label className="field-label" htmlFor="rail-date">Journey date</label>
            <div className="rail-input-wrap"><CalendarDays className="field-icon" aria-hidden="true" />
              <input className="field-input date-input" id="rail-date" type="date" required value={journeyDate} onChange={(event) => setJourneyDate(event.target.value)} />
            </div>
          </div>
          {error && <div className="error-banner" role="alert">{error}</div>}
          <div className="form-footer">
            <span className="form-note">No external rail API calls are made.</span>
            <button className="search-button" type="submit" disabled={searching}>
              <Search aria-hidden="true" />{searching ? "Checking…" : "Check rail options"}
            </button>
          </div>
        </form>
      </section>

      {result && <section className="surface rail-result-panel" aria-live="polite">
        <div className="rail-result-heading"><span className="rail-result-icon"><TrainFront aria-hidden="true" /></span>
          <div><span className="page-eyebrow">{result.origin.code} → {result.destination.code} · {result.journey_date}</span><h2>Live train data is unavailable in FDR</h2></div>
        </div>
        <p>{result.message}</p>
        <div className="rail-unknowns"><span><strong>Schedule</strong>Unavailable</span><span><strong>Fare</strong>Unavailable</span><span><strong>Seat availability</strong>Unavailable</span></div>
        <div className="rail-fallbacks">{result.fallbacks.map((item) => <a key={item.name} href={item.url} target="_blank" rel="noreferrer">{item.name}<ArrowUpRight size={14} aria-hidden="true" /></a>)}</div>
      </section>}

      <div className="rail-provider-note">
        <span className="provider-dot" aria-hidden="true" />
        <div><strong>Official data and provider status</strong>
          <p>Station names and codes come from Indian Railways’ 2026 Station Code Index. FDR does not fetch train schedules, fares, or seat inventory yet. It does not scrape IRCTC or NTES.</p>
        </div>
      </div>
    </main>
  </AppShell>;
}
