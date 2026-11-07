#!/usr/bin/env python3
"""test_quality_sensor.py — unit tests for quality_sensor tool.

Tests:
- Luminance metrics
- Sharpness (Laplacian variance)
- Edge density
- Clipping detection
- Saturation statistics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from quality_sensor import analyze_quality, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_clean_image_quality():
    """Test quality metrics on clean image."""
    result = analyze_quality(FIXTURES / "clean.png")
    assert result is not None
    assert "luminance" in result
    assert "sharpness" in result
    assert "edge_density" in result
    assert "clipping" in result
    assert "saturation" in result
    print("  PASS: test_clean_image_quality")


def test_low_contrast_quality():
    """Test quality metrics on low contrast image."""
    result = analyze_quality(FIXTURES / "low_contrast.png")
    assert result is not None
    assert result["contrast"]["michelson"] < 0.5
    print("  PASS: test_low_contrast_quality")


def test_line_art_sharpness():
    """Test sharpness on line art image."""
    result = analyze_quality(FIXTURES / "line_art.png")
    assert result is not None
    assert result["sharpness"]["laplacian_variance"] > 0
    print("  PASS: test_line_art_sharpness")


def test_clipping_detection():
    """Test clipping detection."""
    result = analyze_quality(FIXTURES / "line_art.png")
    assert "clipped_low_pct" in result["clipping"]
    assert "clipped_high_pct" in result["clipping"]
    print("  PASS: test_clipping_detection")


def test_saturation_stats():
    """Test saturation statistics."""
    result = analyze_quality(FIXTURES / "clean.png")
    assert "sat_mean" in result["saturation"]
    assert "sat_std" in result["saturation"]
    print("  PASS: test_saturation_stats")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "clean.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "clean.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_quality_sensor.py ===")
    test_clean_image_quality()
    test_low_contrast_quality()
    test_line_art_sharpness()
    test_clipping_detection()
    test_saturation_stats()
    test_run_function()
    print("=== test_quality_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
