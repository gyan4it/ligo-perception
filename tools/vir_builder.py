#!/usr/bin/env python3
"""vir_builder.py — Visual Intermediate Representation (VIR) builder for LiGeo.

Combines renderer evidence (HTML/SVG/PDF via CDP) and bitmap evidence
(PNG/JPEG ingestion, pixel analysis, OCR, vision, color, quality, edge,
geometry, similarity, registration, region, document, diagram, illustration)
into a shared VIR schema. Preserves evidence tiers (DETECTED/DERIVED/
INTERPRETED) and provenance.

  python tools/vir_builder.py --layout out/evidence.json --bitmap out/bitmap_evidence.json
                                 --ocr out/ocr_evidence.json --vision out/vision_evidence.json
                                 --color out/color_evidence.json --quality out/quality_evidence.json
                                 --edge out/edge_evidence.json --geometry out/geometry_evidence.json
                                 --similarity out/similarity_evidence.json
                                 --registration out/registration_evidence.json
                                 --region out/region_evidence.json
                                 --document out/document_evidence.json
                                 --diagram out/diagram_evidence.json
                                 --illustration out/illustration_evidence.json
                                 --pdf out/pdf_evidence.json --out out/vir.json

Exit code 0 = VIR built successfully.
"""
import argparse, json, sys
from pathlib import Path
from datetime import datetime, timezone

VIR_SCHEMA_VERSION = "1.1.0"


def load_json(path: Path | None) -> dict | None:
    """Load a JSON evidence file if it exists."""
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"cannot load {p}: {str(e)[:200]}"}


def _normalize_target(entry: dict) -> dict:
    """Normalize a single target's evidence into a standard dict."""
    issues = entry.get("issues", [])
    return {
        "file": entry.get("file", "unknown"),
        "root": entry.get("root"),
        "meta": entry.get("meta"),
        "issues": issues,
        "issue_count": len(issues),
        "codes": [i.get("t") for i in issues if i.get("t")],
        "evidence_tier": "DETECTED",
    }


def _extract_entries(data: dict | list) -> list:
    """Extract list of target entries from data.

    data can be:
    - A list of entry dicts
    - A dict with 'targets' key containing a list
    - A single dict representing one entry
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "targets" in data:
        return data["targets"]
    return [data]


def normalize_layout_evidence(layout_data: dict | None) -> dict:
    """Normalize layout probe evidence into VIR renderer section."""
    if not layout_data:
        return {"available": False, "reason": "no layout evidence provided"}

    targets = []
    for entry in _extract_entries(layout_data):
        targets.append(_normalize_target(entry))

    return {
        "available": True,
        "component": "layout_probe.js / layout_check.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_bitmap_evidence(bitmap_data: dict | None) -> dict:
    """Normalize bitmap ingestion evidence into VIR bitmap section."""
    if not bitmap_data:
        return {"available": False, "reason": "no bitmap evidence provided"}

    targets = []
    for entry in _extract_entries(bitmap_data):
        record = entry.get("record", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "asset_id": record.get("asset_id"),
            "format": record.get("format"),
            "width": record.get("width"),
            "height": record.get("height"),
            "aspect_ratio": record.get("aspect_ratio"),
            "mode": record.get("mode"),
            "has_alpha": record.get("has_alpha"),
            "total_pixels": record.get("total_pixels"),
            "file_size_mb": record.get("file_size_mb"),
            "valid": record.get("valid"),
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/bitmap_check.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_pixel_evidence(pixel_data: dict | None) -> dict:
    """Normalize pixel analysis evidence into VIR bitmap section."""
    if not pixel_data:
        return {"available": False, "reason": "no pixel evidence provided"}

    targets = []
    for entry in _extract_entries(pixel_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/pixel_check.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_color_evidence(color_data: dict | None) -> dict:
    """Normalize color analysis evidence into VIR bitmap section."""
    if not color_data:
        return {"available": False, "reason": "no color evidence provided"}

    targets = []
    for entry in _extract_entries(color_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/cv_sensors/color_sensor.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_quality_evidence(quality_data: dict | None) -> dict:
    """Normalize quality evidence into VIR bitmap section."""
    if not quality_data:
        return {"available": False, "reason": "no quality evidence provided"}

    targets = []
    for entry in _extract_entries(quality_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/cv_sensors/quality_sensor.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_edge_evidence(edge_data: dict | None) -> dict:
    """Normalize edge detection evidence into VIR bitmap section."""
    if not edge_data:
        return {"available": False, "reason": "no edge evidence provided"}

    targets = []
    for entry in _extract_entries(edge_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/cv_sensors/edge_sensor.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_geometry_evidence(geometry_data: dict | None) -> dict:
    """Normalize geometry evidence into VIR bitmap section."""
    if not geometry_data:
        return {"available": False, "reason": "no geometry evidence provided"}

    targets = []
    for entry in _extract_entries(geometry_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/cv_sensors/geometry_sensor.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_similarity_evidence(similarity_data: dict | None) -> dict:
    """Normalize similarity evidence into VIR bitmap section."""
    if not similarity_data:
        return {"available": False, "reason": "no similarity evidence provided"}

    targets = []
    for entry in _extract_entries(similarity_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/cv_sensors/similarity_sensor.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_registration_evidence(registration_data: dict | None) -> dict:
    """Normalize registration evidence into VIR bitmap section."""
    if not registration_data:
        return {"available": False, "reason": "no registration evidence provided"}

    targets = []
    for entry in _extract_entries(registration_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/cv_sensors/registration_sensor.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_region_evidence(region_data: dict | None) -> dict:
    """Normalize region evidence into VIR bitmap section."""
    if not region_data:
        return {"available": False, "reason": "no region evidence provided"}

    targets = []
    for entry in _extract_entries(region_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/cv_sensors/region_sensor.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_document_evidence(document_data: dict | None) -> dict:
    """Normalize document evidence into VIR renderer section."""
    if not document_data:
        return {"available": False, "reason": "no document evidence provided"}

    targets = []
    for entry in _extract_entries(document_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/cv_sensors/document_sensor.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_diagram_evidence(diagram_data: dict | None) -> dict:
    """Normalize diagram evidence into VIR bitmap section."""
    if not diagram_data:
        return {"available": False, "reason": "no diagram evidence provided"}

    targets = []
    for entry in _extract_entries(diagram_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/cv_sensors/diagram_sensor.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_illustration_evidence(illustration_data: dict | None) -> dict:
    """Normalize illustration evidence into VIR bitmap section."""
    if not illustration_data:
        return {"available": False, "reason": "no illustration evidence provided"}

    targets = []
    for entry in _extract_entries(illustration_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/cv_sensors/illustration_sensor.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_ocr_evidence(ocr_data: dict | None) -> dict:
    """Normalize OCR evidence into VIR OCR section."""
    if not ocr_data:
        return {"available": False, "reason": "no OCR evidence provided"}

    targets = []
    for entry in _extract_entries(ocr_data):
        ocr = entry.get("ocr", {})
        targets.append({
            "file": entry.get("file", "unknown"),
            "engine": ocr.get("engine") if ocr else None,
            "engine_version": ocr.get("engine_version") if ocr else None,
            "lang": ocr.get("lang") if ocr else None,
            "full_text": ocr.get("full_text") if ocr else None,
            "n_words": ocr.get("n_words") if ocr else None,
            "avg_confidence": ocr.get("avg_confidence") if ocr else None,
            "text_blocks": ocr.get("text_blocks") if ocr else [],
            "available": ocr.get("ocr_available") if ocr else False,
            "issues": entry.get("issues", []),
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/ocr_adapter.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def normalize_vision_evidence(vision_data: dict | None) -> dict:
    """Normalize vision evidence into VIR vision section.

    Vision evidence is classified as INTERPRETED — model hypotheses,
    not ground truth.
    """
    if not vision_data:
        return {"available": False, "reason": "no vision evidence provided"}

    targets = []
    for entry in _extract_entries(vision_data):
        vision = entry.get("vision", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "engine": vision.get("engine") if vision else None,
            "model": vision.get("model") if vision else None,
            "mode": vision.get("mode") if vision else None,
            "available": vision.get("vision_available") if vision else False,
            "result": vision.get("vision") if vision else None,
            "issues": issues,
            "issue_count": len(issues),
            "evidence_tier": "INTERPRETED",
            "evidence_tier_note": "Vision output is model hypothesis, not ground truth",
        })

    return {
        "available": True,
        "component": "tools/vision_adapter.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "INTERPRETED",
    }



def normalize_pdf_evidence(pdf_data: dict | None) -> dict:
    """Normalize PDF evidence into VIR renderer section."""
    if not pdf_data:
        return {"available": False, "reason": "no PDF evidence provided"}

    targets = []
    for entry in _extract_entries(pdf_data):
        metrics = entry.get("metrics", {})
        issues = entry.get("issues", [])
        targets.append({
            "file": entry.get("file", "unknown"),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "codes": [i.get("t") for i in issues if i.get("t")],
            "evidence_tier": "DETECTED",
        })

    return {
        "available": True,
        "component": "tools/pdf_text_adapter.py",
        "targets": targets,
        "dirty_targets": sum(1 for t in targets if len(t.get("issues", [])) > 0),
        "total_targets": len(targets),
        "evidence_tier": "DETECTED",
    }


def build_vir(
    layout_data: dict | None = None,
    bitmap_data: dict | None = None,
    pixel_data: dict | None = None,
    ocr_data: dict | None = None,
    vision_data: dict | None = None,
    color_data: dict | None = None,
    quality_data: dict | None = None,
    edge_data: dict | None = None,
    geometry_data: dict | None = None,
    similarity_data: dict | None = None,
    registration_data: dict | None = None,
    region_data: dict | None = None,
    document_data: dict | None = None,
    diagram_data: dict | None = None,
    illustration_data: dict | None = None,
    pdf_data: dict | None = None,
    asset_id: str | None = None,
    project_profile: str | None = None,
    expected_page_size: dict | None = None,
) -> dict:
    """Build a complete VIR document from all evidence sources.

    The VIR preserves provenance and evidence tiers:
    - DETECTED: direct measurements from renderer/pixel/OCR
    - DERIVED: arithmetic on evidence (requires re-measurement after edits)
    - INTERPRETED: vision model hypotheses (requires human review)
    """
    renderer = normalize_layout_evidence(layout_data)
    bitmap = normalize_bitmap_evidence(bitmap_data)
    pixels = normalize_pixel_evidence(pixel_data)
    ocr = normalize_ocr_evidence(ocr_data)
    vision = normalize_vision_evidence(vision_data)
    color = normalize_color_evidence(color_data)
    quality = normalize_quality_evidence(quality_data)
    edge = normalize_edge_evidence(edge_data)
    geometry = normalize_geometry_evidence(geometry_data)
    similarity = normalize_similarity_evidence(similarity_data)
    registration = normalize_registration_evidence(registration_data)
    region = normalize_region_evidence(region_data)
    document = normalize_document_evidence(document_data)
    diagram = normalize_diagram_evidence(diagram_data)
    illustration = normalize_illustration_evidence(illustration_data)
    pdf = normalize_pdf_evidence(pdf_data)

    # Determine input type
    input_types = []
    if renderer["available"]:
        input_types.append("renderer")
    if bitmap["available"] or pixels["available"]:
        input_types.append("bitmap")
    if ocr["available"]:
        input_types.append("ocr")
    if vision["available"]:
        input_types.append("vision")
    if color["available"]:
        input_types.append("color")
    if quality["available"]:
        input_types.append("quality")
    if edge["available"]:
        input_types.append("edge")
    if geometry["available"]:
        input_types.append("geometry")
    if similarity["available"]:
        input_types.append("similarity")
    if registration["available"]:
        input_types.append("registration")
    if region["available"]:
        input_types.append("region")
    if document["available"]:
        input_types.append("document")
    if diagram["available"]:
        input_types.append("diagram")
    if illustration["available"]:
        input_types.append("illustration")
    if pdf["available"]:
        input_types.append("pdf")

    input_type = "mixed" if len(input_types) > 1 else (input_types[0] if input_types else "none")

    # Count total issues across all sources
    all_issues = []
    all_sections = [
        renderer, bitmap, pixels, ocr, vision, color, quality, edge,
        geometry, similarity, registration, region, document, diagram,
        illustration, pdf,
    ]
    for section in all_sections:
        if section["available"]:
            for t in section.get("targets", []):
                for iss in t.get("issues", []):
                    all_issues.append({
                        "source_file": t.get("file", "unknown"),
                        "source_section": section.get("component", "unknown"),
                        "code": iss.get("t"),
                        "detail": iss.get("det"),
                        "confidence": iss.get("conf"),
                        "evidence_tier": t.get("evidence_tier", "DETECTED"),
                    })

    # Separate DETECTED vs INTERPRETED
    detected_issues = [i for i in all_issues if i["evidence_tier"] == "DETECTED"]
    interpreted_issues = [i for i in all_issues if i["evidence_tier"] == "INTERPRETED"]

    vir = {
        "schema_version": VIR_SCHEMA_VERSION,
        "asset_id": asset_id,
        "project_profile": project_profile,
        "expected_page_size": expected_page_size,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "input_type": input_type,
        "input_types": input_types,
        "renderer": renderer,
        "bitmap": bitmap,
        "pixels": pixels,
        "ocr": ocr,
        "vision": vision,
        "color": color,
        "quality": quality,
        "edge": edge,
        "geometry": geometry,
        "similarity": similarity,
        "registration": registration,
        "region": region,
        "document": document,
        "diagram": diagram,
        "illustration": illustration,
        "pdf": pdf,
        "evidence_summary": {
            "total_findings": len(all_issues),
            "detected_findings": len(detected_issues),
            "interpreted_findings": len(interpreted_issues),
            "dirty_targets": sum(
                s.get("dirty_targets", 0)
                for s in all_sections if s["available"]
            ),
            "total_targets": sum(
                s.get("total_targets", 0)
                for s in all_sections if s["available"]
            ),
        },
        "issues": all_issues,
        "evidence_tiers": {
            "DETECTED": "Direct measurement from renderer/pixel/OCR — ground truth",
            "DERIVED": "Arithmetic on evidence — requires re-measurement after edits",
            "INTERPRETED": "Model hypothesis — requires human review",
        },
        "provenance_chain": [
            "Source", "Evidence", "Claim", "Content Block", "Chapter", "Book", "Release"
        ],
        "limitations": [],
    }

    # Add limitations based on what's missing
    if not vision["available"]:
        vir["limitations"].append(
            "Semantic vision unavailable — text-only model cannot interpret images"
        )
    if not ocr["available"]:
        vir["limitations"].append(
            "OCR unavailable — text extraction from images skipped"
        )
    if not bitmap["available"] and not pixels["available"]:
        vir["limitations"].append(
            "No bitmap evidence — pixel-level analysis not performed"
        )
    if not renderer["available"]:
        vir["limitations"].append(
            "No renderer evidence — HTML/SVG/layout inspection not performed"
        )
    if interpreted_issues:
        vir["limitations"].append(
            f"{len(interpreted_issues)} interpreted finding(s) require human validation before approval"
        )

    return vir


def run(layout: Path | None = None,
        bitmap: Path | None = None,
        pixels: Path | None = None,
        ocr: Path | None = None,
        vision: Path | None = None,
        color: Path | None = None,
        quality: Path | None = None,
        edge: Path | None = None,
        geometry: Path | None = None,
        similarity: Path | None = None,
        registration: Path | None = None,
        region: Path | None = None,
        document: Path | None = None,
        diagram: Path | None = None,
        illustration: Path | None = None,
        pdf: Path | None = None,
        asset_id: str | None = None,
        project_profile: str | None = None,
        expected_page_size: dict | None = None,
        out: Path | None = None) -> dict:
    """Build VIR from evidence files and optionally write to disk."""
    layout_data = layout_data if layout_data else None
    bitmap_data = load_json(bitmap) if bitmap else None
    pixel_data = load_json(pixels) if pixels else None
    ocr_data = load_json(ocr) if ocr else None
    vision_data = load_json(vision) if vision else None
    color_data = load_json(color) if color else None
    quality_data = load_json(quality) if quality else None
    edge_data = load_json(edge) if edge else None
    geometry_data = load_json(geometry) if geometry else None
    similarity_data = load_json(similarity) if similarity else None
    registration_data = load_json(registration) if registration else None
    region_data = load_json(region) if region else None
    document_data = load_json(document) if document else None
    diagram_data = load_json(diagram) if diagram else None
    illustration_data = load_json(illustration) if illustration else None
    pdf_data = load_json(pdf) if pdf else None

    vir = build_vir(
        layout_data=layout_data,
        bitmap_data=bitmap_data,
        pixel_data=pixel_data,
        ocr_data=ocr_data,
        vision_data=vision_data,
        color_data=color_data,
        quality_data=quality_data,
        edge_data=edge_data,
        geometry_data=geometry_data,
        similarity_data=similarity_data,
        registration_data=registration_data,
        region_data=region_data,
        document_data=document_data,
        diagram_data=diagram_data,
        illustration_data=illustration_data,
        pdf_data=pdf_data,
        asset_id=asset_id,
        project_profile=project_profile,
        expected_page_size=expected_page_size,
    )

    if out:
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(vir, indent=2), encoding="utf-8")

    return vir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", help="layout evidence JSON file")
    ap.add_argument("--bitmap", help="bitmap ingestion evidence JSON file")
    ap.add_argument("--pixels", help="pixel analysis evidence JSON file")
    ap.add_argument("--ocr", help="OCR evidence JSON file")
    ap.add_argument("--vision", help="vision evidence JSON file")
    ap.add_argument("--color", help="color evidence JSON file")
    ap.add_argument("--quality", help="quality evidence JSON file")
    ap.add_argument("--edge", help="edge evidence JSON file")
    ap.add_argument("--geometry", help="geometry evidence JSON file")
    ap.add_argument("--similarity", help="similarity evidence JSON file")
    ap.add_argument("--registration", help="registration evidence JSON file")
    ap.add_argument("--region", help="region evidence JSON file")
    ap.add_argument("--document", help="document evidence JSON file")
    ap.add_argument("--diagram", help="diagram evidence JSON file")
    ap.add_argument("--illustration", help="illustration evidence JSON file")
    ap.add_argument("--pdf", help="PDF evidence JSON file")
    ap.add_argument("--asset-id", help="stable asset ID for this VIR")
    ap.add_argument("--project-profile", help="project profile JSON file")
    ap.add_argument("--out", help="write VIR to this file")
    a = ap.parse_args()

    from profile_loader import load_profile

    profile = load_profile(a.project_profile) if a.project_profile else None
    profile_id = profile.get("profile_id") if profile else None
    expected_page_size = None
    if profile:
        pp = profile.get("page", {})
        ps = pp.get("size", {})
        expected_page_size = {
            "width_cm": ps.get("width_cm"),
            "height_cm": ps.get("height_cm"),
            "name": ps.get("name"),
        }

    vir = run(
        layout=a.layout,
        bitmap=a.bitmap,
        pixels=a.pixels,
        ocr=a.ocr,
        vision=a.vision,
        color=a.color,
        quality=a.quality,
        edge=a.edge,
        geometry=a.geometry,
        similarity=a.similarity,
        registration=a.registration,
        region=a.region,
        document=a.document,
        diagram=a.diagram,
        illustration=a.illustration,
        pdf=a.pdf,
        asset_id=a.asset_id,
        project_profile=profile_id,
        expected_page_size=expected_page_size,
        out=a.out,
    )

    print(f"VIR built: schema={vir['schema_version']}, input_type={vir['input_type']}")
    print(f"  targets: {vir['evidence_summary']['total_targets']}")
    print(f"  dirty: {vir['evidence_summary']['dirty_targets']}")
    print(f"  findings: {vir['evidence_summary']['total_findings']} "
          f"(DETECTED: {vir['evidence_summary']['detected_findings']}, "
          f"INTERPRETED: {vir['evidence_summary']['interpreted_findings']})")
    if vir["limitations"]:
        print("  limitations:")
        for lim in vir["limitations"]:
            print(f"    - {lim}")
    if a.out:
        print(f"  written: {a.out}")
    sys.exit(0)


if __name__ == "__main__":
    main()
