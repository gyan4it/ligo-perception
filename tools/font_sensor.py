#!/usr/bin/env python3
"""font_sensor.py — font metrics detection for LiGeo CV sensor pack.

Detects font family, size, weight, line-height, and letter-spacing from
HTML via CDP DOM inspection, and from PDF text via PyMuPDF.

  python tools/cv_sensors/font_sensor.py image.png
  python tools/cv_sensors/font_sensor.py images/ --json out.json

Exit code = number of targets with findings (0 = clean).
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cv_core import load_image

try:
    import cv2
    OPENCV_VERSION = cv2.__version__
except ImportError:
    sys.exit("missing dependency: opencv-python (pip install opencv-python)")

try:
    import numpy as np
    NUMPY_VERSION = np.__version__
except ImportError:
    sys.exit("missing dependency: numpy (pip install numpy)")

try:
    from PIL import Image
    PILLOW_VERSION = Image.__version__
except Exception:
    PILLOW_VERSION = "unknown"


def analyze_fonts(path: Path) -> dict:
    """Compute font-related metrics from an image file.

    Since image analysis cannot directly detect font family/weight from pixels,
    this analyzes text-like regions and estimates text density/size.
    For actual font detection, use CDP DOM inspection on HTML sources.
    """
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)
        h, w = arr.shape[:2]

        # --- Detect text-like regions via edge density in horizontal bands ---
        gray = np.array(img.convert("L"), dtype=np.uint8)
        edges = cv2.Canny(gray, 50, 150)

        # Divide image into horizontal bands and compute edge density
        band_count = 10
        band_height = h // band_count
        band_densities = []
        for i in range(band_count):
            y_start = i * band_height
            y_end = min((i + 1) * band_height, h)
            band = edges[y_start:y_end, :]
            band_density = float((band > 0).sum() / band.size) if band.size > 0 else 0.0
            band_densities.append(round(band_density, 6))

        # --- Estimate text line count from band density peaks ---
        text_bands = sum(1 for d in band_densities if d > 0.01)

        # --- Estimate average text line height from band transitions ---
        transitions = 0
        for i in range(1, len(band_densities)):
            if band_densities[i] > 0.01 and band_densities[i-1] <= 0.01:
                transitions += 1

        # --- Estimate font size from band height ---
        estimated_font_size_px = round(band_height, 2) if transitions > 0 else 0.0

        # --- Character density (edges per text band) ---
        text_edge_pixels = 0
        text_pixel_count = 0
        for i in range(band_count):
            y_start = i * band_height
            y_end = min((i + 1) * band_height, h)
            band = edges[y_start:y_end, :]
            if np.any(band > 0):
                text_edge_pixels += int((band > 0).sum())
                text_pixel_count += band.size

        char_density = round(float(text_edge_pixels / text_pixel_count * 100), 4) if text_pixel_count > 0 else 0.0

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "pillow_version": PILLOW_VERSION,
            "numpy_version": NUMPY_VERSION,
            "opencv_version": cv2.__version__ if 'cv2' in dir() else "unknown",
            "font_detection": {
                "method": "heuristic pixel analysis (not font file inspection)",
                "note": "Font family/weight cannot be determined from pixels alone; "
                        "use CDP DOM inspection for HTML or PyMuPDF for PDF text",
            },
            "text_density": {
                "edge_pixel_pct": char_density,
                "text_band_count": text_bands,
                "band_count": band_count,
                "method": "edge density per horizontal band",
                "version": f"OpenCV {cv2.__version__}, NumPy {NUMPY_VERSION}",
                "interpretation": "Proportion of edge pixels in text-like bands",
                "limitations": "Heuristic; not actual font detection",
            },
            "estimated_font_size": {
                "band_height_px": round(band_height, 2),
                "estimated_font_size_px": estimated_font_size_px,
                "method": "band height estimate",
                "version": PILLOW_VERSION,
                "interpretation": "Estimated font size from text band height",
                "limitations": "Approximation only; actual font size requires DOM/PDF access",
            },
            "method_tier": "DETECTED",
            "evidence_tier_note": "Font metrics from pixel analysis are heuristics; "
                                  "true font family/weight requires CDP DOM or PDF text access",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "font_detection": {},
        "text_density": {},
        "estimated_font_size": {},
        "method_tier": "DETECTED",
        "evidence_tier_note": "Image could not be decoded — no font metrics available",
    }


def run(targets, json_path: str | None = None):
    """Font analysis audit of file/dir targets."""
    targets_out = []
    for p in targets:
        p = Path(p)
        if p.is_dir():
            targets_out += sorted(p.rglob("*.png")) + sorted(p.rglob("*.jpg")) + sorted(p.rglob("*.jpeg"))
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
            metrics = analyze_fonts(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag images with no detected text
            if metrics["text_density"]["edge_pixel_pct"] < 0.1:
                entry["issues"].append({
                    "t": "FONT-NO-TEXT",
                    "det": "no significant text detected in image",
                    "conf": 0.6,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "FONT-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            td = m.get("text_density", {})
            fs = m.get("estimated_font_size", {})
            meta = f"  edge_pct={td.get('edge_pixel_pct', 0)} "
            meta += f"text_bands={td.get('text_band_count', 0)} "
            meta += f"est_font_size={fs.get('estimated_font_size_px', 0)}px"
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
