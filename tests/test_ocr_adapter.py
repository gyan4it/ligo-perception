#!/usr/bin/env python3
"""test_ocr_adapter.py — unit tests for ocr_adapter tool.

Tests:
- OCR on image with text
- OCR on image without text
- OCR availability check
- OCR confidence reporting
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from ocr_adapter import analyze_ocr, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_ocr_on_text_image():
    """Test OCR on image with text."""
    result = analyze_ocr(FIXTURES / "text_image.png")
    assert result is not None
    assert result["ocr_available"] is True
    assert result["ocr"]["engine"] == "tesseract"
    assert result["ocr"]["n_words"] > 0
    assert result["ocr"]["full_text"] != ""
    print("  PASS: test_ocr_on_text_image")


def test_ocr_on_clean_image():
    """Test OCR on clean image with no text."""
    result = analyze_ocr(FIXTURES / "clean.png")
    assert result is not None
    assert result["ocr_available"] is True
    # Clean image should have 0 words
    assert result["ocr"]["n_words"] == 0
    assert result["ocr"]["full_text"] == ""
    print("  PASS: test_ocr_on_clean_image")


def test_ocr_confidence_reporting():
    """Test that OCR reports confidence."""
    result = analyze_ocr(FIXTURES / "text_image.png")
    ocr = result["ocr"]
    assert "avg_confidence" in ocr
    assert isinstance(ocr["avg_confidence"], float)
    assert 0 <= ocr["avg_confidence"] <= 100
    print("  PASS: test_ocr_confidence_reporting")


def test_ocr_text_blocks():
    """Test that OCR returns text blocks with bounding boxes."""
    result = analyze_ocr(FIXTURES / "text_image.png")
    text_blocks = result["ocr"]["text_blocks"]
    assert len(text_blocks) > 0
    for block in text_blocks:
        assert "text" in block
        assert "left" in block
        assert "top" in block
        assert "width" in block
        assert "height" in block
        assert "conf" in block
    print("  PASS: test_ocr_text_blocks")


def test_ocr_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "text_image.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "text_image.png")
    assert "ocr" in report[0]
    print("  PASS: test_ocr_run_function")


def run_all():
    print("\n=== test_ocr_adapter.py ===")
    test_ocr_on_text_image()
    test_ocr_on_clean_image()
    test_ocr_confidence_reporting()
    test_ocr_text_blocks()
    test_ocr_run_function()
    print("=== test_ocr_adapter.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
