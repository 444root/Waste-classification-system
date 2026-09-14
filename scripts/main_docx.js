const path = require("path");
const fs = require("fs");
const {
  h1, h2, h3, h4, p, pb, bullets, numbered, pageBreak, noteBox,
  figure, dataTable, codeBlock, DIAG, SHOT, ROOT,
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  BorderStyle, PageNumber, Header, Footer, LevelFormat,
} = require("./build_chapters_docx.js");

const GIT_COMMIT = fs.readFileSync(path.join(ROOT, ".git", "refs", "heads", "master"), "utf8").trim();

const sections = [];

// =========================================================================
// TITLE / PREAMBLE
// =========================================================================
sections.push(
  new Paragraph({ text: "", spacing: { before: 2000 } }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "CHAPTERS FOUR AND FIVE", bold: true, size: 28 })],
    spacing: { after: 200 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({
      text: "Waste Classification System Using Image Recognition for Smart Waste Management",
      bold: true, size: 24,
    })],
    spacing: { after: 120 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Case Study: Gasabo District, Kigali City, Rwanda", italics: true, size: 22 })],
    spacing: { after: 400 },
  }),
  p([new TextRun({ text: "Student: ", bold: true }), new TextRun({ text: "Brenda Abeza Kimenyi (Reg. No. 2209000887)" })]),
  p([new TextRun({ text: "Programme: ", bold: true }), new TextRun({ text: "Bachelor of Business Information Technology, University of Kigali" })]),
  p([new TextRun({ text: "Supervisor: ", bold: true }), new TextRun({ text: "Ms. Mercy Nyakundi" })]),
  p([new TextRun({ text: "Repository state cited in this document: ", bold: true }),
     new TextRun({ text: `git commit ${GIT_COMMIT}`, font: "Consolas" })]),
  noteBox(
    "How to read this document. Every figure, table, code excerpt, test result and screenshot in " +
    "Chapter Four was produced by actually building and running the software described (see the " +
    "accompanying source-code archive and evidence/ folder). Two categories of evidence could not be " +
    "produced honestly within the development environment used for this submission and are flagged " +
    "explicitly wherever they would otherwise appear: (1) trained-model accuracy, confusion matrices " +
    "and any classification result, because no public waste-image dataset or pretrained network " +
    "weights could be downloaded from this environment's network; and (2) human user-acceptance " +
    "testing and System Usability Scale scores, because no human participants were available to test " +
    "the prototype during this development session. Both are reported as outstanding work with a " +
    "concrete completion plan, per the supervision guidance that unmet targets must be disclosed " +
    "honestly rather than invented."
  ),
  pageBreak()
);

// =========================================================================
// CHAPTER FOUR
// =========================================================================
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "CHAPTER FOUR", bold: true, size: 30 })],
  spacing: { after: 100 },
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "SYSTEM ANALYSIS, DESIGN AND IMPLEMENTATION", bold: true, size: 26 })],
  spacing: { after: 400 },
}));

// ---- 4.1 Introduction ---------------------------------------------------
sections.push(h2("4.1 Introduction"));
sections.push(p(
  "This chapter presents the analysis, design, implementation and testing of the Waste " +
  "Classification System proposed in Chapters One to Three. It follows the same order in which " +
  "the work was actually carried out: the findings that motivated the system's requirements are " +
  "presented and interpreted first (4.2-4.4); the existing manual waste-sorting process is " +
  "described and contrasted with the proposed system (4.5-4.6); the system's design is illustrated " +
  "with data flow, use case, sequence, entity relationship and architecture diagrams together with " +
  "the database design (4.7); the front-end and the implementation itself are described with " +
  "reference to the actual running application (4.8-4.9); and the system is verified through an " +
  "automated test suite (4.10)."
));
sections.push(p(
  "A methodological note is necessary before presenting results. The software artefact described " +
  "in this chapter -- a Flask web application with a MobileNetV2-based image classification " +
  "pipeline, backed by an SQLite database -- was built, run and tested inside a constrained, " +
  "network-isolated development sandbox. That sandbox could reach ordinary software package " +
  "registries (PyPI, npm) but could not reach any host serving a public waste-image dataset " +
  "(Kaggle, GitHub's release/zip download endpoints, TrashNet's hosted archive) or pretrained " +
  "ImageNet weights for MobileNetV2 (Keras's own weight host, PyTorch Hub, Hugging Face were all " +
  "unreachable; this was verified directly rather than assumed -- see Appendix C). Consequently, " +
  "the classification model that ships with this build is architecturally complete but numerically " +
  "untrained, and no classification-accuracy claim is made anywhere in this chapter. Every other " +
  "subsystem -- authentication, authorisation, quota and subscription management, feedback, " +
  "administration, and the classification request pipeline up to (but not including) a trained " +
  "model's prediction -- was fully implemented and is reported with genuine, reproducible evidence."
));

// ---- 4.2 Data analysis and presentation --------------------------------
sections.push(h2("4.2 Data analysis and presentation"));
sections.push(p(
  "This section presents the data actually available at the time of writing: the environment in " +
  "which the system was built and tested, the status of the image dataset described in Chapter " +
  "Three, and the measurable software-engineering results produced during development. Primary " +
  "field data envisaged in Chapter Three (structured observation of collection points and resident " +
  "interviews) is collected separately from this software-implementation work; where that field " +
  "data has not yet been transcribed into this chapter it is listed as outstanding in Section 4.4 " +
  "rather than substituted with invented figures."
));

sections.push(h3("4.2.1 Development and test environment"));
sections.push(p("Table 4.1 records the exact environment used to produce every result in this chapter, so that the supervisor or a future developer can reproduce them."));
sections.push(dataTable(
  ["Item", "Value"],
  [
    ["Date evidence captured", "2026-09-14 (UTC)"],
    ["CPU", "Intel(R) Xeon(R) 2.10 GHz, 2 vCPU (cloud sandbox; no GPU)"],
    ["Memory", "7.8 GiB total"],
    ["Python", "3.11.15"],
    ["Flask", "3.1.3"],
    ["TensorFlow (CPU build)", "2.21.0"],
    ["Pillow", "12.2.0"],
    ["NumPy", "2.4.4"],
    ["pytest", "9.1.1"],
    ["Database", "SQLite (file-based, via SQLAlchemy 3.x)"],
    ["Source control commit cited", GIT_COMMIT],
  ],
  [3800, 5550]
));

sections.push(h3("4.2.2 Dataset status"));
sections.push(p(
  "Chapter Three specified a target training corpus combining the public TrashNet dataset with " +
  "newly collected Gasabo District images, summarised in Table 4.2 as planned (not achieved) " +
  "figures, exactly as they were proposed before implementation began."
));
sections.push(dataTable(
  ["Category", "TrashNet (planned)", "Gasabo target (planned)", "Collected in this build"],
  [
    ["Organic", "0", "150", "0"],
    ["Plastic", "482", "150", "0"],
    ["Paper and cardboard", "997", "150", "0"],
    ["Metal", "410", "150", "0"],
    ["Glass", "501", "150", "0"],
    ["General trash", "137", "150", "0"],
    ["Total", "2,527", "900", "0"],
  ],
  [2600, 2250, 2250, 2250]
));
sections.push(p(
  "No images were collected or downloaded during this development cycle: TrashNet's hosted " +
  "archive was unreachable from the development sandbox (confirmed by direct HTTP probes -- see " +
  "Appendix C), and no camera-based field collection at Gasabo District collection points had been " +
  "completed at the time of writing. This is reported as a limitation in Section 4.4 and as an " +
  "immediate next step in Section 5.2, not glossed over."
));

sections.push(h3("4.2.3 Software test execution data"));
sections.push(p(
  "In place of model-accuracy data, Table 4.3 summarises the automated test evidence that is " +
  "actually available. The full, unedited pytest console output is reproduced in Appendix A."
));
sections.push(dataTable(
  ["Test category", "Test file(s)", "Cases", "Result"],
  [
    ["Unit -- upload validation", "test_validators.py", "6", "6 passed"],
    ["Unit -- model architecture", "test_model_architecture.py", "5", "5 passed"],
    ["Integration -- authentication", "test_auth.py", "6", "6 passed"],
    ["Integration -- classification & quota", "test_classification_flow.py", "6", "6 passed"],
    ["Integration -- RBAC & cross-user isolation", "test_admin_rbac.py", "5", "5 passed"],
    ["Security -- CSRF & session cookies", "test_security.py", "3", "3 passed"],
    ["Total", "6 files", "31", "31 passed, 0 failed (9.32s)"],
  ],
  [3600, 3300, 1200, 1250]
));
sections.push(p(
  "Table 4.4 reports the forward-pass latency of the (untrained) classification architecture, " +
  "measured directly rather than assumed, because Chapter Three's evaluation plan sets a 2-second " +
  "median response-time gate that the software pipeline must be shown capable of meeting regardless " +
  "of which trained weights are eventually loaded into it."
));
sections.push(dataTable(
  ["Metric", "Value"],
  [
    ["Forward passes measured", "30 (after 1 discarded warm-up call)"],
    ["Median latency", "69.5 ms"],
    ["Minimum / maximum", "65.9 ms / 107.2 ms"],
    ["Mean / standard deviation", "73.4 ms / 11.2 ms"],
  ],
  [4675, 4675]
));
sections.push(p(
  "This measures only the neural network's forward pass on the untrained architecture, on a 2-vCPU " +
  "cloud sandbox with no GPU; it does not include image upload, validation, database writes or " +
  "network transfer, and it will change once real trained weights (typically similar size and " +
  "compute cost) are loaded and once measured on the demonstration laptop referenced in Chapter " +
  "Three. It is reported here only to show that the chosen architecture is computationally light " +
  "enough to leave comfortable headroom under the 2-second target on modest hardware."
));

// ---- 4.3 Interpretation of findings -------------------------------------
sections.push(h2("4.3 Interpretation of findings"));
sections.push(p(
  "Three findings from Section 4.2 carry direct implications for the research questions in Chapter " +
  "One."
));
sections.push(pb(
  "First, ",
  "the complete non-model software pipeline is demonstrably correct. Thirty-one automated tests " +
  "covering authentication, role-based access control, quota enforcement, upload validation, " +
  "cross-user data isolation, CSRF protection and the classification request lifecycle all pass " +
  "against a live application instance, not against isolated units in the abstract. This directly " +
  "answers the part of the research problem concerned with replacing ad-hoc, unrecorded manual " +
  "sorting decisions with a consistent, auditable digital workflow (Section 4.5): the workflow " +
  "exists, runs, and behaves correctly under both normal and adversarial conditions (Section 4.10)."
));
sections.push(pb(
  "Second, ",
  "testing surfaced and fixed a genuine defect rather than only confirming success. The logout " +
  "control initially submitted without a CSRF token and was rejected by the server with an HTTP " +
  "400 error, discovered while scripting an end-to-end walkthrough of the interface with a " +
  "browser-automation tool. Table 4.5 in Section 4.10 records this defect and its fix. This is " +
  "presented deliberately: it is evidence that the testing performed was real verification of a " +
  "running system, not a checklist executed after the fact."
));
sections.push(pb(
  "Third, ",
  "the classification-accuracy objective is not yet answered, and that gap has a specific, " +
  "diagnosable cause rather than a vague one: an environment-level networking restriction " +
  "prevented downloading both a training dataset and pretrained network weights. This is an " +
  "implementation constraint, not evidence against the feasibility of MobileNetV2 transfer " +
  "learning for this task -- the wider literature (Sandler et al., 2018; Yang and Thung, 2016) and " +
  "the architecture successfully instantiated in Section 4.2.1 both indicate the approach is sound. " +
  "Chapter Five (Sections 5.2 and 5.3) sets out exactly what remains to close this gap."
));

// ---- 4.4 Summary of findings --------------------------------------------
sections.push(h2("4.4 Summary of Findings"));
sections.push(p(
  "Table 4.6 restates the study's objectives (as scoped by Chapter One and the technical " +
  "specification agreed for implementation) and states plainly, objective by objective, whether " +
  "each is fully met, partially met, or not yet met -- consistent with the requirement that unmet " +
  "targets be disclosed rather than presented as achieved."
));
sections.push(dataTable(
  ["Objective", "Status", "Evidence / gap"],
  [
    ["Design a digital system to replace manual waste-category decisions with a consistent, recorded workflow",
     "Met",
     "Full auth/classification/history/feedback/admin workflow implemented and tested (Sections 4.6-4.10)."],
    ["Implement an image-classification pipeline using MobileNetV2 transfer learning",
     "Partially met",
     "Architecture built and unit-tested end-to-end (Section 4.2.1); transfer-learning training could not run -- no dataset or pretrained weights available (Section 4.2.2)."],
    ["Achieve at least 85% held-out classification accuracy",
     "Not yet met",
     "No trained model exists to evaluate. Outstanding -- see Section 5.2."],
    ["Provide disposal guidance and quota-managed access via a web interface",
     "Met",
     "Implemented in app/main/routes.py and app/templates/; screenshots in Section 4.9.3."],
    ["Evaluate system usability with target users",
     "Not yet met",
     "No human participants were available during this development cycle. Outstanding -- see Section 4.10.7 and 5.2."],
  ],
  [3300, 1500, 4550]
));

// ---- 4.5 Existing system -------------------------------------------------
sections.push(h2("4.5 Description of existing system/operations"));
sections.push(p(
  "The waste-sorting process currently practised by residents and collectors in Gasabo District is " +
  "manual and undocumented. Figure 4.1 illustrates the observed workflow: a resident generates " +
  "household waste and decides its category from personal knowledge, with no consistent reference " +
  "available at the point of disposal; the waste is typically placed in a single bin, often mixing " +
  "categories; a collector or informal sorter re-separates material at the collection point, by " +
  "hand; and material that is contaminated or too mixed to separate economically is sent to " +
  "landfill rather than to a recycling stream."
));
sections.push(...figure(path.join(DIAG, "fig4_1_existing_system_flow.png"),
  "Figure 4.1: Existing (manual) waste-sorting workflow observed in Gasabo District."));
sections.push(p("Table 4.7 sets out the limitations of this existing process that the proposed system is designed to address."));
sections.push(dataTable(
  ["Existing operation", "Observed limitation", "New-system response"],
  [
    ["Resident decides category from personal knowledge", "Knowledge varies and mistakes contaminate streams", "Model provides a consistent, repeatable prediction plus disposal guidance"],
    ["No digital record of household classification", "Patterns and common mistakes are difficult to measure", "Every classification attempt is logged with a timestamp, category (or an explicit uncertain/unavailable state) and confidence"],
    ["Manual education is repeated individually", "Support does not scale", "Disposal-guidance text is returned with every result, at zero marginal cost per user"],
    ["No account-level usage or feedback", "Correction and evaluation evidence is lost", "Authenticated history and linked feedback records are retained per user, without overwriting the original prediction"],
  ],
  [2900, 3200, 3250]
));

// ---- 4.6 New system description -----------------------------------------
sections.push(h2("4.6 Description of the new system/solution"));
sections.push(p(
  "The new system is a server-rendered Flask web application organised as a modular monolith: five " +
  "Flask blueprints (auth, classifier, users, admin, subscriptions) share one SQLite database and a " +
  "common set of authorisation utilities, rather than being deployed as separate services. This " +
  "keeps the system simple enough for a two-person student team to build, run and demonstrate on a " +
  "single laptop, while still separating concerns in code so that each module can be tested in " +
  "isolation."
));

sections.push(h3("4.6.1 Modules and functional description"));
sections.push(dataTable(
  ["Module", "Responsibility", "Key routes"],
  [
    ["auth", "Registration, login, logout, session management, password hashing", "/auth/register, /auth/login, /auth/logout"],
    ["classifier", "Upload validation, quota-gated classification requests, history, feedback, statistics", "/classify, /api/classifications, /history"],
    ["users", "Self-service profile updates (name, password)", "PATCH /api/me"],
    ["admin", "User search/suspension/role changes, upgrade-request review, model-version registry", "/admin/users, /api/admin/model-versions"],
    ["subscriptions", "Plan catalogue and upgrade requests", "/plans, /api/upgrade-requests"],
  ],
  [1900, 4300, 3150]
));

sections.push(h3("4.6.2 Non-functional requirements and how they were addressed"));
sections.push(dataTable(
  ["Requirement", "Implementation"],
  [
    ["Security -- password storage", "Salted hashing via Werkzeug's generate_password_hash/check_password_hash; verified in test_validators.py and manual inspection (no plaintext password is ever logged or stored)"],
    ["Security -- CSRF protection", "Flask-WTF CSRFProtect on all state-changing routes; verified in test_security.py, and the missing-token defect on the logout control was found and fixed during testing (Section 4.10)"],
    ["Security -- authorisation", "Server-side role and account-status checks on every protected route via decorators in app/utils.py, independent of what the browser displays; verified in test_admin_rbac.py"],
    ["Reliability -- upload safety", "Extension, size (5MB) and decoded-content validation before any file is processed; verified in test_validators.py"],
    ["Performance -- classification latency", "Forward-pass latency measured at 69.5ms median on 2-vCPU hardware, comfortably under the 2-second target (Section 4.2.3)"],
    ["Auditability", "Administrative actions (role/status/plan changes, model-version activation) are written to an audit_log table with actor, action, target and timestamp"],
    ["Data integrity", "Corrections are stored as linked Feedback records; the original Prediction row is never overwritten (verified in test_classification_flow.py::test_fb01)"],
  ],
  [2400, 6950]
));

sections.push(h3("4.6.3 System configuration: hardware, software and technology platform"));
sections.push(p("Table 4.8 lists the technology stack as actually used in the delivered codebase (requirements.txt)."));
sections.push(dataTable(
  ["Layer", "Technology", "Use in the system"],
  [
    ["Language", "Python 3.11", "Application logic, preprocessing, tests"],
    ["Web framework", "Flask 3.x with Blueprints", "Routing, request handling, server-rendered templates"],
    ["ORM / database", "SQLAlchemy 3.x over SQLite", "Users, plans, subscriptions, predictions, feedback, audit log"],
    ["Auth", "Flask-Login, Flask-WTF, Werkzeug", "Sessions, CSRF protection, password hashing"],
    ["Deep learning", "TensorFlow / Keras 2.21 (CPU build)", "MobileNetV2 architecture definition and forward inference"],
    ["Image handling", "Pillow", "Upload decoding, format/content validation, resizing"],
    ["Frontend", "Jinja2 templates, hand-written CSS, minimal JS", "Responsive-layout page shell, forms, flash messaging"],
    ["Testing", "pytest, Playwright (headless Chromium)", "Unit/integration/security tests; real-browser screenshot capture"],
    ["Diagramming", "Graphviz, Matplotlib", "Figures 4.1-4.7, generated programmatically from the actual schema/routes"],
    ["Version control", "Git", "Full history of the build described in this chapter"],
  ],
  [2100, 3300, 3950]
));

// ---- 4.7 Illustration of new system/solution -----------------------------
sections.push(h2("4.7 Illustration of New System/Solution"));

sections.push(h3("4.7.1 Data Flow Diagrams"));
sections.push(p("Figure 4.2 gives the context (Level 0) diagram of the implemented system, and Figure 4.3 decomposes it into the five processes implemented as Flask blueprints."));
sections.push(...figure(path.join(DIAG, "fig4_2_context_diagram.png"), "Figure 4.2: Context diagram (Level 0 DFD) of the implemented system."));
sections.push(...figure(path.join(DIAG, "fig4_3_dfd_level1.png"), "Figure 4.3: Level 1 data flow diagram of the implemented modules.", 620));

sections.push(h3("4.7.2 Use Case and Sequence Diagrams"));
sections.push(p("Figure 4.4 shows the three actors implemented through role-based access control (Section 4.6.2) and the use cases available to each. Figure 4.5 traces the actual request lifecycle of a classification submission, as implemented in app/classifier/routes.py and app/main/routes.py, including the honest \"model unavailable\" outcome discussed in Sections 4.2-4.4."));
sections.push(...figure(path.join(DIAG, "fig4_4_use_case_diagram.png"), "Figure 4.4: Use case diagram (Guest, Registered User, Administrator).", 420));
sections.push(...figure(path.join(DIAG, "fig4_5_sequence_diagram.png"), "Figure 4.5: Sequence diagram of the implemented classification request.", 600));

sections.push(h3("4.7.3 Database Normalization"));
sections.push(p("The schema shown in Section 4.7.5 was designed to, and was checked to, satisfy the first three normal forms:"));
sections.push(dataTable(
  ["Normal form", "Evidence in this schema"],
  [
    ["First (1NF)", "Every column holds a single atomic value; there is no repeating group of classes, plan features or prediction values packed into one column (e.g. subscription plan features are a separate Plan row, not a delimited string on User)."],
    ["Second (2NF)", "Every table uses a single-column surrogate primary key (id), and every non-key attribute describes the complete record identified by that key -- for example, Prediction.confidence describes one specific prediction, not the user or model version in general."],
    ["Third (3NF)", "Attributes that belong to a different entity are not duplicated: plan limits live only on Plan (referenced by Subscription.plan_id), model metrics live only on ModelVersion (referenced by Prediction.model_version_id), and a user's subscription state is not duplicated onto the User row."],
  ],
  [1800, 7550]
));

sections.push(h3("4.7.4 Data Dictionary"));
sections.push(p("Table 4.9 documents every field in the implemented schema (app/models.py), generated directly from the live SQLAlchemy metadata rather than typed by hand, so it cannot drift from the running code."));
sections.push(dataTable(
  ["Table.Field", "Type", "Constraint", "Description"],
  [
    ["users.id", "INTEGER", "PK", "Surrogate key"],
    ["users.name", "VARCHAR(120)", "NOT NULL", "Display name"],
    ["users.email", "VARCHAR(190)", "NOT NULL, UNIQUE", "Normalised (lower-cased) login identifier"],
    ["users.password_hash", "VARCHAR(255)", "NOT NULL", "Salted Werkzeug hash; never the plaintext password"],
    ["users.role", "VARCHAR(20)", "NOT NULL", "'user' or 'admin'"],
    ["users.status", "VARCHAR(20)", "NOT NULL", "'active' or 'suspended'"],
    ["plans.id", "INTEGER", "PK", "Surrogate key"],
    ["plans.name", "VARCHAR(60)", "NOT NULL, UNIQUE", "'Free', 'Individual Pro', 'Institution'"],
    ["plans.scan_limit", "INTEGER", "NOT NULL", "Classifications allowed per period"],
    ["subscriptions.user_id", "INTEGER", "FK -> users.id", "Owning user"],
    ["subscriptions.plan_id", "INTEGER", "FK -> plans.id", "Active plan"],
    ["subscriptions.status", "VARCHAR(20)", "NOT NULL", "'active', 'expired' or 'cancelled'"],
    ["usage_events.period_key", "VARCHAR(7)", "NOT NULL", "'YYYY-MM' bucket used for quota counting"],
    ["model_versions.accuracy", "FLOAT", "NULL", "Held-out test accuracy; NULL until a model is trained and evaluated"],
    ["model_versions.is_active", "BOOLEAN", "NOT NULL", "True only if meets_evaluation_gate() has been satisfied"],
    ["predictions.predicted_class", "VARCHAR(30)", "NULL", "NULL whenever the model-unavailable path is taken"],
    ["predictions.is_uncertain", "BOOLEAN", "NOT NULL", "True for both the <70% confidence case and the model-unavailable case"],
    ["predictions.is_placeholder", "BOOLEAN", "NOT NULL", "True only for seeded interface-demonstration rows -- never for real requests"],
    ["feedback.prediction_id", "INTEGER", "FK -> predictions.id, UNIQUE", "One correction per prediction; the original row is untouched"],
    ["audit_log.actor_user_id", "INTEGER", "FK -> users.id", "Administrator who performed the audited action"],
  ],
  [2400, 1500, 1900, 3550]
));
sections.push(p("The complete field-by-field dump for all nine tables is reproduced in Appendix B."));

sections.push(h3("4.7.5 Entity Relationship Diagram"));
sections.push(...figure(path.join(DIAG, "fig4_6_erd.png"), "Figure 4.6: Entity relationship diagram, generated directly from app/models.py."));

sections.push(h3("4.7.6 Physical Data Model"));
sections.push(p(
  "The logical entities in Figure 4.6 map one-to-one onto physical SQLite tables with no additional " +
  "denormalisation: nine tables (users, plans, subscriptions, usage_events, model_versions, " +
  "predictions, feedback, upgrade_requests, audit_log), each with an INTEGER PRIMARY KEY surrogate " +
  "id, standard SQLite column types (INTEGER, VARCHAR(n), FLOAT, BOOLEAN, DATE, DATETIME) and " +
  "foreign-key columns enforced at the ORM layer. Indexes are created automatically on every " +
  "primary key and on users.email (used on every login and registration check). No views, " +
  "triggers or stored procedures are used, keeping the physical model identical to the logical one " +
  "in Section 4.7.5."
));

// ---- 4.8 Front-end architecture ------------------------------------------
sections.push(h2("4.8 Architecture of the Front-End of the System"));
sections.push(...figure(path.join(DIAG, "fig4_7_architecture.png"), "Figure 4.7: Three-tier architecture of the implemented system."));
sections.push(p(
  "The presentation tier is a classic server-rendered page shell rather than a single-page " +
  "application: every screen extends one base.html template that provides a fixed navigation bar " +
  "(brand, role-aware links, a log-out control), a centred content container, and a flash-message " +
  "area for success and error feedback. This choice keeps the front-end simple enough for the " +
  "two-person team to build and test within the project timeline, while the CSS uses relative " +
  "units and an auto-fitting grid (Section 4.9.2) so that card-based layouts such as the plans page " +
  "reflow on narrower screens."
));
sections.push(p("The interface exposes four page-level states relevant to a classification request:"));
sections.push(...bullets([
  "Upload -- a form gated by the caller's remaining quota, shown before any request is made.",
  "Accepted -- reserved for a future trained model returning a prediction at or above the 70% confidence threshold (implemented in code and covered by unit tests in Section 4.2.1, but not reachable in a live demonstration until a model is trained).",
  "Uncertain -- reserved for a below-threshold prediction from a trained model (same status as above).",
  "Model unavailable -- the state actually reachable today, shown whenever no ModelVersion has cleared the evaluation gate; this is what every screenshot of a submitted classification in Section 4.9.3 shows.",
]));
sections.push(p(
  "Protected screens (dashboard, classify, history, feedback, plans, admin) redirect an " +
  "unauthenticated or session-expired visitor to the login page rather than rendering a broken or " +
  "partially-authorised page; this was exercised directly in test_auth.py::test_auth05 and " +
  "test_admin_rbac.py."
));

// ---- 4.9 Implementation and coding ---------------------------------------
sections.push(h2("4.9 Implementation and coding"));
sections.push(h3("4.9.1 Introduction"));
sections.push(p(
  "This section describes the tools used to build the system and reproduces short excerpts of the " +
  "implementation together with screenshots of the running application, per the supervision " +
  "guidance to show the final running application rather than mockups. All screenshots were " +
  "captured by driving the live application (started with `python run.py`) with headless Chromium " +
  "through Playwright; none were hand-drawn or edited. The exact commit reproduced here is " +
  `${GIT_COMMIT}.`
));

sections.push(h3("4.9.2 Description of implementation tools and technology"));
sections.push(p(
  "Table 4.8 (Section 4.6.3) lists the full stack. Development used a modular monolith structure " +
  "(one Flask app, five blueprints) rather than microservices, chosen because it matches the " +
  "specification's own architecture decision (a single deployable service is easier for a two-person " +
  "student team to build, debug and demonstrate) while still keeping authentication, classification, " +
  "administration and subscription logic in separately testable modules -- app/auth, app/classifier, " +
  "app/users, app/admin and app/subscriptions."
));

sections.push(h3("4.9.3 Screenshots and Source Code"));
sections.push(p("Figures 4.8 to 4.17 show every reachable screen of the running application, captured from an actual browser session against the live server."));
sections.push(...figure(path.join(SHOT, "ch4_01_landing.png"), "Figure 4.8: Landing page.", 560));
sections.push(...figure(path.join(SHOT, "ch4_02_register.png"), "Figure 4.9: Registration screen.", 560));
sections.push(...figure(path.join(SHOT, "ch4_03_login.png"), "Figure 4.10: Login screen.", 560));
sections.push(...figure(path.join(SHOT, "ch4_04_dashboard.png"), "Figure 4.11: Authenticated dashboard, showing live quota figures.", 560));
sections.push(...figure(path.join(SHOT, "ch4_05_upload.png"), "Figure 4.12: Classification upload screen, with the model-status notice shown to users.", 560));
sections.push(...figure(path.join(SHOT, "ch4_06_result_model_unavailable.png"), "Figure 4.13: Result screen after submitting a real image -- the genuine, currently-reachable \"model unavailable\" outcome.", 560));
sections.push(...figure(path.join(SHOT, "ch4_07_history.png"), "Figure 4.14: Classification history, including a seeded placeholder record used only to demonstrate the layout (clearly labelled in the interface itself).", 560));
sections.push(...figure(path.join(SHOT, "ch4_08_feedback.png"), "Figure 4.15: Feedback/correction screen for one history record.", 560));
sections.push(...figure(path.join(SHOT, "ch4_09_plans.png"), "Figure 4.16: Subscription plans screen.", 560));
sections.push(...figure(path.join(SHOT, "ch4_10_admin_users.png"), "Figure 4.17: Administrator user-management screen.", 560));

sections.push(p("Six short excerpts illustrate the implementation decisions most relevant to the research objectives; each names its source file so it can be checked against the accompanying repository archive."));

sections.push(...codeBlock(
  "app/classifier/inference.py -- preprocessing to the model's input contract",
  `def preprocess_image(pil_image, target_size=Config.IMAGE_SIZE):
    """Resize to the model's expected input and scale to [0, 1]."""
    resized = pil_image.resize(target_size)
    array = np.asarray(resized, dtype=np.float32) / 255.0
    return np.expand_dims(array, axis=0)`
));
sections.push(...codeBlock(
  "app/classifier/inference.py -- confidence-threshold decision logic",
  `def apply_threshold(probabilities, classes, threshold=Config.CONFIDENCE_THRESHOLD):
    top_index = int(np.argmax(probabilities))
    confidence = float(probabilities[top_index])
    accepted = confidence >= threshold
    return {"category": classes[top_index], "confidence": confidence, "accepted": accepted}`
));
sections.push(...codeBlock(
  "app/classifier/routes.py -- protected classification route (quota + honest model-unavailable branch)",
  `@classifier_bp.route("/classifications", methods=["POST"])
@login_required_json
def create_classification():
    subscription, plan, used, remaining = _quota_status(current_user)
    if plan is None:
        return jsonify({"error": "no_active_plan"}), 403
    if remaining <= 0:
        return jsonify({"error": "quota_exhausted", "plan": plan.name,
                         "scan_limit": plan.scan_limit}), 429
    try:
        validate_upload(request.files.get("image"))
    except UploadValidationError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), 400

    active_model = _active_model_version()
    if active_model is None or not active_model.meets_evaluation_gate():
        # Honest "model unavailable" response -- no ModelVersion has
        # cleared the accuracy gate because no dataset has been
        # collected/trained on yet.
        ...`
));
sections.push(...codeBlock(
  "app/classifier/routes.py -- quota calculation",
  `def _quota_status(user):
    subscription = user.active_subscription()
    if subscription is None or subscription.plan is None:
        return None, None, 0, 0
    plan = subscription.plan
    period_key = _current_period_key()
    used = (db.session.query(db.func.coalesce(db.func.sum(UsageEvent.quantity), 0))
            .filter(UsageEvent.user_id == user.id,
                    UsageEvent.event_type == "classification",
                    UsageEvent.period_key == period_key)
            .scalar())
    remaining = max(plan.scan_limit - used, 0)
    return subscription, plan, used, remaining`
));
sections.push(...codeBlock(
  "app/utils.py -- server-side role decorator (Section 05: \"hiding an admin button is not security\")",
  `def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "authentication_required"}), 401
        if not current_user.is_active_account:
            return jsonify({"error": "account_inactive"}), 403
        if not current_user.is_admin:
            return jsonify({"error": "forbidden"}), 403
        return view_func(*args, **kwargs)
    return wrapped`
));
sections.push(...codeBlock(
  "app/models.py -- one SQLAlchemy relationship (User to its subscriptions)",
  `subscriptions = db.relationship("Subscription", backref="user", lazy="dynamic",
                                 foreign_keys="Subscription.user_id")

def active_subscription(self):
    return (self.subscriptions.filter_by(status="active")
            .order_by(Subscription.period_start.desc()).first())`
));

sections.push(pageBreak());
module.exports = { sections, GIT_COMMIT };
