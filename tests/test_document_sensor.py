#!/usr/bin/env python3
"""test_document_sensor.py — unit tests for document_sensor tool.

Tests:
- Page dimensions detection
- Content bounding box
- Margin detection
- Skew detection
- Content density
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from document_sensor import analyze_document, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_clean_image_document():
    """Test document analysis on clean image."""
    result = analyze_document(FIXTURES / "clean.png")
    assert result is not None
    assert "page" in result
    assert "content_box" in result
    assert "margins" in result
    assert "skew" in result
    assert "content_density" in result
    print("  PASS: test_clean_image_document")


def test_line_art_document():
    """Test document analysis on line art image."""
    result = analyze_document(FIXTURES / "line_art.png")
    assert result is not None
    assert "page" in result
    print("  PASS: test_line_art_document")


def test_page_dimensions():
    """Test page dimension detection."""
    result = analyze_document(FIXTURES / "line_art.png")
    page = result["page"]
    assert "width_px" in page
    assert "height_px" in page
    assert page["width_px"] == 200
    assert page["height_px"] == 200
    print("  PASS: test_page_dimensions")


def test_content_bounding_box():
    """Test content bounding box detection."""
    result = analyze_document(FIXTURES / "line_art.png")
    box = result["content_box"]
    assert "x" in box
    assert "y" in box
    assert "width" in box
    assert "height" in box
    print("  PASS: test_content_bounding_box")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "line_art.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "line_art.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_document_sensor.py ===")
    test_clean_image_document()
    test_line_art_document()
    test_page_dimensions()
    test_content_bounding_box()
    test_run_function()
    print("=== test_document_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
