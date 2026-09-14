"""Tests for the forgot-password / reset-password flow.

Covers: generic response whether or not the email exists (no account
enumeration, matching the same principle already used by login/register),
the token actually working end-to-end to change a password, the token
being single-use (it embeds a stamp of the current password hash, so it
self-invalidates the moment the password changes), and expired/invalid
tokens being rejected.
"""

import app.auth.routes as auth_routes
from app.models import AuditLog, User
from app.utils import generate_reset_token, verify_reset_token
from tests.conftest import register, login


def test_pwreset01_request_for_existing_email_sends_an_email_and_is_generic(app, client, monkeypatch):
    sent = {}

    def fake_send_email(to_address, subject, body):
        sent["to_address"] = to_address
        sent["subject"] = subject
        sent["body"] = body
        return True

    monkeypatch.setattr(auth_routes, "send_email", fake_send_email)
    register(client, email="resetme@example.com")
    client.post("/auth/logout")

    resp = client.post("/auth/forgot-password", data={"email": "resetme@example.com"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"a password reset link has been sent" in resp.data
    assert sent["to_address"] == "resetme@example.com"
    assert "/auth/reset-password/" in sent["body"]


def test_pwreset02_request_for_nonexistent_email_gives_same_generic_message_and_sends_nothing(app, client, monkeypatch):
    calls = []
    monkeypatch.setattr(auth_routes, "send_email", lambda **kw: calls.append(kw))

    resp = client.post("/auth/forgot-password", data={"email": "nobody-here@example.com"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"a password reset link has been sent" in resp.data
    assert calls == []  # no email sent for an account that doesn't exist


def test_pwreset03_valid_token_lets_the_user_set_a_new_password_and_log_in_with_it(app, client):
    register(client, email="resetflow@example.com", password="OldPass123")
    client.post("/auth/logout")

    with app.app_context():
        user = User.query.filter_by(email="resetflow@example.com").first()
        token = generate_reset_token(user)
        user_id = user.id

    resp = client.post(f"/auth/reset-password/{token}",
                        data={"password": "NewPass456", "confirm_password": "NewPass456"},
                        follow_redirects=True)
    assert resp.status_code == 200
    assert b"Your password has been reset" in resp.data

    # Old password no longer works, new one does.
    fail_login = login(client, email="resetflow@example.com", password="OldPass123")
    assert b"Incorrect email or password" in fail_login.data

    ok_login = login(client, email="resetflow@example.com", password="NewPass456")
    assert ok_login.status_code == 200
    assert b"Incorrect email or password" not in ok_login.data

    with app.app_context():
        entry = AuditLog.query.filter_by(action="password_reset", target_id=user_id).first()
        assert entry is not None


def test_pwreset04_token_cannot_be_used_twice(app, client):
    register(client, email="reusetoken@example.com", password="OldPass123")
    client.post("/auth/logout")

    with app.app_context():
        user = User.query.filter_by(email="reusetoken@example.com").first()
        token = generate_reset_token(user)

    first = client.post(f"/auth/reset-password/{token}",
                         data={"password": "FirstNew123", "confirm_password": "FirstNew123"},
                         follow_redirects=True)
    assert b"Your password has been reset" in first.data

    second = client.post(f"/auth/reset-password/{token}",
                          data={"password": "SecondNew123", "confirm_password": "SecondNew123"},
                          follow_redirects=True)
    assert b"invalid or has expired" in second.data

    # The first reset's password is still the one that works.
    ok_login = login(client, email="reusetoken@example.com", password="FirstNew123")
    assert b"Incorrect email or password" not in ok_login.data


def test_pwreset05_mismatched_confirmation_is_rejected(app, client):
    register(client, email="mismatch@example.com")
    client.post("/auth/logout")
    with app.app_context():
        user = User.query.filter_by(email="mismatch@example.com").first()
        token = generate_reset_token(user)

    resp = client.post(f"/auth/reset-password/{token}",
                        data={"password": "SomePass123", "confirm_password": "Different123"})
    assert resp.status_code == 400
    assert b"Passwords do not match" in resp.data


def test_pwreset06_expired_token_is_rejected(app, client):
    register(client, email="expired@example.com")
    with app.app_context():
        user = User.query.filter_by(email="expired@example.com").first()
        token = generate_reset_token(user)
        # max_age=-1 simulates a token that expired the instant it was issued.
        assert verify_reset_token(token, max_age=-1) is None


def test_pwreset07_garbage_token_is_rejected(client):
    resp = client.get("/auth/reset-password/not-a-real-token", follow_redirects=True)
    assert b"invalid or has expired" in resp.data
