"""
Integration test file
"""

import os
import sys

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
    assert "Empty field" in response_text


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
    assert response.status_code == 401


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
    assert response.status_code == 401


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
    assert b"Unauthorized" in response.data


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

    competitions = mocker.patch("server.competitions", sample_competitions()["competitions"])
    clubs = mocker.patch("server.clubs", sample_clubs()["clubs"])

    with client.session_transaction() as session:
        session["email"] = "club1@test.com"

    client.post("/purchase_places", data={"competition": competitions[2]["name"], "club": clubs[0]["name"], "places": 1}, follow_redirects=True)

    assert "clubBookings" not in competitions
    assert competitions[2]["clubBookings"] == {"Club1": 1}


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


def test_display_club_points_authenticated(client, mocker):
    """
    Test that the clubs page is rendered correctly when the user is authenticated.

    This test mocks the club data and simulates a logged-in user session.
    It then sends a GET request to the `/clubs` route and checks:

    - The HTTP response status code is 200 (OK).
    - The names of the clubs are present in the rendered HTML.

    :param client: The Flask test client used to simulate requests.
    :type client: flask.testing.FlaskClient
    :param mocker: The pytest mock object used for patching functions and variables.
    :type mocker: pytest_mock.MockerFixture
    """
    # Mock club data
    clubs = [
        {"name": "Club1", "points": 20},
        {"name": "Club2", "points": 30},
    ]
    mocker.patch("server.clubs", clubs)

    # Simulate a session with a logged-in user
    with client.session_transaction() as session:
        session["email"] = "club1@test.com"

    response = client.get("/clubs")

    assert response.status_code == 200
    assert b"Club1" in response.data
    assert b"Club2" in response.data


def test_display_club_points_unauthenticated(client):
    """
    Test that an unauthenticated user is redirected to the index page.

    This test sends a GET request to the `/clubs` route without a logged-in user session.
    It checks:

    - The HTTP response status code is 200 after the redirect.
    - A flash message is displayed informing the user they must be logged in.
    - The redirect leads to the index page.

    :param client: The Flask test client used to simulate requests.
    :type client: flask.testing.FlaskClient
    """

    response = client.get("/clubs", follow_redirects=True)

    assert response.status_code == 401


def test_book_success(client, mocker):
    """
    Test the booking process when the user is successfully logged in.

    This test verifies that a user who is logged in can successfully book a competition
    for a club and that the response contains the expected competition name.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mocker fixture used for mocking dependencies.
    :type mocker: pytest_mock.mocker.MockerFixture
    :return: None
    """
    mocker.patch("server.competitions", sample_competitions()["competitions"])
    mocker.patch("server.clubs", sample_clubs()["clubs"])

    with client.session_transaction() as sess:
        sess["email"] = "club1@test.com"

    response = client.get("/book/Comp1/Club1")

    assert response.status_code == 200
    assert b"Comp1" in response.data


def test_book_not_connected(client, mocker):
    """
    Test the booking process when the user is not logged in.

    This test verifies that a user who is not logged in receives an authentication error
    when trying to book a competition for a club, and that the response contains the
    appropriate error message.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mocker fixture used for mocking dependencies.
    :type mocker: pytest_mock.mocker.MockerFixture
    :return: None
    """
    mocker.patch("server.competitions", sample_competitions()["competitions"])
    mocker.patch("server.clubs", sample_clubs()["clubs"])

    response = client.get("/book/Comp1/Club1")

    assert response.status_code == 401
    assert b"You must be connected." in response.data


def test_book_invalid_club(client, mocker):
    """
    Test the booking process with an invalid club name.

    This test verifies that when a logged-in user attempts to book a competition for a
    non-existent club, the response contains a 400 Bad Request status code.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mocker fixture used for mocking dependencies.
    :type mocker: pytest_mock.mocker.MockerFixture
    :return: None
    """
    mocker.patch("server.competitions", sample_competitions()["competitions"])
    mocker.patch("server.clubs", sample_clubs()["clubs"])

    with client.session_transaction() as sess:
        sess["email"] = "club1@test.com"

    response = client.get("/book/Comp1/UnknownClub")

    assert response.status_code == 400


def test_book_invalid_competition(client, mocker):
    """
    Test the booking process with an invalid competition name.

    This test verifies that when a logged-in user attempts to book a non-existent
    competition for a valid club, the response contains a 400 Bad Request status code.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mocker fixture used for mocking dependencies.
    :type mocker: pytest_mock.mocker.MockerFixture
    :return: None
    """
    mocker.patch("server.competitions", sample_competitions()["competitions"])
    mocker.patch("server.clubs", sample_clubs()["clubs"])

    with client.session_transaction() as sess:
        sess["email"] = "club1@test.com"

    response = client.get("/book/UnknownComp/Club1")

    assert response.status_code == 400


def test_book_competition_past_date(client, mocker):
    """
    Test the booking process for a competition with a past date.

    This test verifies that when a logged-in user attempts to book a competition that
    has already passed, the response contains a 400 Bad Request status code.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :param mocker: The mocker fixture used for mocking dependencies.
    :type mocker: pytest_mock.mocker.MockerFixture
    :return: None
    """
    mocker.patch("server.competitions", sample_competitions()["competitions"])
    mocker.patch("server.clubs", sample_clubs()["clubs"])

    with client.session_transaction() as sess:
        sess["email"] = "club1@test.com"

    response = client.get("/book/Comp3/Club1")

    assert response.status_code == 400


def test_logout(client):
    """
    Test the logout process.

    This test verifies that the user is logged out when they access the logout route,
    and that they are redirected to the registration portal.

    :param client: The Flask test client.
    :type client: flask.testing.FlaskClient
    :return: None
    """
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Registration Portal" in response.data
    with client.session_transaction() as sess:
        assert "email" not in sess
