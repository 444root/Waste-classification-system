"""Drives the actual running Flask application with headless Chromium and
saves real screenshots of every reachable screen for Chapter Four. No
screen state requiring a trained model (an "accepted" or "low-confidence"
classification result, or a confusion matrix) is captured, because none
of those states can currently be produced honestly -- see the note in
app/classifier/inference.py and Chapter Four, Section 4.4.
"""

import os
import re
import time

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5055"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")
SAMPLE_IMAGE = "/tmp/sample_plastic_bottle.jpg"

os.makedirs(OUT_DIR, exist_ok=True)


def shot(page, name):
    path = os.path.join(OUT_DIR, name)
    page.screenshot(path=path, full_page=True)
    print("saved", name)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        page.goto(f"{BASE_URL}/")
        shot(page, "ch4_01_landing.png")

        page.goto(f"{BASE_URL}/auth/register")
        shot(page, "ch4_02_register.png")

        page.goto(f"{BASE_URL}/auth/login")
        shot(page, "ch4_03_login.png")

        # Log in as the seeded demo user to reach authenticated screens.
        page.fill("#email", "demo@wcs.local")
        page.fill("#password", "DemoPass123!")
        page.click("#login-submit-btn")
        page.wait_for_url(f"{BASE_URL}/dashboard")
        shot(page, "ch4_04_dashboard.png")

        page.goto(f"{BASE_URL}/classify")
        shot(page, "ch4_05_upload.png")

        page.set_input_files("#image", SAMPLE_IMAGE)
        page.click("#classify-submit-btn")
        page.wait_for_load_state("networkidle")
        shot(page, "ch4_06_result_model_unavailable.png")

        page.goto(f"{BASE_URL}/history")
        shot(page, "ch4_07_history.png")

        # Feedback screen for the freshly created (non-placeholder) record.
        links = page.get_by_role("link", name="Correct this")
        if links.count() > 0:
            links.first.click()
            page.wait_for_load_state("networkidle")
            shot(page, "ch4_08_feedback.png")
        else:
            print("WARNING: no 'Correct this' link found on history page")

        page.goto(f"{BASE_URL}/plans")
        shot(page, "ch4_09_plans.png")

        page.locator("nav button", has_text="Log out").click()
        page.wait_for_url(f"{BASE_URL}/")

        # Admin screens
        page.goto(f"{BASE_URL}/auth/login")
        page.fill("#email", "admin@wcs.local")
        page.fill("#password", "ChangeMe123!")
        page.click("#login-submit-btn")
        page.wait_for_url(f"{BASE_URL}/dashboard")

        page.goto(f"{BASE_URL}/admin/users")
        shot(page, "ch4_10_admin_users.png")

        browser.close()


if __name__ == "__main__":
    run()
