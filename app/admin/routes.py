"""Administrative endpoints: user management and model version registry.

Technical Documentation Section 05: admins can search, inspect, activate,
suspend, change role and assign a plan; every one of those actions is
audited. Section 09/13: only a ModelVersion with a stored evaluation
report meeting the accuracy gate may be activated -- a version cannot be
"turned on" by an administrator simply asserting it works.
"""

from flask import Blueprint, request, jsonify
from flask_login import current_user

from app.extensions import db
from app.models import User, Plan, Subscription, ModelVersion, UpgradeRequest
from app.utils import admin_required, record_audit

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users", methods=["GET"])
@admin_required
def search_users():
    query = User.query
    email_term = request.args.get("email")
    if email_term:
        query = query.filter(User.email.ilike(f"%{email_term}%"))
    status_term = request.args.get("status")
    if status_term:
        query = query.filter_by(status=status_term)

    users = query.order_by(User.created_at.desc()).limit(100).all()
    return jsonify([
        {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "status": u.status}
        for u in users
    ])


@admin_bp.route("/users/<int:user_id>", methods=["PATCH"])
@admin_required
def update_user(user_id):
    target = db.session.get(User, user_id)
    if target is None:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or request.form
    changes = []

    new_status = payload.get("status")
    if new_status in {"active", "suspended"} and new_status != target.status:
        target.status = new_status
        changes.append(f"status={new_status}")

    new_role = payload.get("role")
    if new_role in {"user", "admin"} and new_role != target.role:
        target.role = new_role
        changes.append(f"role={new_role}")

    new_plan_id = payload.get("plan_id")
    if new_plan_id:
        plan = db.session.get(Plan, int(new_plan_id))
        if plan is None:
            return jsonify({"error": "invalid_plan"}), 400
        active_sub = target.active_subscription()
        if active_sub is not None:
            active_sub.plan_id = plan.id
        else:
            db.session.add(Subscription(user_id=target.id, plan_id=plan.id, status="active"))
        changes.append(f"plan={plan.name}")

    db.session.commit()
    record_audit(current_user.id, "admin_update_user", "user", target.id, "; ".join(changes) or "no-op")
    return jsonify({"id": target.id, "status": target.status, "role": target.role})


@admin_bp.route("/upgrade-requests/<int:request_id>", methods=["PATCH"])
@admin_required
def review_upgrade_request(request_id):
    from datetime import datetime

    upgrade = db.session.get(UpgradeRequest, request_id)
    if upgrade is None:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(silent=True) or request.form
    decision = payload.get("decision")
    if decision not in {"approved", "rejected"}:
        return jsonify({"error": "invalid_decision"}), 400

    upgrade.status = decision
    upgrade.reviewed_by = current_user.id
    upgrade.reviewed_at = datetime.utcnow()

    if decision == "approved":
        active_sub = upgrade.user.active_subscription()
        if active_sub is not None:
            active_sub.plan_id = upgrade.requested_plan_id
        else:
            db.session.add(Subscription(user_id=upgrade.user_id, plan_id=upgrade.requested_plan_id, status="active"))

    db.session.commit()
    record_audit(current_user.id, f"upgrade_request_{decision}", "upgrade_request", upgrade.id)
    return jsonify({"id": upgrade.id, "status": upgrade.status})


@admin_bp.route("/statistics", methods=["GET"])
@admin_required
def admin_statistics():
    from app.models import Prediction

    total_users = User.query.count()
    active_users = User.query.filter_by(status="active").count()
    total_predictions = Prediction.query.count()
    uncertain_predictions = Prediction.query.filter_by(is_uncertain=True).count()
    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "total_predictions": total_predictions,
        "uncertain_predictions": uncertain_predictions,
    })


@admin_bp.route("/model-versions", methods=["POST"])
@admin_required
def register_model_version():
    payload = request.get_json(silent=True) or request.form
    version = payload.get("version")
    if not version:
        return jsonify({"error": "version_required"}), 400

    if ModelVersion.query.filter_by(version=version).first() is not None:
        return jsonify({"error": "version_already_exists"}), 409

    model_version = ModelVersion(
        version=version,
        artifact_path=payload.get("artifact_path"),
        labels_version=payload.get("labels_version"),
        threshold=float(payload.get("threshold", 0.70)),
        accuracy=float(payload["accuracy"]) if payload.get("accuracy") else None,
        macro_f1=float(payload["macro_f1"]) if payload.get("macro_f1") else None,
        evaluation_report_path=payload.get("evaluation_report_path"),
        is_active=False,
    )
    db.session.add(model_version)
    db.session.commit()

    activate = payload.get("activate") in (True, "true", "1", 1)
    if activate:
        if not model_version.meets_evaluation_gate():
            return jsonify({
                "error": "evaluation_gate_not_met",
                "message": "A model version can only be activated once it has a stored "
                           "evaluation report with held-out accuracy of at least 85%.",
                "id": model_version.id,
            }), 422
        ModelVersion.query.filter(ModelVersion.id != model_version.id).update({"is_active": False})
        model_version.is_active = True
        db.session.commit()
        record_audit(current_user.id, "activate_model_version", "model_version", model_version.id, version)

    return jsonify({"id": model_version.id, "version": model_version.version, "is_active": model_version.is_active}), 201
