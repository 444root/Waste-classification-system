"""Plans and upgrade-request endpoints.

Technical Documentation Section 11: the MVP implements plans, an upgrade
request flow and manual admin activation; real payment collection is
explicitly deferred, so no card or mobile-money integration exists here.
"""

from flask import Blueprint, request, jsonify
from flask_login import current_user

from app.extensions import db
from app.models import Plan, UpgradeRequest
from app.utils import login_required_json

subscriptions_bp = Blueprint("subscriptions", __name__)


@subscriptions_bp.route("/plans", methods=["GET"])
def list_plans():
    plans = Plan.query.filter_by(is_active=True).order_by(Plan.price_rwf.asc()).all()
    return jsonify([
        {"id": p.id, "name": p.name, "price_rwf": p.price_rwf,
         "scan_limit": p.scan_limit, "history_days": p.history_days}
        for p in plans
    ])


@subscriptions_bp.route("/upgrade-requests", methods=["POST"])
@login_required_json
def request_upgrade():
    payload = request.get_json(silent=True) or request.form
    plan_id = payload.get("plan_id")
    plan = db.session.get(Plan, int(plan_id)) if plan_id else None
    if plan is None or not plan.is_active:
        return jsonify({"error": "invalid_plan"}), 400

    existing = UpgradeRequest.query.filter_by(user_id=current_user.id, status="pending").first()
    if existing is not None:
        return jsonify({"error": "request_already_pending"}), 409

    upgrade = UpgradeRequest(user_id=current_user.id, requested_plan_id=plan.id, status="pending")
    db.session.add(upgrade)
    db.session.commit()
    return jsonify({"id": upgrade.id, "status": upgrade.status, "requested_plan": plan.name}), 201
