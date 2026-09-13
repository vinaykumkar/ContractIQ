/* ContractIQ — project presentation deck (14 slides, 13.33x7.5in) */
const pptxgen = require("pptxgenjs");
const path = require("path");

const A = "D:/ContractIQ/reports/deck_assets"; // assets

// ---------- palette (from the app's "Fluid Legal Intelligence" system) ----------
const INK = "0D1A1C";      // dark background (obsidian/ink)
const INK2 = "14262A";     // panel on dark
const IVORY = "F0EFE9";    // text on dark
const MUT_D = "9AB3AE";    // muted text on dark
const BG = "FFFFFF";       // light background
const PRIMARY = "0E6E63";  // deep teal
const TEAL2 = "2FA08D";    // lighter teal (charts)
const TEAL3 = "7CC5B7";    // lightest teal (charts)
const TINT = "E9F3F0";     // mint tint band / highlight
const CORAL = "E4572E";    // accent (HIGH risk)
const AMBER = "C9962E";    // MEDIUM band only
const TEXT = "182A2C";
const MUTED = "5E7370";

const DISP = "Georgia";
const BODY = "Segoe UI";

const W = 13.33, H = 7.5, M = 0.5;

let p = new pptxgen();
p.layout = "LAYOUT_WIDE";
p.author = "ContractIQ";
p.title = "ContractIQ — AI Contract Intelligence & Risk Analysis";

// ---------- helpers (factories: fresh objects every call) ----------
const bu = () => ({ code: "2022", indent: 12 });
const kicker = (s, txt, color = PRIMARY, x = M, y = 0.42) =>
  s.addText(txt, { x, y, w: 9, h: 0.32, fontSize: 12.5, fontFace: BODY, bold: true,
    color, charSpacing: 3, margin: 0 });
const title = (s, txt, opts = {}) => {
  const o = Object.assign({ x: M, y: 0.72, w: W - 2 * M, h: 0.75, fontSize: 31,
    fontFace: DISP, bold: true, color: TEXT, margin: 0 }, opts);
  s.addText(txt, o);
};
const source = (s, txt, y = 7.06, color = MUTED) =>
  s.addText(txt, { x: M, y, w: W - 2 * M, h: 0.28, fontSize: 12, fontFace: BODY,
    color, margin: 0 });
const card = (s, x, y, w, h, fill = "FFFFFF") =>
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill },
    rectRadius: 0.07,
    shadow: { type: "outer", color: "0D1A1C", blur: 7, offset: 2, angle: 90, opacity: 0.13 } });

// ===========================================================================
// SLIDE 1 — TITLE (dark)
// ===========================================================================
let s = p.addSlide();
s.background = { color: INK };

// clause-map ring motif: mint ring + node dots (echoes the Clause Intelligence Map)
const cx = 10.35, cy = 3.75, R = 1.95;
s.addShape(p.shapes.OVAL, { x: cx - R, y: cy - R, w: 2 * R, h: 2 * R,
  fill: { color: INK, transparency: 100 }, line: { color: "2A4A46", width: 1.5 } });
s.addShape(p.shapes.OVAL, { x: cx - R + 0.55, y: cy - R + 0.55, w: 2 * (R - 0.55), h: 2 * (R - 0.55),
  fill: { color: INK, transparency: 100 }, line: { color: "223C39", width: 1 } });
// hub
s.addShape(p.shapes.OVAL, { x: cx - 0.34, y: cy - 0.34, w: 0.68, h: 0.68,
  fill: { color: TINT }, line: { color: TINT, width: 0 } });
// nodes on outer ring
const nodes = [
  [cx + R * Math.cos(-Math.PI / 2), cy + R * Math.sin(-Math.PI / 2), CORAL],
  [cx + R * Math.cos(Math.PI / 9), cy + R * Math.sin(Math.PI / 9), TEAL2],
  [cx + R * Math.cos((Math.PI / 9) + Math.PI / 4.5), cy + R * Math.sin((Math.PI / 9) + Math.PI / 4.5), TEAL2],
  [cx + R * Math.cos((Math.PI / 9) + 2 * Math.PI / 4.5), cy + R * Math.sin((Math.PI / 9) + 2 * Math.PI / 4.5), TEAL3],
  [cx + R * Math.cos((Math.PI / 9) + 3 * Math.PI / 4.5), cy + R * Math.sin((Math.PI / 9) + 3 * Math.PI / 4.5), TEAL3],
  [cx + R * Math.cos((Math.PI / 9) + 4 * Math.PI / 4.5), cy + R * Math.sin((Math.PI / 9) + 4 * Math.PI / 4.5), TEAL2],
  [cx + R * Math.cos((Math.PI / 9) + 5 * Math.PI / 4.5), cy + R * Math.sin((Math.PI / 9) + 5 * Math.PI / 4.5), TEAL2],
  [cx + R * Math.cos((Math.PI / 9) + 6 * Math.PI / 4.5), cy + R * Math.sin((Math.PI / 9) + 6 * Math.PI / 4.5), TEAL3],
];
nodes.forEach(([nx, ny, c]) =>
  s.addShape(p.shapes.OVAL, { x: nx - 0.09, y: ny - 0.09, w: 0.18, h: 0.18,
    fill: { color: c }, line: { color: INK, width: 1.5 } }));

s.addText("PROJECT PRESENTATION", { x: M, y: 1.62, w: 6.6, h: 0.34, fontSize: 13,
  fontFace: BODY, bold: true, color: TEAL2, charSpacing: 4, margin: 0 });
s.addText("ContractIQ", { x: M - 0.04, y: 2.0, w: 7.2, h: 1.35, fontSize: 72,
  fontFace: DISP, bold: true, color: IVORY, margin: 0 });
s.addText("AI Contract Intelligence & Risk Analysis", { x: M, y: 3.36, w: 7.4, h: 0.5,
  fontSize: 22, fontFace: BODY, color: "CDE3DE", margin: 0 });
s.addText([
  { text: "Upload a contract. Get every key clause, the exact evidence it rests on,", options: { breakLine: true } },
  { text: "and a transparent risk score — entirely on your own machine.", options: {} },
], { x: M, y: 4.05, w: 6.9, h: 0.85, fontSize: 15.5, fontFace: BODY, color: MUT_D,
  paraSpaceAfter: 4, margin: 0 });

const chips = ["Python 3.11", "FastAPI", "PyTorch · MiniLM", "CUAD v1", "React 19", "SQLite"];
let chipX = M;
chips.forEach((c) => {
  const w = 0.32 + c.length * 0.082;
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: chipX, y: 5.42, w, h: 0.42,
    fill: { color: INK2 }, rectRadius: 0.2, line: { color: "2A4A46", width: 0.75 } });
  s.addText(c, { x: chipX, y: 5.42, w, h: 0.42, fontSize: 12, fontFace: BODY,
    color: "BFD6D1", align: "center", valign: "middle", margin: 0 });
  chipX += w + 0.16;
});
s.addText("Local-first · No cloud · No paid APIs          September 2026",
  { x: M, y: 6.78, w: 9, h: 0.3, fontSize: 12.5, fontFace: BODY, color: MUT_D, margin: 0 });

// ===========================================================================
// SLIDE: AGENDA (light)
s = p.addSlide();
s.background = { color: BG };
kicker(s, "AGENDA");
title(s, "What we will cover");

const agenda = [
  ["01", "The problem & the solution", "why contract review breaks, and the pipeline that fixes it"],
  ["02", "System architecture", "four layers, one direction of data flow"],
  ["03", "Machine learning", "CUAD dataset, model choice, evidence-accurate extraction"],
  ["04", "Risk methodology", "fifteen auditable rules behind the 0-100 score"],
  ["05", "Engineering", "backend API, data model, security & privacy"],
  ["06", "Proof", "199 tests, benchmarks, and a live demo on real files"],
];
agenda.forEach((a, i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = M + col * 6.42, y = 1.98 + row * 1.58;
  s.addText(a[0], { x, y, w: 0.95, h: 0.75, fontSize: 34, fontFace: DISP, bold: true,
    color: TEAL2, margin: 0 });
  s.addText([
    { text: a[1], options: { bold: true, fontSize: 16.5, color: TEXT, breakLine: true } },
    { text: a[2], options: { fontSize: 12.5, color: MUTED } },
  ], { x: x + 1.0, y: y + 0.02, w: 5.3, h: 1.4, fontFace: BODY, paraSpaceAfter: 4, margin: 0, valign: "top" });
});
s.addText("Everything shown runs 100% locally \u2014 the demo at the end uses real files, not slides.",
  { x: M, y: 6.8, w: 12, h: 0.35, fontSize: 12.5, fontFace: BODY, italic: true, color: PRIMARY, margin: 0 });

// SLIDE 2 — PROBLEM (light)
// ===========================================================================
s = p.addSlide();
s.background = { color: BG };
kicker(s, "THE PROBLEM");
title(s, "Contract review is slow, manual, and easy to get wrong");

const stats = [
  ["6.7k", "median tokens per contract", "max observed: 78.6k tokens"],
  ["41", "risk-relevant clause categories", "tracked in the CUAD v1 dataset"],
  ["100%", "of review burden on one reader", "key clauses buried in boilerplate"],
];
stats.forEach((st, i) => {
  const x = M + i * 4.19;
  card(s, x, 1.86, 3.95, 2.1, TINT);
  s.addText(st[0], { x: x + 0.3, y: 2.02, w: 3.4, h: 0.95, fontSize: 60, fontFace: DISP,
    bold: true, color: PRIMARY, margin: 0 });
  s.addText(st[1], { x: x + 0.32, y: 3.0, w: 3.35, h: 0.4, fontSize: 14, fontFace: BODY,
    bold: true, color: TEXT, margin: 0 });
  s.addText(st[2], { x: x + 0.32, y: 3.4, w: 3.35, h: 0.35, fontSize: 12.5, fontFace: BODY,
    color: MUTED, margin: 0 });
});

const pains = [
  ["Missed clauses are expensive", "A missed auto-renewal, exclusivity or non-compete term binds the business for years."],
  ["Manual review doesn't scale", "Reading every page to find 15 things that matter is hours of expert time per contract."],
  ["Cloud tools break confidentiality", "Contracts are among the most sensitive documents a company holds; pasting them into web services is a non-starter."],
];
pains.forEach((pi, i) => {
  const y = 4.42 + i * 0.82;
  s.addShape(p.shapes.OVAL, { x: M + 0.05, y: y + 0.15, w: 0.16, h: 0.16,
    fill: { color: i === 2 ? CORAL : PRIMARY }, line: { color: BG, width: 0 } });
  s.addText([
    { text: pi[0] + "  ", options: { bold: true, color: TEXT, breakLine: false } },
    { text: "— " + pi[1], options: { color: MUTED } },
  ], { x: M + 0.42, y, w: 11.6, h: 0.75, fontSize: 14.5, fontFace: BODY, margin: 0 });
});
source(s, "Dataset facts: CUAD v1 (510 contracts, 20,910 QA pairs) — project Phase 1 dataset analysis");

// ===========================================================================
// SLIDE 3 — WHAT IT DOES: PIPELINE (light)
// ===========================================================================
s = p.addSlide();
s.background = { color: BG };
kicker(s, "THE SOLUTION");
title(s, "One pipeline: from raw file to defensible analysis");

const steps = [
  ["1", "Upload", "PDF · DOCX · TXT,\nvalidated & sanitized"],
  ["2", "Parse", "PyMuPDF / python-docx\nto exact text + offsets"],
  ["3", "Extract", "MiniLM QA model fine-\ntuned on CUAD"],
  ["4", "Score", "15 transparent risk\nrules, 0–100 + band"],
  ["5", "Review", "Evidence-highlighted\nworkspace & history"],
];
steps.forEach((st, i) => {
  const x = M + i * 2.56;
  card(s, x, 2.0, 2.28, 2.5, i === 2 ? PRIMARY : "FFFFFF");
  const dark = i === 2;
  s.addText(st[0], { x: x + 0.24, y: 2.2, w: 0.8, h: 0.7, fontSize: 34, fontFace: DISP,
    bold: true, color: dark ? TINT : TEAL2, margin: 0 });
  s.addText(st[1], { x: x + 0.24, y: 2.95, w: 1.9, h: 0.45, fontSize: 17.5, fontFace: BODY,
    bold: true, color: dark ? "FFFFFF" : TEXT, margin: 0 });
  s.addText(st[2], { x: x + 0.24, y: 3.42, w: 1.85, h: 0.95, fontSize: 12, fontFace: BODY,
    color: dark ? "CFE6E1" : MUTED, margin: 0 });
  if (i < 4) s.addText("→", { x: x + 2.24, y: 3.0, w: 0.4, h: 0.5, fontSize: 20,
    fontFace: BODY, color: TEAL2, align: "center", margin: 0 });
});

const props = [
  ["100% local", "no cloud calls, no API keys — uploads never leave the machine"],
  ["Evidence-linked", "every finding stores the exact character range it came from"],
  ["Never legal advice", "AI-assisted analysis; results are flagged for professional review"],
];
props.forEach((pr, i) => {
  const x = M + i * 4.19;
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 5.05, w: 3.95, h: 1.5,
    fill: { color: TINT }, rectRadius: 0.07, line: { color: BG, width: 0 } });
  s.addText(pr[0], { x: x + 0.28, y: 5.25, w: 3.4, h: 0.4, fontSize: 15.5, fontFace: BODY,
    bold: true, color: PRIMARY, margin: 0 });
  s.addText(pr[1], { x: x + 0.28, y: 5.66, w: 3.42, h: 0.75, fontSize: 12.5, fontFace: BODY,
    color: TEXT, margin: 0 });
});

// ===========================================================================
// SLIDE 4 — UI SHOWCASE: ANALYSIS WORKSPACE (dark, full-bleed)
// ===========================================================================
s = p.addSlide();
s.background = { color: INK };
s.addImage({ path: path.join(A, "ui_detail.png"), x: 0, y: 0, w: W, h: H });
s.addShape(p.shapes.RECTANGLE, { x: 0, y: 6.72, w: W, h: H - 6.72,
  fill: { color: "0A1416" }, line: { color: "0A1416", width: 0 } });
s.addText([
  { text: "Analysis workspace  ", options: { bold: true, color: IVORY, breakLine: false } },
  { text: "— Risk Orb (67 · HIGH), Clause Intelligence Map, evidence highlighting", options: { color: MUT_D } },
], { x: M, y: 6.72, w: W - 2 * M, h: H - 6.72, fontSize: 13, fontFace: BODY, valign: "middle", margin: 0 });

// ===========================================================================
// SLIDE 5 — KEY FEATURES (light)
// ===========================================================================
s = p.addSlide();
s.background = { color: BG };
kicker(s, "CAPABILITIES");
title(s, "What the engine delivers for every contract");

const feats = [
  ["15 clause types", "Parties, dates, governing law, termination, non-compete, exclusivity, liability cap, insurance and more — from a 41-type CUAD registry."],
  ["Exact evidence", "Every clause maps to precise character offsets; verified at 0 mismatches across 129 checks on real analyses."],
  ["Transparent risk", "Deterministic 0–100 score from 15 readable rules in three bands — deliberately separate from AI confidence."],
  ["Robust ingestion", "Safe handling of corrupt, encrypted, scanned and oversized files — rejected with clear errors, never fabricated text."],
  ["History & recovery", "Searchable contract history, duplicate detection (SHA-256), crash recovery and idempotent re-analysis."],
  ["GPU or CPU", "CUDA detection at startup with automatic CPU fallback — same code, no configuration."],
];
feats.forEach((f, i) => {
  const x = M + (i % 3) * 4.19, y = 1.92 + Math.floor(i / 3) * 2.42;
  card(s, x, y, 3.95, 2.2, "FFFFFF");
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: x + 0.26, y: y + 0.26, w: 0.3, h: 0.3,
    fill: { color: i === 1 ? CORAL : PRIMARY }, rectRadius: 0.06, line: { color: BG, width: 0 } });
  s.addText(f[0], { x: x + 0.68, y: y + 0.27, w: 3.1, h: 0.38, fontSize: 16, fontFace: BODY,
    bold: true, color: TEXT, margin: 0 });
  s.addText(f[1], { x: x + 0.28, y: y + 0.68, w: 3.42, h: 1.35, fontSize: 12.5, fontFace: BODY,
    color: MUTED, margin: 0 });
});

// ===========================================================================
// SLIDE 6 — ARCHITECTURE (light, diagram)
// ===========================================================================
s = p.addSlide();
s.background = { color: BG };
kicker(s, "SYSTEM DESIGN");
title(s, "Four layers, one direction of data flow");

const box = (x, y, w, h, head, sub, fill, headColor, subColor, line) => {
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill },
    rectRadius: 0.06, line: line ? { color: line, width: 1 } : { color: fill, width: 0 } });
  s.addText(head, { x: x + 0.18, y: y + 0.14, w: w - 0.36, h: 0.36, fontSize: 14.5,
    fontFace: BODY, bold: true, color: headColor, margin: 0 });
  if (sub) s.addText(sub, { x: x + 0.18, y: y + 0.52, w: w - 0.36, h: h - 0.6,
    fontSize: 11.5, fontFace: BODY, color: subColor, margin: 0 });
};
const arrow = (x1, y1, x2, y2) =>
  s.addShape(p.shapes.LINE, { x: x1, y: y1, w: x2 - x1, h: y2 - y1,
    line: { color: TEAL2, width: 2, endArrowType: "triangle" } });

// frontend
box(M, 2.2, 2.58, 1.7, "React 19 + TypeScript", "Vite 7 · Tailwind 4\nRisk Orb · Clause Map\nAPI client w/ timeouts", TINT, TEXT, MUTED, null);
arrow(3.08, 3.05, 4.05, 3.05);
s.addText("HTTP /api", { x: 2.72, y: 3.32, w: 1.7, h: 0.3, fontSize: 12, fontFace: BODY, color: MUTED, align: "center", margin: 0 });
// backend core
box(4.05, 1.9, 2.75, 2.3, "FastAPI (uvicorn)", "10 routes · request IDs\nerror envelope\nupload validation\nlifespan + recovery", PRIMARY, "FFFFFF", "CFE6E1", null);
arrow(6.8, 3.05, 7.2, 3.05);
// services column
box(7.2, 1.62, 3.0, 0.9, "Document parser", "PyMuPDF · python-docx", "FFFFFF", TEXT, MUTED, "D8E6E2");
box(7.2, 2.72, 3.0, 0.9, "ML adapter → MiniLM QA", "lazy-loaded singleton", "FFFFFF", TEXT, MUTED, "D8E6E2");
box(7.2, 3.82, 3.0, 0.9, "Risk engine", "15 deterministic rules", "FFFFFF", TEXT, MUTED, "D8E6E2");
arrow(10.2, 4.27, 10.85, 4.27);
// model + db
box(10.85, 1.62, 1.98, 1.5, "Fine-tuned model", "ml/models/final\n33.4M params", INK2, IVORY, MUT_D, null);
box(10.85, 3.32, 1.98, 1.4, "SQLite", "SQLAlchemy 2.0\nstorage/contractiq.db", INK2, IVORY, MUT_D, null);

s.addText([
  { text: "Design choices  ", options: { bold: true, color: TEXT, fontSize: 14, breakLine: true } },
  { text: "Contract text is never logged; every failure maps to a typed error envelope; analysis state survives crashes; the ML layer sits behind a Protocol so models swap without touching the backend.", options: { color: MUTED, fontSize: 13 } },
], { x: M, y: 5.35, w: 10.6, h: 1.5, fontFace: BODY, paraSpaceAfter: 5, margin: 0 });
s.addText("All state changes flow left to right — the UI never writes to the database directly.",
  { x: M, y: 6.95, w: 10, h: 0.3, fontSize: 12, fontFace: BODY, color: MUTED, margin: 0 });

// ===========================================================================
// SLIDE: DATASET DEEP-DIVE (light)
s = p.addSlide();
s.background = { color: BG };
kicker(s, "MACHINE LEARNING \u00b7 DATA");
title(s, "CUAD v1 \u2014 trained on real commercial contracts");

const ds = [
  ["510", "contracts, 100+ pages average", "US commercial agreements across 27 industries"],
  ["41", "clause categories", "each with a curated legal question template"],
  ["20,910", "annotated QA pairs", "span-level annotations by contract lawyers"],
];
ds.forEach((d, i) => {
  const x = M + i * 4.19;
  card(s, x, 1.86, 3.95, 1.95, i === 2 ? TINT : "FFFFFF");
  s.addText(d[0], { x: x + 0.3, y: 2.0, w: 3.4, h: 0.85, fontSize: 46, fontFace: DISP, bold: true,
    color: PRIMARY, margin: 0 });
  s.addText(d[1], { x: x + 0.32, y: 2.85, w: 3.35, h: 0.35, fontSize: 13.5, fontFace: BODY,
    bold: true, color: TEXT, margin: 0 });
  s.addText(d[2], { x: x + 0.32, y: 3.2, w: 3.35, h: 0.5, fontSize: 12, fontFace: BODY,
    color: MUTED, margin: 0 });
});

s.addText("How each clause type becomes a question", { x: M, y: 4.1, w: 7, h: 0.35, fontSize: 13.5,
  fontFace: BODY, bold: true, color: TEXT, margin: 0 });
const qas = [
  ["\"Is there a non-compete restriction?\"", "extracts the restriction, or answers: no"],
  ["\"What is the Cap on Liability?\"", "extracts the exact cap wording from the text"],
  ["\"What is the Renewal Term?\"", "no clause present \u2192 confident no-answer"],
];
qas.forEach((q, i) => {
  const y = 4.55 + i * 0.72;
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: M, y, w: 4.55, h: 0.58, fill: { color: TINT },
    rectRadius: 0.06, line: { color: BG, width: 0 } });
  s.addText(q[0], { x: M + 0.2, y, w: 4.2, h: 0.58, fontSize: 12.5, fontFace: "Consolas",
    color: PRIMARY, valign: "middle", margin: 0 });
  s.addText(q[1], { x: 5.3, y, w: 4.4, h: 0.58, fontSize: 12.5, fontFace: BODY, color: MUTED,
    valign: "middle", margin: 0 });
});

card(s, 10.05, 4.1, 2.78, 2.62, INK2);
s.addText([
  { text: "SPLIT", options: { bold: true, fontSize: 12.5, color: TEAL2, charSpacing: 2, breakLine: true } },
  { text: "367", options: { bold: true, fontSize: 24, fontFace: DISP, color: IVORY, breakLine: true } },
  { text: "train contracts", options: { fontSize: 11, color: MUT_D, breakLine: true } },
  { text: "41", options: { bold: true, fontSize: 24, fontFace: DISP, color: IVORY, breakLine: true } },
  { text: "validation (thresholds)", options: { fontSize: 11, color: MUT_D, breakLine: true } },
  { text: "102", options: { bold: true, fontSize: 24, fontFace: DISP, color: "F5A08B", breakLine: true } },
  { text: "test \u2014 touched exactly once", options: { fontSize: 11, color: MUT_D } },
], { x: 10.3, y: 4.3, w: 2.3, h: 2.3, fontFace: BODY, paraSpaceAfter: 2, margin: 0 });
source(s, "Source: The Atticus Project, CUAD v1 (2021); project dataset integrity guarded by SHA-256 checksum");

// SLIDE: MODEL SELECTION (light)
s = p.addSlide();
s.background = { color: BG };
kicker(s, "MACHINE LEARNING \u00b7 MODEL CHOICE");
title(s, "Small enough for a laptop, smart enough for contracts");

s.addTable([
  [{ text: "Candidate", options: { bold: true, color: "FFFFFF", fill: { color: PRIMARY } } },
   { text: "Params", options: { bold: true, color: "FFFFFF", fill: { color: PRIMARY } } },
   { text: "CPU speed (win/s)", options: { bold: true, color: "FFFFFF", fill: { color: PRIMARY } } },
   { text: "Knows when a clause is absent", options: { bold: true, color: "FFFFFF", fill: { color: PRIMARY } } },
   { text: "Verdict", options: { bold: true, color: "FFFFFF", fill: { color: PRIMARY } } }],
  ["MiniLM (SQuAD 2.0)", "33.4M", "4.43", "Yes \u2014 trained on no-answer data",
   { text: "SELECTED", options: { bold: true, color: PRIMARY } }],
  ["DistilBERT (SQuAD 1.1)", "66M", "3.41", "No \u2014 always guesses an answer",
   { text: "Rejected", options: { color: MUTED } }],
  ["RoBERTa (SQuAD 2.0)", "125M", "~1.2", "Yes",
   { text: "Rejected: 3.7x compute", options: { color: MUTED } }],
], {
  x: M, y: 1.95, w: W - 2 * M, colW: [2.9, 1.3, 2.1, 3.3, 3.23],
  fontFace: BODY, fontSize: 12.5, color: TEXT, valign: "middle",
  border: { pt: 0.75, color: "DCE9E5" }, rowH: 0.52, margin: 0.07,
});

s.addText([
  { text: "Why it matters  ", options: { bold: true, fontSize: 13.5, color: TEXT, breakLine: false } },
  { text: "the whole model is ~127 MB on disk and runs on a plain laptop CPU \u2014 the privacy promise (\u201cnever leaves your machine\u201d) only holds if inference does not need a data-center GPU.", options: { fontSize: 12.5, color: MUTED } },
], { x: M, y: 4.85, w: 12.3, h: 0.8, fontFace: BODY, margin: 0 });

card(s, M, 5.75, 12.33, 0.95, TINT);
s.addText([
  { text: "Trade-off we accept  ", options: { bold: true, fontSize: 13, color: PRIMARY, breakLine: false } },
  { text: "MiniLM trades some accuracy for a 3\u20134x speed edge \u2014 retrieval and windowing win it back, and the same code serves a gaming laptop (seconds per contract) and an office laptop without one.", options: { fontSize: 12, color: TEXT } },
], { x: M + 0.3, y: 5.75, w: 11.7, h: 0.95, fontFace: BODY, valign: "middle", margin: 0 });
source(s, "Benchmark: project phase-3 model benchmark \u2014 batch inference on CPU, identical pre-processing");

// SLIDE 7 — ML PIPELINE (light)
// ===========================================================================
s = p.addSlide();
s.background = { color: BG };
kicker(s, "MACHINE LEARNING");
title(s, "Extractive QA, fine-tuned on legal contracts");

const mlL = [
  ["Task formulation", "Each clause type becomes a question (CUAD template) asked over the contract; the model returns the answer span — or 'no answer'."],
  ["Sliding windows", "512-token windows, stride 128, max answer 64 tokens — handles contracts far beyond the model's context."],
  ["Base model", "deepset/minilm-uncased-squad2 — 33.4M params, ~127 MB, no-answer aware; chosen over DistilBERT and RoBERTa on speed-per-accuracy."],
];
mlL.forEach((r, i) => {
  const y = 1.95 + i * 1.52;
  s.addText([
    { text: r[0], options: { bold: true, color: TEXT, fontSize: 15, breakLine: true } },
    { text: r[1], options: { color: MUTED, fontSize: 12.5 } },
  ], { x: M, y, w: 6.1, h: 1.42, fontFace: BODY, paraSpaceAfter: 5, margin: 0 });
  if (i < 2) s.addShape(p.shapes.LINE, { x: M, y: y + 1.36, w: 5.9, h: 0,
    line: { color: "DCE9E5", width: 0.75 } });
});

// right panel: fine-tuning facts + retrieval
card(s, 7.0, 1.95, 5.83, 2.5, TINT);
s.addText("FINE-TUNING RUN", { x: 7.3, y: 2.15, w: 3.5, h: 0.3, fontSize: 12,
  fontFace: BODY, bold: true, color: PRIMARY, charSpacing: 2, margin: 0 });
const ft = [["20,420", "train windows"], ["1 epoch", "batch 16 · lr 3e-5"], ["838 s", "on an RTX 2050 GPU"]];
ft.forEach((f, i) => {
  const x = 7.3 + i * 1.88;
  s.addText(f[0], { x, y: 2.55, w: 1.8, h: 0.55, fontSize: 26, fontFace: DISP, bold: true,
    color: PRIMARY, margin: 0 });
  s.addText(f[1], { x, y: 3.12, w: 1.75, h: 0.62, fontSize: 11.5, fontFace: BODY,
    color: MUTED, margin: 0 });
});
s.addText("1 epoch at batch 16, lr 3e-5, fp16, 1:3 positives-to-negatives — thresholds frozen on the 41-contract dev split before a single test run.",
  { x: 7.3, y: 3.78, w: 5.25, h: 0.6, fontSize: 12, fontFace: BODY, color: TEXT, margin: 0 });

card(s, 7.0, 4.68, 5.83, 1.95, "FFFFFF");
s.addText("RETRIEVAL — GOLD-ANSWER RECALL @ K=15", { x: 7.3, y: 4.86, w: 5.3, h: 0.3,
  fontSize: 12, fontFace: BODY, bold: true, color: PRIMARY, charSpacing: 1.5, margin: 0 });
const ret = [["79.4%", "question only"], ["91.4%", "+ TF-IDF keywords"], ["95.2%", "+ title boost"]];
ret.forEach((r, i) => {
  const x = 7.3 + i * 1.88;
  s.addText(r[0], { x, y: 5.24, w: 1.8, h: 0.62, fontSize: 30, fontFace: DISP, bold: true,
    color: i === 2 ? CORAL : TEXT, margin: 0 });
  s.addText(r[1], { x: x + 0.02, y: 5.9, w: 1.75, h: 0.35, fontSize: 11.5, fontFace: BODY,
    color: MUTED, margin: 0 });
  if (i < 2) s.addText("→", { x: x + 1.42, y: 5.3, w: 0.4, h: 0.5, fontSize: 18,
    fontFace: BODY, color: TEAL2, margin: 0 });
});
source(s, "Sources: phase3_retrieval_recall.md · phase3_training.md (project reports)");

// ===========================================================================
// SLIDE: FROM DOCUMENT TO EVIDENCE (light, flow diagram)
s = p.addSlide();
s.background = { color: BG };
kicker(s, "MACHINE LEARNING \u00b7 EXTRACTION FLOW");
title(s, "From a 78,000-token contract to exact evidence");

const flowSteps = [
  ["Contract", "up to 78.6k tokens,\nfar beyond the model"],
  ["Blocks", "1,200 chars,\n200-char overlap"],
  ["TF-IDF ranking", "keywords + title boost\ntop-15 blocks"],
  ["Windows", "512 tokens, stride 128,\nmax answer 64"],
  ["MiniLM QA", "best span per clause\nor no-answer"],
  ["Evidence", "exact character\noffsets \u2192 UI highlight"],
];
flowSteps.forEach((f, i) => {
  const x = M + i * 2.115;
  card(s, x, 2.05, 1.92, 1.95, i === 2 ? PRIMARY : "FFFFFF");
  const dark = i === 2;
  s.addText(f[0], { x: x + 0.16, y: 2.22, w: 1.62, h: 0.62, fontSize: 14, fontFace: BODY, bold: true,
    color: dark ? "FFFFFF" : TEXT, margin: 0 });
  s.addText(f[1], { x: x + 0.16, y: 2.86, w: 1.62, h: 1.0, fontSize: 10.5, fontFace: BODY,
    color: dark ? "CFE6E1" : MUTED, margin: 0 });
  if (i < 5) s.addText("\u2192", { x: x + 1.86, y: 2.75, w: 0.32, h: 0.5, fontSize: 16,
    fontFace: BODY, color: TEAL2, align: "center", margin: 0 });
});

s.addText([
  { text: "Why retrieval first?  ", options: { bold: true, fontSize: 13.5, color: TEXT, breakLine: false } },
  { text: "running every window of a long contract on CPU would dominate the ~80 s budget; ranking first cuts the work \u2014 and measured gold-answer recall at K=15 reaches 95.2%.", options: { fontSize: 12.5, color: MUTED } },
], { x: M, y: 4.35, w: 12.3, h: 0.75, fontFace: BODY, margin: 0 });

const flowNotes = [
  ["95.2%", "of gold answers survive into the search window (was 79.4% with questions alone)"],
  ["11 / 15", "clauses use retrieval; 4 high-value clause types scan the full document instead"],
  ["0", "offset mismatches in 129 evidence checks \u2014 spans decode back to exact character positions"],
];
flowNotes.forEach((n, i) => {
  const x = M + i * 4.19;
  s.addText(n[0], { x, y: 5.25, w: 3.9, h: 0.7, fontSize: 30, fontFace: DISP, bold: true,
    color: i === 2 ? CORAL : PRIMARY, margin: 0 });
  s.addText(n[1], { x: x + 0.02, y: 5.95, w: 3.8, h: 0.75, fontSize: 11.5, fontFace: BODY,
    color: MUTED, margin: 0 });
});
source(s, "Sources: phase3_retrieval_recall.md \u00b7 phase8 evidence-offset verification");

// SLIDE 8 — EVALUATION (light, chart)
// ===========================================================================
s = p.addSlide();
s.background = { color: BG };
kicker(s, "RESULTS");
title(s, "Measured honestly on the official CUAD test set");

s.addText("Clause-level F1 — best and worst of 15 (102-contract test set, run once)",
  { x: M, y: 1.8, w: 7.2, h: 0.35, fontSize: 13.5, fontFace: BODY, bold: true, color: TEXT, margin: 0 });
s.addChart(p.charts.BAR, [{
  name: "F1 %",
  labels: ["Parties", "License grant", "Agreement date", "Governing law", "Document name"],
  values: [13.7, 56.1, 77.9, 84.5, 89.0],
}], {
  x: M, y: 2.2, w: 7.2, h: 4.3, barDir: "bar",
  varyColors: true,
  chartColors: [CORAL, TEAL3, TEAL2, TEAL2, PRIMARY],
  chartArea: { fill: { color: "FFFFFF" } },
  catAxisLabelColor: TEXT, catAxisLabelFontSize: 12, catAxisLabelFontFace: BODY,
  valAxisLabelColor: MUTED, valAxisLabelFontSize: 11, valAxisLabelFontFace: BODY,
  valAxisMaxVal: 100, valAxisMinVal: 0,
  valGridLine: { color: "E4EEEB", size: 0.5 }, catGridLine: { style: "none" },
  showValue: true, dataLabelPosition: "outEnd", dataLabelColor: TEXT,
  dataLabelFontSize: 12, dataLabelFontFace: BODY, dataLabelFormatCode: "0.0",
  showLegend: false, showTitle: false,
});

const evalStats = [
  ["60.8%", "exact match (EM), overall"],
  ["66.2%", "token F1, overall"],
  ["74.4%", "no-answer accuracy — knows when a clause is absent"],
];
evalStats.forEach((st, i) => {
  const y = 2.2 + i * 1.28;
  s.addText(st[0], { x: 8.15, y, w: 2.15, h: 0.75, fontSize: 40, fontFace: DISP, bold: true,
    color: i === 0 ? PRIMARY : TEXT, margin: 0 });
  s.addText(st[1], { x: 10.3, y: y + 0.1, w: 2.6, h: 0.9, fontSize: 12.5, fontFace: BODY,
    color: MUTED, margin: 0 });
});
s.addText("Parties is the known weak spot: the answer spans many entities — flagged, not hidden.",
  { x: 8.15, y: 6.15, w: 4.7, h: 0.7, fontSize: 12, fontFace: BODY, italic: true, color: TEXT, margin: 0 });
source(s, "Source: phase3_test_evaluation.md — official CUAD test split, frozen thresholds, single run");

// ===========================================================================
// SLIDE 9 — RISK ENGINE (light)
// ===========================================================================
s = p.addSlide();
s.background = { color: BG };
kicker(s, "RISK METHODOLOGY");
title(s, "A risk score you can audit line by line");

const bands = [
  ["0–30", "LOW", TEAL2], ["31–60", "MEDIUM", AMBER], ["61–100", "HIGH", CORAL],
];
bands.forEach((b, i) => {
  const x = M + i * 4.19;
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 1.9, w: 3.95, h: 1.15, fill: { color: b[2] },
    rectRadius: 0.07, line: { color: BG, width: 0 } });
  s.addText([
    { text: b[1] + "   ", options: { bold: true, fontSize: 21, color: "FFFFFF", breakLine: false } },
    { text: b[0], options: { fontSize: 15, color: "F4EFE7" } },
  ], { x: x + 0.3, y: 1.9, w: 3.4, h: 1.15, fontFace: BODY, valign: "middle", margin: 0 });
});

s.addText("Example rules (weight · severity)", { x: M, y: 3.4, w: 6, h: 0.35, fontSize: 13.5,
  fontFace: BODY, bold: true, color: TEXT, margin: 0 });
const rules = [
  ["NON_COMPETE_PRESENT", "+18", "HIGH", CORAL],
  ["EXCLUSIVITY_PRESENT", "+15", "HIGH", CORAL],
  ["CAP_ON_LIABILITY_ABSENT", "+12", "MEDIUM", AMBER],
  ["AUTO_RENEWAL_LANGUAGE  (regex)", "+10", "MEDIUM", AMBER],
  ["TERMINATION_CONVENIENCE_ABSENT", "+10", "MEDIUM", AMBER],
  ["AUDIT_RIGHTS_PRESENT", "+4", "LOW", TEAL2],
];
rules.forEach((r, i) => {
  const y = 3.85 + i * 0.47;
  s.addText(r[0], { x: M + 0.05, y, w: 4.7, h: 0.4, fontSize: 12.5, fontFace: "Consolas",
    color: TEXT, margin: 0 });
  s.addText(r[1], { x: 5.3, y, w: 0.7, h: 0.4, fontSize: 13, fontFace: BODY, bold: true,
    color: r[3], align: "right", margin: 0 });
  s.addText(r[2], { x: 6.15, y, w: 1.0, h: 0.4, fontSize: 11, fontFace: BODY, color: MUTED, margin: 0 });
});

card(s, 7.85, 3.4, 4.98, 3.3, TINT);
s.addText([
  { text: "Separation of concerns", options: { bold: true, fontSize: 15, color: PRIMARY, breakLine: true } },
  { text: "The ML model never assigns risk. It extracts facts; rules score them.", options: { fontSize: 12.5, color: TEXT, breakLine: true } },
], { x: 8.13, y: 3.62, w: 4.45, h: 1.1, fontFace: BODY, paraSpaceAfter: 4, margin: 0 });
s.addText([
  { text: "Confidence gate", options: { bold: true, fontSize: 15, color: PRIMARY, breakLine: true } },
  { text: "Rules fire only at extraction confidence ≥ 0.5 — below that the finding is marked uncertain and excluded from the score.", options: { fontSize: 12.5, color: TEXT, breakLine: true } },
], { x: 8.13, y: 4.82, w: 4.45, h: 1.35, fontFace: BODY, paraSpaceAfter: 4, margin: 0 });
source(s, "Weights and bands are data, not code — configurable in ml/configs/clauses.json");

// ===========================================================================
// SLIDE 10 — UI SHOWCASE: DASHBOARD (dark, full-bleed)
// ===========================================================================
s = p.addSlide();
s.background = { color: INK };
s.addImage({ path: path.join(A, "ui_overview.png"), x: 0, y: 0, w: W, h: H });
s.addShape(p.shapes.RECTANGLE, { x: 0, y: 6.72, w: W, h: H - 6.72,
  fill: { color: "0A1416" }, line: { color: "0A1416", width: 0 } });
s.addText([
  { text: "Overview dashboard  ", options: { bold: true, color: IVORY, breakLine: false } },
  { text: "— portfolio stats, risk constellation, recent activity, live engine status", options: { color: MUT_D } },
], { x: M, y: 6.72, w: W - 2 * M, h: H - 6.72, fontSize: 13, fontFace: BODY, valign: "middle", margin: 0 });

// ===========================================================================
// SLIDE: REQUEST LIFECYCLE (light)
s = p.addSlide();
s.background = { color: BG };
kicker(s, "ENGINEERING \u00b7 LIFECYCLE");
title(s, "Every request is a small, safe state machine");

const life = [
  ["Upload", "validate (type, 20 MB cap) \u2192 store as UUID \u2192 parse to text \u2192 SHA-256 duplicate check \u2192 status READY"],
  ["Analyze", "ANALYZING \u2192 lazy-load model \u2192 extract 15 clauses with offsets \u2192 run 15 risk rules \u2192 write atomically \u2192 COMPLETED"],
  ["Fail safely", "corrupt / encrypted / scanned files and CUDA out-of-memory all become typed FAILED analyses \u2014 never a crashed server"],
  ["Recover", "on startup, contracts stuck in ANALYZING from a crash are moved to a safe state automatically"],
];
life.forEach((l, i) => {
  const y = 1.95 + i * 1.02;
  s.addShape(p.shapes.OVAL, { x: M + 0.02, y: y + 0.04, w: 0.34, h: 0.34,
    fill: { color: i === 2 ? CORAL : PRIMARY }, line: { color: BG, width: 0 } });
  s.addText(String(i + 1), { x: M + 0.02, y: y + 0.04, w: 0.34, h: 0.34, fontSize: 13, fontFace: BODY,
    bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  s.addText([
    { text: l[0], options: { bold: true, fontSize: 15, color: TEXT, breakLine: true } },
    { text: l[1], options: { fontSize: 12.5, color: MUTED } },
  ], { x: M + 0.55, y, w: 6.6, h: 0.98, fontFace: BODY, paraSpaceAfter: 3, margin: 0, valign: "top" });
});

card(s, 7.85, 1.95, 4.98, 2.35, INK2);
s.addText("EVERY ERROR IS TYPED \u2014 NEVER A RAW TRACEBACK", { x: 8.13, y: 2.15, w: 4.5, h: 0.3,
  fontSize: 11.5, fontFace: BODY, bold: true, color: TEAL2, charSpacing: 1.5, margin: 0 });
s.addText([
  { text: '{ "error": "OCR_REQUIRED",', options: { color: IVORY, breakLine: true } },
  { text: '  "message": "The PDF has no text layer...",', options: { color: IVORY, breakLine: true } },
  { text: '  "request_id": "dbb1496526d944b5" }', options: { color: IVORY } },
], { x: 8.13, y: 2.55, w: 4.5, h: 1.1, fontSize: 12, fontFace: "Consolas", margin: 0 });
s.addText("the same request_id appears in the X-Request-ID header and in logs",
  { x: 8.13, y: 3.7, w: 4.5, h: 0.5, fontSize: 11.5, fontFace: BODY, color: MUT_D, margin: 0 });

card(s, 7.85, 4.55, 4.98, 1.95, TINT);
s.addText([
  { text: "Idempotent by design", options: { bold: true, fontSize: 14.5, color: PRIMARY, breakLine: true } },
  { text: "Re-analyzing a contract replaces the previous result atomically \u2014 double-clicking Analyze can never corrupt data, and a 409 guards concurrent runs.", options: { fontSize: 12, color: TEXT } },
], { x: 8.13, y: 4.78, w: 4.45, h: 1.6, fontFace: BODY, paraSpaceAfter: 4, margin: 0 });

// SLIDE 11 — BACKEND & DATA (light)
// ===========================================================================
s = p.addSlide();
s.background = { color: BG };
kicker(s, "ENGINEERING");
title(s, "A small, strict API over four tables");

const apiRows = [
  [{ text: "Endpoint", options: { bold: true, color: "FFFFFF", fill: { color: PRIMARY } } },
   { text: "Purpose", options: { bold: true, color: "FFFFFF", fill: { color: PRIMARY } } }],
  ["POST /api/contracts/upload", "validate → parse → store (201)"],
  ["POST /api/contracts/{id}/analyze", "run extraction + risk (idempotent)"],
  ["GET /api/contracts/{id}/analysis", "full analysis: clauses, evidence, findings"],
  ["GET /api/contracts/{id}/text", "raw text for evidence highlighting"],
  ["GET /api/contracts", "search · filter · sort · paginate"],
  ["GET /api/stats · /api/health", "dashboard stats · engine + model status"],
];
s.addTable(apiRows, {
  x: M, y: 1.95, w: 6.6, colW: [3.3, 3.3],
  fontFace: BODY, fontSize: 11.5, color: TEXT, valign: "middle",
  border: { pt: 0.75, color: "DCE9E5" }, rowH: 0.42, margin: 0.06,
});

const tables = [
  ["contracts", "file info · status · text hash · raw text"],
  ["analyses", "risk score · model state · timings"],
  ["clause_results", "found · span offsets · confidence"],
  ["risk_findings", "rule · severity · weight · evidence"],
];
tables.forEach((t, i) => {
  const y = 1.95 + i * 0.78;
  card(s, 7.5, y, 5.33, 0.66, i % 2 ? "FFFFFF" : TINT);
  s.addText(t[0], { x: 7.78, y: y + 0.06, w: 2.1, h: 0.28, fontSize: 13, fontFace: "Consolas",
    bold: true, color: PRIMARY, margin: 0 });
  s.addText(t[1], { x: 7.78, y: y + 0.34, w: 4.8, h: 0.28, fontSize: 11.5, fontFace: BODY,
    color: MUTED, margin: 0 });
});

// state machine strip
s.addText("CONTRACT STATE MACHINE", { x: M, y: 5.6, w: 5, h: 0.3, fontSize: 12, fontFace: BODY,
  bold: true, color: PRIMARY, charSpacing: 2, margin: 0 });
const states = ["UPLOADED", "READY", "ANALYZING", "COMPLETED", "FAILED"];
states.forEach((st, i) => {
  const x = M + i * 1.55;
  const bad = st === "FAILED";
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 6.0, w: 1.35, h: 0.5,
    fill: { color: bad ? "FBEDE7" : TINT }, rectRadius: 0.08, line: { color: BG, width: 0 } });
  s.addText(st, { x, y: 6.0, w: 1.35, h: 0.5, fontSize: 10.5, fontFace: "Consolas", bold: true,
    color: bad ? CORAL : PRIMARY, align: "center", valign: "middle", margin: 0 });
  if (i < 4) s.addText("→", { x: x + 1.3, y: 6.05, w: 0.3, h: 0.4, fontSize: 14, fontFace: BODY,
    color: TEAL2, align: "center", margin: 0 });
});
s.addText("Stale ANALYZING rows are recovered to a safe state on restart.",
  { x: 8.3, y: 6.08, w: 4.5, h: 0.4, fontSize: 12, fontFace: BODY, color: MUTED, margin: 0 });

// ===========================================================================
// SLIDE: SECURITY & PRIVACY (light)
s = p.addSlide();
s.background = { color: BG };
kicker(s, "ENGINEERING \u00b7 SECURITY");
title(s, "Designed so the contract never leaves the machine");

const sec = [
  ["Uploads are untrusted input", "type + 20 MB size checks; corrupt, encrypted and scanned files rejected with typed errors \u2014 content is never executed"],
  ["Path safety by construction", "user filenames are never used as paths; uploads stored under UUID names; traversal like ../../x is neutralized before anything touches disk"],
  ["Log privacy", "contract text is never written to logs \u2014 events carry IDs, codes and timings only; verified in the release secret-scan"],
  ["Raw text is a switch", "STORE_RAW_TEXT=true (needed for evidence highlighting) can be turned off to keep only metadata; temp files cleaned on a 24-hour policy"],
  ["LAN mode is opt-in", "production default binds localhost; the LAN launcher exposes the app without auth \u2014 documented, trusted-networks-only"],
];
sec.forEach((sc, i) => {
  const y = 1.95 + i * 0.94;
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: M, y: y + 0.05, w: 0.28, h: 0.28,
    fill: { color: i === 4 ? CORAL : PRIMARY }, rectRadius: 0.05, line: { color: BG, width: 0 } });
  s.addText([
    { text: sc[0], options: { bold: true, fontSize: 14.5, color: TEXT, breakLine: true } },
    { text: sc[1], options: { fontSize: 12, color: MUTED } },
  ], { x: M + 0.46, y, w: 11.9, h: 0.9, fontFace: BODY, paraSpaceAfter: 3, margin: 0, valign: "top" });
});
source(s, "Full review: docs/SECURITY.md \u00b7 phase 8 secret-scan and evidence checks passed");

// SLIDE 12 — QUALITY & PERFORMANCE (light)
// ===========================================================================
s = p.addSlide();
s.background = { color: BG };
kicker(s, "QUALITY");
title(s, "Verified end to end, not just unit-tested");

const q = [
  ["199", "tests passing", "186 pytest + 13 vitest", PRIMARY],
  ["0", "evidence mismatches", "across 129 checks, browser + DB", CORAL],
  ["11.9×", "GPU speed-up", "52.8 vs 4.43 windows/s — RTX 2050", PRIMARY],
  ["135 kB", "frontend bundle", "gzipped production build", PRIMARY],
];
q.forEach((st, i) => {
  const x = M + i * 3.22;
  s.addText(st[0], { x, y: 1.9, w: 3.0, h: 0.95, fontSize: 54, fontFace: DISP, bold: true,
    color: st[3], margin: 0 });
  s.addText(st[1], { x: x + 0.02, y: 2.85, w: 2.9, h: 0.35, fontSize: 14, fontFace: BODY,
    bold: true, color: TEXT, margin: 0 });
  s.addText(st[2], { x: x + 0.02, y: 3.2, w: 2.9, h: 0.6, fontSize: 12, fontFace: BODY,
    color: MUTED, margin: 0 });
});

s.addShape(p.shapes.LINE, { x: M, y: 4.05, w: W - 2 * M, h: 0, line: { color: "DCE9E5", width: 0.75 } });

const hard = [
  ["Full E2E with the real model", "22-step browser run: upload → analyze → verify; 0 page errors, clean console."],
  ["Security reviewed", "traversal-safe filenames, type/size validation, uploads never executed, no secrets, contract text never logged."],
  ["Failure modes designed", "corrupt / encrypted / scanned files rejected with typed errors; CUDA OOM contained; stale analyses recovered."],
  ["Portable by construction", "runs from any folder (spaces included); 150-file scan: no hardcoded paths."],
];
hard.forEach((hh, i) => {
  const x = M + (i % 2) * 6.42, y = 4.35 + Math.floor(i / 2) * 1.32;
  s.addShape(p.shapes.OVAL, { x, y: y + 0.13, w: 0.14, h: 0.14, fill: { color: PRIMARY },
    line: { color: BG, width: 0 } });
  s.addText([
    { text: hh[0], options: { bold: true, fontSize: 14.5, color: TEXT, breakLine: true } },
    { text: hh[1], options: { fontSize: 12, color: MUTED } },
  ], { x: x + 0.32, y, w: 5.9, h: 1.25, fontFace: BODY, paraSpaceAfter: 3, margin: 0, valign: "top" });
});
source(s, "Sources: phase8_final_qa.md · phase3_gpu_benchmark.md (project reports)");

// ===========================================================================
// SLIDE: LIVE DEMO GUIDE (light)
s = p.addSlide();
s.background = { color: BG };
kicker(s, "LIVE DEMO");
title(s, "Real files, real analysis \u2014 not slides");

const demoSteps = [
  ["01_saas_subscription", "LOW", TEAL2,
   "friendly terms \u2014 the orb stays small; cap on liability and insurance are found, almost nothing fires"],
  ["05_consulting_services", "MEDIUM", AMBER,
   "auto-renewal is flagged (+10) and the soft non-compete shows how wording rules work"],
  ["09_franchise_agreement", "HIGH", CORAL,
   "non-compete, exclusivity, auto-renewal, no convenience exit \u2014 the orb climbs as rules stack"],
];
demoSteps.forEach((d, i) => {
  const x = M + i * 4.19;
  card(s, x, 1.95, 3.95, 2.9, "FFFFFF");
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: x + 0.26, y: 2.18, w: 1.15, h: 0.42,
    fill: { color: d[2] }, rectRadius: 0.2, line: { color: BG, width: 0 } });
  s.addText(d[1], { x: x + 0.26, y: 2.18, w: 1.15, h: 0.42, fontSize: 13, fontFace: BODY, bold: true,
    color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  s.addText(d[0], { x: x + 0.26, y: 2.75, w: 3.45, h: 0.65, fontSize: 14, fontFace: "Consolas",
    bold: true, color: TEXT, margin: 0 });
  s.addText(d[3], { x: x + 0.26, y: 3.42, w: 3.45, h: 1.3, fontSize: 11.5, fontFace: BODY,
    color: MUTED, margin: 0 });
});

s.addText([
  { text: "The demo folder ships with the project:  ", options: { bold: true, fontSize: 13, color: TEXT, breakLine: false } },
  { text: "demo_contracts/ \u2014 22 agreements across SaaS, leases, franchises, joint ventures, GDPR DPAs and more, in LOW / MEDIUM / HIGH flavors, with PDF samples for the PDF pipeline. Nothing is uploaded until you drag it in.", options: { fontSize: 12.5, color: MUTED } },
], { x: M, y: 5.25, w: 12.3, h: 0.85, fontFace: BODY, margin: 0 });

s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: M, y: 6.2, w: W - 2 * M, h: 0.72,
  fill: { color: TINT }, rectRadius: 0.07, line: { color: BG, width: 0 } });
s.addText("Every number you will see is computed live on this laptop \u2014 the model, the rules and the data all stay on this machine.",
  { x: M + 0.3, y: 6.2, w: 12, h: 0.72, fontSize: 13, fontFace: BODY, italic: true, color: PRIMARY,
    valign: "middle", margin: 0 });

// SLIDE 13 — LIMITATIONS & ROADMAP (light)
// ===========================================================================
s = p.addSlide();
s.background = { color: BG };
kicker(s, "HONEST ASSESSMENT");
title(s, "What it can't do yet — and what comes next");

s.addText("CURRENT LIMITATIONS", { x: M, y: 1.9, w: 5.5, h: 0.32, fontSize: 12.5, fontFace: BODY,
  bold: true, color: MUTED, charSpacing: 2, margin: 0 });
const lims = [
  "Single-user, local only — no authentication",
  "Synchronous analysis — the UI waits (no queue)",
  "Risk rules are heuristics, not learned from outcomes",
  "Scanned PDFs need OCR — not implemented",
  "Parties extraction is weak on multi-entity spans",
];
lims.forEach((l, i) => {
  const y = 2.35 + i * 0.72;
  s.addShape(p.shapes.OVAL, { x: M + 0.05, y: y + 0.13, w: 0.13, h: 0.13,
    fill: { color: CORAL }, line: { color: BG, width: 0 } });
  s.addText(l, { x: M + 0.38, y, w: 5.4, h: 0.65, fontSize: 13.5, fontFace: BODY,
    color: TEXT, margin: 0 });
});

s.addText("NEXT STEPS", { x: 6.9, y: 1.9, w: 5.5, h: 0.32, fontSize: 12.5, fontFace: BODY,
  bold: true, color: MUTED, charSpacing: 2, margin: 0 });
const nexts = [
  "Async job queue with live progress streaming",
  "OCR pipeline for scanned contracts (Tesseract)",
  "Learned risk model on top of extracted clauses",
  "Enable more of the 41 CUAD clause types (flag-flip)",
  "Auth + multi-user mode for small teams",
];
nexts.forEach((l, i) => {
  const y = 2.35 + i * 0.72;
  s.addShape(p.shapes.OVAL, { x: 6.95, y: y + 0.13, w: 0.13, h: 0.13,
    fill: { color: PRIMARY }, line: { color: BG, width: 0 } });
  s.addText(l, { x: 7.28, y, w: 5.4, h: 0.65, fontSize: 13.5, fontFace: BODY,
    color: TEXT, margin: 0 });
});

s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: M, y: 6.15, w: W - 2 * M, h: 0.75,
  fill: { color: TINT }, rectRadius: 0.07, line: { color: BG, width: 0 } });
s.addText("Every limitation above is documented in the project reports — the system never hides uncertainty.",
  { x: M + 0.3, y: 6.15, w: 12, h: 0.75, fontSize: 13.5, fontFace: BODY, italic: true,
    color: PRIMARY, valign: "middle", margin: 0 });

// ===========================================================================
// SLIDE 14 — CLOSING (dark)
// ===========================================================================
s = p.addSlide();
s.background = { color: INK };
s.addText("THANK YOU", { x: M, y: 1.7, w: 6, h: 0.36, fontSize: 13, fontFace: BODY, bold: true,
  color: TEAL2, charSpacing: 4, margin: 0 });
s.addText("Every finding traceable\nto its source text.", { x: M, y: 2.15, w: 9.5, h: 1.9,
  fontSize: 44, fontFace: DISP, bold: true, color: IVORY, margin: 0 });

const closing = [["95.2%", "retrieval recall"], ["66.2%", "test F1"], ["15", "clause types"],
  ["199", "tests passing"], ["100%", "local & private"]];
closing.forEach((c, i) => {
  const x = M + i * 2.56;
  s.addText(c[0], { x, y: 4.55, w: 2.3, h: 0.7, fontSize: 34, fontFace: DISP, bold: true,
    color: i === 0 ? CORAL : TINT, margin: 0 });
  s.addText(c[1], { x: x + 0.02, y: 5.28, w: 2.2, h: 0.35, fontSize: 12.5, fontFace: BODY,
    color: MUT_D, margin: 0 });
});
s.addText("ContractIQ — AI-assisted analysis. Results should be reviewed by a qualified professional. Not legal advice.",
  { x: M, y: 6.55, w: 11, h: 0.35, fontSize: 12, fontFace: BODY, italic: true, color: MUT_D, margin: 0 });
s.addText("Questions welcome.", { x: M, y: 6.95, w: 6, h: 0.35, fontSize: 14, fontFace: BODY,
  bold: true, color: "CDE3DE", margin: 0 });

// ---------- write ----------
p.writeFile({ fileName: "D:/ContractIQ/reports/deck_assets/ContractIQ_Presentation.pptx" })
  .then(() => console.log("PPTX written"));
