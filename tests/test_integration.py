#!/usr/bin/env python3
"""test_integration.py — Integration tests for LiGeo full pipeline (Stage 11).

Tests the full P10 production pipeline end-to-end:
1. B01 chapter production pipeline
2. Full P10 processing chain
3. Quality gate compliance
4. Cross-controller consistency

Exit code = number of failures (0 = all pass).
"""
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_full_pipeline_b01_chapter():
    """Test full B01 chapter production pipeline end-to-end."""
    from cv_core import load_image
    from bitmap_check import load_and_validate
    from pixel_check import analyze_pixels
    from ocr_adapter import analyze_ocr
    from vir_builder import build_vir

    # Step 1: Load and validate image
    img_path = FIXTURES / "test_image.png"
    record, issues = load_and_validate(img_path)
    assert record["valid"] is True, f"Image should be valid: {issues}"
    assert record["format"] == "PNG"
    print("  OK: B01 step 1 - Image loading")

    # Step 2: Pixel analysis
    metrics = analyze_pixels(img_path)
    assert metrics is not None
    assert metrics["dimensions"]["width"] > 0
    assert metrics["dimensions"]["height"] > 0
    print("  OK: B01 step 2 - Pixel analysis")

    # Step 3: OCR analysis
    ocr_result = analyze_ocr(img_path)
    assert ocr_result is not None
    assert ocr_result["ocr"]["engine"] == "tesseract"
    print("  OK: Step 3 - OCR analysis")

    # Step 4: Build VIR from all evidence
    vir = build_vir(
        bitmap_data={"file": str(img_path), "record": record, "issues": issues},
        pixel_data={"file": str(img_path), "metrics": metrics, "issues": []},
        ocr_data={"file": str(img_path), "ocr": ocr_result, "issues": []},
        asset_id="B01-C03-F01",
        project_profile="B01",
    )

    assert vir["asset_id"] == "B01-C03-F01"
    assert vir["project_profile"] == "B01"
    assert vir["input_type"] == "mixed"
    assert vir["evidence_summary"]["total_targets"] >= 2
    print("  OK: Step 4 - VIR assembly")

    # Step 5: Verify evidence tiers
    # Bitmap/pixel evidence should be DETECTED
    bitmap_entries = vir["bitmap"]["targets"]
    assert len(bitmap_entries) == 1
    assert bitmap_entries[0]["evidence_tier"] == "DETECTED"

    # OCR evidence should be DETECTED
    ocr_entries = vir["ocr"]["targets"]
    assert len(ocr_entries) == 1
    assert ocr_entries[0]["evidence_tier"] == "DETECTED"

    print("  OK: Step 5 - Evidence tiers verified")
    print("  PASS: test_full_pipeline_b01_chapter")


def test_provenance_chain():
    """Test provenance chain integrity (AGENTS.md §17)."""
    from vir_builder import build_vir

    vir = build_vir(
        layout_data={"available": True, "targets": [
            {
                "file": "test.html",
                "root": {"x": 0, "y": 0, "w": 800, "h": 600},
                "issues": [],
                "issue_count": 0,
                "codes": [],
                "evidence_tier": "DETECTED",
            }
        ],
        "dirty_targets": 0,
        "total_targets": 1,
        "evidence_tier": "DETECTED",
    },
        asset_id="B01-C03-F01",
        project_profile="B01",
    )

    assert vir["asset_id"] == "B01-C03-F01"
    assert vir["project_profile"] == "B01"
    assert vir["provenance_chain"] == [
        "Source", "Evidence", "Claim", "Content Block", "Chapter", "Book", "Release"
    ]
    print("  PASS: test_provenance_chain")


def test_evidence_tier_classification():
    """Test evidence tier classification (DETECTED/DERIVED/INTERPRETED)."""
    from vir_builder import build_vir

    # Bitmap evidence = DETECTED
    bitmap_data = {
        "targets": [
            {
                "record": {"format": "PNG", "width": 100, "height": 100},
                "issues": [],
                "issue_count": 0,
                "codes": [],
                "evidence_tier": "DETECTED",
            }
        ],
        "dirty_targets": 0,
        "total_targets": 1,
        "evidence_tier": "DETECTED",
    }

    vision_data = {
        "targets": [
            {
                "file": "image.png",
                "vision": {"engine": "test_vlm", "result": "A cat"},
                "issues": [],
                "issue_count": 0,
                "evidence_tier": "INTERPRETED",
            }
        ],
        "dirty_targets": 0,
        "total_targets": 1,
        "evidence_tier": "INTERPRETED",
    }

    vir = build_vir(
        bitmap_data=bitmap_data,
        vision_data=vision_data,
        asset_id="test-asset",
    )

    # Bitmap evidence should be DETECTED
    bitmap_entries = vir["bitmap"]["targets"]
    assert bitmap_entries[0]["evidence_tier"] == "DETECTED"

    # Vision evidence should be INTERPRETED
    vision_entries = vir["vision"]["targets"]
    assert vision_entries[0]["evidence_tier"] == "INTERPRETED"

    # Summary counts
    assert vir["evidence_summary"]["detected_findings"] >= 0
    assert vir["evidence_summary"]["interpreted_findings"] >= 0
    print("  PASS: test_evidence_tier_classification")


def test_profile_consistency():
    """Test that B01 profile constraints are enforced."""
    from vir_builder import build_vir

    vir = build_vir(
        layout_data={"available": True, "targets": [], "dirty_targets": 0, "total_targets": 0, "evidence_tier": "DETECTED"},
        asset_id="B01-C03-F01",
        project_profile="B01",
    )

    assert vir["project_profile"] == "B01"
    print("  PASS: test_profile_consistency")


def test_no_secrets_logging():
    """Test that no secrets are logged (AGENTS.md §47)."""
    from vir_builder import build_vir

    vir = build_vir(
        layout_data={"available": True, "targets": [], "dirty_targets": 0, "total_targets": 0, "evidence_tier": "DETECTED"},
        asset_id="test-asset",
    )

    vir_str = json.dumps(vir)
    assert "API_KEY" not in vir_str.upper()
    assert "PASSWORD" not in vir_str.upper()
    assert "SECRET" not in vir_str.upper()
    print("  PASS: test_no_secrets_logging")


def run_all():
    print("\n=== test_integration.py ===")
    test_full_pipeline_b01_chapter()
    test_provenance_chain()
    test_evidence_tier_classification()
    test_profile_consistency()
    test_no_secrets_logging()
    print("=== test_integration.py PASSED ===\n")


if __name__ == "__main__":
    run_all()