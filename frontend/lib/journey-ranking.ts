import type { FlightOffer } from "./flight-api";

export type JourneyGroundAccess = {
  status: "ready" | "partial" | "unavailable" | "blocked" | "error";
  estimated_total_minutes?: number;
  origin_ground_minutes?: number;
  destination_ground_minutes?: number;
  airport_checkin_buffer_minutes?: number;
  estimated_wait_at_departure_airport_minutes?: number;
  estimated_total_known_cost?: number | null;
  unpriced_components?: string[];
  risks?: string[];
};

export type JourneyRanking = "best" | "cheapest" | "fastest" | "fewest-transfers";

export function rankJourneyOffers(
  offers: FlightOffer[],
  groundAccess: Record<string, JourneyGroundAccess | undefined>,
  ranking: JourneyRanking,
): FlightOffer[] {
  const duration = (offer: FlightOffer) => groundAccess[offer.id]?.estimated_total_minutes ?? offer.total_duration_minutes ?? Number.POSITIVE_INFINITY;
  const hasGround = (offer: FlightOffer) => groundAccess[offer.id]?.status === "ready";
  const comparePrice = (left: FlightOffer, right: FlightOffer) => {
    if (left.price == null && right.price != null) return 1;
    if (left.price != null && right.price == null) return -1;
    return (left.price ?? Number.POSITIVE_INFINITY) - (right.price ?? Number.POSITIVE_INFINITY);
  };
  return [...offers].sort((left, right) => {
    if (ranking === "cheapest") return comparePrice(left, right) || (left.stops - right.stops) || duration(left) - duration(right);
    if (ranking === "fastest") {
      if (hasGround(left) !== hasGround(right)) return hasGround(left) ? -1 : 1;
      return duration(left) - duration(right) || comparePrice(left, right);
    }
    if (ranking === "fewest-transfers") {
      return left.stops - right.stops || comparePrice(left, right) || duration(left) - duration(right);
    }

    if (hasGround(left) !== hasGround(right)) return hasGround(left) ? -1 : 1;
    const knownPrices = offers.map((offer) => offer.price).filter((price): price is number => price != null);
    const minPrice = knownPrices.length ? Math.min(...knownPrices) : 0;
    const maxPrice = knownPrices.length ? Math.max(...knownPrices) : 0;
    const knownDurations = offers.map(duration).filter(Number.isFinite);
    const minDuration = knownDurations.length ? Math.min(...knownDurations) : 0;
    const maxDuration = knownDurations.length ? Math.max(...knownDurations) : 0;
    const maxStops = Math.max(...offers.map((offer) => offer.stops), 0);
    const score = (offer: FlightOffer) => {
      const durationScore = maxDuration === minDuration ? 1 : 1 - (duration(offer) - minDuration) / (maxDuration - minDuration);
      const fareScore = offer.price == null ? 0 : maxPrice === minPrice ? 1 : 1 - (offer.price - minPrice) / (maxPrice - minPrice);
      const connectionScore = maxStops === 0 ? 1 : 1 - offer.stops / maxStops;
      return durationScore * 0.55 + fareScore * 0.35 + connectionScore * 0.1;
    };
    return score(right) - score(left) || comparePrice(left, right) || duration(left) - duration(right);
  });
}

export function journeyRankingNote(ranking: JourneyRanking, hasGroundEstimates: boolean): string {
  if (ranking === "cheapest") return "Sorted by known flight fare. Ground transfer costs are not available, so this is not a complete trip cost ranking.";
  if (!hasGroundEstimates) return ranking === "fewest-transfers"
    ? "Sorted by flight connections. Ground access is not included yet."
    : "Provisional flight-only ranking. Estimate airport access to include door-to-door time.";
  if (ranking === "fastest") return "Sorted by estimated door-to-door time, including airport access and the configured check-in buffer.";
  if (ranking === "fewest-transfers") return "Sorted by flight connections. Each journey also includes origin and destination ground legs.";
  return "Balanced ranking uses estimated journey time, known flight fare, and flight connections. Ground fares remain unpriced.";
}
