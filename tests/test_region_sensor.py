#!/usr/bin/env python3
"""test_region_sensor.py — unit tests for region_sensor tool.

Tests:
- Threshold-based foreground detection
- Connected component analysis
- Morphological gradient
- Color clustering
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from region_sensor import analyze_regions, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_clean_image_regions():
    """Test region analysis on clean image."""
    result = analyze_regions(FIXTURES / "clean.png")
    assert result is not None
    assert "threshold" in result
    assert "components" in result
    assert "morphology" in result
    assert "color_clusters" in result
    print("  PASS: test_clean_image_regions")


def test_line_art_regions():
    """Test region analysis on line art image."""
    result = analyze_regions(FIXTURES / "line_art.png")
    assert result is not None
    assert result["components"]["component_count"] > 0
    print("  PASS: test_line_art_regions")


def test_threshold_stats():
    """Test threshold statistics."""
    result = analyze_regions(FIXTURES / "line_art.png")
    thresh = result["threshold"]
    assert "foreground_pixel_count" in thresh
    assert "foreground_pct" in thresh
    print("  PASS: test_threshold_stats")


def test_connected_components():
    """Test connected component analysis."""
    result = analyze_regions(FIXTURES / "line_art.png")
    comps = result["components"]
    assert "component_count" in comps
    assert comps["component_count"] >= 0
    print("  PASS: test_connected_components")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "line_art.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "line_art.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_region_sensor.py ===")
    test_clean_image_regions()
    test_line_art_regions()
    test_threshold_stats()
    test_connected_components()
    test_run_function()
    print("=== test_region_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
