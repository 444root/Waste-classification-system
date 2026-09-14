"""Cross-cutting helpers: authorization decorators, audit logging.

Technical Documentation Section 05 ("Authorization rules"): administrative
checks must be enforced on the server, all protected routes verify both an
authenticated session and an active account, and important admin actions
are written to an audit log with actor, action, target and timestamp.
"""

from functools import wraps

from flask import jsonify
from flask_login import current_user

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
