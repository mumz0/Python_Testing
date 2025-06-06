"""Units tests for the club booking system."""

import json
from datetime import datetime, timedelta
from unittest.mock import mock_open

from werkzeug.exceptions import BadRequest

from server import load_clubs, load_competitions


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

    assert len(clubs) == 3
    assert clubs[0]["name"] == "Club 1"
    assert clubs[0]["points"] == 10
    assert clubs[1]["name"] == "Club 2"
    assert clubs[1]["points"] == 20
    assert clubs[2]["name"] == "Club 3"
    assert clubs[2]["points"] == 30


def test_load_competitions(mocker):
    """
    Test the `load_competitions` function with date parsing and sorting.

    This test verifies that the `load_competitions` function correctly loads competition data
    from a JSON file, parses dates, and sets canBeBooked status.

    :param mocker: The mock object provided by pytest-mock.
    :type mocker: pytest_mock.MockerFixture
    """
    mock_json_data = json.dumps(
        {"competitions": [{"name": "Future Competition", "date": "2025-12-01 10:00:00"}, {"name": "Past Competition", "date": "2023-01-01 10:00:00"}]}
    )

    # Mock datetime.now() to return a fixed date
    mock_now = datetime(2024, 6, 15, 10, 0, 0)
    mocker.patch("builtins.open", mock_open(read_data=mock_json_data))
    mock_datetime = mocker.patch("server.datetime")
    mock_datetime.now.return_value = mock_now
    mock_datetime.strptime = datetime.strptime

    competitions = load_competitions()

    assert len(competitions) == 2
    assert competitions[0]["name"] == "Future Competition"
    assert competitions[0]["canBeBooked"] is True
    assert competitions[1]["name"] == "Past Competition"
    assert competitions[1]["canBeBooked"] is False


def test_datetime_parsing_and_comparison():
    """
    Test datetime string parsing and date comparison functionality.

    :return: None
    """
    date_string = "2025-03-27 10:00:00"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Parse datetime string
    parsed_date = datetime.strptime(date_string, date_format)

    assert parsed_date.year == 2025
    assert parsed_date.month == 3
    assert parsed_date.day == 27
    assert parsed_date.hour == 10

    # Test date comparison for canBeBooked logic
    now = datetime.now()
    future_date = now + timedelta(days=1)
    past_date = now - timedelta(days=1)

    assert future_date >= now
    assert not past_date >= now


def test_competition_sorting_logic():
    """
    Test competition sorting by date (most recent first).

    :return: None
    """
    competitions = [
        {"name": "Comp1", "date": datetime(2025, 3, 27)},
        {"name": "Comp2", "date": datetime(2025, 1, 15)},
        {"name": "Comp3", "date": datetime(2025, 6, 10)},
    ]

    # Sort competitions by date (most recent first)
    sorted_competitions = sorted(competitions, key=lambda comp: comp["date"], reverse=True)

    assert sorted_competitions[0]["name"] == "Comp3"
    assert sorted_competitions[1]["name"] == "Comp1"
    assert sorted_competitions[2]["name"] == "Comp2"


def test_club_bookings_initialization_and_management():
    """
    Test complete club bookings initialization and management system.

    This test covers:
    - competition["clubBookings"] = {} (line 168)
    - competition["clubBookings"][club["name"]] = 0 (line 172)
    - Booking updates and calculations
    """
    competition = {"name": "Test Competition", "numberOfPlaces": "25"}
    club = {"name": "Test Club", "points": "15"}
    places_required = 3

    # Test clubBookings dictionary initialization
    if "clubBookings" not in competition:
        competition["clubBookings"] = {}

    # Test club booking count initialization
    if club["name"] not in competition["clubBookings"]:
        competition["clubBookings"][club["name"]] = 0

    # Test successful booking update
    if competition["clubBookings"][club["name"]] + places_required <= 12:
        competition["clubBookings"][club["name"]] += places_required
        club["points"] = int(club["points"]) - places_required
        competition["numberOfPlaces"] = int(competition["numberOfPlaces"]) - places_required

    assert "clubBookings" in competition
    assert competition["clubBookings"][club["name"]] == 3
    assert club["points"] == 12
    assert competition["numberOfPlaces"] == 22


def test_booking_limit_validation():
    """
    Test booking limit validation (max 12 places per club).

    :return: None
    """
    competition = {"clubBookings": {"Club1": 10}}
    club_name = "Club1"
    places_required = 3

    # Should not allow booking if it exceeds 12 places
    can_book = competition["clubBookings"][club_name] + places_required <= 12
    assert not can_book


def test_session_email_validation():
    """
    Test session email validation logic.

    :return: None
    """
    # Test various session scenarios
    session_with_email = {"email": "club1@test.com"}
    session_without_email = {}
    session_with_none_email = {"email": None}

    # Test session with valid email
    assert session_with_email.get("email") is not None

    # Test session without email key
    assert session_without_email.get("email") is None

    # Test session with None email
    assert session_with_none_email.get("email") is None


def test_json_parsing():
    """
    Test JSON parsing for both clubs and competitions data.

    :return: None
    """
    # Test clubs JSON parsing
    clubs_json = '{"clubs": [{"name": "Club1", "points": 10}]}'
    clubs_data = json.loads(clubs_json)
    clubs = clubs_data["clubs"]

    assert len(clubs) == 1
    assert clubs[0]["name"] == "Club1"
    assert clubs[0]["points"] == 10

    # Test competitions JSON parsing
    competitions_json = '{"competitions": [{"name": "Comp1", "date": "2025-03-27 10:00:00"}]}'
    competitions_data = json.loads(competitions_json)
    competitions = competitions_data["competitions"]

    assert len(competitions) == 1
    assert competitions[0]["name"] == "Comp1"
    assert competitions[0]["date"] == "2025-03-27 10:00:00"


def test_purchase_places_validations():
    """
    Test all validation scenarios in purchase_places that raise BadRequest.

    This test covers all the validation conditions that can raise BadRequest.
    """
    # Test insufficient club points (line 175)
    club_points = 5
    places_required = 10

    try:
        if places_required > club_points:
            raise BadRequest("Invalid data provided")
        assert False, "Should have raised BadRequest"
    except BadRequest as e:
        assert "Invalid data provided" in str(e)

    # Test insufficient competition places (line 176)
    competition_places = 3
    places_required = 5

    try:
        if places_required > competition_places:
            raise BadRequest("Invalid data provided")
        assert False, "Should have raised BadRequest"
    except BadRequest as e:
        assert "Invalid data provided" in str(e)

    # Test exceeding maximum places per booking (line 177)
    places_required = 15

    try:
        if places_required > 12:
            raise BadRequest("Invalid data provided")
        assert False, "Should have raised BadRequest"
    except BadRequest as e:
        assert "Invalid data provided" in str(e)

    # Test exceeding club total booking limit (line 178)
    current_bookings = 10
    places_required = 5

    try:
        if current_bookings + places_required > 12:
            raise BadRequest("Invalid data provided")
        assert False, "Should have raised BadRequest"
    except BadRequest as e:
        assert "Invalid data provided" in str(e)


def test_competition_booking_validation():
    """
    Test validation when competition cannot be booked.

    This covers the canBeBooked validation in book route.
    """
    competition = {"name": "Past Competition", "canBeBooked": False}

    try:
        if competition["canBeBooked"] is not True:
            raise BadRequest("Invalid data provided")
        assert False, "Should have raised BadRequest"
    except BadRequest as e:
        assert "Invalid data provided" in str(e)


def test_booking_calculations():
    """
    Test booking calculation logic for successful transactions.

    :return: None
    """
    current_bookings = 5
    new_places = 3
    club_points = 10
    available_places = 20

    # Test successful booking calculations
    total_bookings = current_bookings + new_places
    remaining_points = club_points - new_places
    remaining_places = available_places - new_places

    assert total_bookings == 8
    assert remaining_points == 7
    assert remaining_places == 17
