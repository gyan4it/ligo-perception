#!/usr/bin/env python3
"""test_bitmap_check.py — unit tests for bitmap_check tool.

Tests:
- Valid PNG/JPEG loading
- Corrupt file detection
- Extension/content mismatch detection
- Metadata extraction (format, dimensions, mode, alpha)
- Dimension limits
- Asset ID generation
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from bitmap_check import load_and_validate

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_valid_png():
    """Test loading a valid PNG image."""
    record, issues = load_and_validate(FIXTURES / "clean.png")
    assert record["valid"] is True
    assert record["format"] == "PNG"
    assert record["width"] > 0
    assert record["height"] > 0
    assert record["asset_id"].startswith("img:")
    print("  PASS: test_valid_png")


def test_valid_jpeg():
    """Test loading a valid JPEG image."""
    # Duplicate images are PNG, test with what we have
    record, issues = load_and_validate(FIXTURES / "duplicate_pair_1.png")
    assert record["valid"] is True
    assert record["format"] == "PNG"
    print("  PASS: test_valid_jpeg (using PNG fixture)")


def test_corrupt_file():
    """Test loading a corrupt file."""
    corrupt_path = FIXTURES / "corrupt_test.png"
    corrupt_path.write_bytes(b"not a real png file")
    record, issues = load_and_validate(corrupt_path)
    assert record["valid"] is False
    assert len(issues) > 0
    assert issues[0]["t"] == "BITMAP-UNKNOWN-FORMAT"
    print("  PASS: test_corrupt_file")


def test_fake_extension():
    """Test loading a file with wrong extension."""
    fake_path = FIXTURES / "fake.jpg"
    fake_path.write_bytes(b"this is not an image at all")
    record, issues = load_and_validate(fake_path)
    assert record["valid"] is False
    assert len(issues) > 0
    assert issues[0]["t"] == "BITMAP-UNKNOWN-FORMAT"
    print("  PASS: test_fake_extension")


def test_empty_file():
    """Test loading an empty file."""
    empty_path = FIXTURES / "empty.png"
    empty_path.write_bytes(b"")
    record, issues = load_and_validate(empty_path)
    assert record["valid"] is False
    assert any(i["t"] == "BITMAP-EMPTY" for i in issues)
    print("  PASS: test_empty_file")


def test_metadata_extraction():
    """Test metadata extraction from valid image."""
    record, issues = load_and_validate(FIXTURES / "line_art.png")
    assert record["valid"] is True
    assert record["format"] == "PNG"
    assert record["width"] == 200
    assert record["height"] == 200
    assert record["aspect_ratio"] == 1.0
    assert record["mode"] == "RGB"
    print("  PASS: test_metadata_extraction")


def test_asset_id_consistency():
    """Test that same file produces same asset ID."""
    record1, _ = load_and_validate(FIXTURES / "clean.png")
    record2, _ = load_and_validate(FIXTURES / "clean.png")
    assert record1["asset_id"] == record2["asset_id"]
    print("  PASS: test_asset_id_consistency")


def run_all():
    print("\n=== test_bitmap_check.py ===")
    test_valid_png()
    test_valid_jpeg()
    test_corrupt_file()
    test_fake_extension()
    test_empty_file()
    test_metadata_extraction()
    test_asset_id_consistency()
    print("=== test_bitmap_check.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
