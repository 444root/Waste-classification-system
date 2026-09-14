"""Application factory for the Waste Classification System."""

import os
from flask import Flask
from flask_login import current_user

from config import Config, INSTANCE_DIR
from app.extensions import db, login_manager, csrf, migrate


def _ensure_schema(app):
    """Idempotent, no-CLI-required schema guard.

    Flask-Migrate is wired up (see extensions.py) but no migration was ever
    generated (migrations/ is empty) -- the database has always been
    created by seed.py's one-off db.create_all() call instead. That's fine
    for wholly new tables, but db.create_all() never alters a table that
    already exists, so adding a column to an existing model (e.g. User.last
    _login_at, added 2026-09-14) would silently do nothing against an
    already-created database, locally or on Render, without someone
    running a manual `flask db migrate`/`upgrade` -- and there's no shell
    access to Render's environment to do that by hand. Running this on
    every app startup instead means the fix ships just by deploying the
    code (git push), the same way every other change to this project does.
    Safe to run every time: db.create_all() only creates missing tables,
    and the column check only adds a column that isn't already there.
    """
    with app.app_context():
        db.create_all()
        inspector = db.inspect(db.engine)
        if "users" in inspector.get_table_names():
            existing_columns = {col["name"] for col in inspector.get_columns("users")}
            if "last_login_at" not in existing_columns:
                with db.engine.begin() as conn:
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))


def create_app(config_class=Config):
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    if not app.config.get("TESTING"):
        # Tests create a fresh in-memory DB per test (see tests/conftest.py)
        # so the current model definitions are already the schema; running
        # this there too would just be wasted work on every test.
        _ensure_schema(app)

    from app.auth.routes import auth_bp
    from app.classifier.routes import classifier_bp
    from app.users.routes import users_bp
    from app.admin.routes import admin_bp
    from app.subscriptions.routes import subscriptions_bp
    from app.main.routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(classifier_bp, url_prefix="/api")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(subscriptions_bp, url_prefix="/api")

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_globals():
        return {"current_user": current_user}

    return app
