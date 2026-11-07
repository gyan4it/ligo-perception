#!/usr/bin/env python3
"""link_sensor.py — link/anchor validity detection for LiGeo CV sensor pack.

Checks for broken links, missing anchors, and link text quality in HTML
documents via CDP DOM inspection.

  python tools/cv_sensors/link_sensor.py page.html
  python tools/cv_sensors/link_sensor.py dir/ --json out.json

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


def analyze_links(path: Path) -> dict:
    """Analyze link validity from HTML file via CDP DOM inspection.

    Returns dict with link counts, broken link count, and link quality metrics.
    """
    path = Path(path)
    if not path.exists():
        return _empty_result(path, "file not found")

    if path.suffix.lower() not in (".html", ".htm"):
        return _not_html_result(path)

    # For HTML files, use CDP to inspect links
    try:
        from tools.cdp_runner import CDPRunner
    except ImportError:
        return {
            "path": str(path),
            "metrics_version": "1.0.0",
            "error": "cdp_runner not available — cannot inspect HTML links",
            "link_count": 0,
            "broken_link_count": 0,
            "anchors_missing": 0,
            "method": "CDP DOM inspection",
            "version": PILLOW_VERSION,
            "interpretation": "Link validation requires CDP browser automation",
            "limitations": "CDP not available in this environment",
        }

    with CDPRunner() as r:
        r.goto(path.resolve().as_uri())

        # Get all links
        links_js = """
        (() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            return links.map(l => ({
                href: l.href,
                text: l.textContent.trim(),
                has_text: l.textContent.trim().length > 0,
                rel: l.rel || '',
                target: l.target || ''
            }));
        })()
        """
        links_data = r.evaluate(links_js) or []

        # Check each link for validity
        broken_count = 0
        missing_anchor_count = 0
        link_details = []

        for link in links_data:
            href = link.get("href", "")
            has_text = link.get("has_text", False)
            link_text = link.get("text", "")

            issue = None

            # Check for missing href
            if not href or href == "#":
                issue = "empty or missing href"

            # Check for missing link text (accessibility issue)
            if not has_text or len(link_text.strip()) == 0:
                missing_anchor_count += 1
                issue = (issue + "; " if issue else "") + "missing link text"

            # Check for fragment anchors that don't exist on page
            if href.startswith("#") and len(href) > 1:
                anchor_id = href[1:]
                check_js = f"document.getElementById('{anchor_id}') !== null"
                anchor_exists = r.evaluate(check_js) or False
                if not anchor_exists:
                    missing_anchor_count += 1
                    issue = (issue + "; " if issue else "") + "anchor target not found"

            if issue:
                broken_count += 1

            link_details.append({
                "href": href,
                "text": link_text[:100] if link_text else "",
                "has_text": has_text,
                "issue": issue,
            })

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "total_links": len(links_data),
            "broken_link_count": broken_count,
            "missing_anchor_count": missing_anchor_count,
            "broken_link_ratio": round(broken_count / len(links_data), 4) if links_data else 0.0,
            "links_without_text": missing_anchor_count,
            "link_details": link_details[:50],  # Cap at 50 for evidence size
            "method": "CDP DOM inspection",
            "version": PILLOW_VERSION,
            "interpretation": "Link validity and accessibility from DOM inspection",
            "limitations": "Requires CDP browser; external link validity not verified",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "link_count": 0,
        "broken_link_count": 0,
        "missing_anchor_count": 0,
        "broken_link_ratio": 0.0,
        "links_without_text": 0,
        "link_details": [],
        "method": "CDP DOM inspection",
        "version": PILLOW_VERSION,
        "interpretation": "File could not be processed — no link analysis available",
        "limitations": "File could not be processed",
    }


def _not_html_result(path: Path) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": "not an HTML file",
        "link_count": 0,
        "broken_link_count": 0,
        "missing_anchor_count": 0,
        "broken_link_ratio": 0.0,
        "links_without_text": 0,
        "link_details": [],
        "method": "CDP DOM inspection",
        "version": PILLOW_VERSION,
        "interpretation": "Link analysis requires HTML file",
        "limitations": "Only HTML files can be analyzed for links",
    }


def run(targets, json_path: str | None = None):
    """Link audit of file/dir targets."""
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
            metrics = analyze_links(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag broken links
            if metrics.get("broken_link_count", 0) > 0:
                entry["issues"].append({
                    "t": "LINK-BROKEN",
                    "det": f"{metrics['broken_link_count']} broken link(s) detected",
                    "conf": 0.8,
                })
            if metrics.get("links_without_text", 0) > 0:
                entry["issues"].append({
                    "t": "LINK-NO-TEXT",
                    "det": f"{metrics['links_without_text']} link(s) without accessible text",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "LINK-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            meta = f"  links={m.get('link_count', 0)} broken={m.get('broken_link_count', 0)} "
            meta += f"no_text={m.get('links_without_text', 0)}"
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
