import { describe, expect, it } from "vitest";
import type { FlightOffer } from "./flight-api";
import { rankJourneyOffers } from "./journey-ranking";

function offer(id: string, price: number | null, minutes: number | null, stops: number): FlightOffer {
  return {
    id, origin_airport: "Origin Airport", origin_code: "AAA", destination_airport: "Destination Airport",
    destination_code: "BBB", segments: [], stops, layovers: [], total_duration_minutes: minutes,
    price, currency: "INR", airlines: [], booking_url: null, source: "SerpApi",
    status: "live", retrieved_at: "2026-10-25T00:00:00Z", provider_created_at: null, fare_note: "Provider fare",
  };
}

describe("journey ranking", () => {
  const offers = [offer("slow", 5000, 300, 1), offer("fast", 8000, 100, 0), offer("unknown", null, 150, 0)];

  it("sorts cheapest by known fares and keeps missing prices last", () => {
    expect(rankJourneyOffers(offers, {}, "cheapest").map((item) => item.id)).toEqual(["slow", "fast", "unknown"]);
  });

  it("sorts fastest by flight duration when no ground estimates exist", () => {
    expect(rankJourneyOffers(offers, {}, "fastest").map((item) => item.id)).toEqual(["fast", "unknown", "slow"]);
  });

  it("uses complete door-to-door durations ahead of flight-only durations", () => {
    const access = { slow: { status: "ready" as const, estimated_total_minutes: 330 } };
    expect(rankJourneyOffers(offers, access, "fastest").map((item) => item.id)).toEqual(["slow", "fast", "unknown"]);
  });

  it("ranks fewest flight connections first", () => {
    expect(rankJourneyOffers(offers, {}, "fewest-transfers").map((item) => item.id)).toEqual(["fast", "unknown", "slow"]);
  });

  it("keeps fully timed itineraries ahead of flight-only entries in the balanced ranking", () => {
    const access = { slow: { status: "ready" as const, estimated_total_minutes: 330 } };
    expect(rankJourneyOffers(offers, access, "best")[0].id).toBe("slow");
  });

  it("places an access route that misses departure after feasible offers", () => {
    const access = { fast: { status: "infeasible" as const } };
    expect(rankJourneyOffers(offers, access, "fastest").at(-1)?.id).toBe("fast");
  });
});
