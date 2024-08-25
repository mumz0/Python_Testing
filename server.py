"""
This Flask application handles the management of clubs and competitions.
"""

import json

from flask import Flask, flash, redirect, render_template, request, url_for


def load_clubs():
    """
    Load the list of clubs from a JSON file.

    Returns:
        list: A list of clubs.
    """
    with open("clubs.json", encoding="utf-8") as file:
        clubs_list = json.load(file)["clubs"]
    return clubs_list


def load_competitions():
    """
    Load the list of competitions from a JSON file.

    Returns:
        list: A list of competitions.
    """
    with open("competitions.json", encoding="utf-8") as file:
        competitions_list = json.load(file)["competitions"]
    return competitions_list


app = Flask(__name__)
app.secret_key = "something_special"

competitions = load_competitions()
clubs = load_clubs()


@app.route("/")
def index():
    """
    Render the index page.

    Returns:
        str: Rendered HTML of the index page.
    """
    return render_template("index.html")


@app.route("/show_summary", methods=["POST"])
def show_summary():
    """
    Render the welcome page with the club details and competitions based on email.

    Returns:
        str: Rendered HTML of the welcome page.
    """
    club = next(club for club in clubs if club["email"] == request.form["email"])
    return render_template("welcome.html", club=club, competitions=competitions)


@app.route("/book/<competition>/<club>")
def book(competition, club):
    """
    Render the booking page based on the competition and club.

    Returns:
        str: Rendered HTML of the booking page or welcome page with an error message.
    """
    found_club = next((c for c in clubs if c["name"] == club), None)
    found_competition = next((c for c in competitions if c["name"] == competition), None)
    if found_club and found_competition:
        return render_template("booking.html", club=found_club, competition=found_competition)

    flash("Something went wrong - please try again")
    return render_template("welcome.html", club=club, competitions=competitions)


@app.route("/purchase_places", methods=["POST"])
def purchase_places():
    """
    Process the purchase of places for a competition and club.

    Returns:
        str: Rendered HTML of the welcome page with a confirmation message.
    """
    competition = next(c for c in competitions if c["name"] == request.form["competition"])
    club = next(c for c in clubs if c["name"] == request.form["club"])
    places_required = int(request.form["places"])
    competition["numberOfPlaces"] = int(competition["numberOfPlaces"]) - places_required
    flash("Great - booking complete!")
    return render_template("welcome.html", club=club, competitions=competitions)


@app.route("/logout")
def logout():
    """
    Redirect to the index page upon logout.

    Returns:
        Redirect: Redirect to the index route.
    """
    return redirect(url_for("index"))


# TODO: Add route for points display
