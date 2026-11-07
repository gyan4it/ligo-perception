#!/usr/bin/env python3
"""test_icc_sensor.py — unit tests for icc_sensor tool.

Tests:
- ICC profile detection
- Color space detection
- Bit depth detection
- Alpha channel detection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from icc_sensor import analyze_icc, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_png_color_profile():
    """Test ICC profile detection on PNG image."""
    result = analyze_icc(FIXTURES / "line_art.png")
    assert result is not None
    assert "image_mode" in result
    assert "color_space" in result
    assert "has_icc_profile" in result
    print("  PASS: test_png_color_profile")


def test_color_space_detection():
    """Test color space detection."""
    result = analyze_icc(FIXTURES / "line_art.png")
    assert result["color_space"] == "RGB"
    print("  PASS: test_color_space_detection")


def test_bit_depth():
    """Test bit depth detection."""
    result = analyze_icc(FIXTURES / "line_art.png")
    assert result["bit_depth"] == 24
    print("  PASS: test_bit_depth")


def test_alpha_channel():
    """Test alpha channel detection."""
    result = analyze_icc(FIXTURES / "line_art.png")
    assert "has_alpha" in result
    print("  PASS: test_alpha_channel")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "line_art.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "line_art.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_icc_sensor.py ===")
    test_png_color_profile()
    test_color_space_detection()
    test_bit_depth()
    test_alpha_channel()
    test_run_function()
    print("=== test_icc_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
