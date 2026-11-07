# Integration — drop it into another project

## 0. Prerequisites

```bash
pip install websocket-client          # only Python dependency for L0/L1
pip install Pillow numpy              # for bitmap_check.py + pixel_check.py
# optional, for the a11y check:
npm install axe-core                  # or pass --axe path/to/axe.min.js
# browser: Edge or Chrome; override with LIGEO_BROWSER=/path/to/browser
```

Windows / macOS / Linux: the auto-detector in `tools/cdp_runner.py` covers
Edge (Win), Microsoft Edge (macOS) and chromium packages (Linux); anything
exotic → `LIGEO_BROWSER`.

## 1. Copy the parts

```text
your-project/
├── tools/    ← cp -r ligeopersys/tools
├── probes/   ← cp -r ligeopersys/probes
├── profiles/ ← cp -r ligeopersys/profiles  (project-specific)
└── tests/    ← cp -r ligeopersys/tests    (self-test gate; keep fixtures)
```

## 2. Choose your project profile

Profiles declare per-project expectations (page size, margins, rubric) so
B01 values do not leak into other projects:

```bash
python tools/profile_loader.py profiles/B01.json
```

Copy `profiles/B01.json` or `profiles/generic.json` as your starting point,
then edit `page.size`, `page.margins`, `checks`, and `rubric` for your
project. Use `--profile` with any tool that accepts it:

```bash
python tools/layout_check.py page.html --profile profiles/MyProject.json --margin-check
python tools/apai_bitmap.py --vir out/vir.json --profile profiles/MyProject.json
python tools/capability_detector.py --profile profiles/MyProject.json
```

## 3. Point the probes at your markup

Default root selection (priority order): `[data-probe-root]` → `.sheet` →
`main` → `body`. Either accept the default or override per run:

```bash
python tools/layout_check.py src/pages/ --root "#app" --json out/ev.json
```

Add `data-probe-root` to your app shell if you want an explicit contract.

## 4. Choose targets (question-guided)

Maintain a small target list per change type — do not crawl everything:

```text
changed a landing hero   →  tools/layout_check.py src/hero.html + svg files
changed shared tokens    →  layout_check + a11y_check on every page
changed @page / print    →  tools/print_check.py --config print-expectations.json
changed an image         →  tools/bitmap_check.py img.png + tools/pixel_check.py img.png
changed text in image    →  tools/ocr_adapter.py img.png
release gate             →  all three + tests/test_selfcheck.py
vir builder              →  tools/vir_builder.py --layout … --bitmap … --pixels … --ocr …
apai assessment          →  tools/apai_bitmap.py --vir out/vir.json --profile profiles/MyProject.json
```

Example `print-expectations.json` (see `../examples/`):

```json
[{"file": "invoice.html", "pages": [1, 2], "orient": "portrait"},
 {"file": "poster.html", "pages": [1, 1], "size_cm": [55, 70]}]
```

## 5. Wire the trust gate (CI or pre-commit)

```bash
python tests/test_selfcheck.py     # must PASS before any "clean" is believed
```

CI runners need a browser; on GitHub Actions install Edge/Chrome (or set
`LIGEO_BROWSER` to the runner's chromium) and run the command above before
your layout job. Exit codes: `0` = trustworthy, `1` = probe regressions.

## 6. Give your agent the rules

The system is only safe under an agent that respects the evidence contract:

```text
→ paste/summarise docs/PLAYBOOK.md into the agent's system instructions
→ make the agent run:  layout_check → reason → fix → re-run → (all checks)
→ require the §10 report template for every QA claim
→ use --profile with project-specific values, never hardcode B01 numbers
```

An agent with the tools but without the playbook will eventually
self-certify taste judgements — that is the failure mode the L3 gate exists
to prevent.

## 7. Custom probes (the extension path)

When a question is measurable but uncovered (PLAYBOOK §5):

1. copy `probes/layout_probe.js` → `probes/<name>_probe.js`;
2. keep the contract: `(opts) => { …, issues:[{t,det,rect?,conf}] }`;
3. add one planted-bug case to `tests/fixtures/` + assert its code in
   `tests/test_selfcheck.py`;
4. document the code in `docs/EVIDENCE-SCHEMA.md` registry.

Run it with:

```python
from cdp_runner import CDPRunner
with CDPRunner() as r:
    r.goto(uri)
    ev = r.run_probe(open("probes/my_probe.js").read(), {"opt": 1})
```

## 8. Pairing with a vision-capable model

The bridge spec's hybrid mode composes cleanly:

```text
probes ──────────► geometry/a11y/print evidence (ground truth) ─┐
screenshot ──────► VLM (if you have one) ──► semantic hints ────┤► reasoner
human L3 gate ───► verdict ─────────────────────────────────────┘
```

Geometry stays the authority for geometric questions; the VLM only adds
L3-ish hints, tagged as such. Never let a VLM hint override a measured rect.

## 9. Tool reference

| Tool | Purpose | Key flags |
|---|---|---|
| `layout_check.py` | HTML/SVG geometry + CSS @page margins | `--profile`, `--margin-check`, `--print`, `--json` |
| `a11y_check.py` | axe-core WCAG + keyboard focus | `--axe`, `--keyboard`, `--block-on-missing-axe` |
| `print_check.py` | printToPDF size/page-count | `--config` |
| `pdf_check.py` | PDF pages/paper size/ink coverage | `--config` |
| `bitmap_check.py` | PNG/JPEG ingestion + metadata | `--max-file-mb`, `--max-pixels`, `--max-dimension`, `--profile`, `--json` |
| `pixel_check.py` | deterministic pixel metrics | `--json` |
| `ocr_adapter.py` | OCR text + boxes + confidence | `--lang`, `--json` |
| `vision_adapter.py` | VLM captioning/VQA/detect | `--mode`, `--endpoint`, `--api-key`, `--model`, `--json` |
| `vir_builder.py` | VIR builder (merge all evidence) | `--layout`, `--bitmap`, `--pixels`, `--ocr`, `--vision`, `--profile`, `--out` |
| `apai_bitmap.py` | APAI rubric art/illustration eval | `--vir`, `--profile`, `--rubric`, `--purpose`, `--out` |
| `capability_detector.py` | reports available capabilities | `--profile`, `--json` |
| `profile_loader.py` | profile loading/validation | profile path |

## 10. Troubleshooting

| symptom | cause | fix |
|---|---|---|
| `cannot attach to browser` | port busy / browser path | change `--port`, set `LIGEO_BROWSER` |
| websocket `403` | origin header | use `CDPRunner` (sets `suppress_origin` + `--remote-allow-origins`) |
| probe returns `None` | expression threw | read `exceptionDetails`; probe must be an arrow fn taking `opts` |
| everything "OK" instantly | probe never called | use `run_probe`, not `evaluate` |
| findings on a clean page | selector picks `body` | priority order / `--root` |
| print PDF off by a few px | parent padding in `@media print` | zero margins/padding; keep `overflow:hidden` on the sheet |
| margin status `NOT_VERIFIABLE` | CSSOM cannot read `@page` | treat as gap; report limitation |
| margin status `FAIL` | declared `@page` margin differs from profile | fix CSS `@page` margin or update profile |
| `VISION-UNAVAILABLE` | no VLM configured | treat as gap; semantic vision requires separate VLM |
| `axe-core not found` | axe.min.js missing | `npm install axe-core` or pass `--axe PATH` |
