"""Server-rendered page shell: landing, dashboard, upload, history, plans,
feedback and admin screens. These views render real data straight from
the database (rather than only via the JSON API) so the interface is
directly demonstrable and testable end-to-end.
"""

from datetime import date

from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Prediction, Plan, User, UpgradeRequest
from app.classifier.routes import _quota_status, DISPOSAL_GUIDANCE, _active_model_version
from app.classifier.validators import validate_upload, UploadValidationError
from app.utils import admin_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def landing():
    plans = Plan.query.filter_by(is_active=True).order_by(Plan.price_rwf.asc()).all()
    return render_template("landing.html", plans=plans)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    subscription, plan, used, remaining = _quota_status(current_user)
    recent = (
        Prediction.query.filter_by(user_id=current_user.id)
        .order_by(Prediction.created_at.desc())
        .limit(5)
        .all()
    )
    # Bug fix (2026-09-14): pop (not just read) the flag set by
    # app/auth/routes.py's register()/login(), so it only applies to the
    # dashboard render immediately after that specific authentication --
    # reloading the dashboard afterwards correctly goes back to "Welcome
    # back" rather than showing "Welcome" on every reload.
    show_first_login_welcome = session.pop("show_first_login_welcome", False)
    return render_template(
        "dashboard.html", plan=plan, used=used, remaining=remaining, recent=recent,
        show_first_login_welcome=show_first_login_welcome,
    )


@main_bp.route("/classify", methods=["GET", "POST"])
@login_required
def classify():
    if request.method == "GET":
        subscription, plan, used, remaining = _quota_status(current_user)
        active_model = _active_model_version()
        model_ready = active_model is not None and active_model.meets_evaluation_gate()
        return render_template(
            "upload.html", plan=plan, remaining=remaining,
            model_ready=model_ready, active_model=active_model,
        )

    from app.classifier.routes import create_classification  # reuse the JSON logic
    response, status_code = create_classification()
    body = response.get_json()

    if status_code == 400:
        flash(body.get("message", "The image could not be processed."), "error")
        return redirect(url_for("main.classify"))
    if status_code == 429:
        flash("Your classification quota for this period is exhausted.", "error")
        return redirect(url_for("main.classify"))

    return render_template(
        "result.html",
        status=body.get("status", "unknown"),
        message=body.get("message"),
        prediction_id=body.get("prediction_id"),
        category=body.get("category"),
        confidence=body.get("confidence"),
        guidance_text=DISPOSAL_GUIDANCE.get(body.get("category")) if body.get("category") else None,
    )


@main_bp.route("/classify/preview", methods=["GET", "POST"])
@login_required
def classify_preview():
    """Experimental 6-class model preview -- see
    app/classifier/routes.py:preview_multiclass for why this is kept
    separate from the main, gated /classify flow."""
    if request.method == "GET":
        return render_template("preview_multiclass.html")

    from app.classifier.routes import preview_multiclass
    response, status_code = preview_multiclass()
    body = response.get_json()

    if status_code == 400:
        flash(body.get("message", "The image could not be processed."), "error")
        return redirect(url_for("main.classify_preview"))

    return render_template(
        "preview_multiclass.html",
        result=body,
    )


@main_bp.route("/history")
@login_required
def history():
    predictions = (
        Prediction.query.filter_by(user_id=current_user.id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    return render_template("history.html", predictions=predictions)


@main_bp.route("/history/<int:prediction_id>/feedback", methods=["GET", "POST"])
@login_required
def feedback(prediction_id):
    prediction = db.session.get(Prediction, prediction_id)
    if prediction is None or prediction.user_id != current_user.id:
        flash("That classification record could not be found.", "error")
        return redirect(url_for("main.history"))

    if request.method == "POST":
        from app.classifier.routes import submit_feedback
        response, status_code = submit_feedback(prediction_id)
        if status_code >= 400:
            flash("That correction could not be saved.", "error")
        else:
            flash("Thank you -- your correction has been recorded.", "success")
        return redirect(url_for("main.history"))

    return render_template("feedback.html", prediction=prediction, categories=DISPOSAL_GUIDANCE.keys())


@main_bp.route("/plans")
def plans_page():
    plans = Plan.query.filter_by(is_active=True).order_by(Plan.price_rwf.asc()).all()
    current_plan = None
    if current_user.is_authenticated:
        sub = current_user.active_subscription()
        current_plan = sub.plan if sub else None
    return render_template("plans.html", plans=plans, current_plan=current_plan)


@main_bp.route("/plans/<int:plan_id>/request", methods=["POST"])
@login_required
def request_plan(plan_id):
    plan = db.session.get(Plan, plan_id)
    if plan is None:
        flash("That plan is not available.", "error")
        return redirect(url_for("main.plans_page"))

    existing = UpgradeRequest.query.filter_by(user_id=current_user.id, status="pending").first()
    if existing is None:
        db.session.add(UpgradeRequest(user_id=current_user.id, requested_plan_id=plan.id, status="pending"))
        db.session.commit()
        flash(f"Upgrade request to {plan.name} submitted for admin review.", "success")
    else:
        flash("You already have a pending upgrade request.", "error")
    return redirect(url_for("main.plans_page"))


@main_bp.route("/admin/users")
@admin_required
def admin_users_page():
    users = User.query.order_by(User.created_at.desc()).all()
    plans = Plan.query.filter_by(is_active=True).all()
    pending_upgrades = UpgradeRequest.query.filter_by(status="pending").all()
    return render_template("admin_users.html", users=users, plans=plans, pending_upgrades=pending_upgrades)


@main_bp.route("/admin/users/<int:user_id>/update", methods=["POST"])
@admin_required
def admin_users_update(user_id):
    from app.admin.routes import update_user
    update_user(user_id)
    return redirect(url_for("main.admin_users_page"))
