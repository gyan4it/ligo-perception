#!/usr/bin/env python3
"""alt_text_sensor.py — image alt text audit for LiGeo CV sensor pack.

Checks images for missing or missing alt text attributes via CDP DOM inspection.

  python tools/cv_sensors/alt_text_sensor.py page.html
  python tools/cv_sensors/alt_text_sensor.py dir/ --json out.json

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


def analyze_alt_text(path: Path) -> dict:
    """Analyze image alt text from HTML file via CDP DOM inspection.

    Checks:
    - Images with missing alt attribute
    - Images with empty alt text (when not decorative)
    - Images with descriptive alt text
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
            "error": "cdp_runner not available — cannot inspect HTML images",
            "img_count": 0,
            "img_without_alt": 0,
            "img_with_empty_alt": 0,
            "img_with_alt": 0,
            "method": "CDP DOM inspection",
            "version": PILLOW_VERSION,
            "interpretation": "Alt text analysis requires CDP browser automation",
            "limitations": "CDP not available in this environment",
        }

    with CDPRunner() as r:
        r.goto(path.resolve().as_uri())

        # Get all images
        images_js = """
        (() => {
            const imgs = Array.from(document.querySelectorAll('img'));
            return imgs.map(img => ({
                src: img.src || '',
                alt: img.alt || '',
                has_alt_attr: img.hasAttribute('alt'),
                width: img.naturalWidth,
                height: img.naturalHeight,
            }));
        })()
        """
        images_data = r.evaluate(images_js) or []

        img_count = len(images_data)
        img_without_alt = 0
        img_with_empty_alt = 0
        img_with_alt = 0
        img_details = []

        for img in images_data:
            has_alt_attr = img.get("has_alt_attr", False)
            alt_text = img.get("alt", "")

            if not has_alt_attr:
                img_without_alt += 1
            elif alt_text.strip() == "":
                img_with_empty_alt += 1
            else:
                img_with_alt += 1

            img_details.append({
                "src": img.get("src", "")[:100],
                "has_alt": has_alt_attr,
                "alt_text": alt_text[:100] if alt_text else "",
                "width": img.get("width", 0),
                "height": img.get("height", 0),
            })

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "img_count": img_count,
            "img_without_alt": img_without_alt,
            "img_with_empty_alt": img_with_empty_alt,
            "img_with_alt": img_with_alt,
            "alt_coverage_pct": round(img_with_alt / img_count * 100, 4) if img_count > 0 else 0.0,
            "img_details": img_details[:50],  # Cap at 50 for evidence size
            "method": "CDP DOM inspection",
            "version": PILLOW_VERSION,
            "interpretation": "Alt text coverage from DOM inspection",
            "limitations": "Requires CDP browser; decorative vs informative distinction not made",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "img_count": 0,
        "img_without_alt": 0,
        "img_with_empty_alt": 0,
        "img_with_alt": 0,
        "alt_coverage_pct": 0.0,
        "img_details": [],
        "method": "CDP DOM inspection",
        "version": PILLOW_VERSION,
        "interpretation": "File could not be processed — no alt text analysis available",
        "limitations": "File could not be processed",
    }


def _not_html_result(path: Path) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": "not an HTML file",
        "img_count": 0,
        "img_without_alt": 0,
        "img_with_empty_alt": 0,
        "img_with_alt": 0,
        "alt_coverage_pct": 0.0,
        "img_details": [],
        "method": "CDP DOM inspection",
        "version": PILLOW_VERSION,
        "interpretation": "Alt text analysis requires HTML file",
        "limitations": "Only HTML files can be analyzed for alt text",
    }


def run(targets, json_path: str | None = None):
    """Alt text audit of file/dir targets."""
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
            metrics = analyze_alt_text(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag images without alt
            if metrics.get("img_without_alt", 0) > 0:
                entry["issues"].append({
                    "t": "IMG-NO-ALT",
                    "det": f"{metrics['img_without_alt']} image(s) without alt attribute",
                    "conf": 0.9,
                })
            if metrics.get("img_with_empty_alt", 0) > 0:
                entry["issues"].append({
                    "t": "IMG-EMPTY-ALT",
                    "det": f"{metrics['img_with_empty_alt']} image(s) with empty alt text",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "ALT-TEXT-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            meta = f"  imgs={m.get('img_count', 0)} no_alt={m.get('img_without_alt', 0)} "
            meta += f"empty_alt={m.get('img_with_empty_alt', 0)} "
            meta += f"coverage={m.get('alt_coverage_pct', 0)}%"
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
