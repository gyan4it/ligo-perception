#!/usr/bin/env python3
"""test_vir_builder.py — unit tests for vir_builder.py (Stage 4/8).

Tests:
- VIR builder with single evidence source
- VIR builder with multiple evidence sources
- Evidence tier classification (DETECTED/INTERPRETED)
- Asset ID and project profile binding
- Evidence summary counts
- Empty evidence handling
"""

import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from vir_builder import build_vir, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_vir_builder_single_source():
    """Test VIR builder with single layout evidence source."""
    layout_data = {
        "available": True,
        "component": "layout_probe.js",
        "targets": [
            {
                "file": "test.html",
                "root": {"x": 0, "y": 0, "w": 800, "h": 600},
                "issues": [{"t": "OVERFLOW", "det": "content overflows", "conf": 0.95}],
                "issue_count": 1,
                "codes": ["OVERFLOW"],
                "evidence_tier": "DETECTED",
            }
        ],
        "dirty_targets": 1,
        "total_targets": 1,
        "evidence_tier": "DETECTED",
    }

    vir = build_vir(layout_data=layout_data, asset_id="test-001", project_profile="B01")

    assert vir["schema_version"] == "1.1.0"
    assert vir["asset_id"] == "test-001"
    assert vir["project_profile"] == "B01"
    assert vir["input_type"] == "renderer"
    assert vir["renderer"]["available"] is True
    assert vir["evidence_summary"]["total_findings"] == 1
    assert vir["evidence_summary"]["detected_findings"] == 1
    assert vir["evidence_summary"]["interpreted_findings"] == 0
    print("  PASS: test_vir_builder_single_source")


def test_vir_builder_multiple_sources():
    """Test VIR builder with multiple evidence sources."""
    layout_data = {
        "available": True,
        "targets": [
            {
                "file": "test.html",
                "root": {"x": 0, "y": 0, "w": 800, "h": 600},
                "issues": [{"t": "OVERFLOW", "det": "content overflows", "conf": 0.95}],
                "issue_count": 1,
                "codes": ["OVERFLOW"],
                "evidence_tier": "DETECTED",
            }
        ],
        "dirty_targets": 1,
        "total_targets": 1,
        "evidence_tier": "DETECTED",
    }
    bitmap_data = {
        "available": True,
        "targets": [
            {
                "file": "image.png",
                "record": {"format": "PNG", "width": 100, "height": 100, "mode": "RGBA"},
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
        "available": True,
        "targets": [
            {
                "file": "image.png",
                "vision": {"engine": "test_vlm", "model": "test-model", "result": "A cat on a mat"},
                "issues": [],
                "issue_count": 0,
                "codes": [],
                "evidence_tier": "INTERPRETED",
            }
        ],
        "dirty_targets": 0,
        "total_targets": 1,
        "evidence_tier": "INTERPRETED",
    }

    vir = build_vir(
        layout_data=layout_data,
        bitmap_data=bitmap_data,
        vision_data=vision_data,
        asset_id="test-multi",
        project_profile="B01",
    )

    assert vir["input_type"] == "mixed"
    assert "renderer" in vir["input_types"]
    assert "bitmap" in vir["input_types"]
    assert "vision" in vir["input_types"]
    assert vir["evidence_summary"]["total_findings"] == 1
    assert vir["evidence_summary"]["detected_findings"] == 1
    assert vir["evidence_summary"]["interpreted_findings"] == 0
    # Vision evidence is INTERPRETED
    assert len(vir["issues"]) == 1
    assert vir["issues"][0]["evidence_tier"] == "DETECTED"
    print("  PASS: test_vir_builder_multiple_sources")


def test_vir_builder_empty():
    """Test VIR builder with no evidence."""
    vir = build_vir()

    assert vir["input_type"] == "none"
    assert vir["input_types"] == []
    assert vir["evidence_summary"]["total_findings"] == 0
    assert vir["evidence_summary"]["total_targets"] == 0
    assert vir["evidence_summary"]["dirty_targets"] == 0
    print("  PASS: test_vir_builder_empty")


def test_vir_builder_provenance():
    """Test VIR builder provenance chain."""
    result = build_vir()
    assert "provenance_chain" in result
    assert result["provenance_chain"] == [
        "Source", "Evidence", "Claim", "Content Block", "Chapter", "Book", "Release"
    ]
    print("  PASS: test_vir_builder_provenance")


def test_vir_builder_evidence_tiers():
    """Test evidence tiers documentation."""
    result = build_vir()
    assert "evidence_tiers" in result
    assert "DETECTED" in result["evidence_tiers"]
    assert "DERIVED" in result["evidence_tiers"]
    assert "INTERPRETED" in result["evidence_tiers"]
    print("  PASS: test_vir_builder_evidence_tiers")


def test_vir_builder_output_file():
    """Test VIR builder writes to output file."""
    import tempfile
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "test_vir.json"
        vir = build_vir(
            layout_data={"available": True, "targets": [], "dirty_targets": 0, "total_targets": 0, "evidence_tier": "DETECTED"},
            asset_id="test-asset",
        )
        assert vir["asset_id"] == "test-asset"
        out_path = Path(tmpdir) / "test_vir.json"
        out_path.write_text(json.dumps(vir, indent=2), encoding="utf-8")
        assert out_path.exists()
        written = json.loads(out_path.read_text(encoding="utf-8"))
        assert written["asset_id"] == "test-asset"
        print("  PASS: test_vir_builder_output_file")


def run_all():
    print("\n=== test_vir_builder.py ===")
    test_vir_builder_single_source()
    test_vir_builder_multiple_sources()
    test_vir_builder_empty()
    test_vir_builder_provenance()
    test_vir_builder_evidence_tiers()
    test_vir_builder_output_file()
    print("=== test_vir_builder.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
