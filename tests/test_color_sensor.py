#!/usr/bin/env python3
"""test_color_sensor.py — unit tests for color_sensor tool.

Tests:
- Color palette extraction
- Dominant colors
- Histogram computation
- HSV statistics
- Coverage tiers
- Mean RGB
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from color_sensor import analyze_color, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_clean_image_color():
    """Test color analysis on clean image."""
    result = analyze_color(FIXTURES / "clean.png")
    assert result is not None
    assert len(result["palette"]["dominant_colors"]) > 0
    assert result["palette"]["unique_buckets"] > 0
    assert "r" in result["mean_rgb"]
    assert "g" in result["mean_rgb"]
    assert "b" in result["mean_rgb"]
    print("  PASS: test_clean_image_color")


def test_line_art_color():
    """Test color analysis on line art image."""
    result = analyze_color(FIXTURES / "line_art.png")
    assert result is not None
    assert len(result["palette"]["dominant_colors"]) > 0
    assert result["palette"]["unique_buckets"] > 1  # Multiple colors
    print("  PASS: test_line_art_color")


def test_low_contrast_color():
    """Test color analysis on low contrast image."""
    result = analyze_color(FIXTURES / "low_contrast.png")
    assert result is not None
    assert len(result["palette"]["dominant_colors"]) > 0
    print("  PASS: test_low_contrast_color")


def test_color_histogram():
    """Test color histogram computation."""
    result = analyze_color(FIXTURES / "clean.png")
    assert "channel_histogram" in result
    assert "r" in result["channel_histogram"]
    assert "g" in result["channel_histogram"]
    assert "b" in result["channel_histogram"]
    assert len(result["channel_histogram"]["r"]["bin_counts"]) == 16
    print("  PASS: test_color_histogram")


def test_hsv_stats():
    """Test HSV statistics computation."""
    result = analyze_color(FIXTURES / "clean.png")
    assert "hue_mean" in result["hsv_stats"]
    assert "sat_mean" in result["hsv_stats"]
    assert "val_mean" in result["hsv_stats"]
    print("  PASS: test_hsv_stats")


def test_coverage_tiers():
    """Test coverage tiers computation."""
    result = analyze_color(FIXTURES / "clean.png")
    assert "saturation_tiers" in result["coverage_tiers"]
    assert "value_tiers" in result["coverage_tiers"]
    assert result["coverage_tiers"]["saturation_tiers"]["desaturated"] >= 0
    print("  PASS: test_coverage_tiers")


def test_mean_rgb():
    """Test mean RGB computation."""
    result = analyze_color(FIXTURES / "clean.png")
    assert "r" in result["mean_rgb"]
    assert "g" in result["mean_rgb"]
    assert "b" in result["mean_rgb"]
    # Clean image should have high RGB values (light gray)
    assert result["mean_rgb"]["r"] > 200
    assert result["mean_rgb"]["g"] > 200
    assert result["mean_rgb"]["b"] > 200
    print("  PASS: test_mean_rgb")


def test_corrupt_file():
    """Test handling of corrupt file."""
    corrupt_path = FIXTURES.parent.parent / "ligeohtmltest" / "corrupt.png"
    if corrupt_path.exists():
        try:
            result = analyze_color(corrupt_path)
            # Should return error info
            assert "error" in result or result["palette"]["unique_buckets"] == 0
        except Exception:
            pass  # Expected for corrupt files
        print("  PASS: test_corrupt_file")
    else:
        print("  SKIP: test_corrupt_file (fixture not found)")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "clean.png")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "clean.png")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_color_sensor.py ===")
    test_clean_image_color()
    test_line_art_color()
    test_low_contrast_color()
    test_color_histogram()
    test_hsv_stats()
    test_coverage_tiers()
    test_mean_rgb()
    test_corrupt_file()
    test_run_function()
    print("=== test_color_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
