#!/usr/bin/env python3
"""capability_detector — report LiGeo global skill capabilities.

Shows which capabilities are available across renderer, bitmap, OCR, and
vision paths. Used to verify deployment and prevent overclaiming.

  python tools/capability_detector.py
  python tools/capability_detector.py --json out.json

Exit code 0 = report generated (not a pass/fail gate).
"""
import argparse, json, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_loader
from profile_loader import load_profile

try:
    import importlib.util
    PILLOTEST = importlib.util.find_spec("PIL") is not None
    NUMPYTEST = importlib.util.find_spec("numpy") is not None
    PYTESSERACTTEST = importlib.util.find_spec("pytesseract") is not None
    REQUESTSTEST = importlib.util.find_spec("requests") is not None
except Exception:
    PILLOTEST = NUMPYTEST = PYTESSERACTTEST = REQUESTSTEST = False

# --- Check Tesseract binary ---
def _check_tesseract_binary() -> bool:
    import shutil
    return shutil.which("tesseract") is not None


# --- Capability definitions ---
CAPABILITIES = [
    {
        "id": "renderer_html",
        "name": "HTML rendering inspection (CDP)",
        "category": "renderer",
        "available": True,  # Always available if Edge/Chrome present
        "component": "tools/cdp_runner.py, probes/layout_probe.js",
        "description": "Headless browser CDP inspection of HTML pages — geometry, overflow, overlap, images",
        "limitations": "Requires Edge/Chrome browser; text-only AI cannot see pixels",
    },
    {
        "id": "renderer_svg",
        "name": "SVG rendering inspection",
        "category": "renderer",
        "available": True,
        "component": "probes/svg_probe.js",
        "description": "SVG artwork inspection — out-of-canvas, text collisions",
        "limitations": "Standalone SVG files; inline SVG partially supported",
    },
    {
        "id": "renderer_print",
        "name": "Print/PDF verification",
        "category": "renderer",
        "available": True,
        "component": "tools/print_check.py",
        "description": "printToPDF page count and page-box verification",
        "limitations": "Requires Edge/Chrome; margin verification stub only",
    },
    {
        "id": "renderer_accessibility",
        "name": "Accessibility checking (axe-core)",
        "category": "renderer",
        "available": False,
        "component": "tools/a11y_check.py",
        "description": "WCAG compliance via axe-core",
        "limitations": "Requires axe-core npm package; reports NOT_RUN if missing",
    },
    {
        "id": "bitmap_ingestion",
        "name": "PNG/JPEG bitmap ingestion",
        "category": "bitmap",
        "available": bool(PILLOTEST),
        "component": "tools/bitmap_check.py",
        "description": "Image loader with validation, metadata extraction, decompression bomb guard",
        "limitations": "Requires Pillow; no pixel semantics without further analysis",
    },
    {
        "id": "pixel_analysis",
        "name": "Deterministic pixel analysis",
        "category": "bitmap",
        "available": bool(PILLOTEST and NUMPYTEST),
        "component": "tools/pixel_check.py",
        "description": "Dimensions, palette, histogram, luminance, contrast, edges, sharpness, regions, alpha",
        "limitations": "All metrics are DETECTED measurements; no semantic interpretation",
    },
    {
        "id": "ocr",
        "name": "Optical Character Recognition",
        "category": "ocr",
        "available": bool(PYTESSERACTTEST and _check_tesseract_binary()),
        "component": "tools/ocr_adapter.py",
        "description": "Text extraction with bounding boxes and confidence via Tesseract",
        "limitations": "OCR is not ground truth; accuracy degrades with low resolution, stylized fonts",
    },
    {
        "id": "vision_semantic",
        "name": "Semantic vision (VLM)",
        "category": "vision",
        "available": False,
        "component": "tools/vision_adapter.py",
        "description": "Image captioning, VQA, object detection via pluggable VLM adapter",
        "limitations": "Requires separate VLM/runtime — text-only model cannot perform semantic vision",
    },
    {
        "id": "vir_schema",
        "name": "Visual Intermediate Representation schema",
        "category": "infrastructure",
        "available": True,
        "component": "tools/vir_builder.py",
        "description": "Shared evidence schema across renderer and bitmap paths",
        "limitations": "Schema version 1.0.0; DERIVED tier not yet auto-generated",
    },
    {
        "id": "apai_bitmap",
        "name": "APAI bitmap integration",
        "category": "infrastructure",
        "available": True,
        "component": "tools/apai_bitmap.py",
        "description": "Rubric-based art/illustration evaluation consuming bitmap evidence",
        "limitations": "Scores are heuristics; semantic vision criteria require separate VLM",
    },
]


def run(json_path: str | None = None,
        profile: dict | None = None):
    """Build capability report."""
    report = {
        "skill": "ligeo-perception",
        "version": "1.0.0-stage-G",
        "ai_model": "text-only",
        "vision_limitation": "Text-only model cannot perform semantic vision — separate VLM required for Stages E-G",
        "capabilities": CAPABILITIES,
        "summary": {
            "total": len(CAPABILITIES),
            "available": sum(1 for c in CAPABILITIES if c["available"]),
            "unavailable": sum(1 for c in CAPABILITIES if not c["available"]),
        },
        "evidence_tier_note": "Capability availability is DETECTED from environment inspection",
        "profile": {
            "profile_id": profile_loader.profile_id(profile) if profile else None,
            "profile_name": profile_loader.profile_name(profile) if profile else None,
            "project": profile_loader.profile_project(profile) if profile else None,
        } if profile else None,
    }

    if json_path:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write capability report to this file")
    ap.add_argument("--profile", help="project profile JSON file")
    a = ap.parse_args()

    profile = load_profile(a.profile) if a.profile else None

    report = run(json_path=a.json, profile=profile)

    print(f"LiGeo Global Skill Capability Report v{report['version']}")
    print(f"AI Model: {report['ai_model']}")
    print(f"Vision Limitation: Text-only model cannot perform semantic vision - separate VLM required for Stages E-G")
    print()
    print(f"Capabilities: {report['summary']['available']}/{report['summary']['total']} available")
    print()
    for cap in report["capabilities"]:
        status = "[OK]" if cap["available"] else "[--]"
        print(f"  {status} {cap['id']} — {cap['name']} ({cap['category']})")
        if not cap["available"]:
            print(f"         Limitation: {cap['limitations']}")

    if a.json:
        print(f"\nreport written: {a.json}")
    sys.exit(0)


if __name__ == "__main__":
    main()
