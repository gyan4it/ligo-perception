#!/usr/bin/env python3
"""geometry_sensor.py — deterministic geometric measurement for LiGeo CV sensor pack.

Computes border detection, alignment, and simple diagram geometry measurements
using OpenCV. All outputs are DETECTED measurements — not semantic object
understanding.

  python tools/cv_sensors/geometry_sensor.py image.png
  python tools/cv_sensors/geometry_sensor.py images/ --json out.json

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


def analyze_geometry(path: Path) -> dict:
    """Compute deterministic geometric metrics from an image file."""
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)
        h, w = arr.shape[:2]
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # --- Border detection: check if edges are dark/empty (content border) ---
        # Sample border pixels (top, bottom, left, right 5% of image)
        border_px = max(5, min(h, w) // 20)
        top_border = gray[:border_px, :].ravel()
        bottom_border = gray[-border_px:, :].ravel()
        left_border = gray[:, :border_px].ravel()
        right_border = gray[:, -border_px:].ravel()
        all_border = np.concatenate([top_border, bottom_border, left_border, right_border])
        border_mean = float(all_border.mean())
        border_std = float(all_border.std())

        border_result = {
            "border_mean_intensity": round(border_mean, 4),
            "border_std_intensity": round(border_std, 4),
            "border_px_sampled": int(len(all_border)),
            "is_dark_border": border_mean < 50,
            "is_light_border": border_mean > 200,
            "method": "OpenCV, mean/std of border pixel rows/cols",
            "version": f"OpenCV {OPENCV_VERSION}, NumPy {np.__version__}",
            "interpretation": "Whether content is bordered by dark/light margins",
            "limitations": "Border definition is arbitrary (5% of min dimension)",
        }

        # --- Alignment: check if content is centered ---
        # Find non-zero (content) pixels via threshold
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        content_pixels = np.column_stack(np.where(thresh > 0))
        if len(content_pixels) > 0:
            content_center_y = float(content_pixels[:, 0].mean())
            content_center_x = float(content_pixels[:, 1].mean())
            image_center_y = h / 2.0
            image_center_x = w / 2.0
            center_offset_y = round(content_center_y - image_center_y, 4)
            center_offset_x = round(content_center_x - image_center_x, 4)
            alignment = {
                "content_center": [round(content_center_y, 4), round(content_center_x, 4)],
                "image_center": [round(image_center_y, 4), round(image_center_x, 4)],
                "offset_y": center_offset_y,
                "offset_x": center_offset_x,
                "content_px_count": int(len(content_pixels)),
                "method": "OpenCV threshold + centroid",
                "version": f"OpenCV {OPENCV_VERSION}, NumPy {np.__version__}",
                "interpretation": "Content centroid relative to image center",
                "limitations": "Content detection depends on threshold; not semantic",
            }
        else:
            alignment = {
                "content_center": None,
                "image_center": [round(h / 2.0, 4), round(w / 2.0, 4)],
                "offset_y": None,
                "offset_x": None,
                "content_px_count": 0,
                "method": "OpenCV threshold + centroid",
                "version": f"OpenCV {OPENCV_VERSION}, NumPy {np.__version__}",
                "interpretation": "No content detected above threshold",
                "limitations": "Threshold may miss low-contrast content",
            }

        # --- Simple diagram geometry: count rectangular contours ---
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rect_contours = 0
        rect_areas = []
        for c in contours:
            area = float(cv2.contourArea(c))
            if area > 100:  # filter tiny noise
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) == 4:  # rectangular
                    rect_contours += 1
                    rect_areas.append(area)
        geometry_result = {
            "rectangular_contour_count": rect_contours,
            "rect_contour_areas": [round(a, 4) for a in rect_areas[:20]],
            "total_rect_area": round(float(sum(rect_areas)), 4),
            "method": "OpenCV Canny + approxPolyDP",
            "version": f"OpenCV {OPENCV_VERSION}",
            "interpretation": "Detected rectangular regions",
            "limitations": "Not semantic objects; threshold-dependent",
        }

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "opencv_version": OPENCV_VERSION,
            "numpy_version": np.__version__,
            "pillow_version": PILLOW_VERSION,
            "border": border_result,
            "alignment": alignment,
            "geometry": geometry_result,
            "method_tier": "DETECTED",
            "evidence_tier_note": "All geometric metrics are DETECTED pixel measurements; "
                                  "not semantic object understanding",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "border": {},
        "alignment": {},
        "geometry": {},
        "method_tier": "DETECTED",
        "evidence_tier_note": "Image could not be decoded — no geometry metrics available",
    }


def run(targets, json_path: str | None = None):
    """Geometry audit of file/dir targets."""
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
            metrics = analyze_geometry(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag if no content detected
            if metrics["alignment"]["content_px_count"] == 0:
                entry["issues"].append({
                    "t": "GEOMETRY-NO-CONTENT",
                    "det": "no content pixels detected above threshold",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "GEOMETRY-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            border = m.get("border", {})
            align = m.get("alignment", {})
            geom = m.get("geometry", {})
            meta = f"  border_mean={border.get('border_mean_intensity', 0)} "
            meta += f"content_px={align.get('content_px_count', 0)} "
            meta += f"rects={geom.get('rectangular_contour_count', 0)}"
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
