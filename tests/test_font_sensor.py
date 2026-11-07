#!/usr/bin/env python3
"""test_font_sensor.py — unit tests for font_sensor tool.

Tests:
- Font metrics extraction from image
- Text density calculation
- Estimated font size
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from font_sensor import analyze_fonts, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_text_image_font():
    """Test font analysis on text image."""
    result = analyze_fonts(FIXTURES / "text_image.png")
    assert result is not None
    assert "text_density" in result
    assert "estimated_font_size" in result
    print("  PASS: test_text_image_font")


def test_clean_image_font():
    """Test font analysis on clean image."""
    result = analyze_fonts(FIXTURES / "clean.png")
    assert result is not None
    assert "text_density" in result
    print("  PASS: test_clean_image_font")


def test_text_density_metrics():
    """Test text density metrics."""
    result = analyze_fonts(FIXTURES / "text_image.png")
    td = result["text_density"]
    assert "edge_pixel_pct" in td
    assert "text_band_count" in td
    assert td["edge_pixel_pct"] >= 0
    print("  PASS: test_text_density_metrics")


def test_estimated_font_size():
    """Test estimated font size."""
    result = analyze_fonts(FIXTURES / "text_image.png")
    fs = result["estimated_font_size"]
    assert "estimated_font_size_px" in fs
    assert fs["estimated_font_size_px"] >= 0
    print("  PASS: test_estimated_font_size")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "text_image.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "text_image.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_font_sensor.py ===")
    test_text_image_font()
    test_clean_image_font()
    test_text_density_metrics()
    test_estimated_font_size()
    test_run_function()
    print("=== test_font_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
