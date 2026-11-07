#!/usr/bin/env python3
"""visual_regression.py — visual regression detection for LiGeo QA.

Compares images or rendered pages between two versions to detect visual
regressions (unexpected changes in layout, content, or appearance).

  python tools/cv_sensors/visual_regression.py img1.png img2.png
  python tools/cv_sensors/visual_regression.py dir1/ dir2/ --json out.json

Exit code = number of visual regressions detected (0 = no change).
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

try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
    IMAGEHASH_VERSION = imagehash.__version__
except ImportError:
    IMAGEHASH_AVAILABLE = False
    IMAGEHASH_VERSION = None

try:
    import skimage.metrics
    SKIMAGE_AVAILABLE = True
    SKIMAGE_VERSION = skimage.metrics.__version__ if hasattr(
        skimage.metrics, '__version__') else "0.26.0"
except ImportError:
    SKIMAGE_AVAILABLE = False
    SKIMAGE_VERSION = None


def load_image_gray(path: Path, size: tuple = (256, 256)) -> np.ndarray:
    """Load image, convert to grayscale, resize for comparison."""
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            raise ValueError(f"could not decode image: {path}")
        gray = img.convert("L")
        gray = gray.resize(size, Image.Resampling.LANCZOS)
        return np.array(gray, dtype=np.uint8)


def analyze_image_pair(path1: Path, path2: Path) -> dict:
    """Compare two images for visual regression.

    Computes:
    - Pixel difference (MSE, RMSE, similarity %)
    - Perceptual hash difference (if imagehash available)
    - SSIM (if scikit-image available)
    """
    img1 = load_image_gray(path1, (256, 256))
    img2 = load_image_gray(path2, (256, 256))

    result = {
        "path1": str(path1),
        "path2": str(path2),
        "metrics_version": "1.0.0",
        "opencv_version": OPENCV_VERSION,
        "numpy_version": NUMPY_VERSION,
        "pillow_version": PILLOW_VERSION,
        "imagehash_available": IMAGEHASH_AVAILABLE,
        "imagehash_version": IMAGEHASH_VERSION,
        "skimage_available": SKIMAGE_AVAILABLE,
        "skimage_version": SKIMAGE_VERSION,
    }

    # --- Pixel difference (MSE, RMSE, similarity) ---
    diff = img1.astype(np.float64) - img2.astype(np.float64)
    mse = float(np.mean(diff ** 2))
    rmse = float(np.sqrt(mse))
    max_mse = 255.0 ** 2
    similarity_pct = round(float((1.0 - mse / max_mse) * 100), 4)

    result["pixel_difference"] = {
        "mse": round(mse, 4),
        "rmse": round(rmse, 4),
        "similarity_pct": similarity_pct,
        "method": "NumPy, normalized mean squared error",
        "version": NUMPY_VERSION,
        "interpretation": "Pixel-level difference after resize alignment",
        "limitations": "Requires same size/resize; not semantic similarity",
    }

    # --- Perceptual hash (if imagehash available) ---
    if IMAGEHASH_AVAILABLE:
        try:
            from PIL import Image as PILImage
            img1_pil = Image.open(path1).convert("L")
            img2_pil = Image.open(path2).convert("L")
            phash1 = imagehash.phash(img1_pil)
            phash2 = imagehash.phash(img2_pil)
            hamming_dist = int(phash1 - phash2)
            max_dist = 16 * 16
            phash_similarity = round(float((1.0 - hamming_dist / max_dist) * 100), 4)

            result["perceptual_hash"] = {
                "hash1": str(phash1),
                "hash2": str(phash2),
                "hamming_distance": hamming_dist,
                "max_distance": max_dist,
                "similarity_pct": phash_similarity,
                "method": "imagehash.phash",
                "version": IMAGEHASH_VERSION,
                "interpretation": "Perceptual hash similarity",
                "limitations": "Hash alone cannot prove identity",
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

    # --- SSIM (if scikit-image available) ---
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

    # --- Overall similarity score ---
    scores = []
    if "pixel_difference" in result and "similarity_pct" in result["pixel_difference"]:
        scores.append(result["pixel_difference"]["similarity_pct"])
    if "perceptual_hash" in result and "similarity_pct" in result["perceptual_hash"]:
        scores.append(result["perceptual_hash"]["similarity_pct"])
    if "ssim" in result and "value" in result["ssim"]:
        scores.append(result["ssim"]["value"] * 100)

    result["overall_similarity_pct"] = round(float(np.mean(scores)), 4) if scores else 0.0
    result["is_regression"] = result["overall_similarity_pct"] < 95.0

    return result


def _empty_result(path1: Path, path2: Path, reason: str) -> dict:
    return {
        "path1": str(path1),
        "path2": str(path2),
        "metrics_version": "1.0.0",
        "error": reason,
        "pixel_difference": {},
        "perceptual_hash": {},
        "ssim": {},
        "overall_similarity_pct": 0.0,
        "is_regression": True,
        "method_tier": "DETECTED",
        "evidence_tier_note": "One or both images could not be decoded",
    }


def run(targets1, targets2, json_path: str | None = None):
    """Visual regression diff of two sets of images.

    Pairs images by filename (stem) or by index if names don't match.
    """
    targets1_out = []
    for p in targets1:
        p = Path(p)
        if p.is_dir():
            targets1_out += sorted(p.rglob("*.png")) + sorted(p.rglob("*.jpg")) + \
                sorted(p.rglob("*.jpeg"))
        elif p.exists():
            targets1_out.append(p)
        else:
            sys.exit(f"no such target: {p}")

    targets2_out = []
    for p in targets2:
        p = Path(p)
        if p.is_dir():
            targets2_out += sorted(p.rglob("*.png")) + sorted(p.rglob("*.jpg")) + \
                sorted(p.rglob("*.jpeg"))
        elif p.exists():
            targets2_out.append(p)
        else:
            sys.exit(f"no such target: {p}")

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

    # Pair by stem name, otherwise by index
    pairs = []
    stem1 = {f.stem: f for f in uniq1}
    stem2 = {f.stem: f for f in uniq2}
    common_stems = sorted(set(stem1.keys()) & set(stem2.keys()))

    if common_stems:
        for s in common_stems:
            pairs.append((stem1[s], stem2[s]))
    else:
        n = min(len(uniq1), len(uniq2))
        for i in range(n):
            pairs.append((uniq1[i], uniq2[i]))

    report, dirty = [], 0
    for f1, f2 in pairs:
        try:
            metrics = analyze_image_pair(f1, f2)
            entry = {"file1": str(f1), "file2": str(f2),
                     "metrics": metrics, "issues": []}
            if metrics.get("is_regression"):
                entry["issues"].append({
                    "t": "VISUAL-REGRESSION",
                    "det": f"visual similarity {metrics['overall_similarity_pct']}% "
                           f"below 95% threshold",
                    "conf": 0.8,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file1": str(f1), "file2": str(f2),
                     "metrics": None,
                     "issues": [{"t": "VISUAL-REGRESSION-ERROR",
                                 "det": str(e)[:200], "conf": 1.0}]}
            dirty += 1
        report.append(entry)

    if json_path and report:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2),
                                   encoding="utf-8")

    return report, dirty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets1", nargs="+",
                    help="First set of images or directory")
    ap.add_argument("targets2", nargs="+",
                    help="Second set of images or directory")
    ap.add_argument("--json", help="write visual regression report to JSON file")
    a = ap.parse_args()

    report, dirty = run(a.targets1, a.targets2, json_path=a.json)

    for entry in report:
        m = entry.get("metrics")
        n = len(entry.get("issues", []))
        if m:
            sim = m.get("overall_similarity_pct", "?")
            meta = f"  overall_similarity={sim}%"
        else:
            meta = "  (no metrics)"
        print(("!! " if n else "OK ") +
              f"{entry['file1']} vs {entry['file2']}" + meta)
        for iss in entry.get("issues", []):
            print(f"     - [{iss.get('t')} conf {iss.get('conf', 0):.2f}] "
                  f"{iss.get('det')}")

    if a.json:
        print(f"\nevidence written: {a.json}")
    print(f"\nTARGETS: {len(report)}  DIRTY: {dirty}")
    sys.exit(min(dirty, 1))


if __name__ == "__main__":
    main()
