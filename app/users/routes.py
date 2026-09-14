"""Self-service profile management.

Technical Documentation Section 10: "User can update name and change
password after confirming the current password."
"""

from flask import Blueprint, request, jsonify
from flask_login import current_user

from app.extensions import db
from app.auth.routes import password_is_acceptable
from app.utils import login_required_json

users_bp = Blueprint("users", __name__)


@users_bp.route("/me", methods=["PATCH"])
@login_required_json
def update_me():
    payload = request.get_json(silent=True) or request.form

    name = payload.get("name")
    if name:
        current_user.name = name.strip()

    new_password = payload.get("new_password")
    if new_password:
        current_password = payload.get("current_password") or ""
        if not current_user.check_password(current_password):
            return jsonify({"error": "current_password_incorrect"}), 403
        if not password_is_acceptable(new_password):
            return jsonify({"error": "weak_password"}), 400
        current_user.set_password(new_password)

    db.session.commit()
    return jsonify({"id": current_user.id, "name": current_user.name, "email": current_user.email})
