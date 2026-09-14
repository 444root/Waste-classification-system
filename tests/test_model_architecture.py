"""Architecture-validation tests (Chapter 4.10.3): prove the classification
pipeline is mechanically correct -- input/output shapes, probability
normalisation, measurable latency -- WITHOUT claiming any classification
accuracy. The network is randomly initialised (see
app/classifier/inference.py) because this environment cannot reach any
host that serves pretrained ImageNet weights or a waste-image dataset.
"""

import numpy as np
from PIL import Image

from app.classifier.inference import (
    build_classifier_model, preprocess_image, predict_probabilities, apply_threshold
)
from config import Config


def test_arch01_model_builds_with_expected_output_shape():
    model = build_classifier_model(num_classes=6)
    assert model.output_shape == (None, 6)


def test_arch02_preprocessing_produces_expected_tensor_shape():
    image = Image.new("RGB", (640, 480), color=(50, 90, 60))
    batch = preprocess_image(image)
    assert batch.shape == (1, 224, 224, 3)
    assert batch.min() >= 0.0 and batch.max() <= 1.0


def test_arch03_forward_pass_returns_valid_probability_distribution():
    model = build_classifier_model(num_classes=6)
    image = Image.new("RGB", (300, 300), color=(120, 40, 40))
    probabilities, latency_seconds = predict_probabilities(image, model=model)
    assert probabilities.shape == (6,)
    assert np.isclose(probabilities.sum(), 1.0, atol=1e-4)
    assert latency_seconds > 0


def test_arch04_threshold_rejects_low_confidence():
    probabilities = np.array([0.30, 0.25, 0.20, 0.10, 0.10, 0.05])
    result = apply_threshold(probabilities, Config.WASTE_CLASSES, threshold=0.70)
    assert result["accepted"] is False
    assert result["category"] == "organic"


def test_arch05_threshold_accepts_high_confidence():
    probabilities = np.array([0.02, 0.02, 0.02, 0.02, 0.02, 0.90])
    result = apply_threshold(probabilities, Config.WASTE_CLASSES, threshold=0.70)
    assert result["accepted"] is True
    assert result["category"] == "general_trash"
