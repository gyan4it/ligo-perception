# Evidence schema

The single data contract between **sensors** (L1) and the **reasoner** (L3).
Machine-readable copy: [evidence.schema.json](evidence.schema.json).

## Envelope

```json
{
  "schema_version": "1.0",
  "target": "web/posters/poster-2.html",
  "probe": "layout_probe.js",
  "browser": "HeadlessChrome/…",
  "ts": "2026-10-06T14:12:03Z",
  "root": {"x": 0, "y": 0, "w": 2079, "h": 2646},
  "context": {"nFigs": 3, "nImgs": 6},
  "issues": [ … ]
}
```

| field | required | meaning |
|---|---|---|
| `schema_version` | yes | contract version; reasoner must refuse unknown majors |
| `target` | yes | what was measured (path/URI) — provenance |
| `probe` | yes | which sensor produced the issues — provenance |
| `ts` | yes | ISO-8601 measurement time |
| `root` | no | the measurement frame (rect) findings are relative to |
| `context` | no | probe-specific counters (figs, imgs, texts, viewBox …) |
| `issues` | yes | array of findings; `[]` means **clean** |

## Issue (finding)

```json
{
  "t": "OVERFLOW",
  "det": "content clipped: scrollH=3106 > clientH=2646",
  "rect": {"x": 0, "y": 0, "w": 2079, "h": 2646},
  "conf": 0.95
}
```

| field | required | meaning |
|---|---|---|
| `t` | yes | violation **code** (registry below) |
| `det` | yes | one human sentence **with the numbers** — no adjectives, no guesses |
| `rect` / `box` | recommended | where: `{x,y,w,h}` in the root's screen space (`layout`) or svg space (`svg`) |
| `a`, `b` | for pairs | both rects when the finding is an intersection |
| `conf` | yes | 0–1 confidence band (below) |
| `src` | optional | provenance override (e.g. `{"engine":"axe-core"}`) |
| `evidence` | optional | nested evidence object (e.g. margin evidence with declared/observed values) |

**Forbidden in evidence:** recommendations, blame, aesthetics, causes.
Evidence states *what was measured*; the reasoner derives causes.

## Confidence bands (from VISION_BRIDGE_ARCHITECTURE §19)

| range | band | how the reasoner may use it |
|---|---|---|
| 0.90 – 1.00 | HIGH | act on it directly (fix) |
| 0.70 – 0.89 | MEDIUM | act with a quick confirmation |
| 0.50 – 0.69 | LOW | mention; corroborate before acting |
| 0.00 – 0.49 | UNCERTAIN | never a factual claim; investigate or drop |

Bands are **not** calibrated probabilities — they express how directly the
measurement implies the claim (e.g. `complete && naturalWidth===0` ⇒
`IMG-FAIL` at 0.98: nearly tautological).

## Violation code registry

### Geometry — `layout_probe.js` (Level 1, measurable)

| code | meaning | typical conf |
|---|---|---|
| `OVERFLOW` | content taller/wider than its root (clipped or pushed out) | 0.95 |
| `OVERLAP` | two boxes intersect by > 2 px in both axes | 0.95 |
| `OUT-OF-BOUNDS` | element escapes the root/frame | 0.95 |
| `IMG-FAIL` | `complete && naturalWidth === 0` — image never loaded | 0.98 |
| `ASPECT` | rendered aspect ratio differs from intrinsic by > 2 % | 0.90 |
| `E00` | probe itself failed (no root) | 1.00 |
| `LANDMARK-MISSING` | document has no `<main>` landmark | 0.90 |
| `MARGIN-VERIFICATION` | margin status from CSSOM `@page` inspection | 0.90 |

### SVG — `svg_probe.js` (Level 1–2)

| code | meaning | typical conf |
|---|---|---|
| `OUT-OF-CANVAS` | text/shape clipped by the SVG edge (screen space) | 0.95 |
| `TEXT-COLLIDE` | two text rects intersect > 2 px | 0.90 |
| `E01` | probe itself failed (no svg) | 1.00 |

### Bitmap — `bitmap_check.py` (Level 1.5)

| code | meaning | typical conf |
|---|---|---|
| `BITMAP-NOT-FOUND` | image file missing | 1.00 |
| `BITMAP-EMPTY` | file is 0 bytes | 1.00 |
| `BITMAP-UNKNOWN-FORMAT` | not a recognized image format | 1.00 |
| `BITMAP-CORRUPT` | cannot decode image | 1.00 |
| `BITMAP-TOO-LARGE` | file size exceeds limit | 1.00 |
| `BITMAP-FORMAT` | format not in allowed set | 1.00 |
| `BITMAP-MODE` | color mode not in allowed set | 1.00 |
| `BITMAP-TOO-MANY-PIXELS` | exceeds pixel limit (decompression bomb guard) | 1.00 |
| `BITMAP-DIMENSION` | width/height exceeds max dimension | 1.00 |
| `BITMAP-RESIZE-FAIL` | safe resize failed | 0.80 |

### Pixel analysis — `pixel_check.py` (Level 1.5)

| code | meaning | typical conf |
|---|---|---|
| `PIXEL-SOFT` | low sharpness (Laplacian variance below threshold) | 0.70 |
| `PIXEL-LOW-CONTRAST` | low Michelson contrast | 0.70 |
| `PIXEL-ANALYSIS-ERROR` | pixel analysis failed | 1.00 |

### OCR — `ocr_adapter.py` (Level 1.5)

| code | meaning | typical conf |
|---|---|---|
| `OCR-LOW-CONFIDENCE` | average OCR confidence below threshold | 0.70 |
| `OCR-UNAVAILABLE` | OCR engine not installed/configured | 1.00 |
| `OCR-ERROR` | OCR engine execution failed | 1.00 |

### Vision — `vision_adapter.py` (Level 1.5)

| code | meaning | typical conf |
|---|---|---|
| `VISION-UNAVAILABLE` | semantic vision not available (text-only model) | 1.00 |
| `VISION-ERROR` | vision task failed | 1.00 |

### Standards & mechanics (produced by the tool drivers)

| code | source | meaning |
|---|---|---|
| `AXE/<id>` | axe-core | WCAG rule violation (`color-contrast`, `region`, …) |
| `KBD/NO-FOCUS` | focus walk | focus-visible without a visible outline |
| `PRN/PAGES`, `PRN/SIZE` | print_check | page-count / page-box expectation failed |
| `PRN-CHECK-ERROR` | print_check | print verification failed |
| `LNK/DEAD`, `ID/DUP`, `H/JUMP` | structure checkers | link/anchor/heading-order integrity |
| `MARGIN-CHECK-ERROR` | layout_check | CSS margin check failed |

### Sensor failures (never silence — see FLOWCHARTS §6)

`E00`–`E01` probe thrown · `F01`–`F08` transport/driver failures.

## Detected · derived · interpreted

Every downstream statement must keep its tier (spec §24):

```text
DETECTED   "scrollH=3106 > clientH=2646"            ← in the evidence
DERIVED    "the second figure block overflows the sheet" ← arithmetic on evidence
INTERPRETED"moving figures side-by-side will fix it"    ← hypothesis; must be
                                                          re-measured after the edit
```

An INTERPRETED claim that has not been re-measured may never be reported as
done.

## Minimal example (clean)

```json
{
  "schema_version": "1.0",
  "target": "web/docs/d3.html",
  "probe": "layout_probe.js",
  "root": {"x": 0, "y": 40, "w": 1200, "h": 3000},
  "issues": []
}
```

## Visual Intermediate Representation (VIR)

The VIR merges evidence from renderer, bitmap, pixel, OCR, and vision
sources into a shared schema. Built by `tools/vir_builder.py`:

```json
{
  "schema_version": "1.0.0",
  "asset_id": "B01-C03-F01",
  "project_profile": "B01",
  "expected_page_size": {"width_cm": 21.0, "height_cm": 29.7, "name": "A4"},
  "built_at": "2026-11-04T17:24:55Z",
  "input_type": "mixed",
  "input_types": ["renderer", "bitmap", "pixels", "ocr", "vision"],
  "renderer": { … layout evidence … },
  "bitmap": { … bitmap evidence … },
  "pixels": { … pixel evidence … },
  "ocr": { … OCR evidence … },
  "vision": { … vision evidence … },
  "evidence_summary": {
    "total_findings": 3,
    "detected_findings": 3,
    "interpreted_findings": 0,
    "dirty_targets": 2,
    "total_targets": 5
  },
  "issues": [ … ],
  "evidence_tiers": {
    "DETECTED": "Direct measurement from renderer/pixel/OCR — ground truth",
    "DERIVED": "Arithmetic on evidence — requires re-measurement after edits",
    "INTERPRETED": "Model hypothesis — requires human verification"
  },
  "provenance_chain": ["Source","Evidence","Claim","Content Block","Chapter","Book","Release"],
  "limitations": [
    "Semantic vision unavailable — text-only model cannot interpret images"
  ]
}
```

VIR fields:

| field | required | meaning |
|---|---|---|
| `schema_version` | yes | VIR contract version |
| `asset_id` | no | stable asset ID (e.g. `B01-C03-F01`) |
| `project_profile` | no | active project profile ID |
| `expected_page_size` | no | page size from profile |
| `built_at` | yes | ISO-8601 build time |
| `input_type` | yes | `renderer`, `bitmap`, `ocr`, `vision`, or `mixed` |
| `input_types` | yes | list of active input types |
| `renderer` | no | normalized layout probe evidence |
| `bitmap` | no | normalized bitmap ingestion evidence |
| `pixels` | no | normalized pixel analysis evidence |
| `ocr` | no | normalized OCR evidence |
| `vision` | no | normalized vision adapter evidence |
| `evidence_summary` | yes | aggregate counts by tier |
| `issues` | yes | all issues across all sources |
| `evidence_tiers` | yes | tier definitions |
| `provenance_chain` | yes | source → evidence → claim → content block → chapter → book → release |
| `limitations` | yes | known limitations (e.g. vision unavailable) |

## Margin evidence

Margin verification produces an evidence object (see `tools/layout_check.py`):

| field | meaning |
|---|---|
| `check_id` | `"margin-verification"` |
| `status` | `PASS`, `FAIL`, `PARTIAL`, `NOT_VERIFIABLE`, `BLOCKED` |
| `status_reason` | human-readable reason |
| `profile_id` | active profile ID |
| `expected_page_size` | page size from profile |
| `expected_margins_mm` | `{top, right, bottom, left}` in mm |
| `declared_page_rules` | list of `@page` rules found via CSSOM |
| `observed_values` | map of selector+property → value_mm |
| `tolerance_mm` | comparison tolerance |
| `verification_method` | `cssom` or `none` |
| `limitations` | known limitations |
| `warnings` | warnings (e.g. inaccessible stylesheets) |
| `timestamp` | ISO-8601 |
| `tool_version` | tool version |

## Project profile schema

Profiles declare per-project expectations:

```json
{
  "profile_schema_version": "1.0.0",
  "profile_id": "B01",
  "profile_name": "B01 — Foundations of AI Engineering",
  "project": "AI Engineering Book Series",
  "inputs": ["html", "svg"],
  "page": {
    "size": {"width_cm": 21.0, "height_cm": 29.7, "name": "A4"},
    "orientation": "portrait",
    "margins": {"top": "1.15cm", "right": "1.15cm", "bottom": "1.15cm", "left": "1.15cm"},
    "margin_tolerance_mm": 0.5
  },
  "checks": {"layout": true, "print": true, "margin": true, "accessibility": true},
  "rubric": {"rubric_id": "APAI-B01-ILLUSTRATION-001", "rubric_version": "1.0.0"},
  "gates": {"l3_requires_human_review": true}
}
```

## APAI assessment

APAI produces a structured rubric evaluation (see `tools/apai_bitmap.py`):

| field | meaning |
|---|---|
| `rubric.rubric_id` | rubric identifier |
| `rubric.rubric_name` | rubric name |
| `rubric.rubric_version` | rubric version |
| `overall_assessment.summary` | overall verdict text |
| `overall_assessment.average_score` | mean of scored criteria (or null) |
| `overall_assessment.confidence` | high / medium / low |
| `overall_assessment.human_review_required` | boolean |
| `criteria[].criterion_id` | criterion identifier |
| `criteria[].criterion_name` | criterion name |
| `criteria[].score` | score 1–5, or null if insufficient evidence |
| `criteria[].sufficiency` | `sufficient`, `partial`, `insufficient` |
| `criteria[].evidence[]` | evidence references with type/source/confidence |
| `criteria[].uncertainty_notes` | uncertainty flags |
| `priority_recommendations[]` | next actions |

## Minimal example (VIR + margin)

```json
{
  "schema_version": "1.0.0",
  "asset_id": "B01-C03-F01",
  "project_profile": "B01",
  "expected_page_size": {"width_cm": 21.0, "height_cm": 29.7, "name": "A4"},
  "built_at": "2026-11-04T17:24:55Z",
  "input_type": "mixed",
  "input_types": ["renderer", "bitmap", "ocr"],
  "renderer": {
    "available": true,
    "targets": [
      {
        "file": "page.html",
        "root": {"x": 0, "y": 0, "w": 794, "h": 1123},
        "issues": [],
        "evidence_tier": "DETECTED"
      }
    ]
  },
  "bitmap": {
    "available": true,
    "targets": [
      {
        "file": "image.png",
        "record": {"format": "PNG", "width": 100, "height": 100, "mode": "RGBA"},
        "issues": [],
        "evidence_tier": "DETECTED"
      }
    ]
  },
  "evidence_summary": {
    "total_findings": 0,
    "detected_findings": 0,
    "interpreted_findings": 0,
    "dirty_targets": 0,
    "total_targets": 2
  },
  "issues": [],
  "limitations": []
}
```
