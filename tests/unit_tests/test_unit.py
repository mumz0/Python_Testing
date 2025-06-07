"Functional tests for the booking system"
from datetime import datetime, timedelta
from unittest.mock import mock_open, patch

import pytest
from werkzeug.exceptions import BadRequest, Unauthorized

from server import (
    _extract_booking_data,
    _find_club_and_competition,
    _find_club_by_email,
    _handle_login_form,
    _initialize_club_bookings,
    _save_booking_changes,
    _update_booking_data,
    _update_competitions_booking_status,
    _validate_booking_request,
    _validate_competition_booking_eligibility,
    _validate_user_authentication,
    app,
    book,
    clubs,
    competitions,
    save_clubs,
    save_competitions,
)
from tests.test_conf import sample_clubs, sample_competitions


def test_extract_booking_data_success():
    """
    Test successful extraction of booking data from request context.
    This test verifies that the _extract_booking_data function correctly
    extracts and processes booking information (competition name, club name,
    and number of places) from a Flask request context. The test ensures
    that string values are preserved as strings and numeric values are
    properly converted to integers.
    Expected behavior:
    - Competition name should be extracted as a string
    - Club name should be extracted as a string
    - Places should be extracted and converted to an integer
    """
    # Simulate a request context with valid booking data
    with app.test_request_context(data={"competition": "Test Competition", "club": "Test Club", "places": "5"}):
        competition, club, places = _extract_booking_data()

        assert competition == "Test Competition"
        assert club == "Test Club"
        assert places == 5


def test_extract_booking_data_missing_field():
    """
    Test that _extract_booking_data raises BadRequest when a required field is missing.

    This test verifies that the function properly validates input data and raises
    a BadRequest exception when the 'places' field is not provided in the request
    data, even when other required fields like 'competition' and 'club' are present.
    """
    # Simulate a request context with missing 'places' field
    with app.test_request_context(data={"competition": "Test Competition", "club": "Test Club"}):
        # Call the function and expect a BadRequest exception
        with pytest.raises(BadRequest):
            _extract_booking_data()


def test_extract_booking_data_invalid_places():
    """
    Test that _extract_booking_data raises BadRequest when 'places' parameter
    contains a non-numeric value.
    """
    # Simulate a request context with invalid 'places' value
    with app.test_request_context(data={"competition": "Test Competition", "club": "Test Club", "places": "not_a_number"}):
        # Call the function and expect a BadRequest exception
        with pytest.raises(BadRequest):
            _extract_booking_data()


@patch("server.competitions")
@patch("server.clubs")
def test_find_club_and_competition_success(mock_clubs, mock_competitions):
    """
    Test successful club and competition lookup.
    This test verifies that the _find_club_and_competition function correctly
    retrieves a club and competition when provided with valid names.
    Args:
        mock_clubs: Mock object for the server.clubs global variable
        mock_competitions: Mock object for the server.competitions global variable
    Test Setup:
        - Mocks the global clubs and competitions lists to avoid side effects
        - Uses sample data for clubs and competitions
        - Searches for 'Club1' and 'Comp1'
    Expected Behavior:
        - The function should return the correct club object with name 'Club1'
        - The function should return the correct competition object with name 'Comp1'
        - No exceptions should be raised during the lookup process
    Assertions:
        - Verifies that the returned club has the expected name
        - Verifies that the returned competition has the expected name
    """
    test_clubs = sample_clubs()["clubs"]
    test_competitions = sample_competitions()["competitions"]

    # Configure the mock to return our test lists
    mock_clubs.__iter__ = lambda x: iter(test_clubs)
    mock_competitions.__iter__ = lambda x: iter(test_competitions)

    club, competition = _find_club_and_competition("Club1", "Comp1")

    assert club["name"] == "Club1"
    assert competition["name"] == "Comp1"


@patch("server.competitions")
@patch("server.clubs")
def test_find_club_and_competition_not_found(mock_clubs, mock_competitions):
    """
    Test that _find_club_and_competition raises BadRequest when either club or competition cannot be found.
    This test verifies two scenarios:
    1. When a club name that doesn't exist in the clubs list is provided
    2. When a competition name that doesn't exist in the competitions list is provided
    Both scenarios should raise a BadRequest exception to indicate the lookup failure.
    Args:
        mock_clubs: Mocked clubs data structure
        mock_competitions: Mocked competitions data structure
    Raises:
        BadRequest: When club or competition is not found in their respective lists
    """
    test_clubs = sample_clubs()["clubs"]
    test_competitions = sample_competitions()["competitions"]

    # Configure the mock to return our test lists
    mock_clubs.__iter__ = lambda x: iter(test_clubs)
    mock_competitions.__iter__ = lambda x: iter(test_competitions)

    # Test with a non-existent club and wait for the exception
    with pytest.raises(BadRequest):
        _find_club_and_competition("Nonexistent Club", "Comp1")
    # Test with a non-existent competition and wait for the exception
    with pytest.raises(BadRequest):
        _find_club_and_competition("Club1", "Nonexistent Competition")


def test_initialize_club_bookings_new():
    """
    Test that _initialize_club_bookings correctly initializes club bookings for a new competition.
    Verifies that:
    - A 'clubBookings' key is added to the competition dictionary
    - The specified club is added to the clubBookings dictionary
    - The club's booking count is initialized to 0
    """
    competition = {"name": "New Competition", "numberOfPlaces": "10"}

    _initialize_club_bookings(competition, "Club1")

    assert "clubBookings" in competition
    assert "Club1" in competition["clubBookings"]
    assert competition["clubBookings"]["Club1"] == 0


def test_initialize_club_bookings_invalid_input():
    """
    Test that _initialize_club_bookings raises ValueError for invalid inputs.
    This test verifies that the function properly validates its parameters and
    raises ValueError when:
    - clubs parameter is None
    - club_name parameter is an empty string
    Expected behavior:
    - ValueError should be raised for None clubs parameter
    - ValueError should be raised for empty club_name parameter
    """
    # Test with None clubs parameter and wait for the exception
    with pytest.raises(ValueError):
        _initialize_club_bookings(None, "Club1")
    # Test with empty club_name parameter and wait for the exception
    with pytest.raises(ValueError):
        _initialize_club_bookings({}, "")


def test_validate_booking_request_success():
    """
    Test that _validate_booking_request succeeds with valid booking parameters.
    This test verifies that the _validate_booking_request function executes
    without raising any exceptions when provided with valid inputs:
    - A reasonable number of places to book (5)
    - A valid club from the sample data (Club3)
    - A competition with sufficient available places (25)
    - Matching club name
    The test uses Club3 from sample data which has no existing bookings
    for the test competition, ensuring the booking request should be valid.
    """
    test_clubs = sample_clubs()["clubs"]
    club = next(c for c in test_clubs if c["name"] == "Club3")
    competition = {"name": "Test Competition", "numberOfPlaces": "25", "clubBookings": {"Club3": 0}}

    _validate_booking_request(5, club, competition, "Club3")


def test_validate_booking_request_exceed_max_per_booking():
    """
    Test that booking validation fails when requesting more than the maximum allowed places per booking.
    This test verifies that the _validate_booking_request function properly enforces
    the business rule limiting bookings to a maximum of 12 places per transaction.
    It uses Club3 (which has sufficient points) and a competition with available places,
    but requests 13 places to trigger the validation error.
    Expected behavior:
    - Should raise BadRequest exception with message "Cannot book more than 12 places at once"
    - Validates the per-booking limit regardless of club points or competition availability
    """
    test_clubs = sample_clubs()["clubs"]
    club = next(c for c in test_clubs if c["name"] == "Club3")
    competition = {"name": "Test Competition", "numberOfPlaces": "25", "clubBookings": {"Club3": 0}}
    # Validate booking request with more than 12 places and wait for the exception
    with pytest.raises(BadRequest, match="Cannot book more than 12 places at once"):
        _validate_booking_request(13, club, competition, "Club3")


def test_validate_booking_request_not_enough_points():
    """
    Test that booking validation raises BadRequest when a club attempts to book
    more places than their available points allow.
    This test verifies that the _validate_booking_request function properly
    validates point availability by:
    - Using Club2 which has 4 points from the sample data
    - Attempting to book 10 places (more than available points)
    - Expecting a BadRequest exception with message "Not enough points available"
    The test ensures the system prevents overbooking beyond a club's point balance.
    """
    test_clubs = sample_clubs()["clubs"]
    club = next(c for c in test_clubs if c["name"] == "Club2")
    competition = {"name": "Test Competition", "numberOfPlaces": "20", "clubBookings": {"Club2": 0}}
    # Validate booking request with insufficient points and wait for the exception
    with pytest.raises(BadRequest, match="Not enough points available"):
        _validate_booking_request(10, club, competition, "Club2")


def test_validate_booking_request_not_enough_places():
    """
    Test that _validate_booking_request raises BadRequest when requested places
    exceed available places in the competition.
    This test verifies that attempting to book more places than are available
    in a competition (10 places requested when only 5 are available) raises
    a BadRequest exception with the appropriate error message.
    """
    test_clubs = sample_clubs()["clubs"]
    club = next(c for c in test_clubs if c["name"] == "Club1")
    competition = {"name": "Test Competition", "numberOfPlaces": "5", "clubBookings": {"Club1": 0}}
    # Validate booking request with more places than available and wait for the exception
    with pytest.raises(BadRequest, match="Not enough places available"):
        _validate_booking_request(10, club, competition, "Club1")


def test_validate_booking_request_exceed_total_limit():
    """
    Test that booking validation fails when the total bookings would exceed the 12-place limit.
    This test verifies that the _validate_booking_request function correctly raises a BadRequest
    exception when a club attempts to book places that would cause their total bookings for
    a competition to exceed the maximum allowed limit of 12 places.
    Test scenario:
    - Club3 already has 10 bookings for the competition
    - Attempts to book 5 additional places (total would be 15)
    - Should raise BadRequest with appropriate error message
    Raises:
        BadRequest: When total bookings would exceed 12 places limit
    """
    test_clubs = sample_clubs()["clubs"]
    club = next(c for c in test_clubs if c["name"] == "Club3")
    competition = {"name": "Test Competition", "numberOfPlaces": "25", "clubBookings": {"Club3": 10}}
    # Validate booking request that would exceed total limit and wait for the exception
    with pytest.raises(BadRequest, match="Total bookings for this club would exceed 12 places"):
        _validate_booking_request(5, club, competition, "Club3")


def test_update_booking_data():
    """
    Test the _update_booking_data function to ensure it correctly updates booking information.
    This test verifies that when booking 5 additional places:
    - Club points are decremented by the booking amount (13 - 5 = 8)
    - Competition available places are reduced by the booking amount (20 - 5 = 15)
    - Club's existing bookings are incremented by the booking amount (3 + 5 = 8)
    Uses Club1 with initial 13 points and 3 existing bookings for a competition
    with 20 available places.
    """
    test_clubs = sample_clubs()["clubs"]
    club = next(c for c in test_clubs if c["name"] == "Club1")
    competition = {"name": "Test Competition", "numberOfPlaces": "20", "clubBookings": {"Club1": 3}}

    _update_booking_data(5, club, competition, "Club1")

    assert club["points"] == 8
    assert competition["numberOfPlaces"] == 15
    assert competition["clubBookings"]["Club1"] == 8


@patch("server.save_competitions")
@patch("server.save_clubs")
@patch("builtins.open", new_callable=mock_open)
def test_save_booking_changes(mock_file, mock_save_clubs, mock_save_competitions):
    """
    Test that _save_booking_changes function correctly calls save_clubs and save_competitions.
    This test verifies that:
    - save_clubs is called exactly once with the clubs parameter
    - save_competitions is called exactly once with the competitions parameter
    - The file opening functionality is not directly called by this function
    """
    _save_booking_changes()

    # Mocked clubs and competitions data
    mock_save_clubs.assert_called_once_with(clubs)
    mock_save_competitions.assert_called_once_with(competitions)

    # Ensure that the file open operation is not called
    mock_file.assert_not_called()


@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_save_competitions_file_operations(mock_json_dump, mock_file):
    """
    Test that save_competitions function performs correct file operations.
    This test verifies that:
    - The function opens the correct file ('competitions.json') in write mode with UTF-8 encoding
    - The function calls json.dump to serialize the data
    - File operations are called exactly once
    Uses mocking to isolate file I/O operations and verify the function's behavior
    without actually writing to the filesystem.
    Args:
        mock_json_dump: Mock object for json.dump function
        mock_file: Mock object for builtins.open function
    """
    test_competitions = [{"name": "Test Comp", "date": datetime(2025, 1, 1), "numberOfPlaces": "10"}]

    save_competitions(test_competitions)

    # Ensure the file is opened correctly
    mock_file.assert_called_once_with("competitions.json", "w", encoding="utf-8")
    # Ensure json.dump is called once with the competitions data
    mock_json_dump.assert_called_once()


@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_save_clubs_file_operations(mock_json_dump, mock_file):
    """
    Test that save_clubs function properly handles file operations.
    This test verifies that:
    - The clubs.json file is opened with correct parameters (write mode, UTF-8 encoding)
    - The json.dump function is called exactly once to serialize the clubs data
    Uses mocks to isolate file I/O operations and verify the function's behavior
    without actual file system interactions.
    Args:
        mock_json_dump: Mock object for json.dump function
        mock_file: Mock object for builtins.open function
    """
    test_clubs = [{"name": "Test Club", "email": "test@test.com", "points": "10"}]

    save_clubs(test_clubs)

    # Ensure the file is opened correctly
    mock_file.assert_called_once_with("clubs.json", "w", encoding="utf-8")
    # Ensure json.dump is called once with the clubs data
    mock_json_dump.assert_called_once()


@patch("server.render_template")
@patch("server._validate_competition_booking_eligibility")
@patch("server._find_club_and_competition")
@patch("server._validate_user_authentication")
def test_book_success(mock_auth, mock_find, mock_validate_comp, mock_render):
    """
    Test the successful booking page rendering functionality.
    This test verifies that when a valid club and competition are provided,
    the book function correctly:
    - Validates user authentication
    - Finds the specified club and competition
    - Validates competition booking eligibility
    - Renders the booking template with the correct context
    - Returns the rendered template
    Mocks:
        server.render_template: Mocks template rendering
        server._validate_competition_booking_eligibility: Mocks competition validation
        server._find_club_and_competition: Mocks club/competition lookup
        server._validate_user_authentication: Mocks user authentication
    Args:
        mock_auth: Mock for user authentication validation
        mock_find: Mock for club and competition finder
        mock_validate_comp: Mock for competition booking eligibility validation
        mock_render: Mock for template rendering
    Asserts:
        - Authentication is called once
        - Club/competition finder is called with correct parameters
        - Competition validation is called with the found competition
        - Template is rendered with correct club and competition context
        - Function returns the rendered template result
    """
    mock_club = {"name": "Test Club", "points": "10"}
    mock_competition = {"name": "Test Competition", "date": datetime.now() + timedelta(days=1)}
    mock_find.return_value = (mock_club, mock_competition)
    mock_render.return_value = "rendered_template"

    result = book("Test Competition", "Test Club")

    # Assert that all mocked functions were called as expected
    mock_auth.assert_called_once()
    mock_find.assert_called_once_with("Test Club", "Test Competition")
    mock_validate_comp.assert_called_once_with(mock_competition)
    mock_render.assert_called_once_with("booking.html", club=mock_club, competition=mock_competition)
    assert result == "rendered_template"


@patch("server._validate_user_authentication")
def test_book_unauthorized_user(mock_auth):
    """
    Test that booking a competition raises an Unauthorized exception when the user is not authenticated.
    This test mocks the user authentication validation to simulate an unauthorized user
    attempting to book a competition. It verifies that the appropriate Unauthorized
    exception is raised with the expected error message.
    Args:
        mock_auth: Mocked authentication validation function that simulates
                an unauthorized user by raising an Unauthorized exception.
    Raises:
        Unauthorized: Expected exception when user authentication fails.
    Returns:
        None: This is a test method that asserts expected behavior.
    """
    # mock_auth.return_value = None  # Simulate no user authenticated
    mock_auth.side_effect = Unauthorized("You must be connected.")

    # Attempt to book a competition without authentication and wait for the exception
    with pytest.raises(Unauthorized, match="You must be connected."):
        book("Test Competition", "Test Club")


@patch("server._find_club_and_competition")
@patch("server._validate_user_authentication")
def test_book_club_or_competition_not_found(mock_auth, mock_find):
    """
    Test case for booking functionality when either the club or competition cannot be found.
    This test verifies that the book function properly handles scenarios where the
    _find_club_and_competition function raises a BadRequest exception due to invalid
    club or competition names. It mocks the authentication and club/competition finding
    functions to simulate the error condition and ensures the exception is properly
    propagated.
    Mocks:
        server._validate_user_authentication: Mocked to avoid authentication logic
        server._find_club_and_competition: Mocked to raise BadRequest exception
    Expected Behavior:
        The book function should raise a BadRequest exception with the message
        "Club or competition not found" when invalid club or competition names
        are provided.
    """
    # Mock the authentication to pass (no exception raised)
    mock_auth.return_value = None

    # Mock the find function to raise BadRequest exception
    mock_find.side_effect = BadRequest("Club or competition not found")

    # Attempt to book with invalid club and competition names and wait for the exception
    with pytest.raises(BadRequest, match="Club or competition not found"):
        book("Invalid Competition", "Invalid Club")


@patch("server._validate_competition_booking_eligibility")
@patch("server._find_club_and_competition")
@patch("server._validate_user_authentication")
def test_book_competition_not_eligible(mock_auth, mock_find, mock_validate_comp):
    """
    Test that booking a competition raises BadRequest when the competition is not eligible for booking.
    This test verifies that when a user attempts to book a competition that fails
    eligibility validation (e.g., past date, full capacity, etc.), the system
    properly raises a BadRequest exception with an appropriate error message.
    Mocks:
        - _validate_user_authentication: Bypassed for this test
        - _find_club_and_competition: Returns test club and competition data
        - _validate_competition_booking_eligibility: Simulates eligibility failure
    Expected Behavior:
        - BadRequest exception is raised
        - Exception message indicates competition is no longer available
    """
    mock_club = {"name": "Test Club"}
    mock_competition = {"name": "Test Competition", "date": datetime.now() - timedelta(days=1)}
    # Patch the find function to return the mock club and competition
    mock_find.return_value = (mock_club, mock_competition)
    # Patch the validate function to raise BadRequest
    mock_validate_comp.side_effect = BadRequest("This competition is no longer available for booking")

    # Attempt to book a competition that is not eligible and wait for the exception and check the message
    with pytest.raises(BadRequest, match="This competition is no longer available for booking"):
        book("Test Competition", "Test Club")


def test_validate_user_authentication_success():
    """
    Test successful user authentication validation.
    This test verifies that the _validate_user_authentication function
    executes without raising any exceptions when a valid email is present
    in the session. It mocks the session.get method to return a test email
    and ensures the function completes successfully.
    Mocks:
        server.session.get: Mocked to return "test@example.com"
    Assertions:
        - No exception is raised during validation
        - session.get is called exactly once with "email" parameter
    """
    # Mock the session to simulate a user with a valid email
    with app.test_request_context():
        # Patch the session.get method to return a test email
        with patch("server.session.get") as mock_session_get:
            # Mock the session.get to return a valid email
            mock_session_get.return_value = "test@example.com"

            _validate_user_authentication()
            # Assert that the session.get was called with "email"
            mock_session_get.assert_called_once_with("email")


def test_validate_user_authentication_empty_email():
    """Test authentication validation with empty email.
    This test verifies that the _validate_user_authentication function
    raises an Unauthorized exception with the message "You must be connected."
    when the session email is an empty string. The test mocks the session.get
    method to return an empty string and asserts that the appropriate
    exception is raised.
    Raises:
        Unauthorized: When session email is empty, indicating user is not authenticated.
    """
    # Mock the session to simulate an unauthenticated user
    with app.test_request_context():
        # Patch the session.get method to return an empty string
        with patch("server.session.get") as mock_session_get:
            # Mock the session.get to return an empty string
            mock_session_get.return_value = ""

            # Expect Unauthorized exception when validating authentication
            with pytest.raises(Unauthorized, match="You must be connected."):
                _validate_user_authentication()


@patch("server.datetime")
def test_validate_competition_booking_eligibility_future_date(mock_datetime):
    """
    Test that competition booking eligibility validation passes for future dates.
    This test verifies that the _validate_competition_booking_eligibility function
    does not raise an exception when validating a competition with a date that is
    in the future relative to the current time.
    The test uses mocking to control the current datetime and ensures that
    competitions scheduled for future dates are considered valid for booking.
    Args:
        mock_datetime: Mocked datetime module to control the current time.
    Raises:
        No exceptions should be raised for valid future competition dates.
    """
    now = datetime(2024, 1, 1, 12, 0, 0)
    future_date = datetime(2024, 1, 2, 12, 0, 0)
    # Patch the datetime module to control the current time
    mock_datetime.now.return_value = now
    competition = {"date": future_date}

    # This should not raise an exception
    _validate_competition_booking_eligibility(competition)


@patch("server.datetime")
def test_validate_competition_booking_eligibility_past_date(mock_datetime):
    """
    Test that _validate_competition_booking_eligibility raises BadRequest
    when attempting to book a competition with a date in the past.
    This test mocks the current datetime to ensure consistent behavior
    and verifies that the appropriate error message is returned when
    trying to book an expired competition.
    Args:
        mock_datetime: Mocked datetime module to control current time
    Raises:
        BadRequest: Expected exception with message about competition
                no longer being available for booking
    """
    now = datetime(2024, 1, 2, 12, 0, 0)
    past_date = datetime(2024, 1, 1, 12, 0, 0)
    # Patch the datetime module to control the current time
    mock_datetime.now.return_value = now
    competition = {"date": past_date}

    # Expect BadRequest exception when validating past competition date
    with pytest.raises(BadRequest, match="This competition is no longer available for booking"):
        _validate_competition_booking_eligibility(competition)


def test_handle_login_form_success():
    """
    Test the successful handling of a login form submission.
    This test verifies that when a valid email is submitted through a POST request,
    the login form handler correctly:
    - Finds the club associated with the email
    - Sets the session email
    - Redirects to the summary page
    - Does not display any flash messages
    - Returns the expected redirect response
    The test uses mocking to isolate the function under test and verify
    all expected interactions with dependencies occur correctly.
    """
    # Simulate a request context with a POST method and a valid email
    with app.test_request_context(data={"email": "test@example.com"}, method="POST"):
        # Patch the necessary functions to isolate the test
        with patch("server._find_club_by_email") as mock_find, patch("server.flash") as mock_flash, patch("server.redirect") as mock_redirect, patch(
            "server.url_for"
        ) as mock_url_for, patch("server.session") as mock_session:

            # Arrange
            # Mock the behavior of _find_club_by_email to return a club dictionary
            mock_find.return_value = {"name": "Test Club", "email": "test@example.com"}
            # Mock the session to simulate setting the email
            mock_url_for.return_value = "/show_summary"
            # Mock the redirect response
            mock_redirect.return_value = "redirect_response"

            # Call the login form handler with the mocked request context
            result = _handle_login_form()

            # Verify that the club was found, session email was set, and redirect occurred
            mock_find.assert_called_once_with("test@example.com")
            mock_session.__setitem__.assert_called_once_with("email", "test@example.com")
            mock_url_for.assert_called_once_with("show_summary")
            mock_redirect.assert_called_once_with("/show_summary")
            mock_flash.assert_not_called()
            assert result == "redirect_response"


def test_handle_login_form_empty_email():
    """Test login form handling with empty email field.
    This test verifies that when a login form is submitted with an empty email field,
    the system properly:
    - Flashes an "Empty field." error message
    - Redirects the user to the index page
    - Returns the expected redirect response
    The test uses mocked Flask components (flash, redirect, url_for) to isolate
    the login form handling logic and verify the correct flow when validation fails
    due to missing email input.
    """
    # Simulate a request context with a POST method and an empty email
    with app.test_request_context(data={"email": ""}, method="POST"):
        # Patch the necessary functions to isolate the test
        with patch("server.flash") as mock_flash, patch("server.redirect") as mock_redirect, patch("server.url_for") as mock_url_for:

            # Mock the behavior of url_for and redirect to return expected values
            mock_url_for.return_value = "/index"
            mock_redirect.return_value = "redirect_response"

            result = _handle_login_form()

            # Verify that the flash message was called with the correct error
            # and that the redirect occurred to the index page
            mock_flash.assert_called_once_with("Empty field.")
            mock_url_for.assert_called_once_with("index")
            mock_redirect.assert_called_once_with("/index")
            assert result == "redirect_response"


def test_handle_login_form_email_not_found():
    """
    Test login form handling when the provided email address is not found in the system.
    This test verifies that when a user attempts to log in with an email that doesn't
    exist in the database, the system:
    - Calls the email lookup function with the provided email
    - Flashes an appropriate error message to the user
    - Redirects the user back to the index page
    - Returns the expected redirect response
    The test uses mocking to isolate the login form handler and verify that all
    expected functions are called with the correct parameters when handling a
    non-existent email scenario.
    """
    # Simulate a request context with a POST method and an email that does not exist
    with app.test_request_context(data={"email": "nonexistent@example.com"}, method="POST"):
        # Patch the necessary functions to isolate the test
        with patch("server._find_club_by_email") as mock_find, patch("server.flash") as mock_flash, patch("server.redirect") as mock_redirect, patch(
            "server.url_for"
        ) as mock_url_for:

            # Mock the behavior of _find_club_by_email to return None, simulating a non-existent email
            mock_find.return_value = None
            # Mock the URL for redirection and the redirect response
            mock_url_for.return_value = "/index"
            # Mock the redirect response
            mock_redirect.return_value = "redirect_response"

            result = _handle_login_form()

            mock_flash.assert_called_once_with("Email does not exist.")
            mock_url_for.assert_called_once_with("index")
            mock_redirect.assert_called_once_with("/index")
            assert result == "redirect_response"


@patch("server.clubs")
def test_find_club_by_email_found(mock_clubs):
    """
    Test that _find_club_by_email returns the correct club when a matching email is found.
    This test mocks the server.clubs data structure and verifies that the function
    correctly identifies and returns the club dictionary that matches the provided
    email address.
    Args:
        mock_clubs: Mocked clubs data structure from server module.
    Expected behavior:
        - Should return the club dictionary with matching email "club2@test.com"
        - Should return {"name": "Club2", "email": "club2@test.com"}
    """
    test_clubs = [{"name": "Club1", "email": "club1@test.com"}, {"name": "Club2", "email": "club2@test.com"}]

    # Configure the mock to return our test list. It replace the patch object
    # with an iterable that returns the test clubs.
    # This allows the _find_club_by_email function to iterate over the mock_clubs
    # collection as if it were the actual clubs collection.
    mock_clubs.__iter__ = lambda x: iter(test_clubs)

    result = _find_club_by_email("club2@test.com")

    assert result == {"name": "Club2", "email": "club2@test.com"}


@patch("server.clubs")
def test_find_club_by_email_not_found(mock_clubs):
    """
    Test case for finding a club by email address when the club doesn't exist in the database.
    This test verifies that the _find_club_by_email function correctly returns None
    when searching for a club with an email address that is not present in the
    clubs collection.
    The test mocks the server.clubs collection with a predefined list of clubs
    and attempts to find a club with an email that doesn't match any of the
    existing clubs in the collection.
    Args:
        mock_clubs: Mocked clubs collection from the server module.
    Asserts:
        The function returns None when no club is found with the specified email.
    """
    test_clubs = [{"name": "Club1", "email": "club1@test.com"}, {"name": "Club2", "email": "club2@test.com"}]

    # Configure the mock to return our test list
    mock_clubs.__iter__ = lambda x: iter(test_clubs)

    result = _find_club_by_email("nonexistent@test.com")

    assert result is None


@patch("server.datetime")
@patch("server.competitions")
def test_update_competitions_booking_status(mock_competitions, mock_datetime):
    """
    Test the _update_competitions_booking_status function.
    This test verifies that the function correctly updates the 'canBeBooked' status
    for competitions based on their date relative to the current datetime.
    Test cases:
    - Past competitions (date < current datetime) should have canBeBooked = False
    - Future competitions (date > current datetime) should have canBeBooked = True
    - Current competitions (date == current datetime) should have canBeBooked = True
    Mocks:
    - server.datetime: Mocked to return a fixed datetime for consistent testing
    - server.competitions: Mocked to provide test competition data
    Args:
        mock_competitions: Mock object for the competitions data structure
        mock_datetime: Mock object for datetime functionality
    """
    now = datetime(2024, 1, 15, 12, 0, 0)
    mock_datetime.now.return_value = now

    test_competitions = [
        {"name": "Past Competition", "date": datetime(2024, 1, 10, 12, 0, 0)},
        {"name": "Future Competition", "date": datetime(2024, 1, 20, 12, 0, 0)},
        {"name": "Current Competition", "date": datetime(2024, 1, 15, 12, 0, 0)},
    ]

    # Configure the mock to return our test list
    mock_competitions.__iter__ = lambda x: iter(test_competitions)

    _update_competitions_booking_status()

    assert test_competitions[0]["canBeBooked"] is False
    assert test_competitions[1]["canBeBooked"] is True
    assert test_competitions[2]["canBeBooked"] is True
