"""
This module provides routes and functionality for a Flask web application.

It includes routes for loading data, rendering pages, booking, and purchasing places,
as well as handling user interactions.
"""

import json

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.exceptions import BadRequest


def load_clubs():
    """Load clubs from the JSON file."""
    with open("clubs.json", encoding="utf-8") as c:
        clubs_list = json.load(c)["clubs"]
    return clubs_list


def load_competitions():
    """Load competitions from the JSON file."""
    with open("competitions.json", encoding="utf-8") as comps:
        competitions_list = json.load(comps)["competitions"]
    return competitions_list


app = Flask(__name__)
app.secret_key = "something_special"

competitions = load_competitions()
clubs = load_clubs()


@app.route("/")
def index():
    """Render the index page."""
    return render_template("index.html")


@app.route("/show_summary", methods=["POST", "GET"])
def show_summary():
    """
    Handle POST request to render the summary page for a specific club.

    Retrieves the club's information based on the email provided in the form data.
    If the email is valid and corresponds to a club, the summary page is rendered.
    If the email is invalid or not provided, the user is redirected to the index page
    with an appropriate error message.

    :return: The rendered HTML template for the summary page or a redirection to the index page.
    :rtype: str

    :raises IndexError: If no club is found with the provided email.

    """
    if request.method == "GET":
        email = session.get("email")
        if email:
            club = [club for club in clubs if club["email"] == email][0]
            return render_template("welcome.html", club=club, competitions=competitions)
        return redirect("/")

    try:
        email = request.form.get("email")
        if not email:
            flash("Email is required.")
            return redirect("/")

        club = [club for club in clubs if club["email"] == request.form["email"]][0]

        if not club:
            flash("Email does not exist.")
            return redirect(url_for("index"))

        session["email"] = email
        return render_template("welcome.html", club=club, competitions=competitions)

    except IndexError:
        flash("Email does not exist.")
        return redirect("/")


@app.route("/book/<competition>/<club>")
def book(competition, club):
    """Render the booking page for a specific competition and club."""
    found_club = [c for c in clubs if c["name"] == club][0]
    found_competition = [c for c in competitions if c["name"] == competition][0]
    if found_club and found_competition:
        return render_template("booking.html", club=found_club, competition=found_competition)
    flash("Something went wrong - please try again.")
    return render_template("welcome.html", club=club, competitions=competitions)


@app.route("/purchase_places", methods=["POST"])
def purchase_places():
    """Handle the reservation of places for a specific competition and club."""
    competition = [c for c in competitions if c["name"] == request.form["competition"]][0]
    club = [c for c in clubs if c["name"] == request.form["club"]][0]
    places_required = int(request.form["places"])

    # Initialize 'clubBookings' for the competition if not present
    if "clubBookings" not in competition:
        competition["clubBookings"] = {}

    # Initialize the club's booking count for this competition if not present
    if club["name"] not in competition["clubBookings"]:
        competition["clubBookings"][club["name"]] = 0

    if places_required > int(club["points"]) or places_required > int(competition["numberOfPlaces"]) or places_required > 12:
        raise BadRequest("Invalid data provided")

    if competition["clubBookings"][club["name"]] + places_required <= 12:
        competition["clubBookings"][club["name"]] += places_required
        club["points"] = int(club["points"]) - places_required
        competition["numberOfPlaces"] = int(competition["numberOfPlaces"]) - places_required
    else:
        raise BadRequest("Invalid data provided")

    flash("Great - booking complete!")
    return render_template("welcome.html", club=club, competitions=competitions)


@app.route("/logout")
def logout():
    """Log out and redirect to the index page."""
    return redirect(url_for("index"))


# TODO: Add route for points display
