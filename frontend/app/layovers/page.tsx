"use client";

import { useState, type FormEvent } from "react";
import { AlertTriangle, Clock3, MapPin, PlaneTakeoff, ShieldAlert } from "lucide-react";
import { AppShell, PageIntro } from "../components/app-shell";
import { evaluateLayover, planLayover, type LayoverEvaluation, type LayoverPlanResult } from "../../lib/flight-api";

function formatTimestamp(value: string) {
  return `${value.slice(0, 16).replace("T", " ")} UTC`;
}

export default function LayoversPage() {
  const [arrival, setArrival] = useState("");
  const [departure, setDeparture] = useState("");
  const [eligibility, setEligibility] = useState<"unknown" | "verified_yes" | "verified_no">("unknown");
  const [baggage, setBaggage] = useState(false);
  const [result, setResult] = useState<LayoverEvaluation | null>(null);
  const [planResult, setPlanResult] = useState<LayoverPlanResult | null>(null);
  const [interests, setInterests] = useState("");
  const [disclaimerAcknowledged, setDisclaimerAcknowledged] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const apiBaseUrl = process.env.NEXT_PUBLIC_FDR_API_URL?.trim();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiBaseUrl) {
      setError("The FDR backend URL is not configured. No layover evaluation was requested.");
      return;
    }
    setBusy(true); setError(""); setResult(null);
    try {
      const evaluated = await evaluateLayover(apiBaseUrl, {
        arrival_at: arrival, departure_at: departure,
        exit_eligibility: eligibility, baggage_recheck_required: baggage,
      });
      setResult(evaluated);
      setPlanResult(null);
      setDisclaimerAcknowledged(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The layover could not be evaluated.");
    } finally { setBusy(false); }
  }

  async function generatePlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiBaseUrl) return;
    setPlanning(true); setPlanResult(null); setError("");
    try {
      const response = await planLayover(apiBaseUrl, {
        arrival_at: arrival, departure_at: departure, exit_eligibility: eligibility,
        baggage_recheck_required: baggage, disclaimer_acknowledged: disclaimerAcknowledged,
        interests: interests.split(",").map((value) => value.trim()).filter(Boolean).slice(0, 8),
      });
      setPlanResult(response);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The layover plan could not be generated.");
    } finally { setPlanning(false); }
  }

  return <AppShell><main className="page-content">
    <PageIntro eyebrow="Make time useful" title="Layover explorer."
      description="Check the conservative time window for a long connection before considering a trip into the city. A long layover does not mean you are allowed to leave the airport." />
    <section className="surface layover-tool" aria-labelledby="layover-form-title">
      <div className="layover-tool-heading"><span className="section-icon"><Clock3 aria-hidden="true" /></span><div><span className="eyebrow">Deterministic estimate</span><h2 id="layover-form-title">Enter your connection times</h2></div></div>
      <p className="muted-copy">Enter airport-local times with their UTC offsets (for example, 2026-10-27T01:00:00+05:30). The backend calculates in UTC. Current flight schedules are not imported automatically.</p>
      <form className="layover-form" onSubmit={submit}>
        <label>Arrival at airport<input type="text" required pattern="\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?[+-]\d{2}:\d{2}" placeholder="2026-10-27T01:00:00+05:30" value={arrival} onChange={(event) => setArrival(event.target.value)} /></label>
        <label>Next departure<input type="text" required pattern="\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?[+-]\d{2}:\d{2}" placeholder="2026-10-27T13:00:00+05:30" value={departure} onChange={(event) => setDeparture(event.target.value)} /></label>
        <label>Airport exit eligibility<select value={eligibility} onChange={(event) => setEligibility(event.target.value as typeof eligibility)}><option value="unknown">Unknown / not verified</option><option value="verified_yes">I have verified I can exit</option><option value="verified_no">I cannot exit</option></select></label>
        <label className="layover-check"><input type="checkbox" checked={baggage} onChange={(event) => setBaggage(event.target.checked)} />Baggage must be collected and re-checked</label>
        <button className="primary-button" type="submit" disabled={busy}>{busy ? "Calculating…" : "Calculate safe window"}</button>
      </form>
      {error && <p className="layover-error" role="alert">{error}</p>}
    </section>

    {result && <section className="surface layover-result" aria-live="polite">
      <div className="layover-result-title"><span className="eyebrow">{result.long_layover ? "Long layover detected" : "Short layover"}</span><h2>{Math.floor(result.layover_minutes / 60)}h {result.layover_minutes % 60}m between flights</h2></div>
      <div className="layover-metrics"><div><span>Conservative time outside airport</span><strong>{Math.floor(result.available_exploration_minutes / 60)}h {result.available_exploration_minutes % 60}m</strong></div><div><span>Latest recommended airport return</span><strong>{formatTimestamp(result.latest_recommended_airport_return_at)}</strong></div></div>
      <div className="layover-warnings"><ShieldAlert aria-hidden="true"/><p>{result.warnings.join(" ")}</p></div>
      {baggage && <div className="layover-warnings"><AlertTriangle aria-hidden="true"/><p>Baggage re-check time is unknown, so the outside window may be overstated. Do not rely on it for a connection.</p></div>}
      <div className="layover-provider-grid">
        <div><MapPin aria-hidden="true"/><strong>Attraction discovery unavailable</strong><span>{result.places_message}</span></div>
        <div><PlaneTakeoff aria-hidden="true"/><strong>Traffic routes unavailable</strong><span>{result.route_message}</span></div>
        <div><AlertTriangle aria-hidden="true"/><strong>Weather unavailable</strong><span>{result.weather_message}</span></div>
      </div>
      <p className="layover-disclaimer">{result.disclaimer}</p>
      {result.long_layover && <form className="layover-plan-form" onSubmit={generatePlan}>
        <h3>Explore this layover</h3>
        <p>Ask Groq to organize verified candidates. It will not be called automatically, and it cannot supply places or travel facts.</p>
        <label>Interests <span>(comma-separated)</span><input type="text" maxLength={240} placeholder="history, food, architecture" value={interests} onChange={(event) => setInterests(event.target.value)} /></label>
        <label className="layover-check"><input type="checkbox" checked={disclaimerAcknowledged} onChange={(event) => setDisclaimerAcknowledged(event.target.checked)} />I understand this is an estimate and will independently confirm immigration, airport, and boarding requirements.</label>
        <button className="primary-button" type="submit" disabled={planning || !disclaimerAcknowledged}>{planning ? "Checking verified candidates…" : "Generate layover plan"}</button>
        {planResult && <div className={`layover-plan-response ${planResult.status === "ready" ? "ready" : "unavailable"}`} role="status">
          <strong>{planResult.status === "ready" ? "Candidate plan ready" : "No plan generated"}</strong>
          <p>{planResult.message ?? (planResult.reason === "verified_candidates_unavailable" ? "Places with verified opening hours and traffic routes are not connected yet. Groq was not called." : `Request status: ${planResult.reason}.`)}</p>
          {planResult.places?.map((place) => <div className="layover-plan-place" key={place.candidate_id}><strong>{place.name}</strong><p>{place.explanation}</p><small>{place.source} · {place.source_status} · cost {place.known_cost_amount == null ? "unavailable" : `${place.known_cost_currency} ${place.known_cost_amount}`}</small></div>)}
          {planResult.disclaimer && <p>{planResult.disclaimer}</p>}
          <small>{planResult.groq_called ? "Groq request recorded." : "No Groq request was made."}</small>
        </div>}
      </form>}
    </section>}
  </main></AppShell>;
}
