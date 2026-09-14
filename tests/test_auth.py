"""Integration tests: registration, login, logout (Chapter 4.10.5, IDs AUTH-)."""

from tests.conftest import register, login
from app.models import User, Subscription
from app.extensions import db


def test_auth01_register_creates_user_with_free_plan(app, client):
    resp = register(client)
    assert resp.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        assert user is not None
        assert user.role == "user"
        sub = Subscription.query.filter_by(user_id=user.id).first()
        assert sub is not None
        assert sub.plan.name == "Free"


def test_auth02_duplicate_email_rejected_generically(client):
    register(client, email="dupe@example.com")
    resp = client.post("/auth/register", data={
        "name": "Second Person", "email": "dupe@example.com", "password": "AnotherPass123"
    })
    assert resp.status_code == 400
    assert b"could not be completed" in resp.data


def test_auth03_short_password_rejected(client):
    resp = client.post("/auth/register", data={
        "name": "Weak Pw", "email": "weak@example.com", "password": "abc"
    })
    assert resp.status_code == 400


def test_auth04_wrong_password_gives_generic_error(client):
    register(client, email="loginuser@example.com")
    resp = client.post("/auth/login", data={"email": "loginuser@example.com", "password": "WrongPass1"})
    assert resp.status_code == 401
    assert b"Incorrect email or password" in resp.data


def test_auth05_login_then_logout_denies_dashboard(app, client):
    register(client, email="logout@example.com")
    client.post("/auth/logout", follow_redirects=True)
    resp = client.get("/dashboard", follow_redirects=False)
    assert resp.status_code == 302  # redirected to login, session invalidated


def test_auth06_suspended_account_cannot_log_in(app, client):
    register(client, email="suspend@example.com")
    with app.app_context():
        user = User.query.filter_by(email="suspend@example.com").first()
        user.status = "suspended"
        db.session.commit()
    client.post("/auth/logout", follow_redirects=True)
    resp = client.post("/auth/login", data={"email": "suspend@example.com", "password": "TestPass123"})
    assert resp.status_code == 403
