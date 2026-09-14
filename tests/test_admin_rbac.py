"""Integration tests: role-based access control and cross-user isolation
(Chapter 4.10.5, IDs ADM-/AUTHZ-)."""

import io
from PIL import Image

from tests.conftest import register
from app.models import User, Prediction
from app.extensions import db


def _make_admin(app):
    with app.app_context():
        admin = User(name="Admin", email="admin@example.com", role="admin", status="active")
        admin.set_password("AdminPass123")
        db.session.add(admin)
        db.session.commit()


def test_authz01_regular_user_cannot_reach_admin_page(app, client):
    register(client, email="plainuser@example.com")
    resp = client.get("/admin/users")
    assert resp.status_code == 403


def test_authz02_anonymous_user_cannot_reach_admin_api(client):
    resp = client.get("/api/admin/users")
    assert resp.status_code == 401


def test_adm01_admin_can_suspend_a_user(app, client):
    _make_admin(app)
    register(client, email="target@example.com")
    client.post("/auth/logout", follow_redirects=True)
    client.post("/auth/login", data={"email": "admin@example.com", "password": "AdminPass123"})

    with app.app_context():
        target = User.query.filter_by(email="target@example.com").first()
        target_id = target.id

    resp = client.post(f"/admin/users/{target_id}/update", data={"status": "suspended"}, follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        target = db.session.get(User, target_id)
        assert target.status == "suspended"


def test_adm02_suspended_user_denied_after_next_request(app, client):
    _make_admin(app)
    register(client, email="victim@example.com")
    client.post("/auth/logout", follow_redirects=True)

    with app.app_context():
        victim = User.query.filter_by(email="victim@example.com").first()
        victim.status = "suspended"
        db.session.commit()

    resp = client.post("/auth/login", data={"email": "victim@example.com", "password": "TestPass123"})
    assert resp.status_code == 403


def test_authz03_user_cannot_submit_feedback_on_anothers_prediction(app, client):
    register(client, email="owner@example.com")
    buf = io.BytesIO()
    Image.new("RGB", (200, 200), color=(1, 2, 3)).save(buf, format="JPEG")
    buf.seek(0)
    client.post("/classify", data={"image": (buf, "item.jpg")}, content_type="multipart/form-data")
    with app.app_context():
        prediction_id = Prediction.query.first().id

    client.post("/auth/logout", follow_redirects=True)
    register(client, email="intruder@example.com")

    resp = client.post(f"/api/classifications/{prediction_id}/feedback",
                        json={"corrected_class": "plastic"})
    assert resp.status_code == 403
