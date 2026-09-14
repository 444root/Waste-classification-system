"""Generates the Chapter 4.7 diagrams directly from the implemented
system (routes in app/*/routes.py, models in app/models.py) rather than
from the plan in the technical specification, so every diagram matches
code that actually exists and passed the test suite.
"""

import os
import graphviz

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "diagrams")
os.makedirs(OUT_DIR, exist_ok=True)

GREEN = "#1f6f4f"
GREEN_LIGHT = "#eaf5ef"
AMBER = "#c9930f"
BLUE = "#1f4f6f"
BLUE_LIGHT = "#eaf1f5"
GREY = "#5c6b64"


def render(dot, name):
    path = os.path.join(OUT_DIR, name)
    dot.render(path, format="png", cleanup=True)
    print("wrote", path + ".png")


# ---------------------------------------------------------------------------
# Figure 4.1 -- Existing (manual) system flow
# ---------------------------------------------------------------------------
def existing_system_flow():
    d = graphviz.Digraph("existing_system", graph_attr={"rankdir": "TB", "bgcolor": "white", "fontsize": "11"})
    d.attr("node", shape="box", style="rounded,filled", fontname="Helvetica", fontsize="11")

    d.node("A", "Resident generates\nhousehold waste", fillcolor=GREEN_LIGHT, color=GREEN)
    d.node("B", "Resident decides category\nfrom personal knowledge", fillcolor=GREEN_LIGHT, color=GREEN)
    d.node("C", "Waste placed in a bin\n(often mixed)", fillcolor="#fff3d6", color=AMBER)
    d.node("D", "Collector or sorter manually\nre-separates at collection point", fillcolor=GREEN_LIGHT, color=GREEN)
    d.node("E", "Contaminated / mixed waste\nsent to general landfill", fillcolor="#fdecea", color="#b3261e")
    d.node("F", "Correctly separated waste\nsent to recycling stream", fillcolor=GREEN_LIGHT, color=GREEN)

    d.edge("A", "B")
    d.edge("B", "C")
    d.edge("C", "D")
    d.edge("D", "E", label="mistakes / contamination")
    d.edge("D", "F", label="correct separation")

    d.attr(label=("Figure 4.1: Existing (manual) waste-sorting workflow observed in Gasabo District.\n"
                   "No digital record is kept and no consistent guidance is available at the point of disposal."),
           fontsize="10", labelloc="b")
    render(d, "fig4_1_existing_system_flow")


# ---------------------------------------------------------------------------
# Figure 4.2 -- Context diagram
# ---------------------------------------------------------------------------
def context_diagram():
    d = graphviz.Digraph("context", graph_attr={"rankdir": "LR", "bgcolor": "white"})
    d.attr("node", fontname="Helvetica", fontsize="11")

    d.node("resident", "Resident /\nRegistered User", shape="box", style="rounded,filled", fillcolor=GREEN_LIGHT, color=GREEN)
    d.node("admin", "Administrator", shape="box", style="rounded,filled", fillcolor=GREEN_LIGHT, color=GREEN)
    d.node("system", "0\nWaste Classification\nSystem", shape="circle", style="filled", fillcolor=BLUE_LIGHT, color=BLUE, width="2")

    d.edge("resident", "system", label="registration, login,\nwaste image, feedback,\nupgrade request")
    d.edge("system", "resident", label="category, confidence,\ndisposal guidance,\nhistory")
    d.edge("admin", "system", label="user management,\nmodel version registration")
    d.edge("system", "admin", label="user/system reports,\naudit confirmations")

    d.attr(label="Figure 4.2: Context diagram (Level 0 DFD) of the implemented system.", fontsize="10", labelloc="b")
    render(d, "fig4_2_context_diagram")


# ---------------------------------------------------------------------------
# Figure 4.3 -- Level 1 DFD
# ---------------------------------------------------------------------------
def dfd_level1():
    d = graphviz.Digraph("dfd1", graph_attr={"rankdir": "LR", "bgcolor": "white", "splines": "ortho"})
    d.attr("node", fontname="Helvetica", fontsize="10")

    d.node("resident", "Resident", shape="box", style="filled", fillcolor=GREEN_LIGHT, color=GREEN)
    d.node("admin", "Administrator", shape="box", style="filled", fillcolor=GREEN_LIGHT, color=GREEN)

    processes = {
        "p1": "1.0\nAuthenticate &\nmanage session",
        "p2": "2.0\nValidate & classify\nwaste image",
        "p3": "3.0\nEnforce quota &\nmanage subscription",
        "p4": "4.0\nRecord feedback &\nhistory",
        "p5": "5.0\nAdminister users &\nmodel versions",
    }
    for key, label in processes.items():
        d.node(key, label, shape="circle", style="filled", fillcolor=BLUE_LIGHT, color=BLUE, width="1.3")

    stores = {
        "d1": "D1 users / subscriptions",
        "d2": "D2 predictions / feedback",
        "d3": "D3 plans / usage_events",
        "d4": "D4 model_versions",
        "d5": "D5 audit_log",
    }
    for key, label in stores.items():
        d.node(key, label, shape="box", style="filled", fillcolor="#f4f4f2", color=GREY)

    d.edge("resident", "p1", label="credentials")
    d.edge("p1", "d1")
    d.edge("p1", "p2", label="authenticated session")
    d.edge("resident", "p2", label="waste image")
    d.edge("p2", "p3", label="check quota")
    d.edge("p3", "d3")
    d.edge("p2", "d2", label="prediction record")
    d.edge("p2", "resident", label="category / model_unavailable")
    d.edge("resident", "p4", label="correction")
    d.edge("p4", "d2")
    d.edge("admin", "p5")
    d.edge("p5", "d1")
    d.edge("p5", "d4")
    d.edge("p5", "d5", label="audit entry")

    d.attr(label="Figure 4.3: Level 1 data flow diagram of the implemented modules.", fontsize="10", labelloc="b")
    render(d, "fig4_3_dfd_level1")


# ---------------------------------------------------------------------------
# Figure 4.4 -- Use case diagram
# ---------------------------------------------------------------------------
def use_case_diagram():
    d = graphviz.Digraph("usecase", graph_attr={"rankdir": "LR", "bgcolor": "white"})
    d.attr("node", fontname="Helvetica", fontsize="10")

    d.node("guest", "Guest", shape="box", style="filled", fillcolor=GREEN_LIGHT, color=GREEN)
    d.node("user", "Registered User", shape="box", style="filled", fillcolor=GREEN_LIGHT, color=GREEN)
    d.node("admin", "Administrator", shape="box", style="filled", fillcolor=GREEN_LIGHT, color=GREEN)

    use_cases_guest = ["View landing page & plans", "Register account"]
    use_cases_user = ["Log in / log out", "Classify waste image", "View classification history",
                       "Submit feedback correction", "Update profile", "Request plan upgrade"]
    use_cases_admin = ["Search & manage users", "Suspend / reactivate account", "Assign plan",
                        "Review upgrade requests", "Register model version"]

    for i, uc in enumerate(use_cases_guest):
        node_id = f"ug{i}"
        d.node(node_id, uc, shape="ellipse", style="filled", fillcolor=BLUE_LIGHT, color=BLUE)
        d.edge("guest", node_id)
    for i, uc in enumerate(use_cases_user):
        node_id = f"uu{i}"
        d.node(node_id, uc, shape="ellipse", style="filled", fillcolor=BLUE_LIGHT, color=BLUE)
        d.edge("user", node_id)
    for i, uc in enumerate(use_cases_admin):
        node_id = f"ua{i}"
        d.node(node_id, uc, shape="ellipse", style="filled", fillcolor=BLUE_LIGHT, color=BLUE)
        d.edge("admin", node_id)

    d.edge("user", "guest", style="dashed", arrowhead="empty", label="(extends)")
    d.attr(label="Figure 4.4: Use case diagram (Guest, Registered User, Administrator).", fontsize="10", labelloc="b")
    render(d, "fig4_4_use_case_diagram")


# ---------------------------------------------------------------------------
# Figure 4.6 -- Entity relationship diagram (matches app/models.py exactly)
# ---------------------------------------------------------------------------
def erd():
    d = graphviz.Graph("erd", graph_attr={"rankdir": "LR", "bgcolor": "white", "splines": "spline"})
    d.attr("node", shape="record", fontname="Helvetica", fontsize="9", style="filled", fillcolor="white")

    def entity(name, fields, color):
        label = "{" + name + "|" + "\\l".join(fields) + "\\l" + "}"
        d.node(name, label=label, color=color)

    entity("User", ["PK id", "name", "email UNIQUE", "password_hash", "role", "status", "created_at"], GREEN)
    entity("Plan", ["PK id", "name UNIQUE", "price_rwf", "scan_limit", "history_days", "is_active"], AMBER)
    entity("Subscription", ["PK id", "FK user_id", "FK plan_id", "status", "period_start", "period_end", "provider_reference"], AMBER)
    entity("UsageEvent", ["PK id", "FK user_id", "event_type", "quantity", "period_key", "created_at"], GREEN)
    entity("ModelVersion", ["PK id", "version UNIQUE", "artifact_path", "labels_version", "threshold", "accuracy", "macro_f1", "is_active", "evaluation_report_path"], BLUE)
    entity("Prediction", ["PK id", "FK user_id", "FK model_version_id", "predicted_class", "confidence", "is_uncertain", "is_placeholder", "created_at"], BLUE)
    entity("Feedback", ["PK id", "FK prediction_id UNIQUE", "corrected_class", "comment", "created_at"], BLUE)
    entity("UpgradeRequest", ["PK id", "FK user_id", "FK requested_plan_id", "status", "FK reviewed_by", "reviewed_at", "created_at"], AMBER)
    entity("AuditLog", ["PK id", "FK actor_user_id", "action", "target_type", "target_id", "details", "created_at"], GREY)

    d.edge("User", "Subscription", label="1..N")
    d.edge("Plan", "Subscription", label="1..N")
    d.edge("User", "UsageEvent", label="1..N")
    d.edge("User", "Prediction", label="1..N")
    d.edge("ModelVersion", "Prediction", label="0..N")
    d.edge("Prediction", "Feedback", label="1..0/1")
    d.edge("User", "UpgradeRequest", label="1..N")
    d.edge("Plan", "UpgradeRequest", label="1..N")
    d.edge("User", "AuditLog", label="1..N (actor)")

    d.attr(label="Figure 4.6: Entity relationship diagram, generated directly from app/models.py.", fontsize="10", labelloc="b")
    render(d, "fig4_6_erd")


# ---------------------------------------------------------------------------
# Figure 4.7 -- Three-tier architecture of the implemented system
# ---------------------------------------------------------------------------
def architecture():
    d = graphviz.Digraph("architecture", graph_attr={"bgcolor": "white", "compound": "true"})
    d.attr("node", fontname="Helvetica", fontsize="10", shape="box", style="rounded,filled")

    with d.subgraph(name="cluster_presentation") as c:
        c.attr(label="Presentation tier (Jinja2 templates + vanilla JS)", style="filled", fillcolor=GREEN_LIGHT, color=GREEN)
        c.node("t_auth", "auth screens\n(register/login)", fillcolor="white")
        c.node("t_upload", "upload & result\nscreens", fillcolor="white")
        c.node("t_history", "history & feedback\nscreens", fillcolor="white")
        c.node("t_admin", "admin screens", fillcolor="white")

    with d.subgraph(name="cluster_application") as c:
        c.attr(label="Application tier (Flask modular monolith)", style="filled", fillcolor=BLUE_LIGHT, color=BLUE)
        c.node("bp_auth", "auth blueprint\n(app/auth)", fillcolor="white")
        c.node("bp_classifier", "classifier blueprint\n(app/classifier)", fillcolor="white")
        c.node("bp_users", "users blueprint\n(app/users)", fillcolor="white")
        c.node("bp_admin", "admin blueprint\n(app/admin)", fillcolor="white")
        c.node("bp_subs", "subscriptions blueprint\n(app/subscriptions)", fillcolor="white")
        c.node("utils", "utils.py\n(RBAC decorators,\naudit logging)", fillcolor="white")

    with d.subgraph(name="cluster_data") as c:
        c.attr(label="Data & model tier", style="filled", fillcolor="#fff3d6", color=AMBER)
        c.node("sqlite", "SQLite\n(instance/waste_classifier.db)", fillcolor="white")
        c.node("model", "MobileNetV2 architecture\n(random weights -- see\nSection 4.4 limitation)", fillcolor="white")

    d.edge("t_auth", "bp_auth")
    d.edge("t_upload", "bp_classifier")
    d.edge("t_history", "bp_classifier")
    d.edge("t_admin", "bp_admin")
    d.edge("bp_auth", "sqlite")
    d.edge("bp_classifier", "sqlite")
    d.edge("bp_classifier", "model", style="dashed", label="architecture-only\n(test suite path)")
    d.edge("bp_users", "sqlite")
    d.edge("bp_admin", "sqlite")
    d.edge("bp_subs", "sqlite")
    d.edge("utils", "bp_admin", style="dotted")
    d.edge("utils", "bp_classifier", style="dotted")

    d.attr(label="Figure 4.7: Three-tier architecture of the implemented system.", fontsize="10", labelloc="b")
    render(d, "fig4_7_architecture")


if __name__ == "__main__":
    existing_system_flow()
    context_diagram()
    dfd_level1()
    use_case_diagram()
    erd()
    architecture()
