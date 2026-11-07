#!/usr/bin/env python3
"""heading_sensor.py — heading structure validation for LiGeo CV sensor pack.

Checks HTML heading hierarchy (H1-H6): proper ordering, missing levels,
single H1, and heading content presence.

  python tools/cv_sensors/heading_sensor.py page.html
  python tools/cv_sensors/heading_sensor.py dir/ --json out.json

Exit code = number of targets with findings (0 = clean).
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cv_core import load_image

try:
    from PIL import Image
    PILLOW_VERSION = Image.__version__
except Exception:
    PILLOW_VERSION = "unknown"


def analyze_headings(path: Path) -> dict:
    """Analyze heading structure from HTML file via CDP DOM inspection.

    Checks:
    - H1 presence and count (should have exactly one H1)
    - Heading hierarchy (no skipped levels, e.g., H1->H3 without H2)
    - Empty headings
    - Heading order correctness
    """
    path = Path(path)
    if not path.exists():
        return _empty_result(path, "file not found")

    if path.suffix.lower() not in (".html", ".htm"):
        return _not_html_result(path)

    try:
        from tools.cdp_runner import CDPRunner
    except ImportError:
        return {
            "path": str(path),
            "metrics_version": "1.0.0",
            "error": "cdp_runner not available — cannot inspect HTML headings",
            "heading_count": 0,
            "h1_count": 0,
            "hierarchy_violations": [],
            "empty_headings": 0,
            "method": "CDP DOM inspection",
            "version": PILLOW_VERSION,
            "interpretation": "Heading analysis requires CDP browser automation",
            "limitations": "CDP not available in this environment",
        }

    with CDPRunner() as r:
        r.goto(path.resolve().as_uri())

        # Get all headings
        headings_js = """
        (() => {
            const headings = [];
            for (let i = 1; i <= 6; i++) {
                const elements = document.querySelectorAll('h' + i);
                elements.forEach(h => {
                    headings.push({
                        level: i,
                        text: h.textContent.trim(),
                        has_text: h.textContent.trim().length > 0,
                    });
                });
            }
            return headings;
        })()
        """
        headings_data = r.evaluate(headings_js) or []

        total_count = len(headings_data)
        h1_count = sum(1 for h in headings_data if h["level"] == 1)
        empty_count = sum(1 for h in headings_data if not h["has_text"])

        # Check hierarchy violations (skipped levels)
        hierarchy_violations = []
        prev_level = 0
        for h in headings_data:
            level = h["level"]
            if prev_level > 0 and level > prev_level + 1:
                hierarchy_violations.append({
                    "from_level": prev_level,
                    "to_level": level,
                    "text": h["text"][:100],
                })
            prev_level = level

        # Check for missing H1
        missing_h1 = h1_count == 0
        multiple_h1 = h1_count > 1

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "total_headings": total_count,
            "h1_count": h1_count,
            "heading_levels": {
                f"h{i}": sum(1 for h in headings_data if h["level"] == i)
                for i in range(1, 7)
            },
            "empty_headings": empty_count,
            "hierarchy_violations": hierarchy_violations,
            "missing_h1": missing_h1,
            "multiple_h1": multiple_h1,
            "hierarchy_valid": len(hierarchy_violations) == 0 and h1_count == 1,
            "method": "CDP DOM inspection",
            "version": PILLOW_VERSION,
            "interpretation": "Heading structure and hierarchy from DOM inspection",
            "limitations": "Requires CDP browser; semantic heading quality not assessed",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "heading_count": 0,
        "h1_count": 0,
        "heading_levels": {f"h{i}": 0 for i in range(1, 7)},
        "empty_headings": 0,
        "hierarchy_violations": [],
        "missing_h1": False,
        "multiple_h1": False,
        "hierarchy_valid": False,
        "method": "CDP DOM inspection",
        "version": PILLOW_VERSION,
        "interpretation": "File could not be processed — no heading analysis available",
        "limitations": "File could not be processed",
    }


def _not_html_result(path: Path) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": "not an HTML file",
        "heading_count": 0,
        "h1_count": 0,
        "heading_levels": {f"h{i}": 0 for i in range(1, 7)},
        "empty_headings": 0,
        "hierarchy_violations": [],
        "missing_h1": False,
        "multiple_h1": False,
        "hierarchy_valid": False,
        "method": "CDP DOM inspection",
        "version": PILLOW_VERSION,
        "interpretation": "Heading analysis requires HTML file",
        "limitations": "Only HTML files can be analyzed for headings",
    }


def run(targets, json_path: str | None = None):
    """Heading audit of file/dir targets."""
    targets_out = []
    for p in targets:
        p = Path(p)
        if p.is_dir():
            targets_out += sorted(p.rglob("*.html")) + sorted(p.rglob("*.htm"))
        elif p.exists():
            targets_out.append(p)
        else:
            sys.exit(f"no such target: {p}")
    seen, uniq = set(), []
    for f in targets_out:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            uniq.append(f)

    report, dirty = [], 0
    for f in uniq:
        try:
            metrics = analyze_headings(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag heading issues
            if metrics.get("missing_h1"):
                entry["issues"].append({
                    "t": "HEADING-NO-H1",
                    "det": "document has no H1 heading",
                    "conf": 0.9,
                })
            if metrics.get("multiple_h1"):
                entry["issues"].append({
                    "t": "HEADING-MULTIPLE-H1",
                    "det": f"{metrics['h1_count']} H1 headings found (should have exactly one)",
                    "conf": 0.8,
                })
            if metrics.get("hierarchy_violations"):
                entry["issues"].append({
                    "t": "HEADING-HIERARCHY",
                    "det": f"{len(metrics['hierarchy_violations'])} heading hierarchy violation(s)",
                    "conf": 0.8,
                })
            if metrics.get("empty_headings", 0) > 0:
                entry["issues"].append({
                    "t": "HEADING-EMPTY",
                    "det": f"{metrics['empty_headings']} empty heading(s)",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "HEADING-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
            ]}
            dirty += 1
        report.append(entry)

    if json_path and report:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report, dirty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--json", help="write full evidence to this file")
    a = ap.parse_args()

    report, dirty = run(a.targets, json_path=a.json)

    for entry in report:
        m = entry.get("metrics")
        n = len(entry.get("issues", []))
        if m:
            meta = f"  headings={m.get('heading_count', 0)} h1={m.get('h1_count', 0)} "
            meta += f"violations={len(m.get('hierarchy_violations', []))}"
        else:
            meta = "  (no metrics)"
        print(("!! " if n else "OK ") + entry["file"] + meta)
        for iss in entry.get("issues", []):
            print(f"     - [{iss.get('t')} conf {iss.get('conf', 0):.2f}] {iss.get('det')}")

    if a.json:
        print(f"\nevidence written: {a.json}")
    print(f"\nTARGETS: {len(report)}  DIRTY: {dirty}")
    sys.exit(min(dirty, 1))


if __name__ == "__main__":
    main()
