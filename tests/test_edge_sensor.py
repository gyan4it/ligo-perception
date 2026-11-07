#!/usr/bin/env python3
"""test_edge_sensor.py — unit tests for edge_sensor tool.

Tests:
- Edge detection on line art
- Edge density measurement
- Hough line detection
- Contour detection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from edge_sensor import analyze_edges, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_line_art_edges():
    """Test edge detection on line art image."""
    result = analyze_edges(FIXTURES / "line_art.png")
    assert result is not None
    assert result["canny"]["edge_density_pct"] > 0
    assert result["sobel"]["mean_gradient_magnitude"] > 0
    print("  PASS: test_line_art_edges")


def test_clean_image_no_edges():
    """Test edge detection on clean image (no edges expected)."""
    result = analyze_edges(FIXTURES / "clean.png")
    assert result is not None
    # Clean image should have very few edges
    assert result["canny"]["edge_density_pct"] < 5.0
    print("  PASS: test_clean_image_no_edges")


def test_canny_edge_density():
    """Test Canny edge density calculation."""
    result = analyze_edges(FIXTURES / "line_art.png")
    canny = result["canny"]
    assert "edge_pixel_count" in canny
    assert "edge_density_pct" in canny
    assert canny["edge_density_pct"] >= 0
    print("  PASS: test_canny_edge_density")


def test_sobel_gradients():
    """Test Sobel gradient computation."""
    result = analyze_edges(FIXTURES / "line_art.png")
    sobel = result["sobel"]
    assert "mean_gradient_magnitude" in sobel
    assert "max_gradient_magnitude" in sobel
    assert sobel["mean_gradient_magnitude"] > 0
    print("  PASS: test_sobel_gradients")


def test_hough_lines():
    """Test Hough line detection."""
    result = analyze_edges(FIXTURES / "line_art.png")
    hough = result["hough_lines"]
    assert "line_count" in hough
    assert "lines" in hough
    print("  PASS: test_hough_lines")


def test_contours():
    """Test contour extraction."""
    result = analyze_edges(FIXTURES / "line_art.png")
    contours = result["contours"]
    assert "contour_count" in contours
    assert "total_contour_area" in contours
    print("  PASS: test_contours")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "line_art.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "line_art.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_edge_sensor.py ===")
    test_line_art_edges()
    test_clean_image_no_edges()
    test_canny_edge_density()
    test_sobel_gradients()
    test_hough_lines()
    test_contours()
    test_run_function()
    print("=== test_edge_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
