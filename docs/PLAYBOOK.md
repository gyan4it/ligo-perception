# Playbook — how a non-vision reasoner must use the evidence

This is the operating manual for the **L3 reasoner** (the AI agent). Paste or
summarise these rules into your agent's instructions when it drives the
system. They were written from bugs and judgement errors that actually
happened while the system was built — not from theory.

## 0. The contract

```text
You receive structured evidence about a rendered artifact.
You do not see the artifact. You never have.
Therefore:

  1. Every visual claim you make must trace to an evidence field.
  2. If the evidence does not cover a question, you do not answer it —
     you extend the sensor (§5) or escalate (§6).
  3. "Clean" means "these specific probes found nothing", never
     "the artifact is good".
  4. A `VISION-UNAVAILABLE` or `NOT_VERIFIABLE` status means the sensor
     cannot answer — it is not a "clean" result.
```

## 1. The loop (measure → hypothesise → fix → re-measure)

```text
run probes → read findings → for each finding:
   DETECTED (in evidence)  →  form cause hypothesis (DERIVED)
       →  edit the SOURCE file (html/css/svg/md), never the output
       →  re-run the SAME probe on the SAME target
       →  finding gone? yes: continue; no: new hypothesis
    after fixes: re-run EVERYTHING (shared CSS has side effects)
```

- **One artefact under test at a time**, targets chosen by what changed
  (question-guided scope) — a full sweep only before a release gate.
- Fixes are **proven, not asserted**: a fix exists when the re-measurement
  says so. INTERPRETED claims ("this should look right now") may not be
  reported as done (see EVIDENCE-SCHEMA §tiers).

## 2. Evidence-reading rules

| Rule | Why |
|---|---|
| Read `rect` numbers before believing `det` prose | the sentence is a summary; the numbers are the fact |
| `conf >= 0.90` -> act; `0.70–0.89` -> confirm first; `< 0.70` -> corroboration only | bands from the bridge spec §19 |
| An `E0x` finding means the **sensor** failed, not the page | triage it as infrastructure |
| `issues: []` is scoped clean — name the scope in your report | honesty (bridge spec §44) |
| Pair findings (`a`/`b`) before fixing — the *pair* is the fact | fixing one box can move the other |
| A margin `NOT_VERIFIABLE` means CSSOM could not read `@page` — treat as gap, not pass | honesty |

## 3. Sensor trust rules

1. **Never trust a green you cannot seed.** Before relying on a probe, the seeded fixture must raise its codes and the clean fixture must raise none: `python tests/test_selfcheck.py` (L4 gate).
2. **The call contract is load-bearing.** Probes go through `run_probe()` which wraps `(src)(opts)`. Raw `evaluate("() => {...}")` returns a function and *looks* like success. (Founding bug: a whole audit printed "all OK" because nothing was ever called.)
3. **Measure in screen space.** `getBoundingClientRect()` includes every transform; `getBBox()` ignores the element's own transform. Conflict rule: rect beats bbox (FLOWCHARTS §4).
4. **Selectors resolve by priority, not document order** — a combined selector list lets `<body>` win over `[data-probe-root]`. (Real bug, caught by the self-test.)
5. **One rect vocabulary.** If `R()` returns `w`/`h`, never read `width`/`height` — silent `NaN` kills conditions. (Real bug: the `ASPECT` check could never fire.)
6. **Profile-aware margins.** `--margin-cm 1.15` is a CLI override only; expected margins must come from the active project profile (`--profile profiles/B01.json`). B01 values must not leak into other projects.

## 4. Evidence → fix: worked examples (founding case study)

**Example 1 — poster overflow (geometry).**
Evidence: `{t:OVERFLOW, det:"content clipped: scrollH=3106 > clientH=2646", conf:.95}`.
Derivation: two figure blocks stacked `span-2` (full column) cost ≈ 2×460 px; sheet has 460 px spare horizontally, not vertically.
Fix: figures side-by-side in the grid. Re-run: `issues: []` **and** print check still 1 page. Both measurements are the proof.

**Example 2 — style drift (rule).**
Evidence from the style audit: `off-palette: #014F7E`.
Derivation: `#014F7E` ≈ the palette's sky hue but not a token.
Fix: replace with `#0277BD` in source *and* rebuild (source-of-truth rule).
Re-run: colour set ⊆ allowlist.

**Example 3 — print spills a blank second page.**
Evidence: `printToPDF` → MediaBox correct (1559×1984 pt) but **2 pages**.
Measurement (print emulation): `sheetTop = 24 px` — a parent `main` padding the screen style never cleared. Fix: zero `main` margin/padding inside `@media print`. Re-run: 1 page, exact size. Note the loop used *two* sensors: page-box metrics located the frame, DOM metrics located the cause.

**Example 4 — a check that could not decide.**
Evidence: axe `color-contrast` on links over `#F4F7F4`, ratio ≈ 4.44 (needs 4.5). Derivation: `#0277BD` was tuned for white backgrounds. Fix: darker link token for tinted backgrounds (`#01579B`, 6.9:1). Re-run axe: 0. L2 rule now exists → future drift is codified.

**Example 5 — bitmap pixel analysis.**
Evidence: pixel metrics `luminance=0.4335`, `contrast.michelson=0.4007`, `sharpness.laplacian_variance=0.0603`.
Derivation: low contrast → low accessibility for small text; low sharpness → image may be soft or downscaled too far.
Fix: increase contrast ratio or replace with higher-resolution source. Re-run pixel_check: confirm contrast ≥ target, sharpness ≥ threshold.

**Example 6 — margin verification via CSSOM.**
Evidence: margin evidence `status=PASS`, `observed_values={...all 11.5mm...}`, `verification_method=cssom`.
Derivation: declared `@page { margin: 1.15cm }` matches B01 profile expectation within 0.5mm tolerance.
Fix: none — margin verified. If `NOT_VERIFIABLE`, report gap, do not mark as clean.

## 5. When evidence is insufficient: extend the sensor

```text
question the probes cannot answer      example
──────────────────────────────────────────────────────────────
"does the PDF keep headings off page   → printToPDF + MediaBox/page-count
 bottoms?"                             probe (became print_check.py)
"is keyboard focus visible?"          → Tab walk + :focus-visible (focus probe)
"is the colour off-brand?"            → source regex vs palette allowlist
"do rotated axis labels collide?"     → screen-space text rects (svg_probe)
"does it LOOK finished?"              → NOT a probe: human gate (§6)
"what are the pixel dimensions?"      → pixel_check.py dimensions metric
"does the image have text?"           → ocr_adapter.py OCR extraction
"is the @page margin 1.15cm?"         → layout_check.py --margin-check --profile profiles/B01.json
"does it look balanced?"              → NOT a probe: human gate (§6)
```

Rule: if you catch yourself reasoning from *vibes* about a measurable property, that is a missing probe — write it (copy an existing one, add a seeded fixture case, wire it into the self-test).

## 6. The gate — L1 / L2 / L3

| Level | Question | Authority | Example verdicts |
|---|---|---|---|
| **L1** measurable | is the geometry/mechanics right? | agent decides alone | overlap fixed, PDF is 1 page, links resolve |
| **L2** codified rules | within written limits? | agent decides; *the rule* is reviewable | AA contrast, palette, min 11 px type, label-in-name, margins match profile |
| **L3** judgement | does it look/feel right? | **human only** | "professional", hierarchy, balance, poster artistry |

Escalating too late is the dangerous error: **never self-certify L3.**
Package the gate for the human: screenshot (`runner.screenshot()`), print PDF (`runner.print_to_pdf()`), plus the L1/L2 green status. The human's verdict is data for the next session — log it (it becomes an L2 rule once it repeats: "Director disliked X twice" → codify X as a check).

When `VISION-UNAVAILABLE` is reported, the reasoner must state what the vision sensor could not decide — it is an explicit gap, not a pass.

## 7. Bitmap and pixel workflow

```text
1. bitmap_check.py image.png        → validate, metadata, decompress bomb guard
2. pixel_check.py image.png         → dimensions, palette, luminance, contrast,
                                        edges, sharpness, regions, alpha
3. ocr_adapter.py image.png         → text + bounding boxes + confidence
4. (optional) vision_adapter.py     → caption/VQA/detect if VLM configured
5. vir_builder.py                   → merge all evidence into VIR
6. apai_bitmap.py                   → rubric-based art/illustration assessment
```

OCR is **separate from semantic vision**: OCR extracts text; vision models interpret meaning. Never confuse the two. OCR text is `DETECTED`; vision output is `INTERPRETED`.

## 8. Project profiles

Profiles declare per-project expectations so B01 values do not leak into other projects:

```bash
python tools/layout_check.py page.html --profile profiles/B01.json --margin-check
python tools/apai_bitmap.py --vir out/vir.json --profile profiles/B01.json
```

A profile defines page size, margins, tolerance, checks, and rubric. Use `capability_detector.py --profile profiles/B01.json` to verify which capabilities are available before running checks.

## 9. Failure honesty

- Sensor down → report **gap + what was not checked**, not a bare green.
- Probe loop exhausted (N iterations) → stop and write a fix brief; churn without convergence means the hypothesis is wrong, not the evidence.
- Conflicting sources → keep both, mark `REQUIRES_VERIFICATION` (spec §37); never average, never silently choose.
- `VISION-UNAVAILABLE` → state what semantic vision could not decide.
- `NOT_VERIFIABLE` (CSSOM) → state that @page margins could not be read.

## 10. Report template

```text
CHECKED:  <targets> with <probes> (scope)
FOUND:    <n> findings → codes: … → all fixed, re-measured to 0
GAPS:     <what the probes cannot decide> → human gate / not checked
VISION:   <vision unavailable / available but unused / available and used>
EVIDENCE: out/<run>.json (attach path)
```
