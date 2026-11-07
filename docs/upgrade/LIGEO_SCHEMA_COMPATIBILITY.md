# LiGeo Schema Compatibility Document
**Document ID:** LIGEO_SCHEMA_COMPATIBILITY.md  
**Version:** 1.0  
**Status:** COMPLETE  
**Source:** LiGeo_CPU_First_Vision_Upgrade_Controller.md §1 (Stage 0)

## Schema Compatibility Overview

The LiGeo Perception System uses a unified evidence chain and evidence tier system. All components must maintain schema compatibility to ensure interoperability between components.

## Schema Registry

| Schema | Version | Status | Components Using |
|--------|---------|--------|----------------|
| Evidence Envelope | 1.1.0 | Stable | All sensor outputs |
| VIR Schema | 1.1.0 | Stable | vir_builder.py, assessment modules |
| Asset ID Schema | 1.0.0 | Stable | All image processing modules |
| Profile Schema | 1.0.0 | Stable | profile_loader.py, profile configs |

## Evidence Tiers

| Tier | Definition | Usage |
|------|------------|-------|
| DETECTED | Direct measurement from renderer/pixel/OCR | Ground truth measurements |
| DERIVED | Arithmetic on evidence — requires re-measurement after edits | Derived metrics |
| INTERPRETED | Model hypothesis — requires human review | Model hypotheses |

## Evidence Contract

All probes return the same envelope:
```json
{
  "target": "string",
  "probe": "string",
  "root": {"x": number, "y": 0, "w": number, "h": number},
  "issues": [{"t": string, "det": string, "rect": {...}, "conf": number}]
}
```

## Compatibility Rules

1. **ID Stability**: Asset IDs must be SHA-256 hashes, deterministic
2. **Coordinate Space**: Canonical coordinates with origin top-left, X increases right, Y increases down
3. **Provenance Chain**: Source → Evidence → Claim → Content Block → Chapter → Book → Release
4. **Confidence Bands**: HIGH (≥0.90), MEDIUM (0.70-0.89), LOW (0.50-0.69), UNCERTAIN (<0.49)
5. **Bloom Level**: REMEMBER, UNDERSTAND, APPLY, ANALYZE, EVALUATE, CREATE
6. **Competency**: Specific competency identifiers

## Compliance Requirements

All sensors must:
1. Output evidence envelopes conforming to the schema
2. Use stable asset IDs (SHA-256 hashes)
3. Use canonical coordinate space
4. Preserve provenance chain
5. Use defined confidence bands
6. Document limitations
7. Never skip required validation
8. Treat generated content as reviewed content
9. Treat reviewed content as approved content
10. Treat approval of one artifact as approval of unrelated artifacts