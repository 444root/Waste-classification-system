"""Registration, login, logout and profile routes.

Behavior matches Technical Documentation Section 10 (Authentication and
user management): unique normalized email, salted password hashing via
Werkzeug, generic failure messages that never reveal which field was
wrong, an automatically-created Free subscription on registration, and
server-side session invalidation on logout.
"""

import re
from datetime import date

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, Plan, Subscription

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

    db.session.commit()
    login_user(user)
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

    login_user(user)
    return redirect(url_for("main.dashboard"))


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
