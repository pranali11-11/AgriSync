from datetime import date, timedelta
from types import SimpleNamespace

from app.api.v1.endpoints.resources import coordinates_from_location, is_machine_available, validate_radius


def test_coordinates_are_returned_as_lat_lng():
    assert coordinates_from_location("POINT(73.8567 18.5204)") == {
        "lat": 18.5204,
        "lng": 73.8567,
    }


def test_postgis_wkb_coordinates_are_not_swapped():
    import struct

    wkb = b"\x01\x01\x00\x00\x00" + struct.pack("<dd", 73.8567, 18.5204)
    assert coordinates_from_location(type("Wkb", (), {"data": wkb})()) == {
        "lat": 18.5204,
        "lng": 73.8567,
    }


def test_radius_validation():
    assert validate_radius(10) == 10000
    assert validate_radius(100) == 100000


def test_machine_availability_window_and_full_booking():
    machine = SimpleNamespace(available_from=date.today(), available_to=date.today() + timedelta(days=4))
    assert is_machine_available(machine, date.today())
    assert not is_machine_available(machine, date.today() + timedelta(days=5))
    assert not is_machine_available(machine, date.today(), confirmed_acres=20, capacity=20)
