const path = require("path");
const {
  h2, h3, p, pb, bullets, pageBreak, noteBox, dataTable, codeBlock,
  Paragraph, TextRun, AlignmentType,
} = require("./build_chapters_docx.js");
const { sections, GIT_COMMIT } = require("./main_docx.js");
const fs = require("fs");
const ROOT = path.join(__dirname, "..");

const PYTEST_OUTPUT = fs.readFileSync(path.join(ROOT, "evidence", "pytest_full_output.txt"), "utf8");

// ---- 4.10 Testing ---------------------------------------------------------
sections.push(h2("4.10 Testing"));

sections.push(h3("4.10.1 Introduction"));
sections.push(p(
  "This section reports what was actually tested, what the tests actually returned, and one " +
  "defect the tests actually found and that was actually fixed -- rather than only defining what " +
  "testing means. Every result below comes from a single, reproducible pytest run against commit " +
  `${GIT_COMMIT} (31 tests, 9.32 seconds, 0 failures; full console output in Appendix A) plus a ` +
  "scripted Playwright walkthrough of the live application used to capture the screenshots in " +
  "Section 4.9.3."
));

sections.push(h3("4.10.2 Objective of Testing"));
sections.push(p("Testing was designed to answer five questions directly relevant to the research objectives:"));
sections.push(...bullets([
  "Does upload validation correctly accept valid images and reject invalid, oversized or corrupt ones without ever consuming a user's quota?",
  "Is the classification request pipeline (quota check -> validation -> model lookup -> logging -> response) wired correctly end-to-end, including its honest failure mode when no trained model is available?",
  "Do authentication and role-based access control actually prevent a suspended account, an anonymous visitor, or a non-administrator from reaching protected functionality?",
  "Is a user's data isolated from other users (can user A read or correct user B's classification)?",
  "Are the specified security controls (CSRF protection, HttpOnly session cookies) actually enforced, not merely configured?",
]));

sections.push(h3("4.10.3 Unit Testing outputs"));
sections.push(p("Table 4.10 reports every unit-level test: upload validation (VAL) and the classification architecture (ARCH)."));
sections.push(dataTable(
  ["ID", "Requirement tested", "Expected", "Actual", "Status"],
  [
    ["VAL-01", "Well-formed JPEG accepted", "Decoded RGB image returned", "Image object returned, size (300,300)", "Pass"],
    ["VAL-02", "Missing file rejected", "UploadValidationError(no_file)", "Raised with code no_file", "Pass"],
    ["VAL-03", "Disallowed extension (.gif) rejected", "UploadValidationError(unsupported_extension)", "Raised with code unsupported_extension", "Pass"],
    ["VAL-04", "File over 5MB rejected", "UploadValidationError(file_too_large)", "Raised with code file_too_large", "Pass"],
    ["VAL-05", "Corrupt bytes with .jpg extension rejected", "UploadValidationError(corrupt_or_not_an_image)", "Raised with code corrupt_or_not_an_image", "Pass"],
    ["VAL-06", "Well-formed PNG accepted", "Decoded RGB image returned", "Image object returned, mode RGB", "Pass"],
    ["ARCH-01", "MobileNetV2 head builds with 6-class output", "output_shape == (None, 6)", "(None, 6)", "Pass"],
    ["ARCH-02", "Preprocessing yields the model's input contract", "Tensor shape (1,224,224,3), values in [0,1]", "Confirmed", "Pass"],
    ["ARCH-03", "Forward pass returns a valid probability distribution", "6 values summing to 1.0", "Sum = 1.0000 (±1e-4), latency measured", "Pass"],
    ["ARCH-04", "Threshold rejects a low-confidence prediction", "accepted = False", "False, category = organic (top of a flat distribution)", "Pass"],
    ["ARCH-05", "Threshold accepts a high-confidence prediction", "accepted = True", "True, category = general_trash", "Pass"],
  ],
  [1100, 2800, 2200, 2500, 800]
));

sections.push(h3("4.10.4 Validation Testing outputs"));
sections.push(p("Table 4.11 reports business-rule validation: that quota accounting only reacts to genuinely valid, billable requests."));
sections.push(dataTable(
  ["ID", "Requirement tested", "Expected", "Actual", "Status"],
  [
    ["SUB-01", "6th classification in a period on the Free plan (limit 5)", "Blocked with a quota message; exactly 5 Prediction rows exist", "Blocked; 5 rows confirmed by direct query", "Pass"],
    ["SUB-02", "10 consecutive invalid uploads followed by 1 valid one", "None of the invalid uploads consume quota; the valid one still succeeds", "0 quota consumed by invalid uploads; valid request succeeded", "Pass"],
  ],
  [1100, 3200, 2400, 1900, 700]
));

sections.push(h3("4.10.5 Integration Testing outputs"));
sections.push(p("Table 4.12 covers multi-component flows: registration through to a logged classification, feedback, and role-based access."));
sections.push(dataTable(
  ["ID", "Requirement tested", "Expected", "Actual", "Status"],
  [
    ["AUTH-01", "Registration creates a user with an automatic Free subscription", "User + active Free Subscription rows exist", "Confirmed by direct query", "Pass"],
    ["AUTH-02", "Duplicate email registration", "Generic rejection, no hint that the email exists", "HTTP 400, generic message", "Pass"],
    ["AUTH-03", "Password under 8 characters", "Registration rejected", "HTTP 400", "Pass"],
    ["AUTH-04", "Wrong password at login", "Generic \"Incorrect email or password\"", "HTTP 401, generic message", "Pass"],
    ["AUTH-05", "Dashboard access after logout", "Redirected (session invalidated)", "HTTP 302 to login", "Pass"],
    ["AUTH-06", "Suspended account attempts login", "Login refused", "HTTP 403", "Pass"],
    ["CLS-01", "Valid image submitted with no trained model available", "Logged; honest model_unavailable response", "1 Prediction row, is_uncertain=True, predicted_class=None", "Pass"],
    ["CLS-02", "Invalid-extension image submitted", "Rejected before logging", "0 Prediction rows created", "Pass"],
    ["CLS-03", "History page after one classification", "Record visible with correct status", "\"Model unavailable\" shown", "Pass"],
    ["FB-01", "Feedback submitted for a logged prediction", "Correction stored; original prediction untouched", "Feedback row created; Prediction.predicted_class still None", "Pass"],
    ["ADM-01", "Administrator suspends a user", "Target user's status becomes 'suspended'", "Confirmed by direct query", "Pass"],
    ["ADM-02", "Suspended user's next login attempt", "Denied", "HTTP 403", "Pass"],
    ["AUTHZ-01", "Non-admin requests /admin/users page", "Denied", "HTTP 403", "Pass"],
    ["AUTHZ-02", "Anonymous request to /api/admin/users", "Denied", "HTTP 401", "Pass"],
    ["AUTHZ-03", "User A submits feedback on User B's prediction", "Denied", "HTTP 403", "Pass"],
  ],
  [1150, 3300, 2350, 1750, 800]
));

sections.push(h3("4.10.6 Functional and system testing results"));
sections.push(p(
  "Running the full suite together (rather than file by file, to catch cross-test interference such " +
  "as shared state) produced 31 passed, 0 failed in 9.32 seconds against commit " +
  `${GIT_COMMIT}. Table 4.13 documents one real defect this process found and its resolution -- ` +
  "included deliberately as evidence that verification, not just implementation, took place."
));
sections.push(dataTable(
  ["ID", "How found", "Symptom", "Root cause", "Fix", "Verified"],
  [
    ["DEF-01",
     "Scripted Playwright walkthrough of the live application (capturing Section 4.9.3 screenshots)",
     "Clicking \"Log out\" returned HTTP 400 instead of logging out",
     "The log-out form in app/templates/base.html was missing its CSRF hidden field",
     "Added <input type=\"hidden\" name=\"csrf_token\" ...> to the log-out form",
     "Re-ran the walkthrough end-to-end (register -> classify -> history -> feedback -> plans -> log out -> admin login); log-out now returns HTTP 302 as expected"],
  ],
  [900, 2050, 1650, 1900, 1550, 1300]
));
sections.push(p(
  "A second, lower-severity issue was found and fixed during the same walkthrough: two independent " +
  "form-submit buttons on the same page both matched a non-specific CSS selector used by the test " +
  "script (not a defect in the application itself), which was corrected by giving each primary " +
  "submit button a stable, unique id attribute -- a change that also makes the interface easier to " +
  "test in future."
));

sections.push(h3("4.10.7 Acceptance Testing Report"));
sections.push(noteBox(
  "No human user-acceptance testing was performed. Chapter Three's plan calls for 20 participants " +
  "completing five core tasks (register/log in, classify an item, understand the result, find " +
  "history, correct a result and request an upgrade) followed by a System Usability Scale (SUS) " +
  "questionnaire (Brooke, 1996). No participants were available during this development session, " +
  "and no SUS score, task-completion count or participant quotation is reported anywhere in this " +
  "document, because none exists yet. This is recorded here as outstanding work, with the concrete " +
  "next step given in Section 5.2."
));
sections.push(p(
  "As a partial, and explicitly non-equivalent, substitute, an automated walkthrough was scripted " +
  "against the live application covering the same primary task sequence a human participant would " +
  "attempt: register, view the dashboard, submit an image for classification, view history, submit " +
  "a correction, view plans, log out, and log in as an administrator to manage users. This " +
  "walkthrough completed successfully after the CSRF defect above was fixed, and produced the " +
  "screenshots in Section 4.9.3. It demonstrates that the primary task sequence is mechanically " +
  "reachable without a script error, but it says nothing about how a real resident of Gasabo " +
  "District would find the interface -- only human participants can answer that, and Table 4.6 " +
  "records it as not yet met."
));

module.exports = { sections, GIT_COMMIT, PYTEST_OUTPUT };
