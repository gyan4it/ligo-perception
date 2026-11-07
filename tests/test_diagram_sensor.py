#!/usr/bin/env python3
"""test_diagram_sensor.py — unit tests for diagram_sensor tool.

Tests:
- Diagram bounds detection
- Crop detection
- Line art density
- Arrow/connector detection
- Text-to-shape proximity
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from diagram_sensor import analyze_diagram, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_line_art_diagram():
    """Test diagram analysis on line art image."""
    result = analyze_diagram(FIXTURES / "line_art.png")
    assert result is not None
    assert "diagram_bounds" in result
    assert "crop_detection" in result
    assert "line_art_density" in result
    assert "arrow_connector" in result
    assert "text_proximity" in result
    print("  PASS: test_line_art_diagram")


def test_clean_image_diagram():
    """Test diagram analysis on clean image."""
    result = analyze_diagram(FIXTURES / "clean.png")
    assert result is not None
    lad = result["line_art_density"]
    assert "edge_density_pct" in lad
    assert lad["edge_density_pct"] >= 0
    print("  PASS: test_clean_image_diagram")


def test_diagram_bounds():
    """Test diagram bounds detection."""
    result = analyze_diagram(FIXTURES / "line_art.png")
    bounds = result["diagram_bounds"]
    assert "width" in bounds
    assert "height" in bounds
    print("  PASS: test_diagram_bounds")


def test_line_art_density():
    """Test line art density calculation."""
    result = analyze_diagram(FIXTURES / "line_art.png")
    lad = result["line_art_density"]
    assert "edge_pixel_count" in lad
    assert "edge_density_pct" in lad
    print("  PASS: test_line_art_density")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "line_art.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "line_art.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_diagram_sensor.py ===")
    test_line_art_diagram()
    test_clean_image_diagram()
    test_diagram_bounds()
    test_line_art_density()
    test_run_function()
    print("=== test_diagram_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
