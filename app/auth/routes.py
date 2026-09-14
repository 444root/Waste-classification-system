"""Registration, login, logout and profile routes.

Behavior matches Technical Documentation Section 10 (Authentication and
user management): unique normalized email, salted password hashing via
Werkzeug, generic failure messages that never reveal which field was
wrong, an automatically-created Free subscription on registration, and
server-side session invalidation on logout.
"""

import re
from datetime import date, datetime

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, Plan, Subscription
from app.utils import generate_reset_token, verify_reset_token, send_email, record_audit

auth_bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(raw_email):
    return raw_email.strip().lower()


def password_is_acceptable(raw_password):
    """Minimum password policy: at least 8 characters. Kept simple and
    documented rather than silently strict, per Section 13's requirement
    that controls be explicit and testable."""
    return isinstance(raw_password, str) and len(raw_password) >= 8


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = (request.form.get("name") or "").strip()
    email = normalize_email(request.form.get("email") or "")
    password = request.form.get("password") or ""

    if not name or not EMAIL_RE.match(email) or not password_is_acceptable(password):
        flash("Please provide a valid name, email address and a password of at least 8 characters.", "error")
        return render_template("register.html"), 400

    if User.query.filter_by(email=email).first() is not None:
        # Generic message: do not reveal that the account already exists.
        flash("Registration could not be completed with the information provided.", "error")
        return render_template("register.html"), 400

    user = User(name=name, email=email, role="user", status="active")
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # obtain user.id before creating the subscription

    free_plan = Plan.query.filter_by(name="Free").first()
    if free_plan is not None:
        db.session.add(Subscription(user_id=user.id, plan_id=free_plan.id,
                                     status="active", period_start=date.today()))

    # Bug fix (2026-09-14): registration is this user's first-ever
    # authentication, so mark it as such (see login() below and
    # app/main/routes.py dashboard()) instead of dashboard.html
    # unconditionally saying "Welcome back".
    user.last_login_at = datetime.utcnow()
    db.session.commit()
    login_user(user)
    session["show_first_login_welcome"] = True
    return redirect(url_for("main.dashboard"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = normalize_email(request.form.get("email") or "")
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email).first()
    generic_error = "Incorrect email or password."

    if user is None or not user.check_password(password):
        flash(generic_error, "error")
        return render_template("login.html"), 401

    if not user.is_active_account:
        flash(generic_error, "error")
        return render_template("login.html"), 403

    # Bug fix (2026-09-14): capture whether this is the account's first-ever
    # login (last_login_at not yet set) BEFORE overwriting it, so the
    # dashboard can show "Welcome" instead of "Welcome back" exactly once.
    is_first_login = user.last_login_at is None
    user.last_login_at = datetime.utcnow()
    db.session.commit()

    login_user(user)
    session["show_first_login_welcome"] = is_first_login
    return redirect(url_for("main.dashboard"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html")

    email = normalize_email(request.form.get("email") or "")
    user = User.query.filter_by(email=email).first() if EMAIL_RE.match(email) else None

    if user is not None and user.is_active_account:
        token = generate_reset_token(user)
        reset_url = url_for("auth.reset_password", token=token, _external=True)
        send_email(
            to_address=user.email,
            subject="Reset your Waste Classification System password",
            body=(
                f"Hello {user.name},\n\n"
                f"Use the link below to reset your password. It expires in 1 hour and can "
                f"only be used once.\n\n{reset_url}\n\n"
                f"If you didn't request this, you can safely ignore this email."
            ),
        )

    # Same message whether or not the account exists, to avoid revealing
    # which email addresses are registered (same principle as login/register
    # above -- generic messages that don't leak account existence).
    flash(
        "If an account exists for that email address, a password reset link has been sent.",
        "success",
    )
    return redirect(url_for("auth.login"))


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = verify_reset_token(token)
    if user is None:
        flash("That password reset link is invalid or has expired. Please request a new one.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "GET":
        return render_template("reset_password.html", token=token)

    password = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not password_is_acceptable(password):
        flash("Password must be at least 8 characters long.", "error")
        return render_template("reset_password.html", token=token), 400
    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return render_template("reset_password.html", token=token), 400

    user.set_password(password)
    db.session.commit()
    record_audit(actor_user_id=user.id, action="password_reset", target_type="user", target_id=user.id)

    flash("Your password has been reset. Please log in with your new password.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.landing"))


@auth_bp.route("/api/me", methods=["GET"])
@login_required
def me():
    sub = current_user.active_subscription()
    return jsonify({
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "status": current_user.status,
        "plan": sub.plan.name if sub else None,
    })
