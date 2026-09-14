"""Integration tests: end-to-end classification workflow
(Chapter 4.10.5-4.10.6, IDs CLS-/SUB-)."""

import io
from PIL import Image

from tests.conftest import register
from app.models import Prediction, Feedback
from app.extensions import db


def _upload(client, endpoint="/classify"):
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), color=(90, 130, 80)).save(buf, format="JPEG")
    buf.seek(0)
    return client.post(endpoint, data={"image": (buf, "item.jpg")},
                        content_type="multipart/form-data", follow_redirects=True)


def test_cls01_valid_upload_is_logged_and_reports_model_unavailable(app, client):
    register(client, email="classify1@example.com")
    resp = _upload(client)
    assert resp.status_code == 200
    assert b"Model unavailable" in resp.data
    with app.app_context():
        assert Prediction.query.count() == 1
        prediction = Prediction.query.first()
        assert prediction.is_uncertain is True
        assert prediction.predicted_class is None


def test_cls02_invalid_extension_rejected_and_not_logged(app, client):
    register(client, email="classify2@example.com")
    buf = io.BytesIO(b"fake content")
    resp = client.post("/classify", data={"image": (buf, "item.gif")},
                        content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        assert Prediction.query.count() == 0  # rejected uploads never reach logging


def test_cls03_history_shows_logged_record(client):
    register(client, email="classify3@example.com")
    _upload(client)
    resp = client.get("/history")
    assert resp.status_code == 200
    assert b"Model unavailable" in resp.data


def test_fb01_feedback_can_be_submitted_and_preserves_original(app, client):
    register(client, email="feedback1@example.com")
    _upload(client)
    with app.app_context():
        prediction = Prediction.query.first()
        pid = prediction.id
    resp = client.post(f"/history/{pid}/feedback", data={"corrected_class": "plastic", "comment": "It was a bottle"},
                        follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        fb = Feedback.query.filter_by(prediction_id=pid).first()
        assert fb is not None
        assert fb.corrected_class == "plastic"
        prediction = db.session.get(Prediction, pid)
        assert prediction.predicted_class is None  # original record untouched


def test_sub01_quota_exhaustion_blocks_further_classification(app, client):
    register(client, email="quota1@example.com")
    for _ in range(5):  # Free plan limit
        resp = _upload(client)
        assert resp.status_code == 200
    resp = _upload(client)
    assert b"quota" in resp.data.lower()
    with app.app_context():
        assert Prediction.query.count() == 5  # 6th request never created a record


def test_sub02_failed_validation_does_not_consume_quota(app, client):
    register(client, email="quota2@example.com")
    for _ in range(10):  # far more than the Free plan's limit of 5
        buf = io.BytesIO(b"not an image")
        client.post("/classify", data={"image": (buf, "bad.jpg")}, content_type="multipart/form-data")
    # A subsequent valid upload should still succeed because none of the
    # invalid attempts consumed quota.
    resp = _upload(client)
    assert b"Model unavailable" in resp.data
