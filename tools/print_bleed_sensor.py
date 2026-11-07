#!/usr/bin/env python3
"""print_bleed_sensor.py — print bleed and crop mark detection for LiGeo CV sensor pack.

Analyzes PDF/page geometry for bleed margins, crop marks, and print-safe areas.

  python tools/cv_sensors/print_bleed_sensor.py image.png
  python tools/cv_sensors/print_bleed_sensor.py images/ --json out.json

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


def analyze_bleed(path: Path) -> dict:
    """Analyze print bleed and crop marks from an image file.

    Detects:
    - Crop marks (corner registration marks)
    - Bleed area (content extending to page edge)
    - Safe area (content staying within safe margin)
    - Trim marks
    """
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)
        h, w = arr.shape[:2]
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # --- Bleed detection: content touching page edges ---
        border_px = max(5, min(h, w) // 50)
        top_touch = int(gray[:border_px, :].sum() > 0)
        bottom_touch = int(gray[-border_px:, :].sum() > 0)
        left_touch = int(gray[:, :border_px].sum() > 0)
        right_touch = int(gray[:, -border_px:].sum() > 0)
        bleed = {
            "top_touch": bool(top_touch),
            "bottom_touch": bool(bottom_touch),
            "left_touch": bool(left_touch),
            "right_touch": bool(right_touch),
            "touches_any_edge": bool(top_touch or bottom_touch or left_touch or right_touch),
            "border_px": border_px,
            "method": "OpenCV, content pixels within border_px of image edge",
            "version": OPENCV_VERSION,
            "interpretation": "Whether content extends to page edge (bleed)",
            "limitations": "Border threshold is arbitrary",
        }

        # --- Crop mark detection: L-shaped marks at corners ---
        crop_marks = []
        corner_size = max(10, min(h, w) // 20)
        corners = {
            "top_left": gray[:corner_size, :corner_size],
            "top_right": gray[:corner_size, -corner_size:],
            "bottom_left": gray[-corner_size:, :corner_size],
            "bottom_right": gray[-corner_size:, -corner_size:],
        }
        for corner_name, corner_region in corners.items():
            dark_pixels = int((corner_region < 100).sum())
            total_pixels = corner_region.size
            dark_pct = round(float(dark_pixels / total_pixels * 100), 4) if total_pixels > 0 else 0.0
            crop_marks.append({
                "corner": corner_name,
                "dark_pixel_pct": dark_pct,
                "has_crop_mark": dark_pct > 30,  # Threshold for crop mark presence
            })

        # --- Safe area check: content within safe margin ---
        safe_margin_px = max(10, min(h, w) // 25)
        inner_region = gray[safe_margin_px:-safe_margin_px, safe_margin_px:-safe_margin_px]
        inner_dark_pixels = int((inner_region < 100).sum())
        inner_total = inner_region.size
        safe_area_pct = round(float(inner_dark_pixels / inner_total * 100), 4) if inner_total > 0 else 0.0

        safe_area = {
            "safe_margin_px": safe_margin_px,
            "content_in_safe_area_pct": safe_area_pct,
            "content_outside_safe_pct": round(100.0 - safe_area_pct, 4),
            "method": "OpenCV, content within safe margin from page edges",
            "version": OPENCV_VERSION,
            "interpretation": "Percentage of content within safe print area",
            "limitations": "Safe margin is arbitrary; actual bleed requirements vary by printer",
        }

        # --- Overall bleed assessment ---
        total_dark_pixels = int((gray < 100).sum())
        total_pixels = gray.size
        total_dark_pct = round(float(total_dark_pixels / total_pixels * 100), 4) if total_pixels > 0 else 0.0

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "opencv_version": OPENCV_VERSION,
            "numpy_version": NUMPY_VERSION,
            "pillow_version": PILLOW_VERSION,
            "page_size": {"width_px": w, "height_px": h},
            "bleed": bleed,
            "crop_marks": crop_marks,
            "safe_area": safe_area,
            "total_dark_pct": total_dark_pct,
            "method": "OpenCV, pixel-based bleed and margin detection",
            "version": f"OpenCV {OPENCV_VERSION}, NumPy {NUMPY_VERSION}, Pillow {PILLOW_VERSION}",
            "interpretation": "Print bleed, crop marks, and safe area from pixel analysis",
            "limitations": "Pixel-based detection; actual print requirements vary by printer",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "page_size": {},
        "bleed": {},
        "crop_marks": [],
        "safe_area": {},
        "total_dark_pct": 0.0,
        "method": "OpenCV, pixel-based bleed detection",
        "version": OPENCV_VERSION if 'OPENCV_VERSION' in globals() else "unknown",
        "interpretation": "Image could not be decoded — no bleed metrics available",
        "evidence_tier_note": "Image could not be decoded — no bleed metrics available",
    }


def run(targets, json_path: str | None = None):
    """Bleed/crop audit of file/dir targets."""
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
            metrics = analyze_bleed(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag content touching edges (bleed issues)
            if metrics["bleed"]["touches_any_edge"]:
                entry["issues"].append({
                    "t": "BLEED-TOUCHES-EDGE",
                    "det": "content touches page edge — possible bleed issue",
                    "conf": 0.7,
                })
            # Flag content outside safe area
            if metrics["safe_area"]["content_outside_safe_pct"] > 10:
                entry["issues"].append({
                    "t": "BLEED-CONTENT-OUTSIDE-SAFE",
                    "det": f"{metrics['safe_area']['content_outside_safe_pct']}% content outside safe margin",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "BLEED-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            bleed = m.get("bleed", {})
            safe = m.get("safe_area", {})
            meta = f"  bleed_edges={bleed.get('touches_any_edge', False)} "
            meta += f"safe_area_pct={safe.get('content_outside_safe_pct', 0)}% "
            meta += f"total_dark={m.get('total_dark_pct', 0)}%"
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
