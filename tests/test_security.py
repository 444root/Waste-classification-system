"""Security tests: CSRF enforcement (Chapter 4.10.5, IDs SEC-).

CSRF protection is disabled in TestConfig for the functional tests above
(the standard, documented Flask-WTF testing practice) so that business
logic can be exercised without hand-rolling tokens for every request.
This file uses a dedicated app instance with CSRF enabled -- matching
what actually runs in production/demo mode -- specifically to prove the
protection itself works.
"""

import re

from app import create_app
from app.extensions import db
from app.models import Plan
from config import Config


class CSRFEnabledTestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = True


def _csrf_app():
    application = create_app(CSRFEnabledTestConfig)
    with application.app_context():
        db.create_all()
        db.session.add(Plan(name="Free", price_rwf=0, scan_limit=5, history_days=7, is_active=True))
        db.session.commit()
    return application


def test_sec01_registration_without_csrf_token_is_rejected():
    app = _csrf_app()
    client = app.test_client()
    resp = client.post("/auth/register", data={
        "name": "No Token", "email": "notoken@example.com", "password": "TestPass123"
    })
    assert resp.status_code == 400


def test_sec02_registration_with_valid_csrf_token_succeeds():
    app = _csrf_app()
    client = app.test_client()
    get_resp = client.get("/auth/register")
    token = re.search(r'name="csrf_token" value="([^"]+)"', get_resp.get_data(as_text=True)).group(1)
    resp = client.post("/auth/register", data={
        "csrf_token": token, "name": "With Token", "email": "withtoken@example.com", "password": "TestPass123"
    }, follow_redirects=True)
    assert resp.status_code == 200


def test_sec03_session_cookie_is_httponly():
    app = _csrf_app()
    client = app.test_client()
    get_resp = client.get("/auth/register")
    token = re.search(r'name="csrf_token" value="([^"]+)"', get_resp.get_data(as_text=True)).group(1)
    post_resp = client.post("/auth/register", data={
        "csrf_token": token, "name": "Cookie Check", "email": "cookie@example.com", "password": "TestPass123"
    })
    set_cookie_headers = post_resp.headers.getlist("Set-Cookie")
    session_cookie_headers = [h for h in set_cookie_headers if h.startswith("session=")]
    assert len(session_cookie_headers) == 1
    assert "HttpOnly" in session_cookie_headers[0]
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
