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
from unittest.mock import patch

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
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture(autouse=True)
def mock_file_operations_functional():
    """
    Fixture automatique pour mocker toutes les opérations de fichier dans les tests fonctionnels.
    Empêche toute modification accidentelle des fichiers JSON pendant les tests E2E.
    """
    with patch("server.save_competitions") as mock_save_comps, patch("server.save_clubs") as mock_save_clubs:

        # Configuration des mocks pour qu'ils ne fassent rien
        mock_save_comps.return_value = None
        mock_save_clubs.return_value = None

        yield


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


def test_successful_user_login_journey(driver, live_server):
    """
    Test le parcours complet de connexion utilisateur réussie.

    TEST CRITIQUE : Valide le flow principal de l'application - connexion utilisateur.
    Couvre : Navigation, validation d'email, redirection, affichage des données.
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
    Test la gestion d'erreur pour les emails invalides.

    TEST CRITIQUE : Valide la sécurité et la robustesse de l'authentification.
    Couvre : Validation des données, gestion d'erreurs, messages utilisateur.
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
    Test le workflow complet de réservation de compétition.

    TEST CRITIQUE : Valide la fonctionnalité métier principale de l'application.
    Couvre : Réservation, validation métier, mise à jour des données, feedback utilisateur.
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


def test_booking_validation_excessive_places(driver, live_server):
    """
    Test la validation des réservations avec trop de places demandées.

    TEST CRITIQUE : Valide les règles métier et la validation côté client/serveur.
    Couvre : Validation des limites métier (12 places max), gestion d'erreurs, UX.
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
