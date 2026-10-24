"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowDownUp, CalendarDays, Check, Clock3, Info, MapPin, Plane, Search, ShieldCheck, TrainFront, WalletCards } from "lucide-react";
import { AppShell, PageIntro } from "./components/app-shell";
import { validateSearch, type SearchValidationErrors, type TripType } from "../lib/search-validation";

function localDateString(date: Date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

export default function Home() {
  const router = useRouter();
  const [tripType, setTripType] = useState<TripType>("round");
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [departureDate, setDepartureDate] = useState("");
  const [returnDate, setReturnDate] = useState("");
  const [passengers, setPassengers] = useState("1");
  const [travelClass, setTravelClass] = useState("economy");
  const [nearbyAirports, setNearbyAirports] = useState(true);
  const [includeRail, setIncludeRail] = useState(false);
  const [budget, setBudget] = useState("");
  const [maxDuration, setMaxDuration] = useState("");
  const [errors, setErrors] = useState<SearchValidationErrors>({});
  const [status, setStatus] = useState<"idle" | "checking">("idle");

  function validate() {
    const next = validateSearch({ origin, destination, departureDate, returnDate, tripType, budget, maxDuration }, localDateString(new Date()));
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!validate()) {
      setStatus("idle");
      return;
    }
    setStatus("checking");
    const params = new URLSearchParams({
      origin: origin.trim(),
      destination: destination.trim(),
      departure: departureDate,
      tripType,
      passengers,
      travelClass,
      nearbyAirports: String(nearbyAirports),
      includeRail: String(includeRail),
    });
    if (tripType === "round" && returnDate) params.set("return", returnDate);
    if (budget) params.set("budget", budget);
    if (maxDuration) params.set("maxDuration", maxDuration);
    await new Promise((resolve) => window.setTimeout(resolve, 260));
    router.push(`/results?${params.toString()}`);
  }

  function swapLocations() {
    setOrigin(destination);
    setDestination(origin);
    setErrors((current) => ({ ...current, origin: undefined, destination: undefined }));
  }

  return (
    <AppShell>
      <main className="page-content">
        <PageIntro
          eyebrow="Plan a better journey"
          title="Travel, from door to door."
          description="Compare the whole trip, including airport access, transfers, and alternative routes. Start with the places that matter to you."
        />

        <div className="search-layout">
          <section className="surface search-card" aria-labelledby="search-heading">
            <div className="card-heading">
              <div><h2 id="search-heading" className="card-heading-title">Build your search</h2><span className="card-heading-note">Choose your journey details</span></div>
              <span className="stage-label"><Plane aria-hidden="true" /> Search setup</span>
            </div>

            <form className="form-body" onSubmit={handleSubmit} noValidate>
              <div className="trip-toggle" role="group" aria-label="Trip type">
                <button type="button" className={tripType === "round" ? "selected" : ""} aria-pressed={tripType === "round"} onClick={() => setTripType("round")}>Round trip</button>
                <button type="button" className={tripType === "one-way" ? "selected" : ""} aria-pressed={tripType === "one-way"} onClick={() => setTripType("one-way")}>One way</button>
              </div>

              <div className="trip-row">
                <label className="field">
                  <span className="field-label">From</span>
                  <span className="field-input-wrap">
                    <MapPin className="field-icon" aria-hidden="true" />
                    <input className="field-input" type="text" autoComplete="off" placeholder="City or location" value={origin} onChange={(event) => { setOrigin(event.target.value); setErrors((current) => ({ ...current, origin: undefined })); }} aria-invalid={Boolean(errors.origin)} aria-describedby={errors.origin ? "origin-error" : undefined} />
                  </span>
                  {errors.origin && <span id="origin-error" className="field-error">{errors.origin}</span>}
                </label>

                <button className="swap-button" type="button" aria-label="Swap origin and destination" onClick={swapLocations}><ArrowDownUp aria-hidden="true" /></button>

                <label className="field">
                  <span className="field-label">To</span>
                  <span className="field-input-wrap">
                    <MapPin className="field-icon" aria-hidden="true" />
                    <input className="field-input" type="text" autoComplete="off" placeholder="City or location" value={destination} onChange={(event) => { setDestination(event.target.value); setErrors((current) => ({ ...current, destination: undefined })); }} aria-invalid={Boolean(errors.destination)} aria-describedby={errors.destination ? "destination-error" : undefined} />
                  </span>
                  {errors.destination && <span id="destination-error" className="field-error">{errors.destination}</span>}
                </label>
              </div>

              <div className={tripType === "one-way" ? "date-row single" : "date-row"}>
                <label className="field">
                  <span className="field-label">Departure</span>
                    <input className="field-input date-input" type="date" value={departureDate} onChange={(event) => { setDepartureDate(event.target.value); setErrors((current) => ({ ...current, date: undefined })); }} aria-invalid={Boolean(errors.date)} aria-describedby={errors.date ? "date-error" : undefined} />
                  {errors.date && <span id="date-error" className="field-error">{errors.date}</span>}
                </label>
                {tripType === "round" && <label className="field">
                  <span className="field-label">Return</span>
                  <input className="field-input date-input" type="date" min={departureDate || undefined} value={returnDate} onChange={(event) => { setReturnDate(event.target.value); setErrors((current) => ({ ...current, returnDate: undefined })); }} aria-invalid={Boolean(errors.returnDate)} aria-describedby={errors.returnDate ? "return-date-error" : undefined} />
                  {errors.returnDate && <span id="return-date-error" className="field-error">{errors.returnDate}</span>}
                </label>}
                <label className="field">
                  <span className="field-label">Passengers</span>
                  <select className="field-input select-input" value={passengers} onChange={(event) => setPassengers(event.target.value)} aria-label="Number of passengers">
                    {Array.from({ length: 9 }, (_, index) => <option key={index + 1} value={index + 1}>{index + 1} {index === 0 ? "traveller" : "travellers"}</option>)}
                  </select>
                </label>
              </div>

              <div className="options-row">
                <label className="field">
                  <span className="field-label">Travel class</span>
                  <select className="field-input select-input" value={travelClass} onChange={(event) => setTravelClass(event.target.value)}>
                    <option value="economy">Economy</option><option value="premium-economy">Premium economy</option><option value="business">Business</option><option value="first">First class</option>
                  </select>
                </label>
                <div className="field"><span className="field-label">Search type</span><div className="field-input-wrap"><span className="field-input" style={{ display: "flex", alignItems: "center", gap: 8, paddingLeft: 12, color: "#6f6f6f", fontSize: 11 }}><Search className="preference-icon" aria-hidden="true" /> Door-to-door comparison</span></div></div>
              </div>

              <div className="form-divider" />
              <div className="preferences-header"><h3 className="preferences-title">Journey preferences</h3><span className="preferences-hint">Refine the routes we look for</span></div>
              <div className="preference-list">
                <label className="preference"><input type="checkbox" checked={nearbyAirports} onChange={(event) => setNearbyAirports(event.target.checked)} /><Plane className="preference-icon" aria-hidden="true" />Consider nearby airports</label>
                <label className="preference"><input type="checkbox" checked={includeRail} onChange={(event) => setIncludeRail(event.target.checked)} /><TrainFront className="preference-icon" aria-hidden="true" />Include rail connections</label>
              </div>

              <div className="optional-row">
                <label className="field"><span className="field-label">Maximum budget <span style={{ color: "#858585", fontWeight: 400 }}>· optional</span></span><span className="field-input-wrap"><WalletCards className="field-icon" aria-hidden="true" /><input className="field-input compact-input" type="number" min="0" inputMode="numeric" placeholder="INR per traveller" value={budget} onChange={(event) => setBudget(event.target.value)} aria-invalid={Boolean(errors.budget)} aria-describedby={errors.budget ? "budget-error" : undefined} /></span>{errors.budget && <span id="budget-error" className="field-error">{errors.budget}</span>}</label>
                <label className="field"><span className="field-label">Journey time limit <span style={{ color: "#858585", fontWeight: 400 }}>· optional</span></span><span className="field-input-wrap"><Clock3 className="field-icon" aria-hidden="true" /><input className="field-input compact-input" type="number" min="1" max="96" inputMode="numeric" placeholder="Hours, end to end" value={maxDuration} onChange={(event) => setMaxDuration(event.target.value)} aria-invalid={Boolean(errors.maxDuration)} aria-describedby={errors.maxDuration ? "duration-error" : undefined} /></span>{errors.maxDuration && <span id="duration-error" className="field-error">{errors.maxDuration}</span>}</label>
              </div>

              <div className="form-footer">
                <span className="form-note"><ShieldCheck aria-hidden="true" />No fares will be shown until a live provider is connected.</span>
                <button className="search-button" type="submit" disabled={status === "checking"}>{status === "checking" ? <><Clock3 aria-hidden="true" />Preparing search…</> : <><Search aria-hidden="true" />Search journeys</>}</button>
              </div>

              {Object.keys(errors).length > 0 && <div className="error-banner" role="alert"><AlertCircle size={14} style={{ display: "inline", verticalAlign: "-3px", marginRight: 6 }} />Review the highlighted details before searching.</div>}
            </form>
          </section>

          <aside className="side-stack" aria-label="Search information">
            <section className="surface side-card">
              <div className="side-title-row"><span className="side-title-icon"><RouteIcon /></span><h2 className="side-title">A fuller view of the trip</h2></div>
              <p className="side-copy">A lower fare does not always mean a better journey. FDR is designed to consider the parts before and after the flight, too.</p>
              <ul className="coverage-list">
                <li className="coverage-item"><Check aria-hidden="true" />Ground access time to airports and stations</li>
                <li className="coverage-item"><Check aria-hidden="true" />Alternative airports around your destination</li>
                <li className="coverage-item"><Check aria-hidden="true" />Connection buffers and transfer risks</li>
                <li className="coverage-item"><Check aria-hidden="true" />Source and retrieval time for travel data</li>
              </ul>
              <div className="coverage-foot">Coverage will depend on provider access and the routes actually checked.</div>
            </section>

            <section className="surface side-card">
              <div className="side-title-row"><span className="side-title-icon"><Info aria-hidden="true" /></span><h2 className="side-title">Search status</h2></div>
              <p className="side-copy">The search form is ready. Live flights, railway options, and ground routes will be added in later stages.</p>
              <div className="coverage-foot"><span className="stage-label"><Check aria-hidden="true" />No sample fares</span></div>
            </section>
          </aside>
        </div>

        <section className="results-area" aria-live="polite" aria-atomic="true">
          {status === "checking" && <div className="empty-results"><span className="empty-icon"><Clock3 aria-hidden="true" /></span><div><h3>Preparing your search</h3><p>Checking the details you entered. No provider request is made in this stage.</p></div></div>}
          {status === "idle" && <div className="results-summary"><CalendarDays aria-hidden="true" /><span>Search results will appear here when live travel data is available.</span></div>}
        </section>
      </main>
    </AppShell>
  );
}

function RouteIcon() {
  return <Plane size={16} aria-hidden="true" />;
}
