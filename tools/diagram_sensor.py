#!/usr/bin/env python3
"""diagram_sensor.py — deterministic diagram analysis for LiGeo CV sensor pack.

Checks diagram-specific characteristics: label placement/overlap, arrow/connector
detection, line-art density, text-to-shape proximity, diagram bounds/crop.

  python tools/cv_sensors/diagram_sensor.py image.png
  python tools/cv_sensors/diagram_sensor.py images/ --json out.json

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


def analyze_diagram(path: Path) -> dict:
    """Compute deterministic diagram metrics from an image file."""
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)
        h, w = arr.shape[:2]
        total_px = h * w
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # --- Diagram bounds: content bounding box ---
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        coords = cv2.findNonZero(binary)
        if coords is not None and len(coords) > 0:
            x, y, cw, ch = cv2.boundingRect(coords)
            diagram_bounds = {
                "x": int(x),
                "y": int(y),
                "width": int(cw),
                "height": int(ch),
                "area": int(cw * ch),
                "center_x": round(float(x + cw / 2), 4),
                "center_y": round(float(y + ch / 2), 4),
                "fill_pct": round(float((cw * ch) / (w * h) * 100), 4) if w * h > 0 else 0.0,
            }
        else:
            diagram_bounds = {
                "x": 0, "y": 0, "width": 0, "height": 0,
                "area": 0,
                "center_x": 0.0, "center_y": 0.0,
                "fill_pct": 0.0,
            }

        # --- Crop detection: content touching image edges ---
        border_px = max(2, min(h, w) // 50)
        top_touch = int(binary[:border_px, :].sum() > 0)
        bottom_touch = int(binary[-border_px:, :].sum() > 0)
        left_touch = int(binary[:, :border_px].sum() > 0)
        right_touch = int(binary[:, -border_px:].sum() > 0)
        crop_result = {
            "top_touch": bool(top_touch),
            "bottom_touch": bool(bottom_touch),
            "left_touch": bool(left_touch),
            "right_touch": bool(right_touch),
            "touches_any_edge": bool(top_touch or bottom_touch or left_touch or right_touch),
            "method": "OpenCV, content pixels within border_px of image edge",
            "version": OPENCV_VERSION,
            "interpretation": "Whether diagram content is cropped by image edge",
            "limitations": "Border threshold is arbitrary (min dimension / 50)",
        }

        # --- Line-art density: edge pixels / total pixels ---
        edges = cv2.Canny(gray, 50, 150)
        edge_px = int((edges > 0).sum())
        line_art_density = {
            "edge_pixel_count": edge_px,
            "edge_density_pct": round(float(edge_px / total_px * 100), 4) if total_px > 0 else 0.0,
            "method": "OpenCV Canny edge density",
            "version": OPENCV_VERSION,
            "interpretation": "Proportion of pixels that are edge pixels",
            "limitations": "Threshold-dependent; not semantic line art",
        }

        # --- Arrow/connector detection: Hough lines with strong horizontal/vertical bias ---
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50, minLineLength=50, maxLineGap=10)
        horizontal_lines = 0
        vertical_lines = 0
        diagonal_lines = 0
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                dx = abs(x2 - x1)
                dy = abs(y2 - y1)
                if dx > dy * 2:
                    horizontal_lines += 1
                elif dy > dx * 2:
                    vertical_lines += 1
                else:
                    diagonal_lines += 1
        arrow_result = {
            "horizontal_line_count": horizontal_lines,
            "vertical_line_count": vertical_lines,
            "diagonal_line_count": diagonal_lines,
            "total_line_count": horizontal_lines + vertical_lines + diagonal_lines,
            "method": "OpenCV HoughLinesP with axis bias classification",
            "version": OPENCV_VERSION,
            "interpretation": "Straight line segments classified by orientation",
            "limitations": "Not semantic arrows/connectors; threshold-dependent",
        }

        # --- Text-to-shape proximity: text regions near shape boundaries ---
        # Use connected components of text-like regions (small, text-height boxes)
        text_like_components = []
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        for i in range(1, num_labels):
            x, y, cw, ch, area = stats[i]
            # Text-like: small height, reasonable width, not huge
            if 5 <= ch <= 40 and 10 <= cw <= 200 and area > 20:
                text_like_components.append({
                    "x": int(x), "y": int(y), "width": int(cw), "height": int(ch),
                    "area": int(area),
                })

        # Distance from each text component to nearest non-text edge pixel
        text_to_shape_distances = []
        for tc in text_like_components[:20]:  # cap at 20 for evidence size
            tx, y, tcw, tch = tc["x"], tc["y"], tc["width"], tc["height"]
            # Distance to nearest edge pixel
            min_dist = float("inf")
            for ey in range(max(0, y - 5), min(h, y + tch + 5)):
                for ex in range(max(0, x - 5), min(w, x + tcw + 5)):
                    if edges[ey, ex] > 0:
                        d = float(np.sqrt((ex - (x + tcw // 2)) ** 2 + (ey - (y + tch // 2)) ** 2))
                        min_dist = min(min_dist, d)
            if min_dist != float("inf"):
                text_to_shape_distances.append(round(min_dist, 4))

        text_proximity = {
            "text_component_count": len(text_like_components),
            "avg_text_to_edge_distance": round(float(np.mean(text_to_shape_distances)), 4) if text_to_shape_distances else 0.0,
            "min_text_to_edge_distance": round(float(min(text_to_shape_distances)), 4) if text_to_shape_distances else 0.0,
            "method": "OpenCV connected components + edge distance",
            "version": OPENCV_VERSION,
            "interpretation": "Proximity of text-like components to shape edges",
            "limitations": "Text detection is heuristic; not semantic text recognition",
        }

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "opencv_version": OPENCV_VERSION,
            "numpy_version": np.__version__,
            "pillow_version": PILLOW_VERSION,
            "diagram_bounds": diagram_bounds,
            "crop_detection": crop_result,
            "line_art_density": line_art_density,
            "arrow_connector": arrow_result,
            "text_proximity": text_proximity,
            "method_tier": "DETECTED",
            "evidence_tier_note": "All diagram metrics are DETECTED geometric measurements; "
                                  "not semantic diagram understanding",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "diagram_bounds": {},
        "crop_detection": {},
        "line_art_density": {},
        "arrow_connector": {},
        "text_proximity": {},
        "method_tier": "DETECTED",
        "evidence_tier_note": "Image could not be decoded — no diagram metrics available",
    }


def run(targets, json_path: str | None = None):
    """Diagram audit of file/dir targets."""
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
            metrics = analyze_diagram(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag diagrams touching edges (possible crop)
            crop = metrics.get("crop_detection", {})
            if crop.get("touches_any_edge"):
                entry["issues"].append({
                    "t": "DIAGRAM-CROP",
                    "det": "diagram content touches image edge — possible crop",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "DIAGRAM-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            bounds = m.get("diagram_bounds", {})
            crop = m.get("crop_detection", {})
            lines = m.get("arrow_connector", {})
            meta = f"  bounds={bounds.get('width', 0)}x{bounds.get('height', 0)} "
            meta += f"crop={crop.get('touches_any_edge', False)} "
            meta += f"lines={lines.get('total_line_count', 0)}"
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
