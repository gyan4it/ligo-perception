#!/usr/bin/env python3
"""test_similarity_sensor.py — unit tests for similarity_sensor tool.

Tests:
- Image similarity (MSE, similarity percentage)
- OCR text extraction (via OCR adapter)
- Similarity between similar images
- Similarity between different images
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from similarity_sensor import analyze_similarity, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_similarity_same_image():
    """Test similarity between identical images."""
    result = analyze_similarity(FIXTURES / "duplicate_pair_1.png", FIXTURES / "duplicate_pair_1.png")
    assert result is not None
    pdiff = result["pixel_difference"]
    assert pdiff["similarity_pct"] > 99  # Same image should be very similar
    print("  PASS: test_similarity_same_image")


def test_similarity_different_image():
    """Test similarity between different images."""
    result = analyze_similarity(FIXTURES / "clean.png", FIXTURES / "line_art.png")
    assert result is not None
    pdiff = result["pixel_difference"]
    assert pdiff["similarity_pct"] < 99  # Different images should be less similar
    print("  PASS: test_similarity_different_image")


def test_near_duplicate_pair():
    """Test similarity between near-duplicate pair."""
    result = analyze_similarity(FIXTURES / "duplicate_pair_1.png", FIXTURES / "duplicate_pair_2.png")
    assert result is not None
    pdiff = result["pixel_difference"]
    # Near-duplicate images should have high similarity
    assert pdiff["similarity_pct"] > 50
    print("  PASS: test_near_duplicate_pair")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([FIXTURES / "clean.png", FIXTURES / "line_art.png"],
                        [FIXTURES / "clean.png", FIXTURES / "line_art.png"])
    assert len(report) == 2
    assert report[0]["file1"] == str(FIXTURES / "clean.png")
    assert report[0]["file2"] == str(FIXTURES / "clean.png")
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_similarity_sensor.py ===")
    test_similarity_same_image()
    test_similarity_different_image()
    test_near_duplicate_pair()
    test_run_function()
    print("=== test_similarity_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
