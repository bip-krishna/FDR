from dataclasses import dataclass


@dataclass(frozen=True)
class JourneyTiming:
    total_minutes: int | None
    airport_wait_minutes: int
    feasible_for_scheduled_departure: bool


def calculate_door_to_door_timing(origin_ground_minutes: int, departure_window_minutes: int,
                                  flight_elapsed_minutes: int, destination_ground_minutes: int) -> JourneyTiming:
    """Combine access, scheduled flight elapsed time, and destination access."""
    feasible = origin_ground_minutes <= departure_window_minutes
    total = (max(origin_ground_minutes, departure_window_minutes) + flight_elapsed_minutes
             + destination_ground_minutes) if feasible else None
    wait = max(0, departure_window_minutes - origin_ground_minutes)
    return JourneyTiming(total_minutes=total, airport_wait_minutes=wait,
                         feasible_for_scheduled_departure=feasible)
