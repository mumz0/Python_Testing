"""
Locust test file for the application.

This file contains a set of tasks to be executed by a simulated user to test
the performance and functionality of the application under load.
"""

from locust import HttpUser, between, task

from tests.test_conf import open_clubs_json_file, open_competitions_json_file


class User(HttpUser):
    """
    Simulated user class for performance testing.

    This class defines the behavior of a simulated user, including login,
    accessing various pages, and performing actions like booking and purchasing
    places in competitions.
    """

    wait_time = between(1, 5)
    is_authenticated = False
    competitions = open_competitions_json_file()["competitions"]
    clubs = open_clubs_json_file()["clubs"]

    def on_start(self):
        """
        Called when the simulated user starts.

        This method performs the initial login for the user and sets the
        authentication flag.
        """
        self.login()
        self.is_authenticated = True

    def ensure_authenticated(self):
        """
        Ensure the user is authenticated.

        If the user is not authenticated, this method will perform the login
        process.
        """
        if not self.is_authenticated:
            self.login()

    @task()
    def login(self):
        """
        Perform user login.

        Sends a POST request to the /show_summary endpoint to simulate the user
        logging in with predefined credentials. If the login fails, it records
        the failure with the appropriate status code and error message.
        """
        with self.client.post("/show_summary", data={"email": "kate@shelifts.co.uk"}, catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Got unexpected response code: " + str(response.status_code) + " Error: " + str(response.text))

    @task()
    def logout(self):
        """
        Log out the user.

        Sends a GET request to the /logout endpoint to simulate the user
        logging out. If the logout fails, it records the failure with the
        appropriate status code and error message.
        """
        if self.is_authenticated:
            self.is_authenticated = False
            with self.client.get("/logout", catch_response=True) as response:
                if response.status_code != 200:
                    response.failure("Got unexpected response code: " + str(response.status_code) + " Error: " + str(response.text))

    @task()
    def index(self):
        """
        Access the homepage.

        Sends a GET request to the root ("/") of the application to simulate the
        user accessing the homepage. If the request fails, it records the failure
        with the appropriate status code and error message.
        """
        with self.client.get("/", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Got unexpected response code: " + str(response.status_code) + " Error: " + str(response.text))

    @task()
    def show_summary(self):
        """
        Access the summary page after login.

        Sends a GET request to the /show_summary endpoint to simulate the user
        viewing their summary page. The method first ensures the user is
        authenticated. If the request fails, it records the failure with the
        appropriate status code and error message.
        """
        self.ensure_authenticated()
        with self.client.get("/show_summary", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Got unexpected response code: " + str(response.status_code) + " Error: " + str(response.text))

    @task()
    def book(self):
        """
        Attempt to book a place in a competition.

        Sends a GET request to the /book endpoint with specific competition and
        club names to simulate the user trying to book a place in a competition.
        The method first ensures the user is authenticated. If the request fails,
        it records the failure with the appropriate status code and error message.
        """
        self.ensure_authenticated()
        with self.client.get("/book/Winter%20Classic/She%20Lifts", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Got unexpected response code: " + str(response.status_code) + " Error: " + str(response.text))

    @task()
    def purchase_places(self):
        """
        Simulate a user purchasing places for a competition.

        Sends a POST request to the /purchase_places endpoint with a predefined
        competition name, club name, and number of places. The method first ensures
        the user is authenticated. The response time is measured, and if the
        status code is 200 or 400, the task is considered successful. Otherwise,
        it records the failure with the appropriate status code and error message.
        """
        self.ensure_authenticated()
        data = {
            "competition": "Winter Classic",  # Use a valid competition name from your JSON data
            "club": "She Lifts",  # Use a valid club name from your JSON data
            "places": 1,
        }
        with self.client.post("/purchase_places", data=data, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 400:
                response.success()
            else:
                response.failure("Got unexpected response code: " + str(response.status_code) + " Error: " + str(response.text))

    @task()
    def logout_and_display_club_points(self):
        """
        Log out the user and access the club points page.

        Sends a GET request to the /clubs endpoint to simulate the user viewing
        the club points page after logging out. The method first ensures the user
        is authenticated before logging them out. If the request fails, it records
        the failure with the appropriate status code and error message.
        """
        self.ensure_authenticated()
        with self.client.get("/clubs", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Got unexpected response code: " + str(response.status_code) + " Error: " + str(response.text))
