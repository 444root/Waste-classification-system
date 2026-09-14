import pytest

from app import create_app
from app.extensions import db
from app.models import Plan, User
from config import TestConfig


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        db.session.add_all([
            Plan(name="Free", price_rwf=0, scan_limit=5, history_days=7, is_active=True),
            Plan(name="Individual Pro", price_rwf=3000, scan_limit=100, history_days=365, is_active=True),
        ])
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, name="Test User", email="user@example.com", password="TestPass123"):
    return client.post("/auth/register", data={"name": name, "email": email, "password": password},
                        follow_redirects=True)


def login(client, email="user@example.com", password="TestPass123"):
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def make_admin(app_ctx):
    with app_ctx.app_context():
        user = User(name="Admin", email="admin@example.com", role="admin", status="active")
        user.set_password("AdminPass123")
        db.session.add(user)
        db.session.commit()
