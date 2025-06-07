"""
This module provides routes and functionality for a Flask web application.

It includes routes for loading data, rendering pages, booking, and purchasing places,
as well as handling user interactions.
"""

import json
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.exceptions import BadRequest, InternalServerError, Unauthorized


def load_clubs():
    """
    Load clubs from the JSON file.

    This function reads the `clubs.json` file and loads the list of clubs.

    :return: A list of clubs.
    :rtype: list
    """
    with open("clubs.json", encoding="utf-8") as c:
        clubs_list = json.load(c)["clubs"]
    return clubs_list


def load_competitions():
    """
    Load competitions from the JSON file.

    This function reads the `competitions.json` file, parses the competition dates,
    and determines if each competition can be booked based on the current date and time.
    The competitions are then sorted by date in descending order.

    :return: A sorted list of competitions.
    :rtype: list
    """
    with open("competitions.json", encoding="utf-8") as comps:
        competitions_list = json.load(comps)["competitions"]
        date_format = "%Y-%m-%d %H:%M:%S"
        now = datetime.now()
        for competition in competitions_list:
            # Parse the competition date string into a datetime object
            date_str = competition["date"]
            competition["date"] = datetime.strptime(date_str, date_format)
            competition["canBeBooked"] = competition["date"] >= now

    # Sort competitions by date (most recent first)
    return sorted(competitions_list, key=lambda comp: comp["date"], reverse=True)


app = Flask(__name__)
app.secret_key = "something_special"

competitions = load_competitions()
clubs = load_clubs()


@app.route("/")
def index():
    """Render the index page."""
    return render_template("index.html")


@app.route("/show_summary", methods=["GET", "POST"])
def show_summary():
    """
    Handle the display of the summary page.

    :return: The rendered template for the summary or a redirect.
    :rtype: flask.Response
    """
    if request.method == "POST":
        return _handle_login_form()

    return _handle_summary_display()


def _handle_login_form():
    """Handle POST request for user login."""
    email = request.form.get("email")

    # Validate email input
    if not email:
        flash("Empty field.")
        return redirect(url_for("index"))

    # Find and validate club
    club = _find_club_by_email(email)
    if not club:
        flash("Email does not exist.")
        return redirect(url_for("index"))

    # Save email to session and redirect
    session["email"] = email
    return redirect(url_for("show_summary"))


def _handle_summary_display():
    """Handle GET request for summary page display."""
    # Validate user authentication
    email = session.get("email")
    if not email:
        raise Unauthorized("You must be connected.")

    # Find and validate club
    club = _find_club_by_email(email)
    if not club:
        raise Unauthorized("You must have an account.")

    # Update competitions booking status
    _update_competitions_booking_status()

    return render_template("welcome.html", club=club, competitions=competitions)


def _find_club_by_email(email):
    """
    Find a club by email address.

    :param email: The email address to search for.
    :type email: str
    :return: The club if found, None otherwise.
    :rtype: dict or None
    """
    return next((club for club in clubs if club["email"] == email), None)


def _update_competitions_booking_status():
    """Update the booking status for all competitions based on current time."""
    now = datetime.now()
    for competition in competitions:
        competition["canBeBooked"] = competition["date"] >= now


@app.route("/book/<competition>/<club>")
def book(competition, club):
    """
    Render the booking page for a specific competition and club.

    :param competition: The name of the competition.
    :type competition: str
    :param club: The name of the club.
    :type club: str
    :return: The rendered booking page if the club and competition are found,
             otherwise raises appropriate HTTP exceptions.
    :rtype: werkzeug.wrappers.Response
    :raises Unauthorized: If user is not authenticated.
    :raises BadRequest: If club/competition not found or competition is past.
    """
    try:
        # Validate user authentication
        _validate_user_authentication()

        # Find club and competition
        found_club, found_competition = _find_club_and_competition(club, competition)

        # Validate competition eligibility
        _validate_competition_booking_eligibility(found_competition)

        return render_template("booking.html", club=found_club, competition=found_competition)

    except (Unauthorized, BadRequest):
        raise
    except Exception as exc:
        raise BadRequest("Invalid data provided") from exc


def _validate_user_authentication():
    """Validate that user is authenticated."""
    if not session.get("email"):
        raise Unauthorized("You must be connected.")


def _validate_competition_booking_eligibility(competition):
    """Validate that competition is eligible for booking."""
    if competition["date"] < datetime.now():
        raise BadRequest("This competition is no longer available for booking")


@app.route("/purchase_places", methods=["POST"])
def purchase_places():
    """
    Handle the reservation of places for a specific competition and club.

    This function processes the form submission for booking places in a competition.
    It checks if the user is authenticated, validates the requested number of places,
    and updates the competition and club data accordingly.

    :raises Unauthorized: If the user is not authenticated.
    :raises BadRequest: If the requested number of places is invalid.
    :return: Redirect to the summary page with a success message if the booking is successful,
             otherwise, raise an appropriate error.
    :rtype: werkzeug.wrappers.Response
    """
    if not session.get("email"):
        raise Unauthorized("You must be connected.")

    # Extract form data
    competition_name, club_name, places_required = _extract_booking_data()

    # Find entities
    club, competition = _find_club_and_competition(club_name, competition_name)

    # Initialize booking structure
    _initialize_club_bookings(competition, club_name)

    # Validate booking request
    _validate_booking_request(places_required, club, competition, club_name)

    try:
        # Update data
        _update_booking_data(places_required, club, competition, club_name)

        # Save changes
        _save_booking_changes()

        flash("Great - booking complete!", category=competition["name"])
        return redirect(url_for("show_summary"))

    except Exception as exc:
        # Ne capturer que les erreurs inattendues
        app.logger.exception("Unexpected error during booking:")
        raise InternalServerError("Internal server error") from exc


def _extract_booking_data():
    """Extract and validate booking data from the form."""
    try:
        competition_name = request.form["competition"]
        club_name = request.form["club"]
        places_required = int(request.form["places"])
        return competition_name, club_name, places_required
    except (KeyError, ValueError) as exc:
        raise BadRequest("Invalid form data") from exc


def _find_club_and_competition(club_name, competition_name):
    """Find club and competition by name."""
    competition = next((c for c in competitions if c["name"] == competition_name), None)
    club = next((c for c in clubs if c["name"] == club_name), None)

    if not competition or not club:
        raise BadRequest("Club or competition not found")

    return club, competition


def _initialize_club_bookings(competition, club_name):
    """Initialize club bookings structure if needed."""
    if not isinstance(competition, dict) or not club_name:
        raise ValueError("Invalid competition or club_name provided")

    if "clubBookings" not in competition:
        competition["clubBookings"] = {}
    if club_name not in competition["clubBookings"]:
        competition["clubBookings"][club_name] = 0


def _validate_booking_request(places_required, club, competition, club_name):
    """Validate the booking request against business rules."""
    club_points = int(club["points"])
    available_places = int(competition["numberOfPlaces"])
    current_bookings = competition["clubBookings"][club_name]

    if places_required > 12:
        raise BadRequest("Cannot book more than 12 places at once")

    if places_required > club_points:
        raise BadRequest("Not enough points available")

    if places_required > available_places:
        raise BadRequest("Not enough places available in competition")

    if current_bookings + places_required > 12:
        raise BadRequest("Total bookings for this club would exceed 12 places")


def _update_booking_data(places_required, club, competition, club_name):
    """Update the booking data for club and competition."""
    competition["clubBookings"][club_name] += places_required
    club["points"] = int(club["points"]) - places_required
    competition["numberOfPlaces"] = int(competition["numberOfPlaces"]) - places_required


def _save_booking_changes():
    """Save the updated club and competition data."""
    save_clubs(clubs)
    save_competitions(competitions)


@app.route("/logout")
def logout():
    """Log out and redirect to the index page."""
    session.pop("email", None)
    return redirect(url_for("index"))


@app.route("/clubs", methods=["GET"])
def display_club_points():
    """
    Render the club points table page if the user is authenticated.

    :raises Unauthorized: If the user is not logged in.
    :return: The rendered template for the clubs page.
    :rtype: flask.Response
    """
    if not session.get("email"):
        raise Unauthorized("You must be connected.")

    return render_template("clubs.html", clubs=clubs)


def save_competitions(competitions_list):
    """
    Save competitions to the JSON file.

    This function writes the updated competitions list back to the `competitions.json` file.
    It converts datetime objects back to string format for JSON serialization.

    :param competitions_list: A list of competitions to save.
    :type competitions_list: list
    """
    # Create a copy to avoid modifying the original data
    competitions_copy = []
    date_format = "%Y-%m-%d %H:%M:%S"

    for competition in competitions_list:
        comp_copy = competition.copy()
        # Convert datetime back to string for JSON serialization
        if isinstance(comp_copy["date"], datetime):
            comp_copy["date"] = comp_copy["date"].strftime(date_format)
        # Remove canBeBooked as it's calculated dynamically
        comp_copy.pop("canBeBooked", None)
        competitions_copy.append(comp_copy)

    with open("competitions.json", "w", encoding="utf-8") as comps:
        json.dump({"competitions": competitions_copy}, comps, indent=4)


def save_clubs(clubs_list):
    """
    Save clubs to the JSON file.

    This function writes the updated clubs list back to the `clubs.json` file.

    :param clubs_list: A list of clubs to save.
    :type clubs_list: list
    """
    with open("clubs.json", "w", encoding="utf-8") as c:
        json.dump({"clubs": clubs_list}, c, indent=4)
