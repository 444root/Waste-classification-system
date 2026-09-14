"""Tests for the experimental 6-class preview model and route.

This model is real and trained (see reports/multiclass_detector_v1_evaluation.json)
but does not clear the project's 85% production gate, so it is deliberately
reachable only through /classify/preview -- separate from the gated
/classify flow -- and deliberately does not write to Prediction/UsageEvent
history. These tests check both the model's real (imperfect) behaviour and
that the route correctly keeps it out of production history/quota.
"""

import os

from PIL import Image

from app.classifier.inference import predict_multiclass, MULTICLASS_CLASS_NAMES
from app.models import Prediction, UsageEvent
from tests.conftest import register

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
ALL_CLASSES = ["cardboard", "glass", "metal", "paper", "plastic", "trash"]


def test_predict_multiclass_returns_a_valid_probability_distribution():
    image = Image.open(os.path.join(FIXTURES, "real_paper_sample.jpg")).convert("RGB")
    probabilities, latency = predict_multiclass(image)
    assert probabilities.shape == (6,)
    assert abs(float(probabilities.sum()) - 1.0) < 1e-3
    assert latency > 0


def test_predict_multiclass_correctly_ranks_each_real_class_sample_top1():
    """All six held-out fixtures happen to be correctly classified as
    top-1 by this model (checked directly against the trained weights).
    This is not a claim the model is always right -- see the evaluation
    report for the real, lower aggregate accuracy (78.6%) -- just a
    sanity check that the pipeline produces sensible results on clear
    examples of each class."""
    for class_name in ALL_CLASSES:
        image = Image.open(os.path.join(FIXTURES, f"real_{class_name}_sample.jpg")).convert("RGB")
        probabilities, _ = predict_multiclass(image)
        top_index = int(probabilities.argmax())
        assert MULTICLASS_CLASS_NAMES[top_index] == class_name


def test_preview01_route_returns_experimental_status_and_all_six_probabilities(client):
    register(client, email="preview1@example.com")
    with open(os.path.join(FIXTURES, "real_cardboard_sample.jpg"), "rb") as f:
        resp = client.post("/classify/preview", data={"image": (f, "cardboard.jpg")},
                            content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Cardboard" in resp.data
    assert b"experimental" in resp.data.lower() or b"Experimental" in resp.data


def test_preview02_does_not_touch_production_history_or_quota(app, client):
    register(client, email="preview2@example.com")
    with open(os.path.join(FIXTURES, "real_trash_sample.jpg"), "rb") as f:
        client.post("/classify/preview", data={"image": (f, "trash.jpg")},
                     content_type="multipart/form-data", follow_redirects=True)
    with app.app_context():
        assert Prediction.query.count() == 0
        assert UsageEvent.query.count() == 0
