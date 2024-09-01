"""
This module provides routes and functionality for a Flask web application.

It includes routes for loading data, rendering pages, booking, and purchasing places,
as well as handling user interactions.
"""

import json
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.exceptions import BadRequest, Unauthorized


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
            flash("Email is required.")
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
        flash("Session expired. Please log in again.")
        return redirect(url_for("index"))

    # Find the club by email from the session data
    club = next((club for club in clubs if club["email"] == email), None)
    if not club:
        flash("Email does not exist.")
        return redirect(url_for("index"))

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
    found_club = [c for c in clubs if c["name"] == club][0]
    found_competition = [c for c in competitions if c["name"] == competition][0]
    if found_club and found_competition:
        return render_template("booking.html", club=found_club, competition=found_competition)
    flash("Something went wrong - please try again.")
    return redirect(url_for("show_summary"))


@app.route("/purchase_places", methods=["POST"])
def purchase_places():
    """
    Handle the reservation of places for a specific competition and club.

    This function processes the form submission for booking places in a competition.
    It checks if the user is authenticated, validates the requested number of places,
    and updates the competition and club data accordingly.

    :raises Unauthorized: If the user is not authenticated.
    :raises BadRequest: If the requested number of places is invalid.
    :return: The rendered welcome page with a success message if the booking is successful,
             otherwise the welcome page with an error message.
    :rtype: werkzeug.wrappers.Response
    """
    if not session.get("email"):
        raise Unauthorized("You must be connected.")

    competition = [c for c in competitions if c["name"] == request.form["competition"]][0]
    club = [c for c in clubs if c["name"] == request.form["club"]][0]
    places_required = int(request.form["places"])

    # Initialize 'clubBookings' for the competition if not present
    if "clubBookings" not in competition:
        competition["clubBookings"] = {}

    # Initialize the club's booking count for this competition if not present
    if club["name"] not in competition["clubBookings"]:
        competition["clubBookings"][club["name"]] = 0

    if (
        places_required > int(club["points"])
        or places_required > int(competition["numberOfPlaces"])
        or places_required > 12
        or competition["clubBookings"][club["name"]] + places_required > 12
    ):
        raise BadRequest("Invalid data provided")

    competition["clubBookings"][club["name"]] += places_required
    club["points"] = int(club["points"]) - places_required
    competition["numberOfPlaces"] = int(competition["numberOfPlaces"]) - places_required
    flash("Great - booking complete!", category=competition["name"])

    flash("Great - booking complete!")
    return redirect(url_for("show_summary"))


@app.route("/logout")
def logout():
    """Log out and redirect to the index page."""
    return redirect(url_for("index"))


# TODO: Add route for points display
