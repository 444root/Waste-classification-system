const path = require("path");
const fs = require("fs");
const {
  h1, h2, h3, p, pb, bullets, numbered, pageBreak, noteBox, dataTable, codeBlock,
  Paragraph, TextRun, AlignmentType, Document, Packer, HeadingLevel,
  Header, Footer, PageNumber,
} = require("./build_chapters_docx.js");
const { sections, GIT_COMMIT, PYTEST_OUTPUT } = require("./part2_docx.js");

const ROOT = path.join(__dirname, "..");
const SCHEMA_DUMP = fs.readFileSync(path.join(ROOT, "evidence", "schema_dump.txt"), "utf8");
const NETWORK_PROBE = fs.readFileSync(path.join(ROOT, "evidence", "network_reachability_probe.txt"), "utf8");

function monoBlock(text) {
  return text.split("\n").map(
    (line) =>
      new Paragraph({
        children: [new TextRun({ text: line.length ? line : " ", font: "Consolas", size: 16 })],
        spacing: { after: 0 },
      })
  );
}

// =========================================================================
// CHAPTER FIVE
// =========================================================================
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "CHAPTER FIVE", bold: true, size: 30 })],
  spacing: { after: 100 },
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "CONCLUSIONS AND RECOMMENDATIONS", bold: true, size: 26 })],
  spacing: { after: 400 },
}));

sections.push(h2("5.0 Introduction"));
sections.push(p(
  "This chapter draws conclusions from the evidence presented in Chapter Four, makes " +
  "recommendations to the parties who can act on them, and identifies specific areas for further " +
  "research. As in Chapter Four, conclusions are stated only where they are supported by evidence " +
  "actually produced; where an objective was not met, that is stated plainly rather than implied " +
  "to have succeeded."
));

sections.push(h2("5.1 Conclusion(s)"));
sections.push(p(
  "The study set out to design and implement a system that replaces informal, inconsistent manual " +
  "waste-category decisions in Gasabo District with an image-recognition-based digital workflow. " +
  "On the engineering side of that goal, the conclusion is positive and evidenced: a complete, " +
  "modular Flask application was designed and built covering registration and authentication, " +
  "role-based administration, subscription and quota management, a classification request " +
  "pipeline, history, and user-submitted correction of results. Thirty-one automated tests -- unit, " +
  "integration and security -- pass against a live instance of the application, and the interface " +
  "was walked through end-to-end with browser automation, which itself surfaced and led to the " +
  "fixing of a real defect (a missing CSRF token on the log-out control). This demonstrates that " +
  "the non-model parts of the system -- which are most of what a user or administrator actually " +
  "interacts with -- are functionally correct and were genuinely, not just nominally, verified."
));
sections.push(p(
  "On the artificial-intelligence side of the goal, the conclusion is that the objective is not yet " +
  "achieved, for a specific and disclosed reason rather than an unexplained gap: the development " +
  "environment used for this phase of the work could not reach any host serving a public " +
  "waste-image dataset or pretrained ImageNet weights for MobileNetV2 (Appendix C records the " +
  "exact hosts probed and their results). The classification architecture specified in Chapter " +
  "Three -- MobileNetV2 with a GlobalAveragePooling, Dense(128, ReLU), Dropout(0.3), Dense(6, " +
  "softmax) head -- was successfully built and unit-tested with random weights, proving the " +
  "architecture and the surrounding software contract (image in, six-class probability vector out, " +
  "thresholded at 70% confidence) are correctly wired; what remains is training that architecture " +
  "on real data and evaluating it, which is a data-collection and compute problem rather than a " +
  "software-design one."
));
sections.push(p(
  "Taken together, the study concludes that an image-recognition-based waste classification system " +
  "for Gasabo District is technically feasible and that most of the engineering risk in building " +
  "one -- the parts a student team is most likely to get wrong, such as authorisation, data " +
  "integrity, and quota logic -- has already been retired through working, tested code. The " +
  "remaining risk is narrower and well-understood: obtaining a sufficient, representative image " +
  "dataset and the compute/network access to train on it, and obtaining human participants to " +
  "evaluate the resulting interface. Neither of these is evidence against the proposal; both are " +
  "concrete, schedulable tasks, set out below."
));

sections.push(h2("5.2 Recommendations"));
sections.push(h3("5.2.1 To the research team (immediate next steps)"));
sections.push(...numbered([
  "Complete image data collection at Gasabo District collection points per the Chapter Three " +
  "methodology (consented photography across the six categories), and/or obtain TrashNet and a " +
  "compatible organic-waste dataset from a network environment that can reach them (a normal " +
  "university or home internet connection, unlike the restricted development sandbox used for this " +
  "submission).",
  "Run the training workflow already specified in the technical documentation (freeze-then-fine-tune " +
  "MobileNetV2, class-weighted loss for the imbalanced categories, stratified 70/15/15 split by " +
  "source item) and register the resulting model through the existing POST /api/admin/model-versions " +
  "endpoint and ModelVersion.meets_evaluation_gate() check -- no application code changes are needed " +
  "for a trained model to start serving real predictions once it clears the 85% accuracy gate.",
  "Re-run the existing 31-test suite against the trained build to confirm nothing regressed, then add " +
  "model-specific tests (confusion matrix generation, per-class recall, latency with real weights " +
  "loaded).",
  "Recruit at least the planned 20 participants for System Usability Scale-based user-acceptance " +
  "testing of the five core tasks identified in Section 4.10.7, and report the resulting SUS score " +
  "honestly, including any tasks participants could not complete unassisted.",
  "Move the deployment from Flask's development server to a production WSGI server (e.g. Gunicorn) " +
  "behind HTTPS before any pilot involving real users, per the technical documentation's deployment " +
  "guidance.",
]));

sections.push(h3("5.2.2 To the University and supervision"));
sections.push(...bullets([
  "Where possible, ensure the development environment used for the AI component of similar projects " +
  "has unrestricted access to standard ML resources (dataset hosts, pretrained-weight repositories) " +
  "well before the implementation deadline, since this was the binding constraint on this phase of " +
  "the work, not team effort or the choice of approach.",
  "Consider accepting a staged submission for AI-heavy undergraduate projects, where the software " +
  "engineering and the model-training/evaluation evidence can be reviewed on separate, explicit " +
  "timelines, rather than requiring both to land simultaneously.",
]));

sections.push(h3("5.2.3 To Gasabo District stakeholders (once a trained, evaluated model exists)"));
sections.push(...bullets([
  "Pilot the system at a small number of communal collection points before any wider rollout, using " +
  "the audit log and usage-event data already implemented to measure real usage rather than " +
  "assumed usage.",
  "Validate the illustrative subscription pricing in the technical documentation with genuine " +
  "interviews of institutional buyers (schools, offices, waste-collection companies) before treating " +
  "it as a business model, exactly as the technical documentation itself recommends.",
]));

sections.push(h2("5.3 Area(s) for further research"));
sections.push(...bullets([
  "Comparative evaluation of MobileNetV2 against other lightweight architectures (e.g. " +
  "EfficientNet-Lite, MobileNetV3) once a labelled Gasabo-specific dataset exists, to check whether " +
  "the architecture choice remains optimal for local imagery.",
  "Multi-object detection and segmentation, to handle images containing more than one waste item -- " +
  "explicitly out of scope for this single-item classification MVP.",
  "Integration with IoT sensors or automated physical sorting hardware, deferred in the technical " +
  "documentation's roadmap to a phase after the software classification service is proven.",
  "A longitudinal study of recycling-rate or contamination-rate impact at pilot collection points, " +
  "which requires a deployed, trained system and could not be attempted at this stage.",
  "Formal validation of the subscription/business model with institutional buyers, distinct from the " +
  "technical evaluation reported here.",
]));

sections.push(pageBreak());

// =========================================================================
// REFERENCES
// =========================================================================
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "REFERENCES", bold: true, size: 28 })],
  spacing: { after: 300 },
}));
sections.push(p(
  "This list contains only sources newly cited in Chapters Four and Five. Sources already cited in " +
  "Chapters One to Three (including the Gasabo/Nduba-landfill-specific literature) remain in the " +
  "dissertation's consolidated reference list and are not repeated here.",
  { italics: true }
));
const refs = [
  "Brooke, J. (1996) 'SUS: A quick and dirty usability scale', in Jordan, P.W. et al. (eds.) Usability Evaluation in Industry. London: Taylor & Francis.",
  "Chollet, F. et al. (2015-) Keras [software documentation]. Available at: https://keras.io.",
  "Pallets Projects (2010-) Flask [software documentation]. Available at: https://flask.palletsprojects.com.",
  "Sandler, M., Howard, A., Zhu, M., Zhmoginov, A. and Chen, L.C. (2018) 'MobileNetV2: Inverted Residuals and Linear Bottlenecks', in Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), pp. 4510-4520.",
  "Yang, M. and Thung, G. (2016) Classification of Trash for Recyclability Status. CS229 Course Project Report, Stanford University.",
];
sections.push(...refs.map((r) => new Paragraph({
  children: [new TextRun({ text: r })],
  spacing: { after: 160 },
  indent: { left: 360, hanging: 360 },
})));

sections.push(pageBreak());

// =========================================================================
// APPENDICES
// =========================================================================
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  children: [new TextRun({ text: "APPENDICES", bold: true, size: 28 })],
  spacing: { after: 300 },
}));

sections.push(h2("Appendix A: Full automated test output (verbatim)"));
sections.push(p(`Captured from a single, uninterrupted pytest run against commit ${GIT_COMMIT}.`));
sections.push(...monoBlock(PYTEST_OUTPUT));

sections.push(pageBreak());
sections.push(h2("Appendix B: Complete data dictionary (all nine tables)"));
sections.push(p("Generated directly from the live SQLAlchemy metadata (app/models.py) rather than typed by hand."));
sections.push(...monoBlock(SCHEMA_DUMP));

sections.push(pageBreak());
sections.push(h2("Appendix C: Network reachability probe"));
sections.push(p("The direct evidence behind the environment limitation disclosed throughout Chapter Four."));
sections.push(...monoBlock(NETWORK_PROBE));

sections.push(pageBreak());
sections.push(h2("Appendix D: Repository structure and reproduction steps"));
sections.push(...codeBlock(
  "Repository layout",
  `waste-classifier/
  app/
    auth/ classifier/ users/ admin/ subscriptions/ main/   (Flask blueprints)
    templates/ static/                                     (front-end)
    models.py extensions.py utils.py __init__.py
  tests/            (31 automated tests -- see Appendix A)
  diagrams/         (Figures 4.1-4.7, generated by scripts/generate_diagrams.py
                     and scripts/generate_sequence_diagram.py)
  screenshots/      (Figures 4.8-4.17, generated by scripts/capture_screenshots.py)
  evidence/         (raw environment, latency, schema and network-probe evidence)
  config.py run.py seed.py requirements.txt`
));
sections.push(p("To reproduce every result in this chapter from a clean checkout:"));
sections.push(...codeBlock(
  "Reproduction commands",
  `pip install -r requirements.txt
python seed.py --with-demo-data      # creates plans, an admin account and a
                                      # placeholder demo record (clearly
                                      # labelled; not a real classification)
pytest -v                            # 31 passed (Appendix A)
python run.py                        # serves the application on :5055
python scripts/generate_diagrams.py
python scripts/generate_sequence_diagram.py
python scripts/capture_screenshots.py`
));
sections.push(p(`Full source code and this evidence accompany this document as a separate archive citing commit ${GIT_COMMIT}.`));

// =========================================================================
// BUILD DOCUMENT
// =========================================================================
const doc = new Document({
  creator: "Brenda Abeza Kimenyi",
  title: "Waste Classification System -- Chapters Four and Five",
  styles: {
    default: {
      document: { run: { font: "Calibri", size: 22 } },
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { bold: true, size: 30, color: "1F6F4F" }, paragraph: { spacing: { before: 240, after: 160 } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { bold: true, size: 26, color: "1F6F4F" }, paragraph: { spacing: { before: 260, after: 140 } } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { bold: true, size: 23, color: "1C1F1E" }, paragraph: { spacing: { before: 200, after: 100 } } },
      { id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { bold: true, italics: true, size: 21, color: "1C1F1E" }, paragraph: { spacing: { before: 160, after: 80 } } },
    ],
  },
  sections: [
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: "Waste Classification System -- Chapters Four & Five", size: 16, color: "5C6B64" })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ children: [PageNumber.CURRENT], size: 18 })],
          })],
        }),
      },
      children: sections,
    },
  ],
});

const OUT_PATH = path.join(ROOT, "output", "Waste_Classification_System_Chapters_4_5.docx");
fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(OUT_PATH, buffer);
  console.log("wrote", OUT_PATH, buffer.length, "bytes");
});
