#!/usr/bin/env python3
"""test_illustration_sensor.py — unit tests for illustration_sensor tool.

Tests:
- Figure bounds detection
- Crop detection
- Contrast verification
- Whitespace ratio
- Placement detection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from illustration_sensor import analyze_illustration, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_line_art_illustration():
    """Test illustration analysis on line art image."""
    result = analyze_illustration(FIXTURES / "line_art.png")
    assert result is not None
    assert "bounds" in result
    assert "crop_detection" in result
    assert "fg_bg_contrast" in result
    print("  PASS: test_line_art_illustration")


def test_clean_image_illustration():
    """Test illustration analysis on clean image."""
    result = analyze_illustration(FIXTURES / "clean.png")
    assert result is not None
    assert result["bounds"]["fill_pct"] > 0
    print("  PASS: test_clean_image_illustration")


def test_bounds_detection():
    """Test illustration bounds detection."""
    result = analyze_illustration(FIXTURES / "line_art.png")
    bounds = result["bounds"]
    assert "width" in bounds
    assert "height" in bounds
    print("  PASS: test_bounds_detection")


def test_contrast_detection():
    """Test foreground/background contrast detection."""
    result = analyze_illustration(FIXTURES / "line_art.png")
    contrast = result["fg_bg_contrast"]
    assert "contrast_ratio" in contrast
    print("  PASS: test_contrast_detection")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "line_art.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "line_art.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_illustration_sensor.py ===")
    test_line_art_illustration()
    test_clean_image_illustration()
    test_bounds_detection()
    test_contrast_detection()
    test_run_function()
    print("=== test_illustration_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
