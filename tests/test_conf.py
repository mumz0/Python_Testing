"""File containing data for testing"""

import json
from datetime import datetime


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
            {
                "name": "Comp1",
                "date": datetime(2025, 3, 27, 10, 0),
                "numberOfPlaces": "25",
                "canBeBooked": True,
                "clubBookings": {"Club1": 0, "Club2": 0, "Club3": 0},
            },
            {
                "name": "Comp2",
                "date": datetime(2024, 9, 27, 10, 0),
                "numberOfPlaces": "2",
                "canBeBooked": True,
                "clubBookings": {"Club1": 0, "Club2": 0, "Club3": 0},
            },
            {
                "name": "Comp3",
                "date": datetime(2023, 9, 27, 10, 0),
                "numberOfPlaces": "21",
                "canBeBooked": False,
            },
        ]
    }
    return competitions


def open_competitions_json_file():
    """
    Open the competitions JSON file and return the data.

    :return: The data from the competitions JSON file.
    :rtype: dict
    """

    with open("competitions.json", "r", encoding="utf-8") as file:
        data = json.load(file)
        return data


def open_clubs_json_file():
    """
    Open the clubs JSON file and return the data.

    :return: The data from the clubs JSON file.
    :rtype: dict
    """

    with open("clubs.json", "r", encoding="utf-8") as file:
        data = json.load(file)
        return data
