#!/usr/bin/env python3
"""test_geometry_sensor.py — unit tests for geometry_sensor tool.

Tests:
- Border detection
- Content centroid/alignment
- Rectangular contour detection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from geometry_sensor import analyze_geometry, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_line_art_geometry():
    """Test geometry analysis on line art image."""
    result = analyze_geometry(FIXTURES / "line_art.png")
    assert result is not None
    assert "border" in result
    assert "alignment" in result
    assert "geometry" in result
    assert result["alignment"]["content_px_count"] > 0
    print("  PASS: test_line_art_geometry")


def test_clean_image_geometry():
    """Test geometry analysis on clean image."""
    result = analyze_geometry(FIXTURES / "clean.png")
    assert result is not None
    # Clean image is solid color, so content fills the image
    assert result["alignment"]["content_px_count"] > 0
    assert result["alignment"]["content_px_count"] <= 40000  # 200x200 = 40000
    print("  PASS: test_clean_image_geometry")


def test_border_detection():
    """Test border detection."""
    result = analyze_geometry(FIXTURES / "line_art.png")
    border = result["border"]
    assert "border_mean_intensity" in border
    assert "border_std_intensity" in border
    print("  PASS: test_border_detection")


def test_rect_contours():
    """Test geometry detection on line art image."""
    result = analyze_geometry(FIXTURES / "line_art.png")
    geom = result["geometry"]
    assert "rectangular_contour_count" in geom
    assert "rect_contour_areas" in geom
    # Line art may or may not have rectangular contours depending on line thickness
    assert isinstance(geom["rectangular_contour_count"], int)
    print("  PASS: test_rect_contours")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "line_art.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "line_art.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_geometry_sensor.py ===")
    test_line_art_geometry()
    test_clean_image_geometry()
    test_border_detection()
    test_rect_contours()
    test_run_function()
    print("=== test_geometry_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
