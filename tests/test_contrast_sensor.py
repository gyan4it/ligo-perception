#!/usr/bin/env python3
"""test_contrast_sensor.py — unit tests for contrast_sensor tool.

Tests:
- Contrast ratio calculation on low contrast image
- High contrast image detection
- WCAG level classification
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from contrast_sensor import analyze_contrast, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_low_contrast_image():
    """Test contrast analysis on low contrast image."""
    result = analyze_contrast(FIXTURES / "low_contrast.png")
    assert result is not None
    assert result["worst_ratio"] < 4.5
    assert result["low_contrast_count"] > 0
    print("  PASS: test_low_contrast_image")


def test_high_contrast_image():
    """Test contrast analysis on high contrast image (line art)."""
    result = analyze_contrast(FIXTURES / "line_art.png")
    assert result is not None
    assert "worst_ratio" in result
    assert "best_ratio" in result
    print("  PASS: test_high_contrast_image")


def test_worst_and_best_ratio():
    """Test that worst_ratio <= best_ratio."""
    result = analyze_contrast(FIXTURES / "line_art.png")
    assert result["worst_ratio"] <= result["best_ratio"]
    print("  PASS: test_worst_and_best_ratio")


def test_wcag_levels():
    """Test WCAG level reporting."""
    result = analyze_contrast(FIXTURES / "line_art.png")
    assert "worst_level_normal" in result
    assert "best_level_normal" in result
    assert "worst_level_large" in result
    assert "best_level_large" in result
    print("  PASS: test_wcag_levels")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "low_contrast.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "low_contrast.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_contrast_sensor.py ===")
    test_low_contrast_image()
    test_high_contrast_image()
    test_worst_and_best_ratio()
    test_wcag_levels()
    test_run_function()
    print("=== test_contrast_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
