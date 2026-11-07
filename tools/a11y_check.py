#!/usr/bin/env python3
"""a11y_check — axe-core (WCAG) + keyboard focus probe over HTML pages.

  python tools/a11y_check.py web/                     # scan a directory
  python tools/a11y_check.py page.html --keyboard     # + Tab/focus probe
  python tools/a11y_check.py page.html --axe path/to/axe.min.js

Needs axe-core once:   npm install axe-core   (or pass --axe).
Exit code 0 = no violations / no invisible focus.
Exit code 2 = axe-core NOT_RUN (dependency missing).
"""
import argparse, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp_runner import CDPRunner

HERE = Path(__file__).resolve().parent


def find_axe(explicit=None):
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
        sys.exit(f"--axe path not found: {p}")
    # Search order: local, project, vendor, then global npm
    candidates = [
        Path("node_modules/axe-core/axe.min.js"),
        Path(__file__).resolve().parents[1] / "node_modules/axe-core/axe.min.js",
        HERE / "_vendor" / "axe.min.js",
    ]
    # Global npm prefix on Windows: %APPDATA%\npm\node_modules\
    import os
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "npm" / "node_modules" / "axe-core" / "axe.min.js")
    for c in candidates:
        if c.exists():
            return c
    return None  # axe missing — caller decides NOT_RUN vs BLOCKED


AXE_RUN = """(async () => {
  try {
    const r = await axe.run(document, {resultTypes:['violations'],
      runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a',
                'wcag21aa','wcag22aa','best-practice']}});
    return r.violations.map(v => ({id:v.id, impact:v.impact, help:v.help,
      nodes:v.nodes.slice(0,4).map(n=>n.target.join(' '))}));
  } catch(e) { return [{id:'AXE-ERROR', impact:'critical', help:String(e),
                        nodes:[]}]; }
})()"""

FOCUS_PROBE = """(() => {
  const e = document.activeElement;
  if (!e || e === document.body) return null;
  const cs = getComputedStyle(e);
  return {tag: e.tagName.toLowerCase(),
          name: (e.getAttribute('aria-label') || e.textContent || '')
                .trim().slice(0, 42),
          outline: (cs.outlineStyle + ' ' + cs.outlineWidth),
          fv: e.matches(':focus-visible')};
})()"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--axe", help="path to axe.min.js")
    ap.add_argument("--keyboard", action="store_true",
                    help="also run the Tab/focus probe on each page")
    ap.add_argument("--tabs", type=int, default=14)
    ap.add_argument("--port", type=int, default=9401)
    ap.add_argument("--block-on-missing-axe", action="store_true",
                    help="exit 2 (BLOCKED) instead of NOT_RUN when axe-core missing")
    a = ap.parse_args()

    pages = []
    for p in a.targets:
        p = Path(p)
        pages += sorted(p.rglob("*.html")) if p.is_dir() else [p]

    axe_path = find_axe(a.axe)
    axe_missing = axe_path is None

    if axe_missing:
        if a.block_on_missing_axe:
            print("NOT_RUN/BLOCKED: axe-core not found — "
                  "npm install axe-core or pass --axe PATH")
            for p in pages:
                print(f"  NOT_RUN {p} — axe-core unavailable")
            sys.exit(2)
        else:
            print("NOT_RUN: axe-core not found — "
                  "accessibility checks skipped")
            for p in pages:
                print(f"  NOT_RUN {p} — axe-core unavailable")
            sys.exit(0)

    axe_src = axe_path.read_text(encoding="utf-8")
    findings = 0

    with CDPRunner(port=a.port) as r:
        for page in pages:
            r.goto(page.resolve().as_uri())
            r.evaluate(axe_src + "\n; window.__axe_loaded = true;")
            res = r.evaluate(AXE_RUN) or []
            if res:
                findings += len(res)
                print(f"!! {page}")
                for v in res:
                    print(f"     - [{v.get('impact')}/{v.get('id')}] "
                          f"{v.get('help')} :: {'; '.join(v.get('nodes', []))}")
            else:
                print(f"OK {page}")

        if a.keyboard:
            print("\nKEYBOARD PROBE (Tab order + focus visibility)")
            for page in pages:
                r.goto(page.resolve().as_uri())
                r.send("Page.bringToFront")
                seen = []
                for _ in range(a.tabs):
                    r.send("Input.dispatchKeyEvent", {"type": "rawKeyDown",
                        "key": "Tab", "windowsVirtualKeyCode": 9, "code": "Tab"})
                    r.send("Input.dispatchKeyEvent", {"type": "keyUp",
                        "key": "Tab", "windowsVirtualKeyCode": 9})
                    info = r.evaluate(FOCUS_PROBE)
                    if info is None:
                        break
                    if isinstance(info, dict) and "fv" in info:
                        seen.append(info)
                bad = [s for s in seen if s.get("fv") and
                       s.get("outline", "").startswith(("none", "0px"))]
                print(f"{'!!' if bad else 'OK'} {page} — "
                      f"{len(seen)} focusable stops")
                for s in seen:
                    print(f"     - <{s['tag']}> {s['name']} | "
                          f"focus-visible={s['fv']} outline={s['outline']}")
                findings += len(bad)

    print(f"\nTOTAL FINDINGS: {findings}")
    sys.exit(0 if findings == 0 else 1)


if __name__ == "__main__":
    main()
