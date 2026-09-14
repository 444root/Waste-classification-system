"""SQLAlchemy data models.

Schema mirrors Figure 6 ("Core entity relationship model") and the
"Additional entities" table in the technical specification: identity
(User), commercial state (Plan, Subscription, UsageEvent, UpgradeRequest),
classification records (Prediction, Feedback) and model governance
(ModelVersion, AuditLog) are kept as separate entities so that
subscription status is never mixed into user roles and corrected labels
are never mixed into a prediction's original output.
"""

from datetime import datetime, date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # 'user' | 'admin'
    status = db.Column(db.String(20), nullable=False, default="active")  # 'active' | 'suspended'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # Bug fix (2026-09-14): the dashboard used to hardcode "Welcome back,
    # {name}" even on a brand-new account's very first visit. last_login_at
    # is null until the user's first successful authentication (see
    # app/auth/routes.py register()/login()), which is what lets the
    # dashboard tell a first-ever visit apart from a real return visit.
    # Added after the tables already existed in deployed databases (no
    # formal Alembic migration was ever set up -- see app/__init__.py's
    # _ensure_schema, which adds this column to an existing SQLite `users`
    # table automatically on startup if it's missing).
    last_login_at = db.Column(db.DateTime, nullable=True)

    subscriptions = db.relationship("Subscription", backref="user", lazy="dynamic",
                                     foreign_keys="Subscription.user_id")
    predictions = db.relationship("Prediction", backref="user", lazy="dynamic")
    usage_events = db.relationship("UsageEvent", backref="user", lazy="dynamic")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_active_account(self):
        return self.status == "active"

    def active_subscription(self):
        return (
            self.subscriptions.filter_by(status="active")
            .order_by(Subscription.period_start.desc())
            .first()
        )

    def __repr__(self):
        return f"<User {self.email} role={self.role} status={self.status}>"


class Plan(db.Model):
    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    price_rwf = db.Column(db.Integer, nullable=False, default=0)
    scan_limit = db.Column(db.Integer, nullable=False)  # classifications per period
    history_days = db.Column(db.Integer, nullable=False, default=7)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Plan {self.name} limit={self.scan_limit}>"


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")  # active|expired|cancelled
    period_start = db.Column(db.Date, nullable=False, default=date.today)
    period_end = db.Column(db.Date, nullable=True)
    provider_reference = db.Column(db.String(120), nullable=True)  # future payment integration

    plan = db.relationship("Plan")

    def current_period_key(self):
        """Month key used to bucket usage events, e.g. '2026-09'."""
        anchor = self.period_start or date.today()
        return anchor.strftime("%Y-%m")


class UsageEvent(db.Model):
    __tablename__ = "usage_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_type = db.Column(db.String(30), nullable=False, default="classification")
    quantity = db.Column(db.Integer, nullable=False, default=1)
    period_key = db.Column(db.String(7), nullable=False)  # 'YYYY-MM'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ModelVersion(db.Model):
    __tablename__ = "model_versions"

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(60), unique=True, nullable=False)
    artifact_path = db.Column(db.String(255), nullable=True)
    labels_version = db.Column(db.String(60), nullable=True)
    threshold = db.Column(db.Float, nullable=False, default=0.70)
    accuracy = db.Column(db.Float, nullable=True)   # held-out test accuracy
    macro_f1 = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    evaluation_report_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def meets_evaluation_gate(self):
        """An administrator may only activate a version with a stored
        evaluation report that clears the dissertation's accuracy gate
        (Technical Documentation, Section 09: >=85% held-out accuracy).
        """
        return self.accuracy is not None and self.accuracy >= 0.85 and self.evaluation_report_path


class Prediction(db.Model):
    __tablename__ = "predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    model_version_id = db.Column(db.Integer, db.ForeignKey("model_versions.id"), nullable=True)
    predicted_class = db.Column(db.String(30), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    is_uncertain = db.Column(db.Boolean, nullable=False, default=False)
    is_placeholder = db.Column(db.Boolean, nullable=False, default=False)  # seed/demo record
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    feedback = db.relationship("Feedback", backref="prediction", uselist=False)
    model_version = db.relationship("ModelVersion")


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.id"), nullable=False, unique=True)
    corrected_class = db.Column(db.String(30), nullable=False)
    comment = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class UpgradeRequest(db.Model):
    __tablename__ = "upgrade_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    requested_plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending|approved|rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id])
    requested_plan = db.relationship("Plan")


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(60), nullable=False)
    target_type = db.Column(db.String(40), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
