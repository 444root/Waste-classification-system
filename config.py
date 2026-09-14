"""Application configuration for the Waste Classification System.

Values here mirror the decisions recorded in the project's technical
specification (Sections 07, 08, 10, 12 and 13): Flask modular monolith,
SQLite persistence, server-side sessions, a 5 MB upload ceiling and a
70% acceptance threshold for model predictions.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")


class Config:
    SECRET_KEY = os.environ.get("WCS_SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "WCS_DATABASE_URI", f"sqlite:///{os.path.join(INSTANCE_DIR, 'waste_classifier.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload / classification rules (Technical Documentation, Section 03 & 04)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
    CONFIDENCE_THRESHOLD = 0.70
    IMAGE_SIZE = (224, 224)
    WASTE_CLASSES = ["organic", "plastic", "paper", "metal", "glass", "general_trash"]

    # Session security (Technical Documentation, Section 10)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True

    # Subscription plan defaults (Technical Documentation, Section 11)
    DEFAULT_PLAN_NAME = "Free"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
