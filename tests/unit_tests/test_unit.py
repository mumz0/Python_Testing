"""Units tests for the club booking system."""

import json
from datetime import datetime, timedelta
from unittest.mock import mock_open

from server import load_clubs, load_competitions


def test_initialize_club_bookings():
    """
    Test the initialization of club bookings when 'clubBookings' is not present.

    This test verifies that the 'clubBookings' key is added to the competition
    dictionary and that the club's booking count is initialized to 0 if it is not
    already present.

    :return: None
    """
    competition = {"name": "Comp1", "numberOfPlaces": "25"}
    club = {"name": "Club1", "points": "13"}

    if "clubBookings" not in competition:
        competition["clubBookings"] = {}

    if club["name"] not in competition["clubBookings"]:
        competition["clubBookings"][club["name"]] = 0

    # Test initialization when 'clubBookings' is not present
    assert "clubBookings" in competition
    assert competition["clubBookings"][club["name"]] == 0


def test_club_booking_already_exists():
    """
    Test the scenario where 'clubBookings' and the club are already present.

    This test verifies that the club's booking count remains unchanged if it is
    already present in the 'clubBookings' dictionary of the competition.

    :return: None
    """
    club = {"name": "Club1", "points": "13"}
    competition = {"name": "Comp1", "numberOfPlaces": "25", "clubBookings": {club["name"]: 5}}

    # Test when 'clubBookings' and club are already present
    competition["clubBookings"][club["name"]] = 5
    assert competition["clubBookings"][club["name"]] == 5


def test_update_booking_success():
    """
    Test the successful update of a booking.

    This test verifies that the booking is updated correctly when the club has
    sufficient points and the total bookings do not exceed the limit.

    :return: None
    """
    competition = {"name": "Competition1", "numberOfPlaces": "25", "clubBookings": {"Club1": 5}}
    club = {"name": "Club1", "email": "club1@example.com", "points": "15"}
    places_required = 5

    if competition["clubBookings"][club["name"]] + places_required <= 12:
        competition["clubBookings"][club["name"]] += places_required
        club["points"] = int(club["points"]) - places_required
        competition["numberOfPlaces"] = int(competition["numberOfPlaces"]) - places_required

    assert competition["clubBookings"]["Club1"] == 10
    assert club["points"] == 10
    assert competition["numberOfPlaces"] == 20


def test_update_booking_exceeds_limit():
    """
    Test the update of a booking when it exceeds the limit.

    This test verifies that the booking is not updated if the total bookings
    exceed the limit of 12 places per club.

    :return: None
    """
    competition = {"name": "Competition1", "numberOfPlaces": "25", "clubBookings": {"Club1": 10}}
    club = {"name": "Club1", "email": "club1@example.com", "points": "15"}
    places_required = 3

    if competition["clubBookings"][club["name"]] + places_required <= 12:
        competition["clubBookings"][club["name"]] += places_required
        club["points"] = int(club["points"]) - places_required
        competition["numberOfPlaces"] = int(competition["numberOfPlaces"]) - places_required

    assert competition["clubBookings"]["Club1"] == 10
    assert int(club["points"]) == 15
    assert int(competition["numberOfPlaces"]) == 25


def test_should_transform_date_str_into_datetime():
    """
    Test that a date string is correctly transformed into a datetime object.

    :return: Assertion of successful date conversion.
    :rtype: datetime
    """
    date_format = "%Y-%m-%d %H:%M:%S"
    date_str = "2024-08-17 10:00:00"
    assert datetime.strptime(date_str, date_format)


def test_competition_can_be_booked_future_date():
    """
    Test that 'canBeBooked' is True when the competition date is in the future.

    This test verifies that the 'canBeBooked' key is set to True if the competition
    date is later than the current date and time.

    :return: None
    """
    now = datetime.now()
    future_date = now + timedelta(days=1)
    competition = {"date": future_date}

    competition["canBeBooked"] = competition["date"] >= now

    assert competition["canBeBooked"] is True


def test_competition_can_be_booked_past_date():
    """
    Test that 'canBeBooked' is False when the competition date is in the past.

    This test verifies that the 'canBeBooked' key is set to False if the competition
    date is earlier than the current date and time.

    :return: None
    """
    now = datetime.now()
    past_date = now - timedelta(days=1)
    competition = {"date": past_date}

    competition["canBeBooked"] = competition["date"] >= now

    assert competition["canBeBooked"] is False


def test_load_competitions(mocker):
    """
    Test the `load_competitions` function.

    This test verifies that the `load_competitions` function correctly loads competition data
    from a JSON file and determines if each competition can be booked based on the current date.

    :param mocker: The mock object provided by pytest-mock.
    :type mocker: pytest_mock.MockerFixture
    """
    mock_json_data = json.dumps(
        {
            "competitions": [
                {"name": "Competition 1", "date": "2025-12-01 10:00:00"},
                {"name": "Competition 2", "date": "2024-11-01 10:00:00"},
                {"name": "Competition 3", "date": "2023-10-01 10:00:00"},
            ]
        }
    )

    mock_now = datetime(2024, 11, 15, 10, 0, 0)

    mocker.patch("builtins.open", mock_open(read_data=mock_json_data))
    mock_datetime = mocker.patch("server.datetime")
    mock_datetime.now.return_value = mock_now
    mock_datetime.strptime = datetime.strptime

    competitions = load_competitions()

    assert competitions[0]["name"] == "Competition 1"
    assert competitions[1]["name"] == "Competition 2"
    assert competitions[2]["name"] == "Competition 3"

    assert competitions[0]["canBeBooked"] is True
    assert competitions[1]["canBeBooked"] is False
    assert competitions[2]["canBeBooked"] is False


def test_load_clubs(mocker):
    """
    Test the `load_clubs` function.

    This test verifies that the `load_clubs` function correctly loads club data
    from a JSON file.

    :param mocker: The mock object provided by pytest-mock.
    :type mocker: pytest_mock.MockerFixture
    """
    mock_json_data = json.dumps({"clubs": [{"name": "Club 1", "points": 10}, {"name": "Club 2", "points": 20}, {"name": "Club 3", "points": 30}]})

    mocker.patch("builtins.open", mock_open(read_data=mock_json_data))

    clubs = load_clubs()

    assert clubs[0]["name"] == "Club 1"
    assert clubs[0]["points"] == 10
    assert clubs[1]["name"] == "Club 2"
    assert clubs[1]["points"] == 20
    assert clubs[2]["name"] == "Club 3"
    assert clubs[2]["points"] == 30
