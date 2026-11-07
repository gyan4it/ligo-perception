#!/usr/bin/env python3
"""edge_sensor.py — deterministic edge/line detection for LiGeo CV sensor pack.

Computes Canny edges, Sobel gradients, Hough lines, and contour statistics
using OpenCV. All outputs are DETECTED measurements — edges are not
semantic object boundaries.

  python tools/cv_sensors/edge_sensor.py image.png
  python tools/cv_sensors/edge_sensor.py images/ --json out.json

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


def analyze_edges(path: Path) -> dict:
    """Compute deterministic edge metrics from an image file."""
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # --- Canny edge detection ---
        canny_low = 50
        canny_high = 150
        edges = cv2.Canny(gray, canny_low, canny_high)
        edge_pixel_count = int((edges > 0).sum())
        total_pixels = edges.shape[0] * edges.shape[1]
        edge_density_pct = round(float(edge_pixel_count / total_pixels * 100), 4) if total_pixels > 0 else 0.0

        canny_result = {
            "edge_pixel_count": edge_pixel_count,
            "edge_density_pct": edge_density_pct,
            "low_threshold": canny_low,
            "high_threshold": canny_high,
            "method": "OpenCV Canny",
            "version": f"OpenCV {OPENCV_VERSION}",
            "interpretation": "Edge presence and density",
            "limitations": "Sensitive to threshold; not semantic edges",
        }

        # --- Sobel gradients ---
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_mag = np.sqrt(sobelx ** 2 + sobely ** 2)
        grad_dir = np.arctan2(sobely, sobelx)
        sobel_result = {
            "mean_gradient_magnitude": round(float(grad_mag.mean()), 4),
            "max_gradient_magnitude": round(float(grad_mag.max()), 4),
            "mean_gradient_direction": round(float(grad_dir.mean()), 4),
            "method": "OpenCV Sobel, ksize=3",
            "version": f"OpenCV {OPENCV_VERSION}, NumPy {np.__version__}",
            "interpretation": "Gradient strength and direction",
            "limitations": "Global measure; not object boundaries",
        }

        # --- Hough line detection ---
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=50, maxLineGap=10)
        line_segments = []
        if lines is not None:
            for line in lines[:100]:  # cap at 100 for evidence size
                x1, y1, x2, y2 = line[0]
                length = float(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))
                angle = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
                line_segments.append({
                    "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2),
                    "length": round(length, 2),
                    "angle_deg": round(angle, 2),
                })
        hough_result = {
            "line_count": len(line_segments),
            "lines": line_segments,
            "method": "OpenCV HoughLinesP",
            "version": f"OpenCV {OPENCV_VERSION}",
            "interpretation": "Detected straight line segments",
            "limitations": "Not semantic object boundaries; threshold-dependent",
        }

        # --- Contour extraction ---
        contours, hierarchy = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour_areas = [float(cv2.contourArea(c)) for c in contours]
        contour_result = {
            "contour_count": len(contours),
            "total_contour_area": round(float(sum(contour_areas)), 4),
            "mean_contour_area": round(float(np.mean(contour_areas)), 4) if contour_areas else 0.0,
            "max_contour_area": round(float(max(contour_areas)), 4) if contour_areas else 0.0,
            "method": "OpenCV findContours, RETR_EXTERNAL",
            "version": f"OpenCV {OPENCV_VERSION}",
            "interpretation": "Closed region boundaries from edges",
            "limitations": "Not semantic objects; sensitive to edge noise",
        }

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "opencv_version": OPENCV_VERSION,
            "numpy_version": np.__version__,
            "pillow_version": PILLOW_VERSION,
            "canny": canny_result,
            "sobel": sobel_result,
            "hough_lines": hough_result,
            "contours": contour_result,
            "method_tier": "DETECTED",
            "evidence_tier_note": "All edge metrics are DETECTED pixel measurements; "
                                  "edges are not semantic object boundaries",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "canny": {},
        "sobel": {},
        "hough_lines": {},
        "contours": {},
        "method_tier": "DETECTED",
        "evidence_tier_note": "Image could not be decoded — no edge metrics available",
    }


def run(targets, json_path: str | None = None):
    """Edge detection audit of file/dir targets."""
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
            metrics = analyze_edges(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag images with no detected edges (completely uniform)
            if metrics["canny"]["edge_density_pct"] < 0.1:
                entry["issues"].append({
                    "t": "EDGE-NO-EDGES",
                    "det": "no significant edges detected",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "EDGE-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            canny = m.get("canny", {})
            hough = m.get("hough_lines", {})
            contours = m.get("contours", {})
            meta = f"  edges={canny.get('edge_density_pct', 0)}% "
            meta += f"lines={hough.get('line_count', 0)} contours={contours.get('contour_count', 0)}"
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
