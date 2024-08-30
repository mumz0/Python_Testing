"""
Integration test file
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from server import app


@pytest.fixture
def client_generator():
    """
    Provides a Flask test client.

    :return: A Flask test client.
    :rtype: flask.testing.FlaskClient
    """
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "something_special"
    with app.test_client() as client:
        yield client


def sample_clubs():
    """
    Returns a set of simulated data for clubs.

    :return: A dictionary containing information about the clubs.
    :rtype: dict
    """
    clubs = {
        "clubs": [
            {"name": "Club1", "email": "club1@test.com", "points": "13"},
            {"name": "Club2", "email": "club2@test.com", "points": "4"},
            {"name": "Club3", "email": "club3@test.com", "points": "33"},
        ]
    }
    return clubs


def sample_competitions():
    """
    Returns a set of simulated data for competitions.

    :return: A dictionary containing information about the competitions.
    :rtype: dict
    """
    competitions = {
        "competitions": [
            {"name": "Comp1", "date": "2025-03-27 10:00:00", "numberOfPlaces": "25"},
            {"name": "Comp2", "date": "2024-09-27 10:00:00", "numberOfPlaces": "2"},
            {"name": "Comp3", "date": "2023-09-27 10:00:00", "numberOfPlaces": "21"},
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
    assert response.request.path == "/show_summary"
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
    assert response.request.path == "/"
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
    assert response.request.path == "/"
    assert "Email is required" in response_text


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
        session["email"] = clubs["email"]

    response = client.post(
        "/purchase_places", data={"competition": competition["name"], "club": club["name"], "places": places_required}, follow_redirects=True
    )
    response_text = response.data.decode("utf-8")
    assert response.status_code == 200
    assert "Great - booking complete!" in response_text
    assert club["points"] == int(inital_club_points) - places_required
    assert competition["numberOfPlaces"] == int(initial_competition_places) - places_required
