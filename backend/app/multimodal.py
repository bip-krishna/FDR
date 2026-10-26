"""Bounded, time-dependent itinerary graph for verified travel segments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal


Mode = Literal["flight", "train", "ground"]
DataStatus = Literal["live", "cached", "estimated", "static"]


@dataclass(frozen=True)
class TravelSegment:
    segment_id: str
    mode: Mode
    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    provider: str
    data_status: DataStatus
    estimate_departure_at: datetime | None = None
    fare_amount: Decimal | None = None
    currency: str | None = None
    ticket_group_id: str | None = None
    booking_url: str | None = None


MODE_CHANGE_BUFFER_MINUTES: dict[tuple[Mode, Mode], int] = {
    ("flight", "flight"): 120,
    ("flight", "train"): 90,
    ("flight", "ground"): 30,
    ("train", "flight"): 180,
    ("train", "train"): 45,
    ("train", "ground"): 30,
    ("ground", "flight"): 120,
    ("ground", "train"): 45,
    ("ground", "ground"): 15,
}


def connection_buffer_minutes(previous: TravelSegment, following: TravelSegment) -> int:
    if previous.ticket_group_id and previous.ticket_group_id == following.ticket_group_id:
        return 45 if previous.mode == following.mode == "flight" else 15
    return MODE_CHANGE_BUFFER_MINUTES[(previous.mode, following.mode)]


def validate_segments(segments: list[TravelSegment]) -> None:
    if len(segments) > 120:
        raise ValueError("At most 120 travel segments can be evaluated per request.")
    ids: set[str] = set()
    for segment in segments:
        if not segment.segment_id or segment.segment_id in ids:
            raise ValueError("Segment IDs must be present and unique.")
        ids.add(segment.segment_id)
        if not segment.origin.strip() or not segment.destination.strip() or segment.origin == segment.destination:
            raise ValueError(f"Segment {segment.segment_id} must connect two different named points.")
        if segment.departure_at.tzinfo is None or segment.arrival_at.tzinfo is None:
            raise ValueError(f"Segment {segment.segment_id} needs timezone-aware schedule times.")
        if segment.arrival_at <= segment.departure_at:
            raise ValueError(f"Segment {segment.segment_id} must arrive after it departs.")
        if segment.fare_amount is not None and segment.fare_amount < 0:
            raise ValueError(f"Segment {segment.segment_id} has an invalid negative fare.")
        if segment.fare_amount is not None and not segment.currency:
            raise ValueError(f"Segment {segment.segment_id} has a fare without a currency.")


def _route(path: list[TravelSegment]) -> dict:
    currencies = {segment.currency.upper() for segment in path if segment.fare_amount is not None and segment.currency}
    fully_priced = all(segment.fare_amount is not None and segment.currency for segment in path)
    comparable_currency = next(iter(currencies)) if len(currencies) == 1 else None
    fully_comparable = fully_priced and len(currencies) == 1
    known_fare = sum((segment.fare_amount for segment in path if segment.fare_amount is not None), Decimal(0))
    first, last = path[0], path[-1]
    duration = int((last.arrival_at.astimezone(timezone.utc) - first.departure_at.astimezone(timezone.utc)).total_seconds() // 60)
    risks: list[str] = []
    for previous, following in zip(path, path[1:]):
        if not (previous.ticket_group_id and previous.ticket_group_id == following.ticket_group_id):
            risks.append("This connection may require separate tickets; confirm through-ticket protection and transfer rules.")
        if previous.mode != following.mode:
            risks.append(f"Transfer from {previous.mode} to {following.mode} requires a station or terminal change check.")
    if not fully_comparable:
        risks.append("A complete comparable journey fare is unavailable; at least one fare is missing or currencies differ.")
    if any(segment.data_status in {"cached", "static"} for segment in path):
        risks.append("At least one schedule is cached or static; reconfirm it for the travel date.")
    if any(segment.data_status == "estimated" for segment in path):
        risks.append("Ground transfer times are estimates and can change with conditions.")
    if any(segment.estimate_departure_at and segment.estimate_departure_at.astimezone(timezone.utc)
           != segment.departure_at.astimezone(timezone.utc) for segment in path):
        risks.append("A ground segment's planning time is shifted from its traffic-estimate time to preserve the configured transfer buffer.")
    risks.append("This itinerary is not confirmed bookable; verify every segment with its provider.")
    unique_risks = list(dict.fromkeys(risks))
    return {
        "segment_ids": [segment.segment_id for segment in path],
        "segments": [{
            "id": segment.segment_id, "mode": segment.mode,
            "origin": segment.origin, "destination": segment.destination,
            "departure_at": segment.departure_at.isoformat(), "arrival_at": segment.arrival_at.isoformat(),
            "provider": segment.provider, "data_status": segment.data_status,
            "estimate_departure_at": segment.estimate_departure_at.isoformat() if segment.estimate_departure_at else None,
            "fare_amount": str(segment.fare_amount) if segment.fare_amount is not None else None,
            "currency": segment.currency.upper() if segment.currency else None,
            "booking_url": segment.booking_url,
        } for segment in path],
        "departure_at": first.departure_at.isoformat(),
        "arrival_at": last.arrival_at.isoformat(),
        "duration_minutes": duration,
        "fare_amount": str(known_fare) if fully_comparable else None,
        "known_fare_amount": str(known_fare) if len(currencies) == 1 else None,
        "known_fare_currency": next(iter(currencies)) if len(currencies) == 1 else None,
        "currency": comparable_currency if fully_comparable else None,
        "fare_complete": fully_comparable,
        "confirmed_bookable": False,
        "pareto_efficient": True,
        "risks": unique_risks,
    }


def _dominates(left: dict, right: dict) -> bool:
    if not left["fare_complete"] or not right["fare_complete"] or left["currency"] != right["currency"]:
        return False
    left_fare = Decimal(left["fare_amount"])
    right_fare = Decimal(right["fare_amount"])
    no_worse = left["duration_minutes"] <= right["duration_minutes"] and left_fare <= right_fare
    strictly_better = left["duration_minutes"] < right["duration_minutes"] or left_fare < right_fare
    return no_worse and strictly_better


def optimize_itineraries(
    origin: str,
    destination: str,
    segments: list[TravelSegment],
    *,
    max_segments_per_route: int = 5,
    max_routes: int = 25,
) -> dict:
    """Enumerate feasible time-ordered paths and Pareto-mark comparable ones."""
    validate_segments(segments)
    if not origin.strip() or not destination.strip() or origin.casefold() == destination.casefold():
        raise ValueError("Origin and destination must be different named points.")
    if not 1 <= max_segments_per_route <= 8 or not 1 <= max_routes <= 100:
        raise ValueError("Route bounds are outside the supported range.")

    ordered = sorted(segments, key=lambda item: (item.departure_at.astimezone(timezone.utc), item.segment_id))
    outgoing: dict[str, list[TravelSegment]] = {}
    for segment in ordered:
        outgoing.setdefault(segment.origin.casefold(), []).append(segment)

    routes: list[dict] = []
    explored: set[tuple[str, ...]] = set()
    expanded_paths = 0
    search_truncated = False

    def walk(node: str, path: list[TravelSegment], visited: set[str]) -> None:
        nonlocal expanded_paths, search_truncated
        expanded_paths += 1
        if expanded_paths > 25_000:
            search_truncated = True
            return
        if len(routes) >= max_routes * 8:
            search_truncated = True
            return
        if path and node == destination.casefold():
            identity = tuple(segment.segment_id for segment in path)
            if identity not in explored:
                explored.add(identity)
                routes.append(_route(path))
            return
        if len(path) >= max_segments_per_route:
            return
        for edge in outgoing.get(node, []):
            next_node = edge.destination.casefold()
            if next_node in visited:
                continue
            if path:
                previous = path[-1]
                available = (edge.departure_at.astimezone(timezone.utc) - previous.arrival_at.astimezone(timezone.utc)).total_seconds() / 60
                if available < connection_buffer_minutes(previous, edge):
                    continue
            path.append(edge)
            walk(next_node, path, visited | {next_node})
            path.pop()

    walk(origin.casefold(), [], {origin.casefold()})
    for candidate in routes:
        candidate["pareto_efficient"] = not any(_dominates(other, candidate) for other in routes if other is not candidate)
    routes.sort(key=lambda route: (
        not route["pareto_efficient"], route["duration_minutes"],
        Decimal(route["fare_amount"]) if route["fare_complete"] else Decimal("Infinity"),
    ))
    return {
        "status": "ready" if routes else "unavailable",
        "reason": None if routes else "no_feasible_time_ordered_route",
        "message": "Routes use only the schedule and transfer segments supplied to the optimizer. Missing fares remain unknown; no route is confirmed bookable.",
        "origin": origin,
        "destination": destination,
        "routes": routes[:max_routes],
        "routes_considered": len(routes),
        "pareto_routes": sum(route["pareto_efficient"] for route in routes),
            "search_truncated": search_truncated,
            "search_states_expanded": expanded_paths,
    }
