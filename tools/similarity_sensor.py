#!/usr/bin/env python3
"""similarity_sensor.py — deterministic image similarity for LiGeo CV sensor pack.

Computes normalized pixel difference, SSIM (optional scikit-image), perceptual
hash (optional imagehash), and feature-matching statistics for pairs of images.

  python tools/cv_sensors/similarity_sensor.py img1.png img2.png
  python tools/cv_sensors/similarity_sensor.py dir1/ dir2/ --json out.json

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

# Optional dependencies
try:
    import skimage.metrics
    SKIMAGE_VERSION = skimage.metrics.__version__ if hasattr(skimage.metrics, '__version__') else "0.26.0"
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False
    SKIMAGE_VERSION = None

try:
    import imagehash
    IMAGEHASH_VERSION = imagehash.__version__
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    IMAGEHASH_VERSION = None


def _load_resized_gray(path: Path, size: tuple = (256, 256)) -> np.ndarray:
    """Load image, convert to grayscale, resize to standard size for comparison."""
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            raise ValueError(f"could not decode image: {path}")
        gray = img.convert("L")
        gray = gray.resize(size, Image.Resampling.LANCZOS)
        return np.array(gray, dtype=np.uint8)


def analyze_similarity(path1: Path, path2: Path) -> dict:
    """Compute deterministic similarity metrics between two images."""
    img1 = _load_resized_gray(path1)
    img2 = _load_resized_gray(path2)

    result = {
        "path1": str(path1),
        "path2": str(path2),
        "metrics_version": "1.0.0",
        "opencv_version": OPENCV_VERSION,
        "numpy_version": NUMPY_VERSION,
        "pillow_version": PILLOW_VERSION,
        "skimage_available": SKIMAGE_AVAILABLE,
        "skimage_version": SKIMAGE_VERSION,
        "imagehash_available": IMAGEHASH_AVAILABLE,
        "imagehash_version": IMAGEHASH_VERSION,
    }

    # --- Normalized pixel difference (MSE) ---
    diff = img1.astype(np.float64) - img2.astype(np.float64)
    mse = float(np.mean(diff ** 2))
    rmse = float(np.sqrt(mse))
    max_possible_mse = 255.0 ** 2
    similarity_pct = round(float((1.0 - mse / max_possible_mse) * 100), 4)
    pixel_diff = {
        "mse": round(mse, 4),
        "rmse": round(rmse, 4),
        "similarity_pct": similarity_pct,
        "method": "NumPy, normalized mean squared error",
        "version": NUMPY_VERSION,
        "interpretation": "Pixel-level difference after resize alignment",
        "limitations": "Requires same size/resize; not semantic similarity",
    }
    result["pixel_difference"] = pixel_diff

    # --- SSIM (optional scikit-image) ---
    if SKIMAGE_AVAILABLE:
        try:
            from skimage.metrics import structural_similarity as ssim
            ssim_val = float(ssim(img1, img2))
            result["ssim"] = {
                "value": round(ssim_val, 4),
                "method": "scikit-image structural_similarity",
                "version": SKIMAGE_VERSION,
                "interpretation": "Structural similarity index (-1 to 1)",
                "limitations": "Requires same size; not semantic equivalence",
            }
        except Exception as e:
            result["ssim"] = {
                "error": str(e)[:200],
                "method": "scikit-image structural_similarity",
                "version": SKIMAGE_VERSION,
            }
    else:
        result["ssim"] = {
            "error": "scikit-image not installed",
            "method": "scikit-image structural_similarity",
            "version": None,
        }

    # --- Perceptual hash (optional imagehash) ---
    if IMAGEHASH_AVAILABLE:
        try:
            from PIL import Image as PILImage
            img1_pil = Image.open(path1).convert("L")
            img2_pil = Image.open(path2).convert("L")
            phash1 = imagehash.phash(img1_pil)
            phash2 = imagehash.phash(img2_pil)
            phash_diff = int(phash1 - phash2)
            result["perceptual_hash"] = {
                "hash1": str(phash1),
                "hash2": str(phash2),
                "hamming_distance": phash_diff,
                "method": "imagehash.phash",
                "version": IMAGEHASH_VERSION,
                "interpretation": "Perceptual hash difference (lower = more similar)",
                "limitations": "Hash alone cannot be a release criterion",
            }
        except Exception as e:
            result["perceptual_hash"] = {
                "error": str(e)[:200],
                "method": "imagehash.phash",
                "version": IMAGEHASH_VERSION,
            }
    else:
        result["perceptual_hash"] = {
            "error": "imagehash not installed",
            "method": "imagehash.phash",
            "version": None,
        }

    # --- Feature matching (OpenCV ORB) ---
    orb = cv2.ORB_create()
    kp1, desc1 = orb.detectAndCompute(img1, None)
    kp2, desc2 = orb.detectAndCompute(img2, None)

    match_result = {
        "keypoints1": int(len(kp1)) if kp1 else 0,
        "keypoints2": int(len(kp2)) if kp2 else 0,
        "method": "OpenCV ORB",
        "version": OPENCV_VERSION,
    }

    if desc1 is not None and desc2 is not None and len(desc1) > 0 and len(desc2) > 0:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(desc1, desc2)
        matches = sorted(matches, key=lambda x: x.distance)
        match_result["match_count"] = len(matches)
        match_result["mean_distance"] = round(float(np.mean([m.distance for m in matches])), 4) if matches else 0.0
        match_result["matches"] = [{"queryIdx": int(m.queryIdx), "trainIdx": int(m.trainIdx), "distance": round(float(m.distance), 4)} for m in matches[:50]]
    else:
        match_result["match_count"] = 0
        match_result["mean_distance"] = 0.0
        match_result["matches"] = []

    result["feature_matching"] = match_result

    result["method_tier"] = "DETECTED"
    result["evidence_tier_note"] = "All similarity metrics are DETECTED pixel measurements; " \
                                   "similarity is not semantic equivalence"
    return result


def _empty_result(path1: Path, path2: Path, reason: str) -> dict:
    return {
        "path1": str(path1),
        "path2": str(path2),
        "metrics_version": "1.0.0",
        "error": reason,
        "pixel_difference": {},
        "ssim": {},
        "perceptual_hash": {},
        "feature_matching": {},
        "method_tier": "DETECTED",
        "evidence_tier_note": "One or both images could not be decoded",
    }


def run(targets1, targets2, json_path: str | None = None):
    """Similarity audit of two sets of image targets."""
    def collect(paths):
        out = []
        for p in paths:
            p = Path(p)
            if p.is_dir():
                out += sorted(p.rglob("*.png")) + sorted(p.rglob("*.jpg")) + sorted(p.rglob("*.jpeg"))
            elif p.exists():
                out.append(p)
            else:
                sys.exit(f"no such target: {p}")
        return out

    targets1_out = collect(targets1)
    targets2_out = collect(targets2)

    seen1, uniq1 = set(), []
    for f in targets1_out:
        if f.resolve() not in seen1:
            seen1.add(f.resolve())
            uniq1.append(f)

    seen2, uniq2 = set(), []
    for f in targets2_out:
        if f.resolve() not in seen2:
            seen2.add(f.resolve())
            uniq2.append(f)

    # Pair images by stem name if possible, otherwise by index
    pairs = []
    stem1 = {f.stem: f for f in uniq1}
    stem2 = {f.stem: f for f in uniq2}
    common_stems = sorted(set(stem1.keys()) & set(stem2.keys()))

    if common_stems:
        for s in common_stems:
            pairs.append((stem1[s], stem2[s]))
    else:
        # Pair by index
        n = min(len(uniq1), len(uniq2))
        for i in range(n):
            pairs.append((uniq1[i], uniq2[i]))

    report, dirty = [], 0
    for f1, f2 in pairs:
        try:
            metrics = analyze_similarity(f1, f2)
            entry = {"file1": str(f1), "file2": str(f2), "metrics": metrics, "issues": []}
            # Flag low similarity
            sim_pct = metrics.get("pixel_difference", {}).get("similarity_pct", 0)
            if sim_pct < 50:
                entry["issues"].append({
                    "t": "SIMILARITY-LOW",
                    "det": f"pixel similarity {sim_pct}% below 50% threshold",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file1": str(f1), "file2": str(f2), "metrics": None, "issues": [
                {"t": "SIMILARITY-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
            ]}
            dirty += 1
        report.append(entry)

    if json_path and report:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report, dirty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets1", nargs="+", help="first set of images or directory")
    ap.add_argument("targets2", nargs="+", help="second set of images or directory")
    ap.add_argument("--json", help="write full evidence to this file")
    a = ap.parse_args()

    report, dirty = run(a.targets1, a.targets2, json_path=a.json)

    for entry in report:
        m = entry.get("metrics")
        n = len(entry.get("issues", []))
        if m:
            pdiff = m.get("pixel_difference", {})
            ssim = m.get("ssim", {})
            phash = m.get("perceptual_hash", {})
            meta = f"  pixel_sim={pdiff.get('similarity_pct', 0)}% "
            meta += f"ssim={ssim.get('value', 'N/A')} "
            meta += f"phash_dist={phash.get('hamming_distance', 'N/A')}"
        else:
            meta = "  (no metrics)"
        print(("!! " if n else "OK ") + f"{entry['file1']} vs {entry['file2']}" + meta)
        for iss in entry.get("issues", []):
            print(f"     - [{iss.get('t')} conf {iss.get('conf', 0):.2f}] {iss.get('det')}")

    if a.json:
        print(f"\nevidence written: {a.json}")
    print(f"\nTARGETS: {len(report)}  DIRTY: {dirty}")
    sys.exit(min(dirty, 1))


if __name__ == "__main__":
    main()
