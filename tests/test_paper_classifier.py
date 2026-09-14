"""Tests for the real, trained paper/not_paper detector.

Unlike test_model_architecture.py (which only proves the untrained 6-class
pipeline is mechanically wired up), these tests exercise a genuinely
trained model against real, held-out photographs from the TrashNet test
split (tests/fixtures/*.jpg -- none of these were used in training; see
reports/paper_detector_v1_evaluation.json). One fixture (real_paper_sample_missed.jpg)
is deliberately a case the model gets wrong, to test -- and document -- the
system's real, disclosed weak point (paper recall ~62%) rather than only
testing the happy path.
"""

import os

from PIL import Image

from app.classifier.inference import predict_paper
from app.models import ModelVersion
from app.extensions import db
from tests.conftest import register, login

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _seed_paper_model():
    db.session.add(ModelVersion(
        version="paper_binary_cnn_scratch_v1",
        artifact_path="app/classifier/artifacts/paper_detector_v1.keras",
        labels_version="paper_vs_not_paper_v1",
        threshold=0.70,
        accuracy=0.9008,
        macro_f1=0.8426,
        is_active=True,
        evaluation_report_path="reports/paper_detector_v1_evaluation.json",
    ))
    db.session.commit()


def test_predict_paper_correctly_flags_a_real_paper_photo():
    image = Image.open(os.path.join(FIXTURES, "real_paper_sample.jpg")).convert("RGB")
    probability, latency = predict_paper(image)
    assert 0.0 <= probability <= 1.0
    assert probability >= 0.5  # this specific fixture is a case the model gets right
    assert latency > 0


def test_predict_paper_correctly_rejects_a_real_metal_photo():
    image = Image.open(os.path.join(FIXTURES, "real_metal_sample.jpg")).convert("RGB")
    probability, _ = predict_paper(image)
    assert probability < 0.5


def test_predict_paper_documents_a_real_known_miss():
    """The model's disclosed weak point (62% recall on paper) is real --
    this specific held-out paper photo is one it misses. Testing this
    (rather than only the case that works) keeps the test suite honest
    about the model's actual, evaluated behaviour."""
    image = Image.open(os.path.join(FIXTURES, "real_paper_sample_missed.jpg")).convert("RGB")
    probability, _ = predict_paper(image)
    assert probability < 0.5  # documents the miss; not a desired outcome, an honest one


def test_paper01_uploading_a_real_paper_photo_is_accepted_end_to_end(app, client):
    with app.app_context():
        _seed_paper_model()
    register(client, email="paperclassify1@example.com")
    with open(os.path.join(FIXTURES, "real_paper_sample.jpg"), "rb") as f:
        resp = client.post("/classify", data={"image": (f, "paper.jpg")},
                            content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Accepted" in resp.data
    assert b"Paper" in resp.data


def test_paper02_uploading_a_non_paper_photo_reports_not_paper(app, client):
    with app.app_context():
        _seed_paper_model()
    register(client, email="paperclassify2@example.com")
    with open(os.path.join(FIXTURES, "real_metal_sample.jpg"), "rb") as f:
        resp = client.post("/classify", data={"image": (f, "metal.jpg")},
                            content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Accepted" in resp.data
    assert b"Not Paper" in resp.data  # Jinja |title on "not_paper" -> "Not Paper"


def test_paper03_history_and_statistics_reflect_the_real_prediction(app, client):
    with app.app_context():
        _seed_paper_model()
    register(client, email="paperclassify3@example.com")
    with open(os.path.join(FIXTURES, "real_paper_sample.jpg"), "rb") as f:
        client.post("/classify", data={"image": (f, "paper.jpg")},
                     content_type="multipart/form-data", follow_redirects=True)
    resp = client.get("/history")
    assert b"paper" in resp.data.lower()

    stats_resp = client.get("/api/statistics")
    body = stats_resp.get_json()
    assert body["by_category"].get("paper") == 1
