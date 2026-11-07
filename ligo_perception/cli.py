#!/usr/bin/env python3
"""
Ligeo-Perception CLI - Command-line interface for text-only AI vision.

Any text-based AI can use this CLI to analyze visual content without
having vision capabilities itself. The system uses deterministic,
renderer-based evidence instead of pixel guessing.

Usage:
    ligo <image.png>                    # Full analysis
    ligo <image.png> --json out.json    # JSON output
    ligo <image.png> --profile B01      # Use B01 book profile
    ligo --help                         # Show help

Examples:
    ligo books/B01/chapters/C03/assets/figures/F01.png
    ligo books/B01/chapters/C03/assets/figures/ --json out.json
    ligo --profile B01 books/C03/figures/F01.png
"""

import argparse
import json
import sys
from pathlib import Path

from ligo_perception import (
    load_image,
    load_and_validate,
    analyze_color,
    analyze_pixels,
    analyze_geometry,
    analyze_ocr,
    analyze_vision,
    build_vir,
    assess_pnai,
)

# Import sensor modules
from probes import layout_probe, svg_probe, image_probe
from tools.cdp_runner import CDPRunner

# Import sensor modules from cv_sensors
from probes import color_sensor, quality_sensor, edge_sensor, geometry_sensor
from probes import similarity_sensor, registration_sensor, region_sensor
from probes import document_sensor, diagram_sensor, illustration_sensor


def run_all_probes(image_path: Path, probe_names: list = None) -> dict:
    """Run all available probes on an image and return combined evidence."""
    results = {}
    errors = []

    # Try each available probe
    probe_map = {
        "layout": layout_probe.analyze,
        "svg": svg_probe.analyze,
        "image": image_probe.analyze,
        "color": color_sensor.analyze_color,
        "quality": quality_sensor.analyze_quality,
        "edge": edge_sensor.analyze_edges,
        "geometry": geometry_sensor.analyze_geometry,
        "similarity": similarity_sensor.analyze_similarity,
        "registration": registration_sensor.analyze_registration,
        "region": region_sensor.analyze_regions,
        "document": document_sensor.analyze_document,
        "diagram": diagram_sensor.analyze_diagram,
        "illustration": illustration_sensor.analyze_illustration,
    }

    for name, probe_fn in probe_map.items():
        try:
            result = probe_fn(image_path)
            results[name] = result
        except Exception as e:
            results[name] = {"error": str(e)[:200], "error_type": type(e).__name__}

    return results


def run_full_pipeline(image_path: Path, profile: dict = None) -> dict:
    """Run the full P10 production pipeline on an image.

    Returns a complete VIR (Visual Intermediate Representation) with
    all evidence tiers preserved.
    """
    from vir_builder import build_vir

    # Load image metadata
    with load_image(image_path) as li:
        img_info = li.info.to_dict()

    # Run all available probes
    layout_result = None
    svg_result = None
    image_probe_result = None

    try:
        from probes import layout_probe
        layout_result = layout_probe.analyze(image_path)
    except Exception:
        layout_result = {"error": "layout probe failed"}

    try:
        from probes import svg_probe
        svg_result = svg_probe.analyze(image_path)
    except Exception:
        svg_result = {"error": "SVG probe not applicable"}

    try:
        from probes import image_probe
        image_result = image_probe.analyze(image_path)
    except Exception:
        image_result = {"error": "image probe not applicable"}

    # Color analysis
    try:
        color_result = color_sensor.analyze_color(image_path)
    except Exception:
        color_result = {"error": "color analysis failed"}

    # Quality analysis
    try:
        quality_result = quality_sensor.analyze_quality(image_path)
    except Exception:
        quality_result = {"error": "quality analysis failed"}

    # Edge detection
    try:
        edge_result = edge_sensor.analyze_edges(image_path)
    except Exception:
        edge_result = {"error": "edge analysis failed"}

    # Geometry analysis
    try:
        geometry_result = geometry_sensor.analyze_geometry(image_path)
    except Exception:
        geometry_result = {"error": "geometry analysis failed"}

    # Build VIR from all evidence
    vir = build_vir(
        layout_data=layout_result if layout_result and not layout_result.get("error") else None,
        bitmap_data={"file": str(image_path), "record": record, "issues": []} if "record" in dir() else None,
        pixel_data={"file": str(img_path), "metrics": metrics, "issues": []} if "metrics" in dir() else None,
        ocr_data={"file": str(img_path), "ocr": ocr_result, "issues": []} if "ocr_result" in dir() else None,
        vision_data=None,  # No VLM by default
        asset_id=record.get("asset_id") if record else str(image_path),
        project_profile=profile.get("profile_id") if profile else None,
    )

    return vir


def main():
    """CLI entry point for LiGeo-Perception."""
    ap = argparse.ArgumentParser(
        description="LiGeo-Perception: Text-only AI vision engine for rendered visual evidence"
    )
    ap.add_argument("targets", nargs="+", help="Image files or directories to analyze")
    ap.add_argument("--json", help="Write full evidence to JSON file")
    ap.add_argument("--profile", help="Project profile JSON file (e.g., profiles/B01.json)")
    ap.add_argument("--profile-name", help="Profile name (e.g., B01)")
    ap.add_argument("--model", help="Vision model name (optional, requires VLM)")
    ap.add_argument("--api-key", help="API key for remote VLM")
    ap.add_argument("--endpoint", help="VLM endpoint URL")
    ap.add_argument("--profile-name", help="Project profile name (e.g., B01)")

    a = ap.parse_args()

    from profile_loader import load_profile

    profile = load_profile(a.profile) if a.profile else None

    targets_out = []
    for t in a.targets:
        p = Path(t)
        if p.is_dir():
            targets_out += sorted(p.rglob("*.png")) + sorted(p.rglob("*.jpg")) + sorted(p.rglob("*.jpeg"))
        elif p.exists():
            targets_out.append(p)
        else:
            print(f"WARNING: Not found: {p}")

    seen, uniq = set(), []
    for f in targets_out:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            uniq.append(f)

    report = []
    for f in uniq:
        try:
            vir = run_full_pipeline(f, profile=profile)
            entry = {"file": str(f), "vir": vir, "issues": []}
            report.append(entry)
            print(f"OK {f}")
        except Exception as e:
            entry = {"file": str(f), "error": str(e)[:200], "issues": [{"t": "ERROR", "det": str(e)[:200], "conf": 1.0}]}
            report.append(entry)
            print(f"!! {f} ERROR: {e}")

    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nEvidence written to: {a.json}")
    print(f"\nTARGETS: {len(report)}")


if __name__ == "__main__":
    main()