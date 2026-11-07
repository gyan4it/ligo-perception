#!/usr/bin/env python3
"""region_sensor.py — deterministic region segmentation for LiGeo CV sensor pack.

Computes thresholding, connected components, morphology, and color-region
segmentation statistics using OpenCV. All outputs are DETECTED measurements.

  python tools/cv_sensors/region_sensor.py image.png
  python tools/cv_sensors/region_sensor.py images/ --json out.json

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


def analyze_regions(path: Path) -> dict:
    """Compute deterministic region segmentation metrics from an image file."""
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape

        # --- Global thresholding (Otsu) ---
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        foreground_px = int((binary > 0).sum())
        total_px = binary.shape[0] * binary.shape[1]
        foreground_pct = round(float(foreground_px / total_px * 100), 4) if total_px > 0 else 0.0

        threshold_result = {
            "foreground_pixel_count": foreground_px,
            "foreground_pct": foreground_pct,
            "background_pct": round(100.0 - foreground_pct, 4),
            "method": "OpenCV, Otsu global thresholding",
            "version": OPENCV_VERSION,
            "interpretation": "Foreground/background separation by intensity",
            "limitations": "Global threshold; not content-aware regions",
        }

        # --- Connected components ---
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        # Exclude background (label 0)
        component_areas = stats[1:, cv2.CC_STAT_AREA] if num_labels > 1 else np.array([])
        component_sizes = sorted([int(a) for a in component_areas], reverse=True)

        components_result = {
            "component_count": int(num_labels - 1) if num_labels > 1 else 0,
            "total_component_area": round(float(sum(component_areas)), 4) if len(component_areas) > 0 else 0.0,
            "largest_component_area": round(float(max(component_areas)), 4) if len(component_areas) > 0 else 0.0,
            "top_component_areas": component_sizes[:20],
            "method": "OpenCV connectedComponentsWithStats, connectivity=8",
            "version": OPENCV_VERSION,
            "interpretation": "Connected foreground regions",
            "limitations": "Not semantic objects; threshold-dependent",
        }

        # --- Morphology: morphological gradient (edge-ish) ---
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph_grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)
        morph_px = int((morph_grad > 0).sum())
        morphology_result = {
            "morphological_gradient_pixel_count": morph_px,
            "morphological_gradient_pct": round(float(morph_px / total_px * 100), 4) if total_px > 0 else 0.0,
            "kernel_size": [3, 3],
            "method": "OpenCV morphologyEx, MORPH_GRADIENT",
            "version": OPENCV_VERSION,
            "interpretation": "Edge-like regions from morphological gradient",
            "limitations": "Kernel size dependent; not semantic edges",
        }

        # --- Color-region segmentation: simple k-means on RGB ---
        try:
            pixels = arr.reshape((-1, 3)).astype(np.float32)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            k = 3  # 3 color clusters
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
            cluster_sizes = sorted([int((labels == i).sum()) for i in range(k)], reverse=True)
            kmeans_result = {
                "cluster_count": k,
                "cluster_sizes": cluster_sizes,
                "cluster_centers": [[round(float(c[0]), 2), round(float(c[1]), 2), round(float(c[2]), 2)] for c in centers],
                "method": "OpenCV kmeans, k=3, RGB space",
                "version": OPENCV_VERSION,
                "interpretation": "Dominant color clusters",
                "limitations": "Not semantic regions; k is arbitrary",
            }
        except cv2.error as e:
            kmeans_result = {
                "error": str(e)[:200],
                "method": "OpenCV kmeans",
                "version": OPENCV_VERSION,
            }

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "opencv_version": OPENCV_VERSION,
            "numpy_version": np.__version__,
            "pillow_version": PILLOW_VERSION,
            "threshold": threshold_result,
            "components": components_result,
            "morphology": morphology_result,
            "color_clusters": kmeans_result,
            "method_tier": "DETECTED",
            "evidence_tier_note": "All region metrics are DETECTED pixel measurements; "
                                  "regions are not semantic objects",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "threshold": {},
        "components": {},
        "morphology": {},
        "color_clusters": {},
        "method_tier": "DETECTED",
        "evidence_tier_note": "Image could not be decoded — no region metrics available",
    }


def run(targets, json_path: str | None = None):
    """Region segmentation audit of file/dir targets."""
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
            metrics = analyze_regions(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag images with very few components (completely uniform)
            if metrics["components"]["component_count"] < 2:
                entry["issues"].append({
                    "t": "REGION-FEW-COMPONENTS",
                    "det": f"only {metrics['components']['component_count']} connected component(s) detected",
                    "conf": 0.6,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "REGION-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            thresh = m.get("threshold", {})
            comps = m.get("components", {})
            morph = m.get("morphology", {})
            meta = f"  fg_pct={thresh.get('foreground_pct', 0)} "
            meta += f"comps={comps.get('component_count', 0)} morph={morph.get('morphological_gradient_pct', 0)}%"
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
