from app.journeys import calculate_door_to_door_timing


def test_door_to_door_time_includes_origin_buffer_flight_and_destination_transfer():
    timing = calculate_door_to_door_timing(
        origin_ground_minutes=40,
        departure_window_minutes=120,
        flight_elapsed_minutes=240,
        destination_ground_minutes=25,
    )

    assert timing.total_minutes == 385
    assert timing.airport_wait_minutes == 80
    assert timing.feasible_for_scheduled_departure is True


def test_route_that_reaches_airport_after_departure_is_infeasible():
    timing = calculate_door_to_door_timing(
        origin_ground_minutes=130,
        departure_window_minutes=120,
        flight_elapsed_minutes=240,
        destination_ground_minutes=25,
    )

    assert timing.total_minutes is None
    assert timing.feasible_for_scheduled_departure is False
