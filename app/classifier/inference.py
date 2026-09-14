"""Model architecture, preprocessing and inference.

Environment note, updated (documented honestly in Chapter Four rather than
hidden): this project's ORIGINAL development sandbox could not reach any
host serving pretrained ImageNet weights or a public waste-image dataset,
so the 6-class MobileNetV2(weights=None) architecture below was built and
tested end-to-end but never trained -- it is architecturally correct and
numerically meaningless, and the public API deliberately reports the
honest ``model_unavailable`` state instead of serving predictions from it.
That part is all still true today: this network is still untrained, and
``build_classifier_model`` / ``predict_probabilities`` exist only to prove
the mechanical pipeline (shapes, thresholding, latency) to the test suite.

What changed in a later session: this project's network access turned out
to reach github.com / raw.githubusercontent.com / codeload.github.com even
though storage.googleapis.com, huggingface.co and kaggle.com remained
blocked (403). That was enough to pull the real TrashNet dataset (mirrored
with actual JPEGs, not just index files, at
github.com/winkhai/trash-recycling-classifier) and genuinely train a
SMALLER model from scratch -- a binary "paper vs. not_paper" detector --
which is real, tested on a held-out split it never saw during training,
and does clear this project's own 85% accuracy gate. See
``reports/paper_detector_v1_evaluation.json`` for the full honest write-up,
including its real weak point (paper recall is only ~62%, so it under-calls
paper more often than it falsely calls something paper). This detector
answers one narrower question than the original 6-class spec -- it can only
say "paper" or "not_paper" -- so it is wired up as its own ModelVersion
("paper_binary_cnn_scratch_v1") rather than pretending to be the full
6-class system. The full MobileNetV2 model remains future work.
"""

import os
import time
import numpy as np

from config import Config

_MODEL_CACHE = {}

PAPER_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "artifacts", "paper_detector_v1.keras"
)
PAPER_MODEL_IMAGE_SIZE = (128, 128)

MULTICLASS_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "artifacts", "multiclass_detector_v1.keras"
)
MULTICLASS_MODEL_IMAGE_SIZE = (128, 128)
MULTICLASS_CLASS_NAMES = ["cardboard", "glass", "metal", "paper", "plastic", "trash"]


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


# ---------------------------------------------------------------------------
# Real, trained model: binary paper / not_paper detector.
#
# This is genuinely trained (see module docstring and
# reports/paper_detector_v1_evaluation.json) -- not a placeholder. It is
# kept separate from build_classifier_model() above because it answers a
# narrower question (paper vs. everything else) with a different, smaller
# architecture chosen for CPU-only from-scratch training.
# ---------------------------------------------------------------------------


def get_cached_paper_model():
    """Loads (and caches) the trained paper/not_paper CNN from disk.

    The saved .keras file includes the augmentation and Rescaling(1/255)
    layers as part of the graph, so inputs here must be raw 0-255 pixel
    values, not pre-normalised -- see preprocess_image_for_paper_model.
    Augmentation layers are no-ops at inference time (Keras only applies
    them when called with training=True, which model.predict() does not
    do), so this is safe to use directly for prediction.
    """
    if "paper_model" not in _MODEL_CACHE:
        import tensorflow as tf
        _MODEL_CACHE["paper_model"] = tf.keras.models.load_model(PAPER_MODEL_PATH)
    return _MODEL_CACHE["paper_model"]


def preprocess_image_for_paper_model(pil_image, target_size=PAPER_MODEL_IMAGE_SIZE):
    resized = pil_image.resize(target_size)
    array = np.asarray(resized, dtype=np.float32)  # raw 0-255; model rescales internally
    return np.expand_dims(array, axis=0)


def predict_paper(pil_image, model=None):
    """Runs one forward pass of the real paper/not_paper detector.

    Returns (paper_probability, latency_seconds). paper_probability is the
    model's sigmoid output: probability the image is paper (class 1).
    """
    model = model or get_cached_paper_model()
    batch = preprocess_image_for_paper_model(pil_image)
    start = time.perf_counter()
    paper_probability = float(model.predict(batch, verbose=0)[0][0])
    latency = time.perf_counter() - start
    return paper_probability, latency


# ---------------------------------------------------------------------------
# Real, trained model: 6-class waste classifier (EXPERIMENTAL).
#
# Genuinely trained on all six real TrashNet classes -- see module docstring
# and reports/multiclass_detector_v1_evaluation.json for the full honest
# write-up. Held-out test accuracy is 78.6%, which does NOT clear this
# project's own 85% production gate (ModelVersion.meets_evaluation_gate),
# so this model is deliberately NOT the one served by the main, gated
# /api/classifications endpoint. It is real and it works -- just not well
# enough yet to be presented as a finished, evaluated production model. It
# is reachable only through the clearly-labelled experimental preview route
# (see app/main/routes.py, /classify/preview) so it can be demonstrated
# honestly, alongside its real per-class numbers, rather than hidden.
# ---------------------------------------------------------------------------


def get_cached_multiclass_model():
    if "multiclass_model" not in _MODEL_CACHE:
        import tensorflow as tf
        _MODEL_CACHE["multiclass_model"] = tf.keras.models.load_model(MULTICLASS_MODEL_PATH)
    return _MODEL_CACHE["multiclass_model"]


def preprocess_image_for_multiclass_model(pil_image, target_size=MULTICLASS_MODEL_IMAGE_SIZE):
    resized = pil_image.resize(target_size)
    array = np.asarray(resized, dtype=np.float32)  # raw 0-255; model rescales internally
    return np.expand_dims(array, axis=0)


def predict_multiclass(pil_image, model=None):
    """Runs one forward pass of the experimental 6-class detector.

    Returns (probabilities, latency_seconds). probabilities is a length-6
    array aligned with MULTICLASS_CLASS_NAMES, summing to ~1.0.
    """
    model = model or get_cached_multiclass_model()
    batch = preprocess_image_for_multiclass_model(pil_image)
    start = time.perf_counter()
    probabilities = model.predict(batch, verbose=0)[0]
    latency = time.perf_counter() - start
    return probabilities, latency
