"""
Automated screenshot generator for Distributed IoT Device Management Architecture.
Uses Selenium with headless Chrome/Edge to capture high-definition screenshots of each page.
"""

import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

BASE_URL = "http://localhost:8503"

PAGES = [
    ("01_overview.png", f"{BASE_URL}/?page=Overview", "Fleet Operational Overview"),
    ("02_device_registry.png", f"{BASE_URL}/?page=Device+Registry", "IoT Device Registry"),
    ("03_telemetry_analytics.png", f"{BASE_URL}/?page=Telemetry+%26+Analytics", "Telemetry Analytics & Historical Trends"),
    ("04_control_center.png", f"{BASE_URL}/?page=Control+Center", "Device Control Center & Remote Operations"),
]


def get_driver():
    try:
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        print(f"Chrome failed: {e}. Trying Edge...")

    edge_options = EdgeOptions()
    edge_options.add_argument("--headless=new")
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    driver = webdriver.Edge(options=edge_options)
    return driver


def wait_for_streamlit(driver, timeout=12):
    """Waits for Streamlit to finish rendering and running scripts."""
    time.sleep(2)
    start = time.time()
    while time.time() - start < timeout:
        # Check if the 'RUNNING...' status widget exists
        running_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'RUNNING...')]")
        if not running_elements:
            break
        time.sleep(0.5)
    # Extra pause to ensure charts and tables render fully
    time.sleep(2.5)


def capture_all():
    print("Launching headless browser...")
    driver = get_driver()
    driver.set_window_size(1920, 1080)

    try:
        # Warm-up visit to ensure database connection and initial state are ready
        driver.get(BASE_URL)
        time.sleep(3)

        for filename, url, label in PAGES:
            print(f"Navigating to {label}: {url}...")
            driver.get(url)
            wait_for_streamlit(driver)

            output_path = os.path.join(SCREENSHOTS_DIR, filename)
            driver.save_screenshot(output_path)
            size_kb = os.path.getsize(output_path) / 1024
            print(f"Saved: {filename} ({size_kb:.1f} KB)")

        print("All screenshots successfully captured!")
    finally:
        driver.quit()


if __name__ == "__main__":
    capture_all()
