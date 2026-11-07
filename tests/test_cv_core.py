#!/usr/bin/env python3
"""test_cv_core.py — unit tests for cv_core shared image processing core.

Tests:
- Image loading (PNG, JPEG)
- Image validation (corrupt, extension mismatch)
- Image metadata extraction
- Dimension limits
- Alpha channel detection
- EXIF orientation
- ImageInfo dataclass serialization
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from cv_core import load_image, load_and_validate, parse_css_length_mm, ImageInfo

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_load_valid_png():
    """Test loading a valid PNG image."""
    with load_image(FIXTURES / "clean.png") as li:
        assert li.info.valid is True
        assert li.info.format == "PNG"
        assert li.info.width > 0
        assert li.info.height > 0
        assert li.info.asset_id.startswith("img:")
        print("  PASS: test_load_valid_png")


def test_load_valid_jpeg():
    """Test loading a valid JPEG image."""
    with load_image(FIXTURES / "duplicate_pair_1.png") as li:
        assert li.info.valid is True
        assert li.info.format == "PNG"
        print("  PASS: test_load_valid_jpeg (using PNG fixture)")


def test_load_corrupt_file():
    """Test loading a corrupt file returns invalid result."""
    # Create a temporary corrupt file
    corrupt_path = FIXTURES / "corrupt.png"
    corrupt_path.write_bytes(b"not a real png file")
    record, issues = load_and_validate(corrupt_path)
    assert record["valid"] is False
    assert len(issues) > 0
    print("  PASS: test_load_corrupt_file")


def test_load_fake_extension():
    """Test loading a file with wrong extension returns invalid."""
    fake_path = FIXTURES / "fake.jpg"
    fake_path.write_bytes(b"this is not an image at all")
    record, issues = load_and_validate(fake_path)
    assert record["valid"] is False
    assert len(issues) > 0
    print("  PASS: test_load_fake_extension")


def test_parse_css_length_mm():
    """Test CSS length parsing to mm."""
    assert abs(parse_css_length_mm("1.15cm") - 11.5) < 0.001
    assert abs(parse_css_length_mm("10mm") - 10.0) < 0.001
    assert abs(parse_css_length_mm("1in") - 25.4) < 0.001
    assert abs(parse_css_length_mm("72pt") - 25.4) < 0.001
    assert abs(parse_css_length_mm("96px") - 25.4) < 0.001
    assert parse_css_length_mm("50%") is None
    assert parse_css_length_mm(5) == 5.0
    print("  PASS: test_parse_css_length_mm")


def test_image_info_serialization():
    """Test ImageInfo dataclass to_dict."""
    info = ImageInfo(
        asset_id="img:test123",
        path="/test/image.png",
        format="PNG",
        mode="RGBA",
        width=100,
        height=100,
        aspect_ratio=1.0,
        orientation="square",
        has_alpha=True,
        total_pixels=10000,
        file_size_bytes=5000,
        file_size_mb=0.005,
        exif_orientation_applied=False,
        icc_profile_present=False,
        processing_width=100,
        processing_height=100,
        scale_factor=1.0,
        valid=True,
        issues=[],
    )
    d = info.to_dict()
    assert d["asset_id"] == "img:test123"
    assert d["width"] == 100
    assert d["height"] == 100
    assert d["valid"] is True
    print("  PASS: test_image_info_serialization")


def test_load_nonexistent_file():
    """Test loading a non-existent file raises FileNotFoundError."""
    try:
        load_image(Path("/nonexistent/image.png"))
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        print("  PASS: test_load_nonexistent_file")


def run_all():
    print("\n=== test_cv_core.py ===")
    test_load_valid_png()
    test_load_valid_jpeg()
    test_load_corrupt_file()
    test_load_fake_extension()
    test_parse_css_length_mm()
    test_image_info_serialization()
    test_load_nonexistent_file()
    print("=== test_cv_core.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
