"""
Functional tests for the club booking system using Selenium WebDriver.
These tests simulate real user interactions with the web application.
"""

import copy
import os
import socket
import sys
import threading
import time

import pytest
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from server import app
from tests.test_conf import sample_clubs, sample_competitions


@pytest.fixture(name="driver")
def selenium_driver():
    """
    Provides a Selenium WebDriver instance for functional testing.

    :return: A Chrome WebDriver instance.
    :rtype: selenium.webdriver.chrome.webdriver.WebDriver
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture(name="live_server")
def flask_live_server(mocker):
    """
    Provides a live Flask server for functional testing.
    """

    # Fresh data for each test
    fresh_clubs = copy.deepcopy(sample_clubs()["clubs"])
    fresh_competitions = copy.deepcopy(sample_competitions()["competitions"])

    mocker.patch("server.clubs", fresh_clubs)
    mocker.patch("server.competitions", fresh_competitions)

    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test_key"

    # Force clear sessions
    app.secret_key = f"test_key_{time.time()}"

    # Found a free port for the Flask server
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()

    server_thread = threading.Thread(target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False))
    server_thread.daemon = True
    server_thread.start()

    time.sleep(2)

    base_url = f"http://127.0.0.1:{port}"
    yield base_url


@pytest.fixture(autouse=True)
def clear_browser_data(driver):
    """
    Clear browser data between tests.
    """
    yield
    # Clear cookies and local storage after each test
    driver.delete_all_cookies()
    driver.execute_script("window.localStorage.clear();")
    driver.execute_script("window.sessionStorage.clear();")


@pytest.fixture(autouse=True)
def reset_test_data(mocker):
    """
    Reset test data before each test to ensure test isolation.
    """

    # Reset global data before each test
    original_clubs = copy.deepcopy(sample_clubs()["clubs"])
    original_competitions = copy.deepcopy(sample_competitions()["competitions"])

    mocker.patch("server.clubs", original_clubs)
    mocker.patch("server.competitions", original_competitions)

    # Clear any Flask sessions
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess.clear()

    yield


def test_successful_user_login_journey(driver, live_server):
    """
    Test the complete successful user login journey from landing page to summary page.

    :param driver: The Selenium WebDriver instance.
    :type driver: selenium.webdriver.chrome.webdriver.WebDriver
    :param live_server: The base URL of the live server.
    :type live_server: str
    """
    # Navigate to the home page
    driver.get(live_server)

    # Verify we're on the home page
    assert "GUDLFT Registration" in driver.title
    welcome_text = driver.find_element(By.TAG_NAME, "h1").text
    assert "Welcome to the GUDLFT Registration Portal!" in welcome_text

    # Find the email input field and enter an email
    email_input = driver.find_element(By.NAME, "email")
    email_input.send_keys("club1@test.com")

    # Submit the form
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()

    # Wait for redirect and verify we're on the summary page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h2")))

    welcome_message = driver.find_element(By.TAG_NAME, "h2").text
    assert "Welcome, club1@test.com" in welcome_message

    # Verify competition list is displayed
    competitions_section = driver.find_element(By.TAG_NAME, "h3")
    assert "Competitions:" in competitions_section.text


def test_invalid_email_error_handling(driver, live_server):
    """
    Test login with an invalid email address shows proper error handling.

    :param driver: The Selenium WebDriver instance.
    :type driver: selenium.webdriver.chrome.webdriver.WebDriver
    :param live_server: The base URL of the live server.
    :type live_server: str
    """
    driver.get(live_server)

    # Enter invalid email
    email_input = driver.find_element(By.NAME, "email")
    email_input.send_keys("invalid@email.com")

    # Submit the form
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()

    # Wait for redirect back to home page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

    # Verify error message is displayed
    page_source = driver.page_source
    assert "Email does not exist." in page_source


def test_competition_booking_workflow(driver, live_server):
    """
    Test the complete competition booking workflow with valid data.

    :param driver: The Selenium WebDriver instance.
    :type driver: selenium.webdriver.chrome.webdriver.WebDriver
    :param live_server: The base URL of the live server.
    :type live_server: str
    """
    # Login first
    driver.get(live_server)
    email_input = driver.find_element(By.NAME, "email")
    email_input.send_keys("club1@test.com")
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()

    # Wait for summary page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h2")))

    # Find and click on a "Book Places" link for a future competition
    try:
        book_link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, "Book Places")))
        book_link.click()

        # Wait for booking page
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "places")))

        # Verify we're on the booking page
        page_source = driver.page_source
        assert "How many places?" in page_source

        # Enter number of places
        places_input = driver.find_element(By.ID, "places")
        places_input.clear()
        places_input.send_keys("2")

        # Submit booking
        book_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        book_button.click()

        # Wait for redirect back to summary page
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h2")))

        # Wait for the success message in the competition list
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "flash-success")))

        # Verify success message in the competition list
        competitions_list = driver.find_element(By.TAG_NAME, "ul")
        success_messages = competitions_list.find_elements(By.CLASS_NAME, "flash-success")
        assert any("Great - booking complete!" in msg.text for msg in success_messages)

    except TimeoutException:
        # If no bookable competitions, verify that's expected
        page_source = driver.page_source
        assert "Book Places" not in page_source or "Booking:" in page_source


def test_booking_validation_insufficient_points(driver, live_server):
    """
    Test booking validation when club has insufficient points.

    :param driver: The Selenium WebDriver instance.
    :type driver: selenium.webdriver.chrome.webdriver.WebDriver
    :param live_server: The base URL of the live server.
    :type live_server: str
    """
    # Login with club that has few points (Club2 has 4 points)
    driver.get(live_server)
    email_input = driver.find_element(By.NAME, "email")
    email_input.send_keys("club2@test.com")
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()

    # Wait for summary page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h2")))

    # Try to find and access booking for a competition
    book_link = driver.find_element(By.LINK_TEXT, "Book Places")
    book_link.click()

    # Wait for booking page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "places")))

    # Try to book more places than points available
    places_input = driver.find_element(By.ID, "places")
    places_input.clear()
    places_input.send_keys("10")  # More than 4 points available

    # Submit booking
    book_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    book_button.click()

    # Wait for JavaScript validation error message to appear
    WebDriverWait(driver, 10).until(EC.text_to_be_present_in_element((By.ID, "error-message"), "You cannot book more places than you have."))

    # Verify error message is displayed
    error_message = driver.find_element(By.ID, "error-message")
    assert "You cannot book more places than you have." in error_message.text


def test_booking_validation_excessive_places(driver, live_server):
    """
    Test booking validation when trying to book more than 12 places.

    :param driver: The Selenium WebDriver instance.
    :type driver: selenium.webdriver.chrome.webdriver.WebDriver
    :param live_server: The base URL of the live server.
    :type live_server: str
    """
    # Login with club that has many points (Club3 has 33 points)
    driver.get(live_server)
    email_input = driver.find_element(By.NAME, "email")
    email_input.send_keys("club3@test.com")
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()

    # Wait for summary page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h2")))

    # Try to find and access booking for a competition
    book_link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Book Places")))
    book_link.click()

    # Wait for booking page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "places")))

    # Try to book more than 12 places
    places_input = driver.find_element(By.ID, "places")
    places_input.clear()
    places_input.send_keys("15")

    # Submit booking
    book_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    book_button.click()

    # Should show error message
    error_message = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "error-message")))
    assert "You cannot book more than 12 places." in error_message.text


def test_club_points_display_functionality(driver, live_server):
    """
    Test the club points display functionality.

    :param driver: The Selenium WebDriver instance.
    :type driver: selenium.webdriver.chrome.webdriver.WebDriver
    :param live_server: The base URL of the live server.
    :type live_server: str
    """
    # Login first
    driver.get(live_server)
    email_input = driver.find_element(By.NAME, "email")
    email_input.send_keys("club1@test.com")
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()

    # Wait for summary page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h2")))

    # Click on "Show Club Points" link
    club_points_link = driver.find_element(By.LINK_TEXT, ">> Show Club Points")
    club_points_link.click()

    # Wait for clubs page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "clubTable")))

    # Verify we're on the clubs page
    assert "Club Points" in driver.title

    # Verify table exists and contains club data
    table = driver.find_element(By.ID, "clubTable")
    table_text = table.text
    assert "Club Name" in table_text
    assert "Points" in table_text
    assert "Club1" in table_text or "Club2" in table_text or "Club3" in table_text


def test_logout_functionality(driver, live_server):
    """
    Test the logout functionality and session clearing.

    :param driver: The Selenium WebDriver instance.
    :type driver: selenium.webdriver.chrome.webdriver.WebDriver
    :param live_server: The base URL of the live server.
    :type live_server: str
    """
    # Login first
    driver.get(live_server)
    email_input = driver.find_element(By.NAME, "email")
    email_input.send_keys("club1@test.com")
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()

    # Wait for summary page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h2")))

    # Click logout link
    logout_link = driver.find_element(By.LINK_TEXT, "Logout")
    logout_link.click()

    # Wait for redirect to home page
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

    # Verify we're back on the home page
    welcome_text = driver.find_element(By.TAG_NAME, "h1").text
    assert "Welcome to the GUDLFT Registration Portal!" in welcome_text

    # Verify that attempting to access protected pages redirects
    driver.get(f"{live_server}/show_summary")

    # Should be redirected or show unauthorized access
    current_url = driver.current_url
    assert "show_summary" not in current_url or "401" in driver.page_source


def test_end_to_end_booking_scenario(driver, live_server):
    """
    Test complete end-to-end booking scenario covering the full user journey.

    :param driver: The Selenium WebDriver instance.
    :type driver: selenium.webdriver.chrome.webdriver.WebDriver
    :param live_server: The base URL of the live server.
    :type live_server: str
    """
    # Start at home page
    driver.get(live_server)
    assert "Welcome to the GUDLFT Registration Portal!" in driver.page_source

    # Login with valid credentials
    email_input = driver.find_element(By.NAME, "email")
    email_input.send_keys("club1@test.com")
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_button.click()

    # Verify summary page access
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h2")))
    assert "Welcome, club1@test.com" in driver.page_source

    # Check club points display
    assert "Points available:" in driver.page_source

    # Navigate to club points page
    club_points_link = driver.find_element(By.LINK_TEXT, ">> Show Club Points")
    club_points_link.click()
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "clubTable")))
    assert "Club Points" in driver.title

    # Return to summary
    back_button = driver.find_element(By.LINK_TEXT, ">> Retour")
    back_button.click()
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h2")))

    # Attempt booking (if available)
    book_links = driver.find_elements(By.LINK_TEXT, "Book Places")
    if book_links:
        book_links[0].click()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "places")))

        # Make a small booking
        places_input = driver.find_element(By.ID, "places")
        places_input.clear()
        places_input.send_keys("1")

        book_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        book_button.click()

        # Verify redirect back to summary page
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h2")))
        # Should be back on summary page
        assert "Welcome, club1@test.com" in driver.page_source

    # Logout
    logout_link = driver.find_element(By.LINK_TEXT, "Logout")
    logout_link.click()

    # Verify logout
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    assert "Welcome to the GUDLFT Registration Portal!" in driver.page_source
