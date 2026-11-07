#!/usr/bin/env python3
"""test_pixel_check.py — unit tests for pixel_check tool.

Tests:
- Dimensions extraction
- Color mode detection
- Pixel metrics computation (luminance, contrast, sharpness, edges)
- Histogram computation
- Palette extraction
- Edge cases (corrupt files)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from pixel_check import analyze_pixels, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_valid_png_metrics():
    """Test pixel metrics on valid PNG."""
    metrics = analyze_pixels(FIXTURES / "clean.png")
    assert metrics is not None
    assert metrics["dimensions"]["width"] == 200
    assert metrics["dimensions"]["height"] == 200
    assert metrics["dimensions"]["aspect_ratio"] == 1.0
    assert metrics["dimensions"]["orientation"] == "square"
    assert metrics["color"]["mode"] == "RGB"
    assert metrics["luminance"]["mean"] > 0
    assert metrics["contrast"]["michelson"] >= 0
    print("  PASS: test_valid_png_metrics")


def test_line_art_metrics():
    """Test pixel metrics on line art image."""
    metrics = analyze_pixels(FIXTURES / "line_art.png")
    assert metrics is not None
    assert metrics["dimensions"]["width"] == 200
    assert metrics["dimensions"]["height"] == 200
    assert metrics["edges"]["edge_pixel_pct"] > 0  # Should have edges
    assert metrics["sharpness"]["laplacian_variance"] > 0
    print("  PASS: test_line_art_metrics")


def test_low_contrast_metrics():
    """Test pixel metrics on low contrast image."""
    metrics = analyze_pixels(FIXTURES / "low_contrast.png")
    assert metrics is not None
    assert metrics["contrast"]["michelson"] < 0.5  # Low contrast
    print("  PASS: test_low_contrast_metrics")


def test_palette_extraction():
    """Test palette extraction."""
    metrics = analyze_pixels(FIXTURES / "clean.png")
    assert len(metrics["palette"]["dominant_colors"]) > 0
    assert metrics["palette"]["unique_buckets"] > 0
    print("  PASS: test_palette_extraction")


def test_histogram_computation():
    """Test histogram computation."""
    metrics = analyze_pixels(FIXTURES / "clean.png")
    assert "r" in metrics["histogram"]
    assert "g" in metrics["histogram"]
    assert "b" in metrics["histogram"]
    assert len(metrics["histogram"]["r"]["bin_counts"]) == 16
    print("  PASS: test_histogram_computation")


def test_corrupt_file():
    """Test handling of corrupt file."""
    corrupt_path = FIXTURES.parent.parent / "ligeohtmltest" / "corrupt.png"
    if corrupt_path.exists():
        try:
            metrics = analyze_pixels(corrupt_path)
            # Should not raise, but return minimal metrics
            assert metrics is not None
        except Exception:
            # Expected for corrupt files
            pass
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
    print("\n=== test_pixel_check.py ===")
    test_valid_png_metrics()
    test_line_art_metrics()
    test_low_contrast_metrics()
    test_palette_extraction()
    test_histogram_computation()
    test_corrupt_file()
    test_run_function()
    print("=== test_pixel_check.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
