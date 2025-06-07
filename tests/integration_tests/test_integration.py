"""Integration tests for the club booking system."""

import copy
import json
import os
import sys
from datetime import datetime
from unittest.mock import mock_open

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from server import app, load_clubs, load_competitions
from tests.test_conf import sample_clubs, sample_competitions


@pytest.fixture(name="client")
def flask_test_client():
    """
    Provides a test client for the Flask application.

    :return: A test client for the Flask application.
    :rtype: flask.testing.FlaskClient
    """
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "something_special"
    with app.test_client() as test_client:
        with app.app_context():
            yield test_client


@pytest.fixture(autouse=True)
def setup_test_isolation(mocker):
    """Setup test isolation for integration tests."""
    # Prevent file writes
    mocker.patch("server.save_clubs")
    mocker.patch("server.save_competitions")
    yield


def test_nonexistent_email_error_handling(client, mocker):
    """
    Test that entering a non-existent email shows error message instead of crashing.
    This tests the specific bug fix requirement.
    """
    mocker.patch("server.clubs", sample_clubs()["clubs"])

    response = client.post("/show_summary", data={"email": "nonexistent@test.com"})
    assert response.status_code == 302


def test_load_competitions_integration(mocker):
    """
    Test the complete load_competitions function integration.
    Tests file reading, JSON parsing, date conversion, and canBeBooked logic.

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

    # Test complete integration: file reading + JSON parsing + date logic + sorting
    assert len(competitions) == 3
    assert competitions[0]["name"] == "Competition 1"
    assert competitions[0]["canBeBooked"] is True  # Future date
    assert competitions[1]["canBeBooked"] is False  # Past date
    assert competitions[2]["canBeBooked"] is False  # Past date


def test_load_clubs_integration(mocker):
    """
    Test the complete load_clubs function integration.
    Tests file reading and JSON parsing.

    :param mocker: The mock object provided by pytest-mock.
    :type mocker: pytest_mock.MockerFixture
    """
    mock_json_data = json.dumps({"clubs": [{"name": "Club 1", "points": 10}, {"name": "Club 2", "points": 20}]})

    mocker.patch("builtins.open", mock_open(read_data=mock_json_data))

    clubs = load_clubs()

    # Test complete integration: file reading + JSON parsing
    assert len(clubs) == 2
    assert clubs[0]["name"] == "Club 1"
    assert clubs[0]["points"] == 10


def test_show_summary_integration(client, mocker):
    """
    Test the complete show_summary route integration.
    Tests authentication, data retrieval, and template rendering.

    :param client: The test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    """
    mocker.patch("server.clubs", sample_clubs()["clubs"])
    mocker.patch("server.competitions", sample_competitions()["competitions"])

    # Test login flow (POST)
    response = client.post("/show_summary", data={"email": "club1@test.com"})
    assert response.status_code == 302  # Redirect after login

    # Test authenticated access (GET)
    response = client.get("/show_summary")
    assert response.status_code == 200
    assert b"Welcome, club1@test.com" in response.data
    assert b"Club Points" in response.data

    # Test unauthenticated access
    client.get("/logout")  # Clear session
    response = client.get("/show_summary")
    assert response.status_code == 401


def test_book_page_integration(client, mocker):
    """
    Test the complete book route integration.
    Tests authentication, club/competition lookup, and template rendering.

    :param client: The test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    """
    mocker.patch("server.clubs", sample_clubs()["clubs"])
    mocker.patch("server.competitions", sample_competitions()["competitions"])

    with client.session_transaction() as sess:
        sess["email"] = "club1@test.com"

    # Test valid booking page access
    response = client.get("/book/Comp1/Club1")
    assert response.status_code == 200
    assert b"Comp1" in response.data
    assert b"How many places?" in response.data

    # Test invalid competition
    response = client.get("/book/InvalidComp/Club1")
    assert response.status_code == 400

    # Test invalid club
    response = client.get("/book/Comp1/InvalidClub")
    assert response.status_code == 400


def test_purchase_places_integration(client, mocker):
    """
    Test the complete purchase_places route integration.
    Tests all business rules, validations, and data updates.

    :param client: The test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    """
    clubs_data = copy.deepcopy(sample_clubs()["clubs"])
    competitions_data = copy.deepcopy(sample_competitions()["competitions"])

    mocker.patch("server.clubs", clubs_data)
    mocker.patch("server.competitions", competitions_data)

    with client.session_transaction() as sess:
        sess["email"] = "club1@test.com"

    # Test successful booking
    original_points = int(clubs_data[0]["points"])
    response = client.post("/purchase_places", data={"club": "Club1", "competition": "Comp1", "places": "3"})
    assert response.status_code == 302
    assert int(clubs_data[0]["points"]) == original_points - 3

    # Test insufficient points (Club2 has 4 points)
    with client.session_transaction() as sess:
        sess["email"] = "club2@test.com"

    response = client.post("/purchase_places", data={"club": "Club2", "competition": "Comp1", "places": "10"})
    assert response.status_code == 400

    # Test too many places (>12)
    with client.session_transaction() as sess:
        sess["email"] = "club3@test.com"

    response = client.post("/purchase_places", data={"club": "Club3", "competition": "Comp1", "places": "15"})
    assert response.status_code == 400


def test_display_club_points_integration(client, mocker):
    """
    Test the complete display_club_points route integration.
    Tests authentication and club data display.

    :param client: The test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    """
    mocker.patch("server.clubs", sample_clubs()["clubs"])

    # Test authenticated access
    with client.session_transaction() as sess:
        sess["email"] = "club1@test.com"

    response = client.get("/clubs")
    assert response.status_code == 200
    assert b"Club Points" in response.data
    assert b"Club1" in response.data

    # Test unauthenticated access
    client.get("/logout")  # Clear session
    response = client.get("/clubs")
    assert response.status_code == 401


def test_logout_integration(client):
    """
    Test the complete logout route integration.
    Tests session management and redirection.

    :param client: The test client.
    :type client: flask.testing.FlaskClient
    """
    # Set up authenticated session
    with client.session_transaction() as sess:
        sess["email"] = "club1@test.com"

    # Test logout
    response = client.get("/logout")
    assert response.status_code == 302  # Redirect to index

    # Verify session is cleared
    with client.session_transaction() as sess:
        assert "email" not in sess


def test_index_page_integration(client, mocker):
    """
    Test the complete index route integration.
    Tests form submission with various email scenarios.

    :param client: The test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    """
    mocker.patch("server.clubs", sample_clubs()["clubs"])

    # Test page load
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to the GUDLFT Registration Portal!" in response.data

    # Test valid email submission (handled by show_summary)
    response = client.post("/show_summary", data={"email": "club1@test.com"})
    assert response.status_code == 302

    # Test invalid email
    response = client.post("/show_summary", data={"email": "invalid@email.com"})
    assert response.status_code == 302
    response = client.get("/")  # Follow redirect
    assert b"Email does not exist." in response.data

    # Test empty email
    response = client.post("/show_summary", data={"email": ""})
    assert response.status_code == 302
    response = client.get("/")  # Follow redirect
    assert b"Empty field" in response.data
