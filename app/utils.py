"""Cross-cutting helpers: authorization decorators, audit logging, password
reset tokens and email sending.

Technical Documentation Section 05 ("Authorization rules"): administrative
checks must be enforced on the server, all protected routes verify both an
authenticated session and an active account, and important admin actions
are written to an audit log with actor, action, target and timestamp.
"""

import os
import smtplib
from email.mime.text import MIMEText
from functools import wraps

from flask import current_app, jsonify
from flask_login import current_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.extensions import db
from app.models import AuditLog


def login_required_json(view_func):
    """Like Flask-Login's login_required, but returns JSON 401 instead of
    redirecting to a login page, for use on the JSON API surface."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "authentication_required"}), 401
        if not current_user.is_active_account:
            return jsonify({"error": "account_inactive"}), 403
        return view_func(*args, **kwargs)

    return wrapped


def admin_required(view_func):
    """Enforces the admin role on the server, independent of anything the
    browser does or does not show (Section 05, 'hiding an admin button in
    the browser is not security')."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "authentication_required"}), 401
        if not current_user.is_active_account:
            return jsonify({"error": "account_inactive"}), 403
        if not current_user.is_admin:
            return jsonify({"error": "forbidden"}), 403
        return view_func(*args, **kwargs)

    return wrapped


def record_audit(actor_user_id, action, target_type, target_id=None, details=None):
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


# ---------------------------------------------------------------------------
# Password reset: self-invalidating signed tokens + email sending.
#
# The token embeds the user id and a short "stamp" derived from the
# CURRENT password hash, both signed with the app's SECRET_KEY. Once the
# password actually changes, the stamp in any previously issued token no
# longer matches, so a token can only ever be used once -- without needing
# a database column or table to track used/unused tokens. This is the same
# technique Django's PasswordResetTokenGenerator and Flask-Security use.
# ---------------------------------------------------------------------------

RESET_TOKEN_SALT = "password-reset"
RESET_TOKEN_MAX_AGE_SECONDS = 3600  # 1 hour


def _reset_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_reset_token(user):
    payload = {"user_id": user.id, "pw_stamp": user.password_hash[-12:]}
    return _reset_serializer().dumps(payload, salt=RESET_TOKEN_SALT)


def verify_reset_token(token, max_age=RESET_TOKEN_MAX_AGE_SECONDS):
    """Returns the User the token was issued for, or None if the token is
    invalid, expired, or the password has already been changed since it
    was issued (including by a previous use of this same token)."""
    from app.models import User  # local import avoids a circular import

    try:
        payload = _reset_serializer().loads(token, salt=RESET_TOKEN_SALT, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None

    user = db.session.get(User, payload.get("user_id"))
    if user is None or user.password_hash[-12:] != payload.get("pw_stamp"):
        return None
    return user


def send_email(to_address, subject, body):
    """Sends a plain-text email via SMTP if WCS_SMTP_HOST is configured in
    the environment. If it is not configured (local development, the
    automated test suite, or a deployment where SMTP hasn't been set up
    yet), the email is logged instead of sent -- never silently dropped,
    and never faked as "sent" when it wasn't. Returns True if an actual
    send was attempted, False if it was only logged.
    """
    host = os.environ.get("WCS_SMTP_HOST")
    if not host:
        current_app.logger.info(
            "Email not sent (WCS_SMTP_HOST not configured) -- To: %s | Subject: %s\n%s",
            to_address, subject, body,
        )
        return False

    port = int(os.environ.get("WCS_SMTP_PORT", "587"))
    username = os.environ.get("WCS_SMTP_USERNAME")
    password = os.environ.get("WCS_SMTP_PASSWORD")
    from_address = os.environ.get("WCS_MAIL_FROM", username or "no-reply@localhost")

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = from_address
    message["To"] = to_address

    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls()
        if username and password:
            server.login(username, password)
        server.sendmail(from_address, [to_address], message.as_string())
    return True
