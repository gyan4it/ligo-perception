#!/usr/bin/env python3
"""registration_sensor.py — deterministic image registration for LiGeo CV sensor pack.

Computes image alignment/registration using OpenCV ORB feature matching and
ECC (Enhanced Correlation Coefficient) alignment. All outputs are DETECTED
measurements — transform parameters are geometric, not semantic.

  python tools/cv_sensors/registration_sensor.py img1.png img2.png
  python tools/cv_sensors/registration_sensor.py dir1/ dir2/ --json out.json

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


def _load_resized_gray(path: Path, size: tuple = (512, 512)) -> np.ndarray:
    """Load image, convert to grayscale, resize for registration."""
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            raise ValueError(f"could not decode image: {path}")
        gray = img.convert("L")
        gray = gray.resize(size, Image.Resampling.LANCZOS)
        return np.array(gray, dtype=np.uint8)


def analyze_registration(path1: Path, path2: Path) -> dict:
    """Compute deterministic registration metrics between two images."""
    img1 = _load_resized_gray(path1)
    img2 = _load_resized_gray(path2)

    result = {
        "path1": str(path1),
        "path2": str(path2),
        "metrics_version": "1.0.0",
        "opencv_version": OPENCV_VERSION,
        "numpy_version": np.__version__,
        "pillow_version": PILLOW_VERSION,
    }

    # --- ORB feature matching ---
    orb = cv2.ORB_create(nfeatures=500)
    kp1, desc1 = orb.detectAndCompute(img1, None)
    kp2, desc2 = orb.detectAndCompute(img2, None)

    orb_result = {
        "keypoints1": int(len(kp1)) if kp1 else 0,
        "keypoints2": int(len(kp2)) if kp2 else 0,
        "method": "OpenCV ORB",
        "version": OPENCV_VERSION,
    }

    if desc1 is not None and desc2 is not None and len(desc1) > 0 and len(desc2) > 0:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(desc1, desc2)
        matches = sorted(matches, key=lambda x: x.distance)
        orb_result["match_count"] = len(matches)
        orb_result["mean_match_distance"] = round(float(np.mean([m.distance for m in matches])), 4) if matches else 0.0
        orb_result["matches_sample"] = [
            {"queryIdx": int(m.queryIdx), "trainIdx": int(m.trainIdx), "distance": round(float(m.distance), 4)}
            for m in matches[:30]
        ]
    else:
        orb_result["match_count"] = 0
        orb_result["mean_match_distance"] = 0.0
        orb_result["matches_sample"] = []

    result["orb_features"] = orb_result

    # --- ECC alignment (Enhanced Correlation Coefficient) ---
    try:
        warp_mode = cv2.MOTION_AFFINE
        warp_matrix = np.eye(2, 3, dtype=np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-6)

        # ECC requires same-size images
        if img1.shape == img2.shape:
            cc, warp_matrix = cv2.findTransformECC(img1, img2, warp_matrix, warp_mode, criteria)
            ecc_result = {
                "correlation_coefficient": round(float(cc), 6),
                "warp_matrix": [[round(float(v), 6) for v in row] for row in warp_matrix.tolist()],
                "method": "OpenCV findTransformECC, MOTION_AFFINE",
                "version": OPENCV_VERSION,
                "interpretation": "Geometric alignment quality (-1 to 1)",
                "limitations": "Requires same-size images; affine model only",
            }
        else:
            # Resize img2 to match img1 for ECC
            img2_resized = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            cc, warp_matrix = cv2.findTransformECC(img1, img2_resized, warp_matrix, warp_mode, criteria)
            ecc_result = {
                "correlation_coefficient": round(float(cc), 6),
                "warp_matrix": [[round(float(v), 6) for v in row] for row in warp_matrix.tolist()],
                "method": "OpenCV findTransformECC, MOTION_AFFINE (img2 resized to img1)",
                "version": OPENCV_VERSION,
                "interpretation": "Geometric alignment quality (-1 to 1)",
                "limitations": "Requires same-size images; affine model only; img2 was resized",
            }
    except cv2.error as e:
        ecc_result = {
            "error": str(e)[:200],
            "method": "OpenCV findTransformECC",
            "version": OPENCV_VERSION,
        }

    result["ecc_alignment"] = ecc_result

    # --- Translation estimate from warp matrix ---
    if "warp_matrix" in ecc_result and ecc_result.get("warp_matrix"):
        tx = ecc_result["warp_matrix"][0][2]
        ty = ecc_result["warp_matrix"][1][2]
        translation = {
            "tx": round(float(tx), 4),
            "ty": round(float(ty), 4),
            "translation_magnitude": round(float(np.sqrt(tx ** 2 + ty ** 2)), 4),
            "method": "OpenCV warp_matrix translation components",
            "version": OPENCV_VERSION,
        }
        result["translation"] = translation

    result["method_tier"] = "DETECTED"
    result["evidence_tier_note"] = "All registration metrics are DETECTED geometric measurements; " \
                                   "alignment is not semantic equivalence"
    return result


def _empty_result(path1: Path, path2: Path, reason: str) -> dict:
    return {
        "path1": str(path1),
        "path2": str(path2),
        "metrics_version": "1.0.0",
        "error": reason,
        "orb_features": {},
        "ecc_alignment": {},
        "translation": {},
        "method_tier": "DETECTED",
        "evidence_tier_note": "One or both images could not be decoded",
    }


def run(targets1, targets2, json_path: str | None = None):
    """Registration audit of two sets of image targets."""
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
        n = min(len(uniq1), len(uniq2))
        for i in range(n):
            pairs.append((uniq1[i], uniq2[i]))

    report, dirty = [], 0
    for f1, f2 in pairs:
        try:
            metrics = analyze_registration(f1, f2)
            entry = {"file1": str(f1), "file2": str(f2), "metrics": metrics, "issues": []}
            # Flag low correlation
            cc = metrics.get("ecc_alignment", {}).get("correlation_coefficient")
            if cc is not None and cc < 0.5:
                entry["issues"].append({
                    "t": "REGISTRATION-LOW-CORRELATION",
                    "det": f"ECC correlation {cc} below 0.5 threshold",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file1": str(f1), "file2": str(f2), "metrics": None, "issues": [
                {"t": "REGISTRATION-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            orb = m.get("orb_features", {})
            ecc = m.get("ecc_alignment", {})
            trans = m.get("translation", {})
            meta = f"  orb_matches={orb.get('match_count', 0)} "
            meta += f"ecc_cc={ecc.get('correlation_coefficient', 'N/A')} "
            meta += f"trans_mag={trans.get('translation_magnitude', 'N/A')}"
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
