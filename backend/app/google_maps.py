import hashlib
import json
import re
from datetime import datetime, timezone

import httpx


class MapsProviderError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def fingerprint(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


async def geocode(address: str, api_key: str, timeout: float) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get("https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": address, "key": api_key})
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "OK" or not data.get("results"):
        raise MapsProviderError("geocoding_no_match" if data.get("status") == "ZERO_RESULTS" else "geocoding_unavailable")
    result = data["results"][0]
    location = result["geometry"]["location"]
    return {"latitude": float(location["lat"]), "longitude": float(location["lng"]),
            "formatted_address": result.get("formatted_address", address)}


async def compute_route(origin: dict, destination: dict, departure_time: datetime,
                        api_key: str, timeout: float) -> dict:
    body = {
        "origin": {"location": {"latLng": {"latitude": origin["latitude"], "longitude": origin["longitude"]}}},
        "destination": {"location": {"latLng": {"latitude": destination["latitude"], "longitude": destination["longitude"]}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "departureTime": departure_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "polylineEncoding": "ENCODED_POLYLINE",
        "polylineQuality": "OVERVIEW",
        "units": "METRIC",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post("https://routes.googleapis.com/directions/v2:computeRoutes",
            headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask":
                "routes.distanceMeters,routes.duration,routes.staticDuration,routes.polyline.encodedPolyline"},
            json=body)
    response.raise_for_status()
    routes = response.json().get("routes") or []
    if not routes:
        raise MapsProviderError("route_unavailable")
    route = routes[0]
    def seconds(value: str) -> int:
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)s", value)
        if not match:
            raise MapsProviderError("invalid_route_duration")
        return round(float(match.group(1)))
    polyline = route.get("polyline", {}).get("encodedPolyline")
    if not polyline:
        raise MapsProviderError("route_geometry_unavailable")
    return {"distance_meters": int(route["distanceMeters"]),
        "duration_seconds": seconds(route["duration"]),
        "static_duration_seconds": seconds(route["staticDuration"]),
        "encoded_polyline": polyline}
