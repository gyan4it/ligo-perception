#!/usr/bin/env python3
"""icc_sensor.py — ICC color profile detection for LiGeo CV sensor pack.

Detects embedded ICC color profiles in images and PDFs, reports color space,
and flags missing profiles.

  python tools/cv_sensors/icc_sensor.py image.png
  python tools/cv_sensors/icc_sensor.py images/ --json out.json

Exit code = number of targets with findings (0 = clean).
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cv_core import load_image

try:
    from PIL import Image
    PILLOW_VERSION = Image.__version__
except Exception:
    PILLOW_VERSION = "unknown"


def analyze_icc(path: Path) -> dict:
    """Analyze ICC color profile from an image file.

    Extracts:
    - ICC profile presence
    - Color mode/space
    - Bit depth
    - Alpha channel presence
    """
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        # --- ICC profile detection ---
        icc_profile = img.info.get("icc_profile")
        has_icc = icc_profile is not None and len(icc_profile) > 0

        # --- Color mode analysis ---
        mode = img.mode
        mode_info = {
            "1": "1-bit (black and white)",
            "L": "8-bit grayscale",
            "P": "8-bit palette",
            "RGB": "8-bit RGB",
            "RGBA": "8-bit RGBA",
            "CMYK": "8-bit CMYK",
            "YCbCr": "8-bit YCbCr",
            "LAB": "8-bit LAB",
            "HSV": "8-bit HSV",
            "I": "32-bit signed integer",
            "F": "32-bit floating point",
        }.get(mode, f"unknown ({mode})")

        # --- Bit depth estimation ---
        bit_depth = {
            "1": 1,
            "L": 8,
            "P": 8,
            "RGB": 24,
            "RGBA": 32,
            "CMYK": 32,
            "YCbCr": 24,
            "LAB": 24,
            "HSV": 24,
            "I": 32,
            "F": 32,
        }.get(mode, 0)

        # --- Alpha channel ---
        has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info

        # --- Color space classification ---
        if mode in ("RGB", "RGBA"):
            color_space = "RGB"
        elif mode in ("CMYK",):
            color_space = "CMYK"
        elif mode in ("L", "1"):
            color_space = "Grayscale"
        elif mode == "P":
            color_space = "Palette"
        elif mode in ("YCbCr",):
            color_space = "YCbCr"
        elif mode in ("LAB",):
            color_space = "Lab"
        else:
            color_space = "Unknown"

        # --- Color profile assessment ---
        has_profile = has_icc
        profile_info = {
            "has_icc_profile": has_icc,
            "icc_size_bytes": len(icc_profile) if icc_profile else 0,
            "profile_present": has_icc,
        }

        # --- Overall assessment ---
        needs_profile = False
        if mode in ("RGB", "RGBA", "CMYK") and not has_icc:
            needs_profile = True  # Color images should have ICC profile

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "pillow_version": PILLOW_VERSION,
            "image_mode": mode,
            "mode_info": mode_info,
            "bit_depth": bit_depth,
            "color_space": color_space,
            "has_alpha": has_alpha,
            "has_icc_profile": has_icc,
            "icc_profile_size_bytes": len(icc_profile) if icc_profile else 0,
            "needs_icc_profile": needs_profile,
            "method": "Pillow image metadata inspection",
            "version": PILLOW_VERSION,
            "interpretation": "ICC profile and color space detection from image metadata",
            "limitations": "ICC profile presence detected but profile content not parsed",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "image_mode": None,
        "mode_info": None,
        "bit_depth": None,
        "color_space": None,
        "has_alpha": False,
        "has_icc_profile": False,
        "icc_profile_size_bytes": 0,
        "needs_icc_profile": False,
        "method": "Pillow image metadata inspection",
        "version": PILLOW_VERSION,
        "interpretation": "Image could not be decoded — no ICC profile analysis available",
        "evidence_tier_note": "Image could not be decoded — no ICC profile analysis available",
    }


def run(targets, json_path: str | None = None):
    """ICC profile audit of file/dir targets."""
    targets_out = []
    for p in targets:
        p = Path(p)
        if p.is_dir():
            targets_out += sorted(p.rglob("*.png")) + sorted(p.rglob("*.jpg")) + sorted(p.rglob("*.jpeg")) + sorted(p.rglob("*.tif")) + sorted(p.rglob("*.tiff"))
        elif p.exists():
            targets_out.append(p)
        else:
            sys.exit(f"no such target: {p}")
    seen, uniq = set(), []
    for f in targets_out:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            uniq.append(f)

    report, dirty = [], 0
    for f in uniq:
        try:
            metrics = analyze_icc(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag images without ICC profile (for color images)
            if metrics.get("needs_icc_profile"):
                entry["issues"].append({
                    "t": "ICC-MISSING",
                    "det": f"color image ({metrics['color_space']}) missing ICC profile",
                    "conf": 0.8,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "ICC-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
            ]}
            dirty += 1
        report.append(entry)

    if json_path and report:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report, dirty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--json", help="write full evidence to this file")
    a = ap.parse_args()

    report, dirty = run(a.targets, json_path=a.json)

    for entry in report:
        m = entry.get("metrics")
        n = len(entry.get("issues", []))
        if m:
            meta = f"  mode={m.get('image_mode', '?')} color_space={m.get('color_space', '?')} "
            meta += f"icc={m.get('has_icc_profile', False)} bit_depth={m.get('bit_depth', 0)}"
        else:
            meta = "  (no metrics)"
        print(("!! " if n else "OK ") + entry["file"] + meta)
        for iss in entry.get("issues", []):
            print(f"     - [{iss.get('t')} conf {iss.get('conf', 0):.2f}] {iss.get('det')}")

    if a.json:
        print(f"\nevidence written: {a.json}")
    print(f"\nTARGETS: {len(report)}  DIRTY: {dirty}")
    sys.exit(min(dirty, 1))


if __name__ == "__main__":
    main()
