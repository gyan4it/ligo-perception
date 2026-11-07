#!/usr/bin/env python3
"""test_registration_sensor.py — unit tests for registration_sensor tool.

Tests:
- Image registration between similar images
- ECC correlation coefficient
- ORB feature matching
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from registration_sensor import analyze_registration, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_registration_same_image():
    """Test registration of identical images."""
    result = analyze_registration(FIXTURES / "line_art.png", FIXTURES / "line_art.png")
    assert result is not None
    ecc = result["ecc_alignment"]
    if "correlation_coefficient" in ecc:
        assert ecc["correlation_coefficient"] > 0.9  # Same image should correlate highly
    else:
        # ECC may fail for uniform images; check ORB features instead
        orb = result["orb_features"]
        assert orb["match_count"] > 0
    print("  PASS: test_registration_same_image")


def test_registration_different_image():
    """Test registration between different images."""
    result = analyze_registration(FIXTURES / "clean.png", FIXTURES / "line_art.png")
    assert result is not None
    ecc = result["ecc_alignment"]
    # Different images may or may not have valid ECC correlation
    if "correlation_coefficient" in ecc:
        assert isinstance(ecc["correlation_coefficient"], float)
    assert "orb_features" in result
    assert "match_count" in result["orb_features"]
    print("  PASS: test_registration_different_image")


def test_orb_features():
    """Test ORB feature detection."""
    result = analyze_registration(FIXTURES / "line_art.png", FIXTURES / "line_art.png")
    orb = result["orb_features"]
    assert "keypoints1" in orb
    assert "keypoints2" in orb
    assert "match_count" in orb
    print("  PASS: test_orb_features")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([FIXTURES / "clean.png"], [FIXTURES / "clean.png"])
    assert len(report) == 1
    assert report[0]["file1"] == str(FIXTURES / "clean.png")
    assert report[0]["file2"] == str(FIXTURES / "clean.png")
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_registration_sensor.py ===")
    test_registration_same_image()
    test_registration_different_image()
    test_orb_features()
    test_run_function()
    print("=== test_registration_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
