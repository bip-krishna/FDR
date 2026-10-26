"""Indian Railways reference data and authorized-provider boundary."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Protocol


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIONS_PATH = PROJECT_ROOT / "data" / "rail_stations_2026.csv"
STATION_SOURCE = "Indian Railways Trains at a Glance 2026 — Station Code Index"
STATION_SOURCE_URL = (
    "https://rb.indianrailways.gov.in/uploads/directorate/coaching/"
    "TAG_2026/Station_Code_Index.pdf"
)
STATION_RETRIEVED_ON = date(2026, 10, 26)
NTES_URL = "https://enquiry.indianrail.gov.in/mntes/"
IRCTC_URL = "https://www.irctc.co.in/nget/train-search"


@dataclass(frozen=True)
class Station:
    name: str
    code: str
    source: str = STATION_SOURCE
    retrieved_on: date = STATION_RETRIEVED_ON


class TrainProvider(Protocol):
    """Contract for a provider approved to return current train information."""

    name: str

    async def search(self, origin: Station, destination: Station, journey_date: date) -> list[dict[str, Any]]:
        """Return normalized provider records; implementations must preserve provenance."""


def load_stations() -> list[Station]:
    with STATIONS_PATH.open(encoding="utf-8", newline="") as source:
        return [Station(row["name"], row["code"]) for row in csv.DictReader(source)]


def find_stations(query: str, limit: int = 10) -> list[Station]:
    term = query.strip().casefold()
    if len(term) < 2:
        return []
    stations = load_stations()
    matches = [station for station in stations if station.code.casefold().startswith(term)
               or station.name.casefold().startswith(term)]
    matches.extend(station for station in stations if station not in matches and term in station.name.casefold())
    return matches[:limit]


def normalize_rail_segment(raw: dict[str, Any], *, provider: str, retrieved_at: datetime) -> dict[str, Any]:
    """Normalize an authorized schedule record without implying fare/seat availability."""
    if retrieved_at.tzinfo is None:
        raise ValueError("retrieved_at must include a timezone")
    number = str(raw.get("train_number", "")).strip()
    if not number:
        raise ValueError("train_number is required")
    departure = datetime.fromisoformat(str(raw["departure_time"]).replace("Z", "+00:00"))
    arrival = datetime.fromisoformat(str(raw["arrival_time"]).replace("Z", "+00:00"))
    if departure.tzinfo is None or arrival.tzinfo is None or arrival <= departure:
        raise ValueError("schedule times must be timezone-aware and chronological")
    classes = raw.get("travel_classes", [])
    return {
        "mode": "train",
        "train_number": number,
        "train_name": str(raw.get("train_name", "")).strip() or None,
        "origin_code": str(raw["origin_code"]).upper(),
        "destination_code": str(raw["destination_code"]).upper(),
        "departure_time": departure.isoformat(),
        "arrival_time": arrival.isoformat(),
        "duration_minutes": int((arrival - departure).total_seconds() // 60),
        "travel_classes": sorted({str(item).upper() for item in classes if str(item).strip()}),
        "fare": None,
        "availability": "unavailable",
        "provider": provider,
        "retrieved_at": retrieved_at.astimezone(timezone.utc).isoformat(),
        "data_status": "live",
    }
