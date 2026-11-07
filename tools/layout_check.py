#!/usr/bin/env python3
"""layout_check — run the geometry probes over targets, print evidence.

  python tools/layout_check.py web/posters posters/          # dirs or files
  python tools/layout_check.py page.html --root "#app"       # custom root
  python tools/layout_check.py art/*.svg --json out.json
  python tools/layout_check.py page.html --print --margin-cm 1.15
  python tools/layout_check.py page.html --profile profiles/B01.json --margin-check

Exit code = number of targets with findings (0 = clean).
The `run()` core is reusable: `from layout_check import run` or via ligeo.
"""
import argparse, base64, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp_runner import CDPRunner

HERE = Path(__file__).resolve().parent
PROBES = HERE.parent / "probes"

PT_PER_CM = 72 / 2.54  # 28.3465 pt per cm (1 inch = 2.54 cm = 72 pt)
TOOL_VERSION = "1.0.0-stage-1"


# ----------------------------------------------------------------------
# Profile loading (shared via profile_loader)
# ----------------------------------------------------------------------
from profile_loader import (
    load_profile,
    profile_expected_margins_mm,
    profile_page_size,
    profile_margin_tolerance_mm,
    parse_css_length_mm,
)


# ----------------------------------------------------------------------
# CSSOM page-margin probe integration
# ----------------------------------------------------------------------
def check_page_margins_via_cssom(r, expected_margins_mm: dict | None,
                                 tolerance_mm: float = 0.5) -> dict:
    """Inspect @page rules via CSSOM and compare against expected margins.

    Returns a margin evidence dict with fields:
      check_id, status, profile_id, expected_page_size,
      expected_margins_mm, declared_page_rules, observed_values,
      tolerance_mm, verification_method, limitations, warnings,
      timestamp, tool_version
    """
    margin_probe_js = (PROBES / "page_margin_probe.js").read_text(
        encoding="utf-8")

    opts = {}
    if expected_margins_mm:
        opts["expected_margins_mm"] = expected_margins_mm
    opts["tolerance_mm"] = tolerance_mm

    probe_result = r.run_probe(margin_probe_js, opts) or {}

    # Build declared_page_rules from probe results
    declared = []
    for pr in probe_result.get("page_rules", []):
        for prop, val in pr.get("margin", {}).items():
            declared.append({
                "selector": pr.get("selector", "@page"),
                "property": prop,
                "raw": val.get("raw"),
                "unit": val.get("unit"),
                "value_mm": val.get("value_mm"),
                "source_sheet": pr.get("source_sheet_index"),
            })

    # Build observed_values from probe results
    observed = {}
    for pr in probe_result.get("page_rules", []):
        for prop, val in pr.get("margin", {}).items():
            key = f"{pr.get('selector', '@page')} {prop}"
            observed[key] = val.get("value_mm")

    # Collect errors/warnings from probe
    warnings = []
    limitations = []
    for err in probe_result.get("errors", []):
        if err.get("code") == "SHEET-INACCESSIBLE":
            warnings.append(
                f"stylesheet {err.get('sheet_index')} inaccessible: "
                f"{err.get('error')}"
            )
        elif err.get("code") == "CSSOM-ERROR":
            limitations.append(
                f"CSSOM error: {err.get('error')}"
            )
    if not probe_result.get("cssom_accessible", False):
        limitations.append("CSSOM not accessible — cannot inspect @page rules")
    if probe_result.get("total_page_rules", 0) == 0:
        if probe_result.get("cssom_accessible", False):
            limitations.append("no @page rules found in accessible stylesheets")
        else:
            limitations.append("could not determine if @page rules exist")

    # Determine status
    status, status_reason = _determine_margin_status(
        probe_result, expected_margins_mm, tolerance_mm, declared)

    evidence = {
        "check_id": "margin-verification",
        "status": status,
        "status_reason": status_reason,
        "profile_id": None,  # filled by caller
        "expected_page_size": None,  # filled by caller
        "expected_margins_mm": expected_margins_mm,
        "declared_page_rules": declared,
        "observed_values": observed,
        "tolerance_mm": tolerance_mm,
        "verification_method": "cssom" if probe_result.get(
            "cssom_accessible", False) else "none",
        "limitations": limitations,
        "warnings": warnings,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_version": TOOL_VERSION,
    }
    return evidence


def _determine_margin_status(probe_result, expected_margins_mm,
                             tolerance_mm, declared) -> tuple:
    """Determine PASS/FAIL/PARTIAL/NOT_VERIFIABLE/BLOCKED for margin check.

    Returns (status, reason_string).
    """
    cssom_accessible = probe_result.get("cssom_accessible", False)
    total_rules = probe_result.get("total_page_rules", 0)
    total_errors = probe_result.get("total_errors", 0)

    if not cssom_accessible:
        return ("NOT_VERIFIABLE",
                "CSSOM not accessible — cannot inspect @page rules")

    if total_rules == 0 and total_errors > 0:
        return ("BLOCKED",
                "all stylesheets inaccessible — cannot verify margins")

    if total_rules == 0:
        if expected_margins_mm:
            return ("FAIL",
                    "no @page rules found — expected margins not declared")
        return ("PASS",
                "no @page rules found — no margin expectations to verify")

    # @page rules exist; compare against expected
    if not expected_margins_mm:
        return ("PASS",
                f"{total_rules} @page rule(s) found — no profile expectations "
                "to compare against")

    # Check each expected margin side against declared values
    mismatch_details = []
    matched_sides = set()
    for pr in probe_result.get("page_rules", []):
        for prop, val in pr.get("margin", {}).items():
            val_mm = val.get("value_mm")
            if val_mm is None:
                continue
            # Map CSS property to expected side
            side = _prop_to_side(prop)
            if side and side in expected_margins_mm:
                expected_val = expected_margins_mm[side]
                diff = abs(val_mm - expected_val)
                matched_sides.add(side)
                if diff <= tolerance_mm:
                    continue  # match
                mismatch_details.append(
                    f"{prop}: declared {val_mm}mm vs expected "
                    f"{expected_val}mm (diff {diff:.2f}mm, tolerance "
                    f"{tolerance_mm}mm)"
                )

    # Check if all expected sides are covered
    expected_sides = set(expected_margins_mm.keys())
    missing_sides = expected_sides - matched_sides

    if missing_sides:
        return ("PARTIAL",
                f"margins not fully declared: missing "
                f"{', '.join(sorted(missing_sides))}; "
                f"{'; '.join(mismatch_details) if mismatch_details else ''}")

    if mismatch_details:
        return ("FAIL",
                f"margin mismatch: {'; '.join(mismatch_details)}")

    return ("PASS",
            f"all {len(expected_sides)} margin side(s) match expected values "
            f"(tolerance {tolerance_mm}mm)")


def _prop_to_side(prop: str) -> str | None:
    """Map a CSS margin property to a side name."""
    mapping = {
        "margin-top": "top",
        "margin-right": "right",
        "margin-bottom": "bottom",
        "margin-left": "left",
        "margin": "all",  # shorthand applies to all sides
    }
    return mapping.get(prop)


# ----------------------------------------------------------------------
# Existing helpers (unchanged)
# ----------------------------------------------------------------------
def collect(paths):
    out = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            out += sorted(p.rglob("*.html")) + sorted(p.rglob("*.svg"))
        elif p.exists():
            out.append(p)
        else:
            sys.exit(f"no such target: {p}")
    seen, uniq = set(), []
    for f in out:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            uniq.append(f)
    return uniq


def run_probe_on_inline_svg(r, svg_js):
    """Run svg_probe.js against inline <svg> elements in an HTML page."""
    inject = """
(() => {
  const svgs = document.querySelectorAll('svg');
  return svgs.length;
})()
    """
    n_svgs = r.evaluate(inject)
    if not n_svgs or n_svgs == 0:
        return []
    svg_results = []
    for i in range(n_svgs):
        sel = f'svg:nth-of-type({i + 1})'
        out = r.run_probe(svg_js, {"svg": sel})
        out = out or {}
        out['svg_index'] = i
        out['svg_selector'] = sel
        svg_results.append(out)
    return svg_results


def check_page_margins_via_cssom(r, expected_margins_mm: dict | None,
                                 tolerance_mm: float = 0.5) -> dict:
    """Inspect @page rules via CSSOM and compare against expected margins.

    Returns a margin evidence dict with fields:
      check_id, status, profile_id, expected_page_size,
      expected_margins_mm, declared_page_rules, observed_values,
      tolerance_mm, verification_method, limitations, warnings,
      timestamp, tool_version
    """
    margin_probe_js = (PROBES / "page_margin_probe.js").read_text(
        encoding="utf-8")

    opts = {}
    if expected_margins_mm:
        opts["expected_margins_mm"] = expected_margins_mm
    opts["tolerance_mm"] = tolerance_mm

    probe_result = r.run_probe(margin_probe_js, opts) or {}

    # Build declared_page_rules from probe results
    declared = []
    for pr in probe_result.get("page_rules", []):
        for prop, val in pr.get("margin", {}).items():
            declared.append({
                "selector": pr.get("selector", "@page"),
                "property": prop,
                "raw": val.get("raw"),
                "unit": val.get("unit"),
                "value_mm": val.get("value_mm"),
                "source_sheet": pr.get("source_sheet_index"),
            })

    # Build observed_values from probe results
    observed = {}
    for pr in probe_result.get("page_rules", []):
        for prop, val in pr.get("margin", {}).items():
            key = f"{pr.get('selector', '@page')} {prop}"
            observed[key] = val.get("value_mm")

    # Collect errors/warnings from probe
    warnings = []
    limitations = []
    for err in probe_result.get("errors", []):
        if err.get("code") == "SHEET-INACCESSIBLE":
            warnings.append(
                f"stylesheet {err.get('sheet_index')} inaccessible: "
                f"{err.get('error')}"
            )
        elif err.get("code") == "CSSOM-ERROR":
            limitations.append(
                f"CSSOM error: {err.get('error')}"
            )
    if not probe_result.get("cssom_accessible", False):
        limitations.append("CSSOM not accessible — cannot inspect @page rules")
    if probe_result.get("total_page_rules", 0) == 0:
        if probe_result.get("cssom_accessible", False):
            limitations.append("no @page rules found in accessible stylesheets")
        else:
            limitations.append("could not determine if @page rules exist")

    # Determine status
    status, status_reason = _determine_margin_status(
        probe_result, expected_margins_mm, tolerance_mm, declared)

    evidence = {
        "check_id": "margin-verification",
        "status": status,
        "status_reason": status_reason,
        "profile_id": None,
        "expected_page_size": None,
        "expected_margins_mm": expected_margins_mm,
        "declared_page_rules": declared,
        "observed_values": observed,
        "tolerance_mm": tolerance_mm,
        "verification_method": "cssom" if probe_result.get(
            "cssom_accessible", False) else "none",
        "limitations": limitations,
        "warnings": warnings,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_version": TOOL_VERSION,
    }
    return evidence


def _determine_margin_status(probe_result, expected_margins_mm,
                             tolerance_mm, declared) -> tuple:
    """Determine PASS/FAIL/PARTIAL/NOT_VERIFIABLE/BLOCKED for margin check.

    Returns (status, reason_string).
    """
    cssom_accessible = probe_result.get("cssom_accessible", False)
    total_rules = probe_result.get("total_page_rules", 0)
    total_errors = probe_result.get("total_errors", 0)

    if not cssom_accessible:
        return ("NOT_VERIFIABLE",
                "CSSOM not accessible — cannot inspect @page rules")

    if total_rules == 0 and total_errors > 0:
        return ("BLOCKED",
                "all stylesheets inaccessible — cannot verify margins")

    if total_rules == 0:
        if expected_margins_mm:
            return ("FAIL",
                    "no @page rules found — expected margins not declared")
        return ("PASS",
                "no @page rules found — no margin expectations to verify")

    # @page rules exist; compare against expected
    if not expected_margins_mm:
        return ("PASS",
                f"{total_rules} @page rule(s) found — no profile expectations "
                "to compare against")

    # Check each expected margin side against declared values
    mismatch_details = []
    matched_sides = set()
    for pr in probe_result.get("page_rules", []):
        for prop, val in pr.get("margin", {}).items():
            val_mm = val.get("value_mm")
            if val_mm is None:
                continue
            # Map CSS property to expected side
            side = _prop_to_side(prop)
            if side and side in expected_margins_mm:
                expected_val = expected_margins_mm[side]
                diff = abs(val_mm - expected_val)
                matched_sides.add(side)
                if diff <= tolerance_mm:
                    continue  # match
                mismatch_details.append(
                    f"{prop}: declared {val_mm}mm vs expected "
                    f"{expected_val}mm (diff {diff:.2f}mm, tolerance "
                    f"{tolerance_mm}mm)"
                )

    # Check if all expected sides are covered
    expected_sides = set(expected_margins_mm.keys())
    missing_sides = expected_sides - matched_sides

    if missing_sides:
        return ("PARTIAL",
                f"margins not fully declared: missing "
                f"{', '.join(sorted(missing_sides))}; "
                f"{'; '.join(mismatch_details) if mismatch_details else ''}")

    if mismatch_details:
        return ("FAIL",
                f"margin mismatch: {'; '.join(mismatch_details)}")

    return ("PASS",
            f"all {len(expected_sides)} margin side(s) match expected values "
            f"(tolerance {tolerance_mm}mm)")


def _prop_to_side(prop: str) -> str | None:
    """Map a CSS margin property to a side name."""
    mapping = {
        "margin-top": "top",
        "margin-right": "right",
        "margin-bottom": "bottom",
        "margin-left": "left",
        "margin": "all",
    }
    return mapping.get(prop)


def check_print(r, expected_pages=(1, 1), expected_orient="portrait",
                expected_size_cm=None):
    """Verify print geometry via printToPDF.

    Returns list of issues if print output deviates from expectations.
    A4 portrait = 595.28 x 841.92 pt.
    """
    issues = []
    try:
        pdf_data = r.send("Page.printToPDF", {
            "preferCSSPageSize": True,
            "printBackground": True
        })
        data = base64.b64decode(pdf_data["data"])
        pages, w, h = pdf_facts(data)

        lo, hi = expected_pages
        if not lo <= pages <= hi:
            issues.append({
                "t": "PRN/PAGES",
                "det": f"page count {pages} not in expected range [{lo},{hi}]",
                "conf": 0.98
            })

        if expected_orient == "portrait":
            if not (590 <= w <= 600 and 837 <= h <= 847):
                issues.append({
                    "t": "PRN/ORIENT",
                    "det": f"not A4 portrait ({w:.1f}x{h:.1f}pt)",
                    "conf": 0.98
                })
        elif expected_orient == "landscape":
            if not (837 <= w <= 847 and 590 <= h <= 600):
                issues.append({
                    "t": "PRN/ORIENT",
                    "det": f"not A4 landscape ({w:.1f}x{h:.1f}pt)",
                    "conf": 0.98
                })

        if expected_size_cm:
            cw, ch = expected_size_cm
            if abs(w - cw * PT_PER_CM) > 3 or abs(h - ch * PT_PER_CM) > 3:
                issues.append({
                    "t": "PRN/SIZE",
                    "det": f"not {cw}x{ch}cm ({w:.1f}x{h:.1f}pt)",
                    "conf": 0.98
                })

    except Exception as e:
        issues.append({
            "t": "PRN-CHECK-ERROR",
            "det": f"could not verify print output: {str(e)[:200]}",
            "conf": 0.5
        })
    return issues


def pdf_facts(data: bytes):
    """Extract page count and MediaBox from PDF bytes."""
    pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
    boxes = re.findall(
        rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", data)
    w, h = (float(boxes[-1][2]), float(boxes[-1][3])) if boxes else (0.0, 0.0)
    return pages, w, h


# ----------------------------------------------------------------------
# Main run()
# ----------------------------------------------------------------------
def run(targets, port: int = 9400, root: str | None = None,
        json_path: str | None = None, headed: bool = False,
        do_print: bool = False,
        print_pages: tuple = (1, 1), print_orient: str = "portrait",
        print_size_cm: tuple | None = None,
        profile: dict | None = None, do_margin_check: bool = False,
        margin_tolerance_mm: float = 0.5):
    """Geometry audit of html/svg file targets.

    Returns (report: list[dict], dirty: int).
    """
    targets = collect([Path(t) for t in targets])
    layout_js = (PROBES / "layout_probe.js").read_text(encoding="utf-8")
    svg_js = (PROBES / "svg_probe.js").read_text(encoding="utf-8")
    margin_probe_js = (PROBES / "page_margin_probe.js").read_text(
        encoding="utf-8")

    # Resolve expected margins from profile if margin check requested
    expected_margins_mm = None
    profile_id = None
    expected_page_size = None
    if profile:
        profile_id = profile.get("profile_id")
        expected_margins_mm = profile_expected_margins_mm(profile)
        expected_page_size = profile_page_size(profile)
        if expected_margins_mm is None and do_margin_check:
            # No margins in profile — still run check but report no expectations
            pass

    report, dirty = [], 0
    with CDPRunner(port=port, headless=not headed) as r:
        for f in targets:
            r.goto(f.resolve().as_uri())
            entry = {"file": str(f), "issues": []}

            if f.suffix.lower() == ".svg":
                out = r.run_probe(svg_js, {})
                out = out or {}
                if out.get("issues"):
                    dirty += 1
                entry["issues"].extend(out.get("issues", []))
                if out.get("viewBox"):
                    entry["meta"] = ('svg viewBox {0}, texts={1}'.format(
                        out["viewBox"], out.get("nText", 0)))
            else:
                # HTML: run layout probe
                out = r.run_probe(layout_js, {"root": root} if root else {})
                out = out or {}
                if out.get("issues"):
                    dirty += 1
                entry["issues"].extend(out.get("issues", []))

                # Run svg_probe on inline SVGs
                inline_svg_results = run_probe_on_inline_svg(r, svg_js)
                for svr in inline_svg_results:
                    if svr.get("issues"):
                        dirty += 1
                    for iss in svr.get("issues", []):
                        iss["source"] = f"inline-svg-{svr.get('svg_index', 0)}"
                    entry["issues"].extend(svr.get("issues", []))

                # Meta info
                if out.get("root"):
                    s = out["root"]
                    entry["meta"] = ('root {0}x{1}, {2} figs, {3} imgs, {4} svgs'.format(
                        s["w"], s["h"], out.get("nFigs", 0),
                        out.get("nImgs", 0), out.get("nSvgs", 0)))
                    entry["root"] = s

                # Margin verification: CSSOM-based (primary authority)
                margin_evidence = None
                if do_margin_check:
                    margin_evidence = check_page_margins_via_cssom(
                        r, expected_margins_mm, margin_tolerance_mm)
                    margin_evidence["profile_id"] = profile_id
                    margin_evidence["expected_page_size"] = expected_page_size
                    entry["issues"].append({
                        "t": "MARGIN-VERIFICATION",
                        "det": f"margin status: {margin_evidence['status']} — "
                               f"{margin_evidence['status_reason']}",
                        "conf": 0.9,
                        "evidence": margin_evidence,
                    })
                    if margin_evidence["status"] in ("FAIL", "BLOCKED"):
                        dirty += 1

                # Print check via printToPDF
                if do_print:
                    print_issues = check_print(
                        r, expected_pages=print_pages,
                        expected_orient=print_orient,
                        expected_size_cm=print_size_cm)
                    if print_issues:
                        entry["issues"].extend(print_issues)

            report.append(entry)

    if json_path and report:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2),
                                   encoding="utf-8")
    return report, dirty


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--root", help="CSS selector for the layout root")
    ap.add_argument("--port", type=int, default=9400)
    ap.add_argument("--json", help="write full evidence to this file")
    ap.add_argument("--headed", action="store_true",
                    help="show the browser window (default: headless)")
    ap.add_argument("--profile", help="project profile JSON file")
    ap.add_argument("--margin-check", action="store_true",
                    help="run CSS @page margin verification via CSSOM")
    ap.add_argument("--margin-tolerance-mm", type=float, default=0.5,
                    help="margin tolerance in mm (default: 0.5)")
    ap.add_argument("--print", action="store_true",
                    help="run printToPDF page geometry check")
    ap.add_argument("--print-pages", nargs=2, type=int, default=[1, 1],
                    metavar=("MIN", "MAX"),
                    help="expected page count range (default: 1 1)")
    ap.add_argument("--print-orient", choices=["portrait", "landscape"],
                    default="portrait", help="expected orientation (default: portrait)")
    ap.add_argument("--print-size-cm", nargs=2, type=float, metavar=("W", "H"),
                    help="expected page size in cm (e.g., 21 29.7 for A4)")
    a = ap.parse_args()

    profile = load_profile(a.profile)
    print_size = tuple(a.print_size_cm) if a.print_size_cm else None

    report, dirty = run(a.targets, port=a.port, root=a.root,
                        json_path=a.json, headed=a.headed,
                        do_print=a.print,
                        print_pages=tuple(a.print_pages),
                        print_orient=a.print_orient,
                        print_size_cm=print_size,
                        profile=profile,
                        do_margin_check=a.margin_check,
                        margin_tolerance_mm=a.margin_tolerance_mm)

    for entry in report:
        n = len(entry.get("issues", []))
        meta = f"  {entry['meta']}" if entry.get("meta") else ""
        print(("!! " if n else "OK ") + entry["file"] + meta)
        for iss in entry.get("issues", []):
            det = iss.get("det", "")
            if iss.get("evidence"):
                ev = iss["evidence"]
                det += f" [status={ev.get('status')}, method={ev.get('verification_method')}]"
            print(f"     - [{iss.get('t')} conf {iss.get('conf', 0):.2f}] "
                  f"{det}")

    if a.json:
        print(f"\nevidence written: {a.json}")
    print(f"\nTARGETS: {len(report)}  DIRTY: {dirty}")
    sys.exit(min(dirty, 1))


if __name__ == "__main__":
    main()
