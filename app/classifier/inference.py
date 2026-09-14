"""Model architecture, preprocessing and inference.

Environment note (documented honestly in Chapter Four rather than hidden):
the sandbox this software was developed in cannot reach the hosts that
serve pretrained ImageNet weights for MobileNetV2 (Keras applications'
weight files, PyTorch Hub, and Hugging Face are all unreachable from this
network), nor any public waste-image dataset (Kaggle, GitHub release
archives, TrashNet's hosted archive). The architecture below is therefore
built with ``weights=None`` -- randomly initialised -- which lets the full
software pipeline (validation -> preprocessing -> forward pass ->
thresholding -> JSON response) be built, run and tested end-to-end, but it
produces no meaningful classification and must never be presented as an
evaluated model. ``build_classifier_model`` and ``predict_probabilities``
are exercised directly by the test suite to prove the pipeline is wired
correctly; the public ``/api/classifications`` endpoint does NOT serve
predictions from this randomly initialised network; it instead reports
the honest ``model_unavailable`` state defined in the specification
(Section 04, "System response") because no ModelVersion in the database
has passed the accuracy gate defined in ``ModelVersion.meets_evaluation_gate``.
"""

import time
import numpy as np

from config import Config

_MODEL_CACHE = {}


def build_classifier_model(num_classes=6, input_shape=(224, 224, 3)):
    """Builds the MobileNetV2 + custom head architecture specified in the
    technical documentation (Section 09, "Training configuration"):
    GlobalAveragePooling -> Dense(128, relu) -> Dropout(0.3) -> Dense(6, softmax).

    weights=None because pretrained ImageNet weights could not be
    downloaded in this environment (see module docstring). This means the
    returned model is architecturally correct but numerically untrained.
    """
    import tensorflow as tf
    from tensorflow.keras import layers, models

    base_model = tf.keras.applications.MobileNetV2(
        input_shape=input_shape, include_top=False, weights=None
    )
    inputs = layers.Input(shape=input_shape)
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)
    model = models.Model(inputs, outputs, name="waste_classifier_mobilenetv2")
    return model


def get_cached_model():
    if "model" not in _MODEL_CACHE:
        _MODEL_CACHE["model"] = build_classifier_model()
    return _MODEL_CACHE["model"]


def preprocess_image(pil_image, target_size=Config.IMAGE_SIZE):
    """Resize to the model's expected input and scale to [0, 1], matching
    Section 09's 'RGB image resized to 224 x 224 pixels' input contract.
    """
    resized = pil_image.resize(target_size)
    array = np.asarray(resized, dtype=np.float32) / 255.0
    return np.expand_dims(array, axis=0)


def predict_probabilities(pil_image, model=None):
    """Runs one forward pass and returns (class_probabilities, latency_seconds).

    This proves the mechanical pipeline works -- correct input shape,
    correct output shape, probabilities summing to 1, measurable latency
    -- independent of whether the network has been trained. It is used by
    the automated test suite and is NOT the code path the public API uses
    to answer real classification requests (see module docstring).
    """
    model = model or get_cached_model()
    batch = preprocess_image(pil_image)
    start = time.perf_counter()
    probabilities = model.predict(batch, verbose=0)[0]
    latency = time.perf_counter() - start
    return probabilities, latency


def apply_threshold(probabilities, classes, threshold=Config.CONFIDENCE_THRESHOLD):
    top_index = int(np.argmax(probabilities))
    confidence = float(probabilities[top_index])
    accepted = confidence >= threshold
    return {
        "category": classes[top_index],
        "confidence": confidence,
        "accepted": accepted,
    }
