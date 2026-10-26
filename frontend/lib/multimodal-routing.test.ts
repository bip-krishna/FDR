import { describe, expect, it } from "vitest";
import type { FlightOffer, GroundAccessEstimate } from "./flight-api";
import { buildOptimizationSegments } from "./multimodal-routing";

const offer: FlightOffer = {
  id: "offer-1",
  origin_airport: "Delhi Airport", origin_code: "DEL", destination_airport: "Mumbai Airport", destination_code: "BOM",
  segments: [{ airline: "Air Example", flight_number: "EX1", departure_airport: "Delhi Airport", departure_code: "DEL",
    departure_local_time: "2027-01-01 08:00", departure_at_utc: "2027-01-01T02:30:00Z",
    arrival_airport: "Mumbai Airport", arrival_code: "BOM", arrival_local_time: "2027-01-01 10:00",
    arrival_at_utc: "2027-01-01T04:30:00Z", duration_minutes: 120, aircraft: null, travel_class: "Economy" }],
  stops: 0, layovers: [], total_duration_minutes: 120, price: 5000, currency: "INR", airlines: ["Air Example"],
  booking_url: "https://www.google.com/travel/flights", source: "SerpApi Google Flights", status: "live",
  retrieved_at: "2026-10-26T00:00:00Z", provider_created_at: null, fare_note: "Provider fare.",
};

const access: GroundAccessEstimate = {
  status: "ready", airport_checkin_buffer_minutes: 120,
  legs: [
    { kind: "origin_to_departure_airport", distance_meters: 12000, duration_seconds: 1800,
      static_duration_seconds: 1500, encoded_polyline: "", retrieved_at: "2026-10-26T00:00:00Z",
      departure_time: "2027-01-01T00:00:00Z", provider: "Google Maps Routes API" },
    { kind: "arrival_airport_to_destination", distance_meters: 15000, duration_seconds: 2400,
      static_duration_seconds: 2100, encoded_polyline: "", retrieved_at: "2026-10-26T00:00:00Z",
      departure_time: "2027-01-01T04:30:00Z", provider: "Google Maps Routes API" },
  ],
};

describe("multimodal route graph input", () => {
  it("converts a sourced flight and its two estimated access legs into time-aware edges", () => {
    const segments = buildOptimizationSegments([offer], { [offer.id]: access }, "New Delhi", "Mumbai");
    expect(segments).toHaveLength(3);
    expect(segments.map((segment) => segment.mode)).toEqual(["ground", "flight", "ground"]);
    expect(segments[0].origin).toBe("city:new delhi");
    expect(segments[0].destination).toBe("airport:DEL");
    expect(segments[0].arrival_at).toBe("2027-01-01T00:30:00.000Z");
    expect(segments[1].departure_at).toBe("2027-01-01T02:30:00Z");
    expect(segments[1].fare_amount).toBe(5000);
    expect(segments[2].destination).toBe("city:mumbai");
  });

  it("does not build routes from flight offers without unambiguous UTC times or ready access estimates", () => {
    expect(buildOptimizationSegments([offer], {}, "Delhi", "Mumbai")).toEqual([]);
    const noUtc: FlightOffer = { ...offer, segments: [{ ...offer.segments[0], departure_at_utc: null }] };
    expect(buildOptimizationSegments([noUtc], { [offer.id]: access }, "Delhi", "Mumbai")).toEqual([]);
  });
});
