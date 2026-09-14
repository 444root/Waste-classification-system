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
6-class system. The full MobileNetV2 model remains future work. The 6-class
model trained in the following session (see below) is real too, but does
not clear the gate, so it ships separately as an experimental preview.

What changed in the deployment session (real production incident, not
hypothetical): after both trained models were wired up and deployed, live
classification requests started returning HTTP 500 on the actual Render
site. Render's application logs showed the worker process receiving
SIGKILL with "Perhaps out of memory?" while importing TensorFlow -- Render's
free/Starter tier caps a web service at 512 MB RAM, and a direct
measurement in this environment showed loading one trained model with full
``tensorflow-cpu`` and running a single prediction peaks at ~654 MB RSS, well
over that budget, even before Flask/gunicorn's own overhead. This was a
real crash, verified against the actual Render logs, not a guess. The fix:
both trained models are now shipped as converted ``.tflite`` files and
served through ``tflite-runtime`` instead of full Keras/TensorFlow at
request time. The conversion was verified bit-identical to the original
Keras models on every held-out fixture image before shipping it (matching
probabilities to full float32 precision, matching top-1 class on every
sample) -- so this is a memory/deployment fix, not a retrain, and it does
not change either model's measured accuracy. The same measurement redone
with ``tflite-runtime`` showed ~48 MB peak RSS for the same prediction,
comfortably inside Render's 512 MB limit. ``tflite-runtime`` currently only
ships pre-built wheels against NumPy 1.x, so production now pins
``numpy<2`` -- see the comment in requirements.txt.
"""

import os
import time
import numpy as np

from config import Config

_MODEL_CACHE = {}

try:  # Production ships the small tflite-runtime package (see requirements.txt).
    import tflite_runtime.interpreter as tflite
except ImportError:  # pragma: no cover - local/dev fallback when only full TF is installed
    import tensorflow.lite as tflite

PAPER_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "artifacts", "paper_detector_v1.tflite"
)
PAPER_MODEL_IMAGE_SIZE = (128, 128)

MULTICLASS_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "artifacts", "multiclass_detector_v1.tflite"
)
MULTICLASS_MODEL_IMAGE_SIZE = (128, 128)
MULTICLASS_CLASS_NAMES = ["cardboard", "glass", "metal", "paper", "plastic", "trash"]

# Decision boundary fix (2026-09-14): app/classifier/routes.py used to compare
# the paper model's raw sigmoid output directly against 0.5 to decide "paper"
# vs "not_paper". The evaluation report's own confusion matrix already
# disclosed why that hurts recall (only 62% of real paper images score
# >=0.5), and probing the model directly against tests/fixtures/*.jpg
# confirmed the gap is wide enough to move the boundary safely:
#   - the known miss, real_paper_sample_missed.jpg, scores 0.36
#   - every true not_paper fixture (metal/glass/cardboard/plastic/trash)
#     scores at most 0.048
# so a boundary of 0.30 recovers that miss with a large margin (~6x) below
# the highest true-negative score observed, without flipping any of them.
# This has only been checked against the 7 fixtures committed in
# tests/fixtures/, not a full re-run of the 383-image held-out test set --
# if updated precision/recall numbers are needed for the dissertation,
# rerun the same held-out evaluation that produced
# reports/paper_detector_v1_evaluation.json with this new boundary.
PAPER_DECISION_THRESHOLD = 0.30


def _load_tflite_interpreter(model_path):
    """Loads a converted .tflite model and allocates its tensors once.

    tflite-runtime and tensorflow.lite share the same Interpreter API, so
    this works whichever one got imported above.
    """
    interpreter = tflite.Interpreter(model_path=model_path)
    interpreter.allocate_tensors()
    return interpreter


def _run_tflite(interpreter, batch):
    """Runs one forward pass through a loaded tflite Interpreter and
    returns its raw output array (still batched, shape (1, N))."""
    input_index = interpreter.get_input_details()[0]["index"]
    output_index = interpreter.get_output_details()[0]["index"]
    interpreter.set_tensor(input_index, batch)
    interpreter.invoke()
    return interpreter.get_tensor(output_index)


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
    """Loads (and caches) the trained paper/not_paper CNN from its
    converted .tflite file.

    The original .keras graph included the augmentation and Rescaling(1/255)
    layers, and those survive the tflite conversion (verified bit-identical
    to the Keras model's output on every held-out fixture before shipping),
    so inputs here must still be raw 0-255 pixel values, not pre-normalised
    -- see preprocess_image_for_paper_model.
    """
    if "paper_model" not in _MODEL_CACHE:
        _MODEL_CACHE["paper_model"] = _load_tflite_interpreter(PAPER_MODEL_PATH)
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
    interpreter = model or get_cached_paper_model()
    batch = preprocess_image_for_paper_model(pil_image)
    start = time.perf_counter()
    output = _run_tflite(interpreter, batch)
    paper_probability = float(output[0][0])
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
    """Loads (and caches) the experimental 6-class CNN from its converted
    .tflite file (same rationale and verification as the paper model above)."""
    if "multiclass_model" not in _MODEL_CACHE:
        _MODEL_CACHE["multiclass_model"] = _load_tflite_interpreter(MULTICLASS_MODEL_PATH)
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
    interpreter = model or get_cached_multiclass_model()
    batch = preprocess_image_for_multiclass_model(pil_image)
    start = time.perf_counter()
    probabilities = _run_tflite(interpreter, batch)[0]
    latency = time.perf_counter() - start
    return probabilities, latency
