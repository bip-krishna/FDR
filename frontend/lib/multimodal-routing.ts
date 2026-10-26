import type { FlightOffer, GroundAccessEstimate, OptimizationSegment } from "./flight-api";

function cityNode(value: string) {
  return `city:${value.trim().toLocaleLowerCase("en")}`;
}

function addSeconds(timestamp: string, seconds: number) {
  const result = new Date(new Date(timestamp).getTime() + seconds * 1000);
  return Number.isNaN(result.getTime()) ? null : result.toISOString();
}

export function buildOptimizationSegments(
  offers: FlightOffer[],
  accessByOffer: Record<string, GroundAccessEstimate | undefined>,
  origin: string,
  destination: string,
): OptimizationSegment[] {
  const edges: OptimizationSegment[] = [];
  const startCity = cityNode(origin);
  const endCity = cityNode(destination);

  for (const offer of offers) {
    const access = accessByOffer[offer.id];
    const departure = offer.segments[0];
    const arrival = offer.segments.at(-1);
    if (!access || access.status !== "ready" || !access.legs || access.legs.length < 2
      || !offer.origin_code || !offer.destination_code
      || !departure?.departure_at_utc || !arrival?.arrival_at_utc) continue;

    const originDrive = access.legs.find((leg) => leg.kind === "origin_to_departure_airport");
    const destinationDrive = access.legs.find((leg) => leg.kind === "arrival_airport_to_destination");
    if (!originDrive?.departure_time || !destinationDrive?.departure_time) continue;
    const airportArrivalLeadSeconds = (access.airport_checkin_buffer_minutes ?? 120) * 60;
    const originDriveArrival = addSeconds(departure.departure_at_utc, -airportArrivalLeadSeconds);
    const originDriveDeparture = originDriveArrival ? addSeconds(originDriveArrival, -originDrive.duration_seconds) : null;
    const destinationDriveDeparture = addSeconds(arrival.arrival_at_utc, 30 * 60);
    const destinationDriveArrival = destinationDriveDeparture
      ? addSeconds(destinationDriveDeparture, destinationDrive.duration_seconds) : null;
    if (!originDriveArrival || !originDriveDeparture || !destinationDriveDeparture || !destinationDriveArrival) continue;

    edges.push({
      segment_id: `${offer.id}:origin-access`, mode: "ground", origin: startCity,
      destination: `airport:${offer.origin_code.toUpperCase()}`,
      departure_at: originDriveDeparture, arrival_at: originDriveArrival,
      estimate_departure_at: originDrive.departure_time,
      provider: originDrive.provider ?? "Google Maps Routes API", data_status: "estimated",
      fare_amount: null, currency: null, ticket_group_id: null, booking_url: null,
    });
    edges.push({
      segment_id: `${offer.id}:flight`, mode: "flight",
      origin: `airport:${offer.origin_code.toUpperCase()}`,
      destination: `airport:${offer.destination_code.toUpperCase()}`,
      departure_at: departure.departure_at_utc, arrival_at: arrival.arrival_at_utc,
      provider: offer.source, data_status: offer.status,
      fare_amount: offer.price, currency: offer.price == null ? null : offer.currency,
      ticket_group_id: offer.id, booking_url: offer.booking_url,
    });
    edges.push({
      segment_id: `${offer.id}:destination-access`, mode: "ground",
      origin: `airport:${offer.destination_code.toUpperCase()}`, destination: endCity,
      departure_at: destinationDriveDeparture, arrival_at: destinationDriveArrival,
      estimate_departure_at: destinationDrive.departure_time,
      provider: destinationDrive.provider ?? "Google Maps Routes API", data_status: "estimated",
      fare_amount: null, currency: null, ticket_group_id: null, booking_url: null,
    });
  }
  return edges;
}
