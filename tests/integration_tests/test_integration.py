"""
Integration test file
"""

import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from server import app
from tests.test_conf import sample_clubs, sample_competitions


@pytest.fixture(name="client")
def flask_client():
    """
    Provides a Flask test client.

    :return: A Flask test client.
    :rtype: flask.testing.FlaskClient
    """
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "something_special"
    with app.test_client() as test_client:
        yield test_client


def sample_competitions_initial_version():
    """
    Returns a set of simulated data for competitions.

    :return: A dictionary containing information about the competitions.
    :rtype: dict
    """
    competitions = {
        "competitions": [
            {"name": "Comp1", "date": "2020-03-27 10:00:00", "numberOfPlaces": "25"},
            {"name": "Comp2", "date": "2020-10-22 13:30:00", "numberOfPlaces": "2"},
            {"name": "Comp3", "date": "2025-10-22 10:30:00", "numberOfPlaces": "21"},
        ]
    }
    return competitions


def test_index(client):
    """
    Test the home page.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :return: None
    """
    response = client.get("/")
    assert response.status_code == 200


def test_login_valid_email(client, mocker):
    """
    Test the login process with a valid email.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    :param mock_clubs: The mock clubs data.
    :type mock_clubs: list
    :return: None
    """
    clubs = mocker.patch("server.clubs", sample_clubs()["clubs"])
    response = client.post("/show_summary", data={"email": clubs[0]["email"]}, follow_redirects=True)
    redirected_response_text = response.data.decode("utf-8")
    assert response.status_code == 200
    assert clubs[0]["email"] in redirected_response_text


def test_login_invalid_email(client):
    """
    Test the login process with an invalid email.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    :return: None
    """
    data = {"email": "wrong_email@wrongemail.co"}
    response = client.post("/show_summary", data=data, follow_redirects=True)
    response_text = response.data.decode("utf-8")
    assert response.status_code == 200
    assert "Email does not exist." in response_text


def test_login_no_email(client):
    """
    Test the login process when no email is provided.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :return: None
    """
    response = client.post("/show_summary", data={}, follow_redirects=True)
    response_text = response.data.decode("utf-8")
    assert response.status_code == 200
    assert "Email is required" in response_text


def test_get_welcome_page_with_email_in_session(client, mocker):
    """
    Test accessing the welcome page with a valid email in the session.

    This test verifies that the welcome page is accessible and displays the correct
    information when a valid email is present in the session.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    :return: None
    """
    clubs = mocker.patch("server.clubs", sample_clubs()["clubs"])
    with client.session_transaction() as sess:
        sess["email"] = clubs[0]["email"]

    response = client.get("/show_summary")
    assert response.status_code == 200
    assert b"Welcome" in response.data
    assert b"Points available" in response.data


def test_get_welcome_page_without_email_in_session(client):
    """
    Test accessing the welcome page without an email in the session.

    This test verifies that the user is redirected to the home page when no email
    is present in the session.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :return: None
    """
    response = client.get("/show_summary")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_get_welcome_page_with_invalid_email_in_session(client):
    """
    Test accessing the welcome page with an invalid email in the session.

    This test verifies that the user is redirected to the home page when an invalid
    email is present in the session.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :return: None
    """
    with client.session_transaction() as sess:
        sess["email"] = "invalid@example.com"

    response = client.get("/show_summary")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_purchase_success(client, mocker):
    """
    Test the purchase process when it is successful.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    :param mock_clubs: The mock clubs data.
    :type mock_clubs: list
    :param mock_competitions: The mock competitions data.
    :type mock_competitions: list
    :return: None
    """
    clubs = mocker.patch("server.clubs", sample_clubs()["clubs"])
    competitions = mocker.patch("server.competitions", sample_competitions()["competitions"])

    with client.session_transaction() as session:
        session["email"] = clubs[0]["email"]

    response = client.post(
        "/purchase_places", data={"competition": competitions[1]["name"], "club": clubs[0]["name"], "places": 1}, follow_redirects=True
    )
    response_text = response.data.decode("utf-8")
    assert response.status_code == 200
    assert "Great - booking complete!" in response_text


def test_purchase_exceeding_available_places(client, mocker):
    """
    Test the purchase process when attempting to book more places than available.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    :param mock_clubs: The mock clubs data.
    :type mock_clubs: list
    :param mock_competitions: The mock competitions data.
    :type mock_competitions: list
    :return: None
    """
    clubs = mocker.patch("server.clubs", sample_clubs()["clubs"])
    competitions = mocker.patch("server.competitions", sample_competitions()["competitions"])
    competition_places_available = int(competitions[1]["numberOfPlaces"])
    places_purchase = 3
    with client.session_transaction() as session:
        session["email"] = clubs[0]["email"]

    response = client.post(
        "/purchase_places",
        data={"competition": competitions[1]["name"], "club": clubs[0]["name"], "places": places_purchase},
        follow_redirects=True,
    )
    response_text = response.data.decode("utf-8")
    assert response.status_code == 400
    assert places_purchase > competition_places_available
    assert "Invalid data provided" in response_text


def test_purchase_exceeding_club_points(client, mocker):
    """
    Test the purchase process when attempting to book more places than the club has points for.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    :param mock_clubs: The mock clubs data.
    :type mock_clubs: list
    :param mock_competitions: The mock competitions data.
    :type mock_competitions: list
    :return: None
    """
    clubs = mocker.patch("server.clubs", sample_clubs()["clubs"])
    competitions = mocker.patch("server.competitions", sample_competitions()["competitions"])
    club_points = int(clubs[1]["points"])
    places_purchase = 5
    with client.session_transaction() as session:
        session["email"] = clubs[0]["email"]

    response = client.post(
        "/purchase_places", data={"competition": competitions[0]["name"], "club": clubs[1]["name"], "places": places_purchase}, follow_redirects=True
    )
    response_text = response.data.decode("utf-8")
    assert response.status_code == 400
    assert places_purchase > club_points
    assert "Invalid data provided" in response_text


def test_purchase_places_exceeding_maximum_places(client, mocker):
    """
    Test that attempting to purchase more than the maximum allowed places (12) results in a BadRequest.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    :return: None
    """
    mocker.patch("server.clubs", sample_clubs()["clubs"])
    mocker.patch("server.competitions", sample_competitions()["competitions"])
    club_booked_palces = 0
    place_required = 13
    with client.session_transaction() as session:
        session["email"] = "club1@test.com"

    response = client.post("/purchase_places", data={"competition": "Comp1", "club": "Club1", "places": place_required})
    assert response.status_code == 400
    assert club_booked_palces + place_required > 12
    assert b"Invalid data provided" in response.data


def test_deduct_club_points_and_competition_places_after_purchase_process(client, mocker):
    """
    Test the deduction of club points and competition places after a purchase.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    :param mock_clubs: The mock clubs data.
    :type mock_clubs: list
    :param mock_competitions: The mock competitions data.
    :type mock_competitions: list
    :return: None
    """
    clubs = mocker.patch("server.clubs", sample_clubs()["clubs"])
    competitions = mocker.patch("server.competitions", sample_competitions()["competitions"])
    club = clubs[0]
    inital_club_points = club["points"]
    competition = competitions[1]
    initial_competition_places = competition["numberOfPlaces"]
    places_required = 2

    with client.session_transaction() as session:
        session["email"] = club["email"]

    response = client.post(
        "/purchase_places", data={"competition": competition["name"], "club": club["name"], "places": places_required}, follow_redirects=True
    )
    response_text = response.data.decode("utf-8")
    assert response.status_code == 200
    assert "Great - booking complete!" in response_text
    assert club["points"] == int(inital_club_points) - places_required
    assert competition["numberOfPlaces"] == int(initial_competition_places) - places_required


def test_access_without_email_in_session(client, mocker):
    """
    Test that accessing a route without an email in the session raises an Unauthorized exception.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object.
    :type mocker: pytest_mock.MockerFixture
    :return: None
    """
    clubs = mocker.patch("server.clubs", sample_clubs()["clubs"])
    competitions = mocker.patch("server.competitions", sample_competitions()["competitions"])
    places_required = 2

    # No email set in session
    with client.session_transaction() as session:
        session["email"] = None

    response = client.post(
        "/purchase_places", data={"competition": competitions[0]["name"], "club": clubs[0]["name"], "places": places_required}, follow_redirects=True
    )

    # Check for Unauthorized exception
    assert response.status_code == 401
    assert b"You must be connected." in response.data


def test_update_booking_insufficient_points(client, mocker):
    """
    Test the update of a booking when the club has insufficient points.

    This test verifies that the booking is not updated if the club does not
    have enough points to book the required places.

    :return: None
    """
    clubs = mocker.patch("server.clubs", sample_clubs()["clubs"])
    competitions = mocker.patch("server.competitions", sample_competitions()["competitions"])
    places_required = 14

    with client.session_transaction() as session:
        session["email"] = clubs[0]["email"]

    response = client.post(
        "/purchase_places", data={"competition": competitions[0]["name"], "club": clubs[0]["name"], "places": places_required}, follow_redirects=True
    )

    assert response.status_code == 400
    assert int(competitions[0]["clubBookings"][clubs[0]["name"]]) == 0
    assert int(clubs[0]["points"]) == 13
    assert int(competitions[0]["numberOfPlaces"]) == 25


def test_initialize_club_bookings_if_not_present(client, mocker):
    """
    Test the initialization of `clubBookings` if it is not present in the competition.

    This test verifies that the `clubBookings` dictionary is correctly initialized
    for a competition if it is not already present when a club books a place.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object provided by pytest-mock.
    :type mocker: pytest_mock.MockerFixture
    """
    competitions_data = {
        "competitions": [
            {"name": "Comp1", "date": datetime(2025, 3, 27, 10, 0), "numberOfPlaces": "25", "canBeBooked": True},
        ]
    }
    clubs_data = {
        "clubs": [
            {"name": "Club1", "email": "club1@test.com", "points": "13"},
        ]
    }

    # Mock data
    competitions = mocker.patch("server.competitions", competitions_data["competitions"])
    clubs = mocker.patch("server.clubs", clubs_data["clubs"])

    with client.session_transaction() as session:
        session["email"] = "club1@test.com"

    client.post("/purchase_places", data={"competition": competitions[0]["name"], "club": clubs[0]["name"], "places": 1}, follow_redirects=True)

    assert "clubBookings" not in competitions
    assert competitions[0]["clubBookings"] == {"Club1": 1}


def test_initialize_club_bookings_count_if_not_present(client, mocker):
    """
    Test the initialization of the booking count for a specific club if not present in `clubBookings`.

    This test verifies that the booking count for a specific club is correctly initialized
    in the `clubBookings` dictionary of a competition if it is not already present when a club books a place.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mock object provided by pytest-mock.
    :type mocker: pytest_mock.MockerFixture
    """
    competitions = mocker.patch("server.competitions", sample_competitions()["competitions"])
    clubs = mocker.patch("server.clubs", sample_clubs()["clubs"])

    with client.session_transaction() as session:
        session["email"] = "club1@test.com"

    client.post("/purchase_places", data={"competition": competitions[0]["name"], "club": clubs[0]["name"], "places": 1}, follow_redirects=True)

    assert competitions[0]["clubBookings"]["Club1"] == 1
