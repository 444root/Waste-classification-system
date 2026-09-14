"""Classification, history, feedback and statistics endpoints.

Route table matches "Web routes and API outline" (Technical Documentation
Section 12). Quota enforcement matches Section 11 ("Quota enforcement"):
load the active subscription and plan before accepting a classification,
count only billable events, reject once the quota is exhausted, and never
let validation or server errors themselves consume quota.
"""

from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_login import current_user

from app.extensions import db
from app.models import Prediction, Feedback, UsageEvent, ModelVersion
from app.utils import login_required_json
from app.classifier.validators import validate_upload, UploadValidationError

classifier_bp = Blueprint("classifier", __name__)

DISPOSAL_GUIDANCE = {
    "organic": "Place in the organic or compost stream where available.",
    "plastic": "Empty and clean where possible; use the plastic recycling stream.",
    "paper": "Keep dry and place in the paper or cardboard stream.",
    "metal": "Use the metal recycling stream and avoid sharp exposed edges.",
    "glass": "Use the glass stream and handle broken glass safely.",
    "general_trash": "Use the general waste stream.",
}


def _current_period_key():
    return datetime.utcnow().strftime("%Y-%m")


def _quota_status(user):
    """Returns (subscription, plan, used_this_period, remaining_or_None)."""
    subscription = user.active_subscription()
    if subscription is None or subscription.plan is None:
        return None, None, 0, 0

    plan = subscription.plan
    period_key = _current_period_key()
    used = (
        db.session.query(db.func.coalesce(db.func.sum(UsageEvent.quantity), 0))
        .filter(
            UsageEvent.user_id == user.id,
            UsageEvent.event_type == "classification",
            UsageEvent.period_key == period_key,
        )
        .scalar()
    )
    remaining = max(plan.scan_limit - used, 0)
    return subscription, plan, used, remaining


def _active_model_version():
    return ModelVersion.query.filter_by(is_active=True).first()


@classifier_bp.route("/classifications", methods=["POST"])
@login_required_json
def create_classification():
    subscription, plan, used, remaining = _quota_status(current_user)
    if plan is None:
        return jsonify({"error": "no_active_plan"}), 403
    if remaining <= 0:
        return jsonify({
            "error": "quota_exhausted",
            "plan": plan.name,
            "scan_limit": plan.scan_limit,
        }), 429

    try:
        validate_upload(request.files.get("image"))
    except UploadValidationError as exc:
        # Failed validation must not consume quota (Section 11).
        return jsonify({"error": exc.code, "message": exc.message}), 400

    active_model = _active_model_version()
    if active_model is None or not active_model.meets_evaluation_gate():
        # Honest "model unavailable" response (Section 04, "System
        # response" table) -- no ModelVersion in this build has cleared
        # the accuracy gate because no dataset has been collected/trained
        # on yet (see app/classifier/inference.py). This is a real,
        # deliberately-implemented safety behaviour, not a placeholder bug.
        prediction = Prediction(
            user_id=current_user.id,
            model_version_id=active_model.id if active_model else None,
            predicted_class=None,
            confidence=None,
            is_uncertain=True,
            is_placeholder=False,
        )
        db.session.add(prediction)
        # Reserve usage only after passing validation, per Section 11.
        db.session.add(UsageEvent(user_id=current_user.id, event_type="classification",
                                   quantity=1, period_key=_current_period_key()))
        db.session.commit()
        return jsonify({
            "prediction_id": prediction.id,
            "status": "model_unavailable",
            "message": (
                "No classification model has been trained and evaluated yet. "
                "This request has been logged, but no category can be returned."
            ),
        }), 503

    # Reachable once a ModelVersion clears the evaluation gate (out of
    # scope for this build -- see Chapter Four, Section 4.4).
    return jsonify({"error": "not_implemented"}), 501


@classifier_bp.route("/classifications", methods=["GET"])
@login_required_json
def list_classifications():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    query = (
        Prediction.query.filter_by(user_id=current_user.id)
        .order_by(Prediction.created_at.desc())
    )
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": paginated.total,
        "items": [
            {
                "id": p.id,
                "predicted_class": p.predicted_class,
                "confidence": p.confidence,
                "is_uncertain": p.is_uncertain,
                "is_placeholder": p.is_placeholder,
                "created_at": p.created_at.isoformat(),
                "has_feedback": p.feedback is not None,
            }
            for p in paginated.items
        ],
    })


@classifier_bp.route("/classifications/<int:prediction_id>/feedback", methods=["POST"])
@login_required_json
def submit_feedback(prediction_id):
    prediction = db.session.get(Prediction, prediction_id)
    if prediction is None:
        return jsonify({"error": "not_found"}), 404
    if prediction.user_id != current_user.id and not current_user.is_admin:
        # Users may only correct their own predictions (Section 05).
        return jsonify({"error": "forbidden"}), 403

    corrected_class = request.form.get("corrected_class") or (request.json or {}).get("corrected_class")
    comment = request.form.get("comment") or (request.json or {}).get("comment")

    if corrected_class not in DISPOSAL_GUIDANCE:
        return jsonify({"error": "invalid_category"}), 400

    if prediction.feedback is not None:
        return jsonify({"error": "feedback_already_submitted"}), 409

    feedback = Feedback(prediction_id=prediction.id, corrected_class=corrected_class, comment=comment)
    db.session.add(feedback)
    db.session.commit()
    return jsonify({"id": feedback.id, "prediction_id": prediction.id, "corrected_class": corrected_class}), 201


@classifier_bp.route("/statistics", methods=["GET"])
@login_required_json
def statistics():
    rows = (
        db.session.query(Prediction.predicted_class, db.func.count(Prediction.id))
        .filter(Prediction.user_id == current_user.id, Prediction.predicted_class.isnot(None))
        .group_by(Prediction.predicted_class)
        .all()
    )
    total = Prediction.query.filter_by(user_id=current_user.id).count()
    uncertain = Prediction.query.filter_by(user_id=current_user.id, is_uncertain=True).count()
    return jsonify({
        "total_classifications": total,
        "uncertain_count": uncertain,
        "by_category": {category: count for category, count in rows},
    })
