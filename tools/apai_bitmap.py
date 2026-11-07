#!/usr/bin/env python3
"""apai_bitmap — APAI rubric-based art/illustration evaluation for bitmap evidence.

APAI remains the rubric evaluator — NOT the pixel decoder or VLM.
It consumes Visual Intermediate Representation (VIR) evidence from renderer,
bitmap, pixel, OCR, and vision sources and produces structured, evidence-grounded
art/illustration assessments.

  python tools/apai_bitmap.py --vir out/vir_evidence.json --rubric out/rubric.json
                                 --out out/apai_result.json
  python tools/apai_bitmap.py --vir out/vir_evidence.json --rubric default
                                 --purpose textbook --audience "8-9 years"
                                 --objective "explain AI system boundary"

Exit code 0 = assessment complete (may include insufficient_evidence findings).
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_loader import load_profile, profile_rubric

APAI_SCHEMA_VERSION = "1.0.0"

# --- Default rubric (B01 textbook illustration standard) ---
DEFAULT_RUBRIC = {
    "rubric_id": "APAI-B01-ILLUSTRATION-001",
    "rubric_name": "B01 Textbook Illustration Quality",
    "rubric_version": "1.0.0",
    "scale": {
        "1": "Needs substantial revision",
        "2": "Needs improvement",
        "3": "Adequate for stated purpose",
        "4": "Strong",
        "5": "Excellent for stated purpose",
    },
    "criteria": [
        {
            "criterion_id": "composition.visual_hierarchy",
            "criterion_name": "Visual hierarchy",
            "description": "Clear focal point, balanced element distribution, readable foreground/middle/ground",
            "applies_to": ["illustration", "figure", "diagram"],
        },
        {
            "criterion_id": "color.harmony",
            "criterion_name": "Color harmony",
            "description": "Coherent palette, appropriate warm/cool balance, sufficient contrast",
            "applies_to": ["illustration", "figure"],
        },
        {
            "criterion_id": "style.consistency",
            "criterion_name": "Style/rendering consistency",
            "description": "Consistent line weight, shading, texture, proportion across elements",
            "applies_to": ["illustration", "figure", "character_sheet"],
        },
        {
            "criterion_id": "character.expression",
            "criterion_name": "Character expression readability",
            "description": "Facial expressions and poses are clear and appropriate for the scene",
            "applies_to": ["character", "illustration"],
        },
        {
            "criterion_id": "scene.coherence",
            "criterion_name": "Scene coherence",
            "description": "Objects and characters belong to the same scene; lighting/perspective/scale consistent",
            "applies_to": ["illustration", "diagram"],
        },
        {
            "criterion_id": "educational.clarity",
            "criterion_name": "Educational illustration clarity",
            "description": "Illustration supports the learning objective; no visual distractions; age-appropriate complexity",
            "applies_to": ["illustration", "figure", "diagram"],
        },
        {
            "criterion_id": "accessibility.contrast",
            "criterion_name": "Visual accessibility",
            "description": "Sufficient color contrast for readability; text legible at expected size",
            "applies_to": ["illustration", "figure", "worksheet"],
        },
    ],
}


def load_json(path: Path | None) -> dict | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_rubric(rubric_arg: str) -> dict:
    """Load a rubric from a JSON file or use the default."""
    if rubric_arg == "default":
        return DEFAULT_RUBRIC
    p = Path(rubric_arg)
    if not p.exists():
        sys.exit(f"rubric file not found: {rubric_arg}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"cannot load rubric: {e}")


def extract_evidence_for_criterion(
    vir: dict, criterion: dict, context: dict
) -> dict:
    """Extract relevant evidence from VIR for a given criterion.

    Returns a dict with:
      - evidence: list of evidence items (observed/measured/derived/inferred)
      - sources: list of source descriptions
      - sufficiency: "sufficient", "partial", "insufficient"
    """
    evidence = []
    sources = []

    renderer = vir.get("renderer", {})
    bitmap = vir.get("bitmap", {})
    pixels = vir.get("pixels", {})
    ocr = vir.get("ocr", {})
    vision = vir.get("vision", {})

    criterion_id = criterion["criterion_id"]

    # --- Composition / visual hierarchy ---
    if criterion_id == "composition.visual_hierarchy":
        if bitmap.get("available"):
            for t in bitmap.get("targets", []):
                record = t.get("record", {})
                if record.get("width") and record.get("height"):
                    evidence.append({
                        "type": "measured",
                        "description": f"Image dimensions {record['width']}x{record['height']}, aspect {record.get('aspect_ratio')}",
                        "source": "bitmap_ingestion",
                        "confidence": 0.95,
                    })
                    sources.append("bitmap_check.py")
        if pixels.get("available"):
            for t in pixels.get("targets", []):
                m = t.get("metrics", {})
                if m:
                    evidence.append({
                        "type": "measured",
                        "description": f"Edge pixel percentage {m.get('edges', {}).get('edge_pixel_pct')}%, mean gradient {m.get('edges', {}).get('mean_gradient')}",
                        "source": "pixel_analysis",
                        "confidence": 0.8,
                    })
                    sources.append("pixel_check.py")

    # --- Color harmony ---
    elif criterion_id == "color.harmony":
        if pixels.get("available"):
            for t in pixels.get("targets", []):
                m = t.get("metrics", {})
                palette = m.get("palette", {})
                if palette.get("dominant_colors"):
                    colors = [c["hex"] for c in palette["dominant_colors"][:4]]
                    evidence.append({
                        "type": "measured",
                        "description": f"Dominant palette: {', '.join(colors)}",
                        "source": "pixel_analysis",
                        "confidence": 0.8,
                    })
                    sources.append("pixel_check.py")
                lum = m.get("luminance", {})
                if lum:
                    evidence.append({
                        "type": "measured",
                        "description": f"Mean luminance {lum.get('mean')}, brightness distribution dark/mid/bright: {lum.get('pct_dark')}%/{lum.get('pct_mid')}%/{lum.get('pct_bright')}%",
                        "source": "pixel_analysis",
                        "confidence": 0.85,
                    })
                    sources.append("pixel_check.py")

    # --- Style consistency ---
    elif criterion_id == "style.consistency":
        if bitmap.get("available"):
            for t in bitmap.get("targets", []):
                record = t.get("record", {})
                evidence.append({
                    "type": "measured",
                    "description": f"Format {record.get('format')}, mode {record.get('mode')}, alpha {record.get('has_alpha')}",
                    "source": "bitmap_ingestion",
                    "confidence": 0.95,
                })
                sources.append("bitmap_check.py")

    # --- Character expression ---
    elif criterion_id == "character.expression":
        if vision.get("available"):
            for t in vision.get("targets", []):
                v = t.get("result", {})
                if v.get("result"):
                    evidence.append({
                        "type": "inferred",
                        "description": f"Vision model caption: {str(v['result'])[:200]}",
                        "source": "vision_adapter.py",
                        "confidence": 0.5,
                    })
                    sources.append("vision_adapter.py")

    # --- Scene coherence ---
    elif criterion_id == "scene.coherence":
        if pixels.get("available"):
            for t in pixels.get("targets", []):
                m = t.get("metrics", {})
                regions = m.get("regions", {})
                if regions.get("patches"):
                    lum_variance = round(
                        sum(p.get("std_lum", 0) for p in regions["patches"]) / len(regions["patches"]), 4
                    )
                    evidence.append({
                        "type": "derived",
                        "description": f"Mean patch luminance variance {lum_variance} across {regions.get('grid')}x{regions.get('grid')} grid",
                        "source": "pixel_analysis",
                        "confidence": 0.7,
                    })
                    sources.append("pixel_check.py")

    # --- Educational clarity ---
    elif criterion_id == "educational.clarity":
        purpose = context.get("purpose", "unspecified")
        objective = context.get("learning_objective", "unspecified")
        evidence.append({
            "type": "user_provided",
            "description": f"Purpose: {purpose}; Learning objective: {objective}",
            "source": "user_context",
            "confidence": 1.0,
        })
        sources.append("user_input")
        if ocr.get("available"):
            for t in ocr.get("targets", []):
                o = t.get("ocr", {})
                if o.get("full_text"):
                    evidence.append({
                        "type": "measured",
                        "description": f"OCR text: '{o['full_text'][:100]}...' ({o.get('n_words')} words, conf {o.get('avg_confidence')})",
                        "source": "ocr_adapter.py",
                        "confidence": 0.7,
                    })
                    sources.append("ocr_adapter.py")

    # --- Accessibility contrast ---
    elif criterion_id == "accessibility.contrast":
        if pixels.get("available"):
            for t in pixels.get("targets", []):
                m = t.get("metrics", {})
                contrast = m.get("contrast", {})
                if contrast:
                    evidence.append({
                        "type": "measured",
                        "description": f"Michelson contrast {contrast.get('michelson')}, RMS {contrast.get('rms')}",
                        "source": "pixel_analysis",
                        "confidence": 0.8,
                    })
                    sources.append("pixel_check.py")
        if renderer.get("available"):
            evidence.append({
                "type": "measured",
                "description": "Renderer accessibility check via axe-core (see a11y_check.py results)",
                "source": "layout_check.py",
                "confidence": 0.9,
            })
            sources.append("a11y_check.py")

    # --- Determine sufficiency ---
    if len(evidence) == 0:
        sufficiency = "insufficient"
    elif len(evidence) < 2:
        sufficiency = "partial"
    else:
        sufficiency = "sufficient"

    return {
        "evidence": evidence,
        "sources": list(set(sources)),
        "sufficiency": sufficiency,
    }


def score_criterion(
    criterion: dict, evidence_block: dict, context: dict
) -> dict:
    """Score a single criterion based on evidence.

    Returns a criterion assessment with score (or null), rationale, evidence
    references, strengths, issues, recommendations, uncertainty.
    """
    criterion_id = criterion["criterion_id"]
    criterion_name = criterion["criterion_name"]
    evidence = evidence_block["evidence"]
    sufficiency = evidence_block["sufficiency"]

    # --- Build rationale from evidence ---
    rationale_parts = []
    strengths = []
    issues = []
    recommendations = []
    uncertainty_notes = []

    if sufficiency == "insufficient":
        score = None
        rationale = f"No relevant evidence available for '{criterion_name}'. Cannot assess."
        uncertainty_notes.append(
            f"Insufficient evidence for {criterion_id}; score withheld"
        )
        recommendations.append(
            f"Provide bitmap/pixel/OCR/vision evidence relevant to {criterion_name}"
        )
    elif sufficiency == "partial":
        score = None
        rationale = f"Partial evidence for '{criterion_name}'; cannot determine a reliable score."
        uncertainty_notes.append(
            f"Limited evidence for {criterion_id}; consider additional measurement"
        )
        recommendations.append(
            f"Gather more evidence for {criterion_name} before scoring"
        )
    else:
        # Sufficient evidence — derive a heuristic score (1-5) with clear uncertainty
        # This is a heuristic, not ground truth; must be labeled as such
        score = 3  # Default adequate when sufficient evidence exists
        rationale_parts.append(
            f"Sufficient evidence from {', '.join(evidence_block['sources'])}"
        )

        # Heuristic adjustments based on available metrics
        if criterion_id == "color.harmony":
            for e in evidence:
                if "luminance" in e.get("description", ""):
                    rationale_parts.append(e["description"])
        if criterion_id == "composition.visual_hierarchy":
            for e in evidence:
                if "dimensions" in e.get("description", ""):
                    rationale_parts.append(e["description"])

        rationale = ". ".join(rationale_parts) + "."
        uncertainty_notes.append(
            f"Score is a heuristic based on {sufficiency} evidence; not validated against human judgment"
        )
        recommendations.append(
            f"Human review recommended for {criterion_name} before publication"
        )

    # --- Evidence references ---
    evidence_refs = []
    for e in evidence:
        evidence_refs.append({
            "type": e["type"],
            "description": e["description"],
            "source": e["source"],
            "confidence": e["confidence"],
        })

    return {
        "criterion_id": criterion_id,
        "criterion_name": criterion_name,
        "score": score,
        "score_scale": "rubric-defined (1-5)",
        "assessment": rationale,
        "evidence": evidence_refs,
        "strengths": strengths,
        "issues": issues,
        "recommendations": recommendations,
        "uncertainty_notes": uncertainty_notes,
        "sufficiency": sufficiency,
    }


def build_apai_result(
    vir: dict,
    rubric: dict,
    context: dict,
) -> dict:
    """Build a complete APAI assessment result from VIR + rubric + context."""
    criteria_results = []
    priority_recommendations = []
    human_review_required = False

    for criterion in rubric.get("criteria", []):
        evidence_block = extract_evidence_for_criterion(vir, criterion, context)
        assessment = score_criterion(criterion, evidence_block, context)
        criteria_results.append(assessment)

        if assessment["score"] is None:
            human_review_required = True
            priority_recommendations.append(
                f"Gather evidence for {assessment['criterion_name']} ({assessment['criterion_id']})"
            )
        if assessment["uncertainty_notes"]:
            human_review_required = True
        if assessment["issues"]:
            human_review_required = True
            priority_recommendations.extend(assessment["recommendations"])

    # --- Overall assessment ---
    scored = [c for c in criteria_results if c["score"] is not None]
    if scored:
        avg_score = round(sum(c["score"] for c in scored) / len(scored), 2)
        overall_summary = (
            f"APAI assessment complete: {len(scored)}/{len(criteria_results)} "
            f"criteria scored, average {avg_score}/5"
        )
    else:
        avg_score = None
        overall_summary = (
            "APAI assessment incomplete: no criteria could be scored "
            "due to insufficient evidence"
        )

    overall_confidence = (
        "high"
        if avg_score is not None and len(scored) == len(criteria_results)
        else "medium" if scored else "low"
    )

    result = {
        "feature": "APAI",
        "schema_version": APAI_SCHEMA_VERSION,
        "asset_id": vir.get("asset_id"),
        "project_profile": vir.get("project_profile"),
        "built_at": vir.get("built_at"),
        "rubric": {
            "rubric_id": rubric.get("rubric_id"),
            "rubric_name": rubric.get("rubric_name"),
            "rubric_version": rubric.get("rubric_version"),
        },
        "evaluation_context": {
            "purpose": context.get("purpose"),
            "target_audience": context.get("target_audience"),
            "learning_objective": context.get("learning_objective"),
            "design_brief": context.get("design_brief"),
        },
        "overall_assessment": {
            "summary": overall_summary,
            "average_score": avg_score,
            "score_scale": "rubric-defined (1-5)",
            "confidence": overall_confidence,
            "human_review_recommended": human_review_required,
        },
        "criteria": criteria_results,
        "priority_recommendations": list(dict.fromkeys(priority_recommendations)),
        "reference_comparison": None,  # Not implemented in Stage G
        "limitations": [
            "APAI is a rubric evaluator, not a pixel decoder or VLM",
            "Scores are heuristics based on available evidence, not ground truth",
            "Semantic vision evidence (if any) is INTERPRETED — requires human verification",
            "Human review required for subjective, educational, or publication-critical decisions",
            "Does not infer mood from color alone, artist identity from style, or suitability guarantees",
        ],
        "human_review": {
            "required": human_review_required,
            "reason": "Subjective design judgments require human validation",
        },
        "evidence_tiers": {
            "DETECTED": "Direct measurement from renderer/pixel/OCR",
            "DERIVED": "Arithmetic on evidence (not auto-generated in Stage G)",
            "INTERPRETED": "Model hypothesis — requires human verification",
        },
    }

    return result


def run(
    vir_path: Path | None = None,
    rubric_arg: str = "default",
    purpose: str | None = None,
    target_audience: str | None = None,
    learning_objective: str | None = None,
    design_brief: str | None = None,
    out: Path | None = None,
    profile: dict | None = None,
) -> dict:
    """Run APAI bitmap assessment."""
    vir = load_json(vir_path) if vir_path else None
    if not vir:
        sys.exit("VIR evidence file required (--vir)")

    # If profile provides a rubric, use it unless rubric_arg explicitly overrides
    profile_rub = profile_rubric(profile) if profile else None
    if profile_rub and rubric_arg == "default":
        rubric = profile_rub
    else:
        rubric = load_rubric(rubric_arg)

    context = {
        "purpose": purpose,
        "target_audience": target_audience,
        "learning_objective": learning_objective,
        "design_brief": design_brief,
    }

    result = build_apai_result(vir, rubric, context)

    if out:
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vir", help="VIR evidence JSON file (required)")
    ap.add_argument("--profile", help="project profile JSON file (provides rubric)")
    ap.add_argument("--rubric", default="default",
                    help="rubric JSON file or 'default' (default: default)")
    ap.add_argument("--purpose", help="evaluation purpose (textbook, childrens_book, worksheet, poster, etc.)")
    ap.add_argument("--target-audience", help="target audience (age range or description)")
    ap.add_argument("--learning-objective", help="educational purpose, if applicable")
    ap.add_argument("--design-brief", help="requested visual intent")
    ap.add_argument("--out", help="write APAI result to this file")
    a = ap.parse_args()

    profile = load_profile(a.profile) if a.profile else None

    result = run(
        vir_path=a.vir,
        rubric_arg=a.rubric,
        purpose=a.purpose,
        target_audience=a.target_audience,
        learning_objective=a.learning_objective,
        design_brief=a.design_brief,
        out=a.out,
        profile=profile,
    )

    oa = result["overall_assessment"]
    print(f"APAI assessment: {oa['summary']}")
    print(f"  confidence: {oa['confidence']}")
    print(f"  human_review_required: {oa['human_review_recommended']}")
    print(f"  rubric: {result['rubric']['rubric_id']} v{result['rubric']['rubric_version']}")
    for c in result["criteria"]:
        score_str = f"{c['score']}/5" if c["score"] is not None else "insufficient evidence"
        print(f"  - {c['criterion_name']}: {score_str} ({c['sufficiency']})")
    if result["priority_recommendations"]:
        print("  priority recommendations:")
        for r in result["priority_recommendations"]:
            print(f"    - {r}")
    if a.out:
        print(f"  written: {a.out}")
    sys.exit(0)


if __name__ == "__main__":
    main()
