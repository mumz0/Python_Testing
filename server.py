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
        email = request.form.get("email")
        if not email:
            flash("Empty field.")
            return redirect(url_for("index"))

        # Find the club by email from the form data
        club = next((club for club in clubs if club["email"] == email), None)
        if not club:
            flash("Email does not exist.")
            return redirect(url_for("index"))

        # Save email to session and redirect to avoid resubmission
        session["email"] = email
        return redirect(url_for("show_summary"))

    # Handle GET request
    email = session.get("email")
    if not email:
        raise Unauthorized("You must be connected.")

    # Find the club by email from the session data
    club = next((club for club in clubs if club["email"] == email), None)
    if not club:
        raise Unauthorized("You must have an account.")

    # Update the booking status for each competition
    now = datetime.now()
    for competition in competitions:
        competition["canBeBooked"] = competition["date"] >= now

    # Render the welcome page with the club and competitions data
    return render_template("welcome.html", club=club, competitions=competitions)


@app.route("/book/<competition>/<club>")
def book(competition, club):
    """
    Render the booking page for a specific competition and club.

    :param competition: The name of the competition.
    :type competition: str
    :param club: The name of the club.
    :type club: str
    :return: The rendered booking page if the club and competition are found,
             otherwise the welcome page with an error message.
    :rtype: werkzeug.wrappers.Response
    """
    try:
        if not session.get("email"):
            raise Unauthorized

        found_club = [c for c in clubs if c["name"] == club][0]
        found_competition = [c for c in competitions if c["name"] == competition][0]

        if found_competition["date"] < datetime.now():
            raise BadRequest

        return render_template("booking.html", club=found_club, competition=found_competition)

    except Unauthorized as exc:
        raise Unauthorized("You must be connected.") from exc

    except IndexError as exc:
        raise BadRequest("Invalid data provided") from exc


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
        raise Unauthorized

    try:
        competition_name = request.form["competition"]
        club_name = request.form["club"]
        places_required = int(request.form["places"])

        # Retrieve competition and club from lists
        competition = next((c for c in competitions if c["name"] == competition_name), None)
        club = next((c for c in clubs if c["name"] == club_name), None)
        print("competition_name", competition["name"])
        if not competition or not club:
            raise BadRequest

        # Check and initialize competition's club bookings
        if "clubBookings" not in competition:
            competition["clubBookings"] = {}
        if club_name not in competition["clubBookings"]:
            competition["clubBookings"][club_name] = 0

        # Validate booking request
        if (
            places_required > 12
            or places_required > int(club["points"])
            or places_required > int(competition["numberOfPlaces"])
            or competition["clubBookings"][club_name] + places_required > 12
        ):
            raise BadRequest

        # Update bookings and points
        competition["clubBookings"][club_name] += places_required
        club["points"] = int(club["points"]) - places_required
        competition["numberOfPlaces"] = int(competition["numberOfPlaces"]) - places_required

        flash("Great - booking complete!", category=competition["name"])
        return redirect(url_for("show_summary"))

    except InternalServerError as exc:
        raise InternalServerError("Internal server error") from exc

    except BadRequest as exc:
        raise BadRequest("Invalid data provided.") from exc

    except Unauthorized as exc:
        raise Unauthorized("You must be connected.") from exc


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
