"""Figure 4.5: sequence diagram of the actual classification request
lifecycle, matching app/classifier/routes.py::create_classification and
app/main/routes.py::classify exactly (including the honest
"model_unavailable" branch, since no ModelVersion clears the evaluation
gate in this build).
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "diagrams")
os.makedirs(OUT_DIR, exist_ok=True)

actors = ["Browser", "Flask route\n(/classify)", "Validators", "Quota service", "ModelVersion\nregistry", "SQLite"]
x_positions = [0, 2, 4, 6, 8, 10]

messages = [
    (0, 1, "POST /classify (multipart image)", 1),
    (1, 3, "_quota_status(user)", 2),
    (3, 1, "remaining count", 3),
    (1, 2, "validate_upload(file)", 4),
    (2, 1, "decoded image OR UploadValidationError", 5),
    (1, 4, "_active_model_version()", 6),
    (4, 1, "None (no version meets evaluation gate)", 7),
    (1, 5, "INSERT Prediction(is_uncertain=True)\nINSERT UsageEvent", 8),
    (5, 1, "commit OK", 9),
    (1, 0, "200: result.html (status=model_unavailable)", 10),
]

fig, ax = plt.subplots(figsize=(11, 7.5))
top = len(messages) + 1.5

for x, label in zip(x_positions, actors):
    ax.plot([x, x], [0, top], color="#c9d3cd", linewidth=1.5, zorder=1)
    ax.add_patch(plt.Rectangle((x - 0.9, top - 0.1), 1.8, 0.7, facecolor="#eaf5ef", edgecolor="#1f6f4f", zorder=2))
    ax.text(x, top + 0.25, label, ha="center", va="center", fontsize=8.7, zorder=3, fontweight="bold")

for i, (src, dst, label, order) in enumerate(messages):
    y = top - 0.6 - i
    x_src, x_dst = x_positions[src], x_positions[dst]
    color = "#b3261e" if "Error" in label or "None" in label else "#1f6f4f"
    ax.annotate(
        "", xy=(x_dst, y), xytext=(x_src, y),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4,
                         linestyle="dashed" if dst < src else "solid"),
    )
    mid_x = (x_src + x_dst) / 2
    ax.text(mid_x, y + 0.12, f"{order}. {label}", ha="center", va="bottom", fontsize=7.8, color="#1c1f1e")

ax.set_xlim(-1.5, 11.5)
ax.set_ylim(-1, top + 1)
ax.axis("off")
ax.set_title(
    "Figure 4.5: Sequence diagram of the implemented classification request\n"
    "(reflects the actual code path in app/classifier/routes.py, including the\n"
    "honest 'model_unavailable' outcome documented in Chapter Four, Section 4.4)",
    fontsize=10,
)

path = os.path.join(OUT_DIR, "fig4_5_sequence_diagram.png")
plt.tight_layout()
plt.savefig(path, dpi=160, facecolor="white")
print("wrote", path)
