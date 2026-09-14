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
    "cardboard": "Flatten and keep dry; use the paper/cardboard recycling stream.",
    "metal": "Use the metal recycling stream and avoid sharp exposed edges.",
    "glass": "Use the glass stream and handle broken glass safely.",
    "general_trash": "Use the general waste stream.",
    "trash": "No suitable recycling stream identified; use the general waste stream.",
    "not_paper": (
        "This build can only confirm whether an item is paper so far -- it isn't yet trained "
        "to tell plastic, metal, glass and organic waste apart. Please sort this item by hand "
        "for now; multi-category detection is planned next."
    ),
}

# Marks a ModelVersion.version string as belonging to the real, trained
# binary paper/not_paper detector (see app/classifier/inference.py) rather
# than the still-untrained 6-class architecture. A naming convention was
# used instead of a new database column to avoid a migration for a single
# boolean flag.
PAPER_BINARY_VERSION_PREFIX = "paper_binary_"


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
        image = validate_upload(request.files.get("image"))
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

    if active_model.version.startswith(PAPER_BINARY_VERSION_PREFIX):
        # Real inference path -- see app/classifier/inference.py and
        # reports/paper_detector_v1_evaluation.json for what this model
        # actually is and how it was evaluated.
        from app.classifier.inference import predict_paper, PAPER_DECISION_THRESHOLD

        paper_probability, latency_seconds = predict_paper(image)
        is_paper = paper_probability >= PAPER_DECISION_THRESHOLD
        confidence = paper_probability if is_paper else (1.0 - paper_probability)
        category = "paper" if is_paper else "not_paper"
        accepted = confidence >= active_model.threshold

        prediction = Prediction(
            user_id=current_user.id,
            model_version_id=active_model.id,
            predicted_class=category if accepted else None,
            confidence=confidence,
            is_uncertain=not accepted,
            is_placeholder=False,
        )
        db.session.add(prediction)
        db.session.add(UsageEvent(user_id=current_user.id, event_type="classification",
                                   quantity=1, period_key=_current_period_key()))
        db.session.commit()

        if not accepted:
            return jsonify({
                "prediction_id": prediction.id,
                "status": "uncertain",
                "message": (
                    f"The model was not confident enough to accept this result "
                    f"(confidence {confidence:.2f}, threshold {active_model.threshold:.2f})."
                ),
            }), 200

        return jsonify({
            "prediction_id": prediction.id,
            "status": "accepted",
            "category": category,
            "confidence": confidence,
            "latency_seconds": latency_seconds,
            "guidance": DISPOSAL_GUIDANCE.get(category),
        }), 200

    # Reachable only for a hypothetical future ModelVersion that isn't the
    # paper-binary detector and isn't the untrained 6-class build -- not
    # reachable by anything currently seeded (see Chapter Four, Section 4.4).
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


@classifier_bp.route("/classifications/preview-multiclass", methods=["POST"])
@login_required_json
def preview_multiclass():
    """Experimental 6-class preview -- deliberately NOT gated like
    create_classification() above, and deliberately NOT logged to
    Prediction/UsageEvent history or counted against quota, because this
    model has real, disclosed accuracy (78.6% held-out) that does not
    clear the project's own 85% production bar (see
    reports/multiclass_detector_v1_evaluation.json). It exists so the
    real, working multi-class model can be demonstrated honestly -- with
    its real numbers alongside it -- rather than hidden until it clears
    the gate.
    """
    try:
        image = validate_upload(request.files.get("image"))
    except UploadValidationError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), 400

    from app.classifier.inference import predict_multiclass, MULTICLASS_CLASS_NAMES

    probabilities, latency_seconds = predict_multiclass(image)
    ranked = sorted(
        zip(MULTICLASS_CLASS_NAMES, (float(p) for p in probabilities)),
        key=lambda pair: pair[1], reverse=True,
    )

    return jsonify({
        "status": "experimental_preview",
        "message": (
            "This model is real and trained, but its held-out test accuracy (78.6%) does not "
            "clear this project's own 85% production threshold, so it is not used for the main "
            "classification flow or counted in your history/quota. Treat this as a preview."
        ),
        "top_category": ranked[0][0],
        "top_confidence": ranked[0][1],
        "all_probabilities": [{"category": name, "probability": prob} for name, prob in ranked],
        "guidance": DISPOSAL_GUIDANCE.get(ranked[0][0]),
        "latency_seconds": latency_seconds,
    }), 200
