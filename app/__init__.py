"""Application factory for the Waste Classification System."""

import os
from flask import Flask
from flask_login import current_user

from config import Config, INSTANCE_DIR
from app.extensions import db, login_manager, csrf, migrate


def create_app(config_class=Config):
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

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
