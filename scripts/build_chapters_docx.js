const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, ImageRun,
  BorderStyle, PageBreak, Header, Footer, PageNumber, LevelFormat,
  ExternalHyperlink, VerticalAlign,
} = require("docx");
const { imageSize: sizeOf } = require("image-size");

const ROOT = path.join(__dirname, "..");
const DIAG = path.join(ROOT, "diagrams");
const SHOT = path.join(ROOT, "screenshots");

// ---------- style helpers ----------------------------------------------
const GREEN = "1F6F4F";
const INK = "1C1F1E";
const MUTED = "5C6B64";

function h1(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 240, after: 160 } });
}
function h2(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 300, after: 120 } });
}
function h3(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_3, spacing: { before: 220, after: 100 } });
}
function h4(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_4, spacing: { before: 180, after: 80 } });
}
function p(text, opts = {}) {
  const runs = Array.isArray(text) ? text : [new TextRun({ text })];
  return new Paragraph({ children: runs, spacing: { after: 160 }, ...opts });
}
function pb(boldText, rest) {
  const runs = [new TextRun({ text: boldText, bold: true })];
  if (rest) runs.push(new TextRun({ text: rest }));
  return new Paragraph({ children: runs, spacing: { after: 160 } });
}
function bullets(items) {
  return items.map(
    (item) =>
      new Paragraph({
        text: item,
        bullet: { level: 0 },
        spacing: { after: 80 },
      })
  );
}
function numbered(items) {
  // Manually-prefixed numbering avoids needing a Word numbering.xml
  // definition + matching numId reference for a single list.
  return items.map(
    (item, i) =>
      new Paragraph({
        children: [new TextRun({ text: `${i + 1}. `, bold: true }), new TextRun({ text: item })],
        spacing: { after: 100 },
        indent: { left: 360, hanging: 360 },
      })
  );
}
function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}
function noteBox(text) {
  // NOTE: docx.js's Paragraph "border" (w:pBdr) always emits child elements
  // in a fixed top/bottom/left/right order internally, which some strict
  // OOXML validators reject (schema expects top/left/bottom/right). Using
  // shading alone (no border) sidesteps that library limitation.
  return new Paragraph({
    children: [new TextRun({ text, italics: true })],
    shading: { type: ShadingType.CLEAR, fill: "FFF8EA" },
    spacing: { before: 120, after: 200 },
    indent: { left: 100, right: 100 },
  });
}

function imageParagraph(filePath, maxWidth = 560) {
  const dims = sizeOf(fs.readFileSync(filePath));
  let w = dims.width;
  let h = dims.height;
  if (w > maxWidth) {
    h = Math.round((h * maxWidth) / w);
    w = maxWidth;
  }
  return new Paragraph({
    children: [new ImageRun({ data: fs.readFileSync(filePath), transformation: { width: w, height: h }, type: "png" })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 60 },
  });
}
function caption(text) {
  return new Paragraph({
    children: [new TextRun({ text, italics: true, size: 20, color: MUTED })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 220 },
  });
}
function figure(filePath, captionText, maxWidth = 560) {
  return [imageParagraph(filePath, maxWidth), caption(captionText)];
}

function cell(text, opts = {}) {
  const { bold = false, shade = null, width = null, align = AlignmentType.LEFT } = opts;
  return new TableCell({
    width: width ? { size: width, type: WidthType.DXA } : undefined,
    shading: shade ? { type: ShadingType.CLEAR, fill: shade } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [
      new Paragraph({
        alignment: align,
        children: [new TextRun({ text: String(text), bold, size: 19 })],
      }),
    ],
  });
}

function dataTable(headers, rows, widths) {
  const totalWidth = 9350;
  const colWidths = widths || headers.map(() => Math.floor(totalWidth / headers.length));
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((htext, i) => cell(htext, { bold: true, shade: "1F6F4F", width: colWidths[i] })),
  });
  const bodyRows = rows.map(
    (row, ri) =>
      new TableRow({
        children: row.map((val, i) => cell(val, { width: colWidths[i], shade: ri % 2 === 1 ? "F4F8F6" : null })),
      })
  );
  // Header text should be white -- rebuild with white font
  const headerRowWhite = new TableRow({
    tableHeader: true,
    children: headers.map(
      (htext, i) =>
        new TableCell({
          width: { size: colWidths[i], type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, fill: "1F6F4F" },
          verticalAlign: VerticalAlign.CENTER,
          margins: { top: 60, bottom: 60, left: 100, right: 100 },
          children: [new Paragraph({ children: [new TextRun({ text: htext, bold: true, color: "FFFFFF", size: 19 })] })],
        })
    ),
  });
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [headerRowWhite, ...bodyRows],
  });
}

function codeBlock(fileLabel, lines) {
  const codeParas = lines.split("\n").map(
    (line) =>
      new Paragraph({
        children: [new TextRun({ text: line.length ? line : " ", font: "Consolas", size: 17 })],
        shading: { type: ShadingType.CLEAR, fill: "F5F5F3" },
        spacing: { after: 0 },
      })
  );
  return [
    new Paragraph({
      children: [new TextRun({ text: fileLabel, bold: true, italics: true, size: 18, color: MUTED })],
      spacing: { before: 160, after: 40 },
    }),
    ...codeParas,
    new Paragraph({ text: "", spacing: { after: 160 } }),
  ];
}

module.exports = {
  h1, h2, h3, h4, p, pb, bullets, numbered, pageBreak, noteBox,
  imageParagraph, caption, figure, dataTable, codeBlock, cell,
  DIAG, SHOT, ROOT, Document, Packer, Paragraph, TextRun, HeadingLevel,
  AlignmentType, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, PageNumber, Header, Footer, LevelFormat,
};
