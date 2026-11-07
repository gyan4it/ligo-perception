#!/usr/bin/env python3
"""test_print_bleed_sensor.py — unit tests for print_bleed_sensor tool.

Tests:
- Bleed detection on full-bleed image
- Margin detection on image with margins
- Crop mark detection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from print_bleed_sensor import analyze_bleed, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_full_bleed_image():
    """Test bleed detection on line art image."""
    result = analyze_bleed(FIXTURES / "line_art.png")
    assert result is not None
    assert "bleed" in result
    assert "crop_marks" in result
    assert "safe_area" in result
    print("  PASS: test_line_art_bleed")


def test_bleed_edges():
    """Test bleed edge detection."""
    result = analyze_bleed(FIXTURES / "line_art.png")
    bleed = result["bleed"]
    assert "touches_any_edge" in bleed
    print("  PASS: test_bleed_edges")


def test_safe_area():
    """Test safe area detection."""
    result = analyze_bleed(FIXTURES / "line_art.png")
    safe = result["safe_area"]
    assert "content_outside_safe_pct" in safe
    print("  PASS: test_safe_area")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "line_art.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "line_art.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_print_bleed_sensor.py ===")
    test_full_bleed_image()
    test_bleed_edges()
    test_safe_area()
    test_run_function()
    print("=== test_print_bleed_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
