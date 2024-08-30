"""Units tests for the club booking system."""


def test_initialize_club_bookings():
    """
    Test the initialization of club bookings when 'clubBookings' is not present.

    This test verifies that the 'clubBookings' key is added to the competition
    dictionary and that the club's booking count is initialized to 0 if it is not
    already present.

    :return: None
    """
    competition = {"name": "Comp1", "numberOfPlaces": "25"}
    club = {"name": "Club1", "points": "13"}

    if "clubBookings" not in competition:
        competition["clubBookings"] = {}

    if club["name"] not in competition["clubBookings"]:
        competition["clubBookings"][club["name"]] = 0

    # Test initialization when 'clubBookings' is not present
    assert "clubBookings" in competition
    assert competition["clubBookings"][club["name"]] == 0


def test_club_booking_already_exists():
    """
    Test the scenario where 'clubBookings' and the club are already present.

    This test verifies that the club's booking count remains unchanged if it is
    already present in the 'clubBookings' dictionary of the competition.

    :return: None
    """
    club = {"name": "Club1", "points": "13"}
    competition = {"name": "Comp1", "numberOfPlaces": "25", "clubBookings": {club["name"]: 5}}

    # Test when 'clubBookings' and club are already present
    competition["clubBookings"][club["name"]] = 5
    assert competition["clubBookings"][club["name"]] == 5


def test_update_booking_success():
    """
    Test the successful update of a booking.

    This test verifies that the booking is updated correctly when the club has
    sufficient points and the total bookings do not exceed the limit.

    :return: None
    """
    competition = {"name": "Competition1", "numberOfPlaces": "25", "clubBookings": {"Club1": 5}}
    club = {"name": "Club1", "email": "club1@example.com", "points": "15"}
    places_required = 5

    if competition["clubBookings"][club["name"]] + places_required <= 12:
        competition["clubBookings"][club["name"]] += places_required
        club["points"] = int(club["points"]) - places_required
        competition["numberOfPlaces"] = int(competition["numberOfPlaces"]) - places_required

    assert competition["clubBookings"]["Club1"] == 10
    assert club["points"] == 10
    assert competition["numberOfPlaces"] == 20


def test_update_booking_exceeds_limit():
    """
    Test the update of a booking when it exceeds the limit.

    This test verifies that the booking is not updated if the total bookings
    exceed the limit of 12 places per club.

    :return: None
    """
    competition = {"name": "Competition1", "numberOfPlaces": "25", "clubBookings": {"Club1": 10}}
    club = {"name": "Club1", "email": "club1@example.com", "points": "15"}
    places_required = 3

    if competition["clubBookings"][club["name"]] + places_required <= 12:
        competition["clubBookings"][club["name"]] += places_required
        club["points"] = int(club["points"]) - places_required
        competition["numberOfPlaces"] = int(competition["numberOfPlaces"]) - places_required

    assert competition["clubBookings"]["Club1"] == 10
    assert int(club["points"]) == 15
    assert int(competition["numberOfPlaces"]) == 25
