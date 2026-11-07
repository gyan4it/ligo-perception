#!/usr/bin/env python3
"""document_sensor.py — deterministic document geometry for LiGeo CV sensor pack.

Computes document page geometry, skew detection, margin estimation, and
content region analysis using OpenCV. All outputs are DETECTED measurements.

  python tools/cv_sensors/document_sensor.py image.png
  python tools/cv_sensors/document_sensor.py images/ --json out.json

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


def analyze_document(path: Path) -> dict:
    """Compute deterministic document geometry metrics from an image file."""
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)
        h, w = arr.shape[:2]
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # --- Page size and orientation ---
        page_result = {
            "width_px": int(w),
            "height_px": int(h),
            "aspect_ratio": round(w / h, 6) if h else 0,
            "orientation": "landscape" if w > h else "portrait" if h > w else "square",
            "method": "Pillow Image.size",
            "version": PILLOW_VERSION,
        }

        # --- Content bounding box ---
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        coords = cv2.findNonZero(binary)
        if coords is not None and len(coords) > 0:
            x, y, cw, ch = cv2.boundingRect(coords)
            content_box = {
                "x": int(x),
                "y": int(y),
                "width": int(cw),
                "height": int(ch),
                "area": int(cw * ch),
                "center_x": round(float(x + cw / 2), 4),
                "center_y": round(float(y + ch / 2), 4),
                "method": "OpenCV findNonZero + boundingRect",
                "version": OPENCV_VERSION,
            }
        else:
            content_box = {
                "x": 0, "y": 0, "width": 0, "height": 0,
                "area": 0,
                "center_x": 0.0, "center_y": 0.0,
                "method": "OpenCV findNonZero + boundingRect",
                "version": OPENCV_VERSION,
            }

        # --- Margins (content distance from page edges) ---
        margins = {
            "top_margin_px": int(content_box["y"]),
            "bottom_margin_px": int(h - content_box["y"] - content_box["height"]),
            "left_margin_px": int(content_box["x"]),
            "right_margin_px": int(w - content_box["x"] - content_box["width"]),
            "method": "OpenCV content bounding box vs page edges",
            "version": OPENCV_VERSION,
        }

        # --- Skew detection: Hough lines on edges ---
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
        angles = []
        if lines is not None:
            for line in lines[:200]:
                x1, y1, x2, y2 = line[0]
                angle = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
                # Normalize to [-90, 90]
                while angle > 90:
                    angle -= 180
                while angle < -90:
                    angle += 180
                angles.append(angle)
        if angles:
            mean_angle = float(np.mean(angles))
            std_angle = float(np.std(angles))
        else:
            mean_angle = 0.0
            std_angle = 0.0
        skew_result = {
            "skew_angle_deg": round(mean_angle, 4),
            "skew_std_deg": round(std_angle, 4),
            "line_count": len(angles),
            "method": "OpenCV Canny + HoughLinesP",
            "version": OPENCV_VERSION,
            "interpretation": "Dominant line angle as skew estimate",
            "limitations": "Not reliable on images without strong horizontal lines",
        }

        # --- Content density ---
        total_px = w * h
        content_density = {
            "content_pixel_pct": round(float((binary > 0).sum() / total_px * 100), 4),
            "content_box_pct": round(float((cw * ch) / (w * h) * 100), 4) if w * h > 0 else 0.0,
            "method": "OpenCV threshold + bounding box",
            "version": OPENCV_VERSION,
        }

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "opencv_version": OPENCV_VERSION,
            "numpy_version": np.__version__,
            "pillow_version": PILLOW_VERSION,
            "page": page_result,
            "content_box": content_box,
            "margins": margins,
            "skew": skew_result,
            "content_density": content_density,
            "method_tier": "DETECTED",
            "evidence_tier_note": "All document metrics are DETECTED geometric measurements; "
                                  "not semantic document structure",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "page": {},
        "content_box": {},
        "margins": {},
        "skew": {},
        "content_density": {},
        "method_tier": "DETECTED",
        "evidence_tier_note": "Image could not be decoded — no document metrics available",
    }


def run(targets, json_path: str | None = None):
    """Document geometry audit of file/dir targets."""
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
            metrics = analyze_document(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag significant skew
            skew_angle = abs(metrics["skew"]["skew_angle_deg"])
            if skew_angle > 5.0:
                entry["issues"].append({
                    "t": "DOCUMENT-SKEW",
                    "det": f"skew angle {skew_angle} degrees exceeds 5 degree threshold",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "DOCUMENT-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            page = m.get("page", {})
            skew = m.get("skew", {})
            margins = m.get("margins", {})
            meta = f"  {page.get('width_px', 0)}x{page.get('height_px', 0)} "
            meta += f"skew={skew.get('skew_angle_deg', 0)}deg "
            meta += f"margins(t={margins.get('top_margin_px', 0)},l={margins.get('left_margin_px', 0)})"
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
