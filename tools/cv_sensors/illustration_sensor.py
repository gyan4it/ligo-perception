#!/usr/bin/env python3
"""illustration_sensor.py — deterministic illustration analysis for LiGeo CV sensor pack.

Checks illustration-specific characteristics: bounds/crop, foreground/background
contrast, whitespace ratio, page image placement/scaling, palette consistency
across a series, and duplicate/near-duplicate illustration detection.

  python tools/cv_sensors/illustration_sensor.py image.png
  python tools/cv_sensors/illustration_sensor.py images/ --json out.json

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

try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
    IMAGEHASH_VERSION = imagehash.__version__
except ImportError:
    IMAGEHASH_AVAILABLE = False
    IMAGEHASH_VERSION = None


def analyze_illustration(path: Path) -> dict:
    """Compute deterministic illustration metrics from an image file."""
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)
        h, w = arr.shape[:2]
        total_px = h * w
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # --- Illustration bounds: content bounding box ---
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        coords = cv2.findNonZero(binary)
        if coords is not None and len(coords) > 0:
            x, y, cw, ch = cv2.boundingRect(coords)
            bounds = {
                "x": int(x),
                "y": int(y),
                "width": int(cw),
                "height": int(ch),
                "area": int(cw * ch),
                "fill_pct": round(float((cw * ch) / (w * h) * 100), 4) if w * h > 0 else 0.0,
            }
        else:
            bounds = {
                "x": 0, "y": 0, "width": 0, "height": 0,
                "area": 0,
                "fill_pct": 0.0,
            }

        # --- Crop detection ---
        border_px = max(2, min(h, w) // 50)
        top_touch = int(binary[:border_px, :].sum() > 0)
        bottom_touch = int(binary[-border_px:, :].sum() > 0)
        left_touch = int(binary[:, :border_px].sum() > 0)
        right_touch = int(binary[:, -border_px:].sum() > 0)
        crop = {
            "top_touch": bool(top_touch),
            "bottom_touch": bool(bottom_touch),
            "left_touch": bool(left_touch),
            "right_touch": bool(right_touch),
            "touches_any_edge": bool(top_touch or bottom_touch or left_touch or right_touch),
            "method": "OpenCV, content pixels within border_px of image edge",
            "version": OPENCV_VERSION,
        }

        # --- Foreground/background contrast: foreground pixels vs background ---
        if len(coords) > 0:
            fg_mask = binary > 0
            fg_pixels = gray[fg_mask]
            bg_mask = binary == 0
            bg_pixels = gray[bg_mask] if bg_mask.any() else np.array([255])
            fg_mean = float(fg_pixels.mean()) if len(fg_pixels) > 0 else 255.0
            bg_mean = float(bg_pixels.mean()) if len(bg_pixels) > 0 else 255.0
            contrast = abs(fg_mean - bg_mean) / 255.0
        else:
            fg_mean = 255.0
            bg_mean = 255.0
            contrast = 0.0
        fg_bg_contrast = {
            "foreground_mean": round(fg_mean, 4),
            "background_mean": round(bg_mean, 4),
            "contrast_ratio": round(contrast, 4),
            "method": "OpenCV threshold + mean intensity",
            "version": OPENCV_VERSION,
            "interpretation": "Difference between foreground and background intensity",
            "limitations": "Global mean; not WCAG contrast ratio",
        }

        # --- Whitespace ratio: background pixel percentage ---
        whitespace_pct = round(float((binary == 0).sum() / total_px * 100), 4) if total_px > 0 else 0.0

        # --- Page image placement/scaling: content position relative to page ---
        placement = {
            "content_center_x": round(float(x + cw / 2) / w, 4) if len(coords) > 0 else 0.5,
            "content_center_y": round(float(y + ch / 2) / h, 4) if len(coords) > 0 else 0.5,
            "content_offset_x": round(float((x + cw / 2) - w / 2) / w, 4) if len(coords) > 0 else 0.0,
            "content_offset_y": round(float((y + ch / 2) - h / 2) / h, 4) if len(coords) > 0 else 0.0,
            "content_is_centered": abs(((x + cw / 2) - w / 2) / w) < 0.1 and abs(((y + ch / 2) - h / 2) / h) < 0.1 if len(coords) > 0 else False,
        }

        # --- Palette hash for consistency across series ---
        palette_hash = None
        if IMAGEHASH_AVAILABLE:
            try:
                pil_img = img.convert("RGB")
                ph = imagehash.phash(pil_img, hash_size=16)
                palette_hash = str(ph)
            except Exception as e:
                palette_hash = f"error: {str(e)[:100]}"

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "opencv_version": OPENCV_VERSION,
            "numpy_version": np.__version__,
            "pillow_version": PILLOW_VERSION,
            "imagehash_available": IMAGEHASH_AVAILABLE,
            "imagehash_version": IMAGEHASH_VERSION,
            "bounds": bounds,
            "crop_detection": crop,
            "fg_bg_contrast": fg_bg_contrast,
            "whitespace_pct": whitespace_pct,
            "placement": placement,
            "palette_hash": palette_hash,
            "method_tier": "DETECTED",
            "evidence_tier_note": "All illustration metrics are DETECTED pixel measurements; "
                                  "not semantic illustration understanding",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "bounds": {},
        "crop_detection": {},
        "fg_bg_contrast": {},
        "whitespace_pct": 0.0,
        "placement": {},
        "palette_hash": None,
        "method_tier": "DETECTED",
        "evidence_tier_note": "Image could not be decoded — no illustration metrics available",
    }


def run(targets, json_path: str | None = None):
    """Illustration audit of file/dir targets."""
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
            metrics = analyze_illustration(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag illustration touching edges (possible crop)
            crop = metrics.get("crop_detection", {})
            if crop.get("touches_any_edge"):
                entry["issues"].append({
                    "t": "ILLUSTRATION-CROP",
                    "det": "illustration content touches image edge — possible crop",
                    "conf": 0.7,
                })
            # Flag low contrast
            contrast = metrics.get("fg_bg_contrast", {}).get("contrast_ratio", 1.0)
            if contrast < 0.2:
                entry["issues"].append({
                    "t": "ILLUSTRATION-LOW-CONTRAST",
                    "det": f"foreground/background contrast {contrast:.2f} below 0.2 threshold",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "ILLUSTRATION-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
            ]}
            dirty += 1
        report.append(entry)

    if json_path and report:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report, dirty


def compare_illustrations(path1: Path, path2: Path) -> dict:
    """Compare two illustrations for duplicate/near-duplicate detection."""
    with load_image(path1) as loaded1:
        img1 = loaded1.image
        if img1 is None:
            return _empty_comparison(path1, path2, "first image could not be decoded")
        rgb1 = img1.convert("RGB")
    with load_image(path2) as loaded2:
        img2 = loaded2.image
        if img2 is None:
            return _empty_comparison(path1, path2, "second image could not be decoded")
        rgb2 = img2.convert("RGB")

    result = {
        "path1": str(path1),
        "path2": str(path2),
        "metrics_version": "1.0.0",
        "pillow_version": PILLOW_VERSION,
        "imagehash_available": IMAGEHASH_AVAILABLE,
        "imagehash_version": IMAGEHASH_VERSION,
    }

    # Perceptual hash similarity
    if IMAGEHASH_AVAILABLE:
        try:
            ph1 = imagehash.phash(rgb1, hash_size=16)
            ph2 = imagehash.phash(rgb2, hash_size=16)
            hamming_dist = int(ph1 - ph2)
            max_dist = 16 * 16  # 256 for 16x16 hash
            similarity_pct = round(float((1.0 - hamming_dist / max_dist) * 100), 4)
            result["phash_similarity"] = {
                "hash1": str(ph1),
                "hash2": str(ph2),
                "hamming_distance": hamming_dist,
                "max_distance": max_dist,
                "similarity_pct": similarity_pct,
                "is_near_duplicate": hamming_dist <= 5,  # threshold: very similar
                "method": "imagehash.phash",
                "version": IMAGEHASH_VERSION,
                "interpretation": "Perceptual hash similarity (higher = more similar)",
                "limitations": "Hash alone cannot prove identity",
            }
        except Exception as e:
            result["phash_similarity"] = {
                "error": str(e)[:200],
                "method": "imagehash.phash",
                "version": IMAGEHASH_VERSION,
            }
    else:
        result["phash_similarity"] = {
            "error": "imagehash not installed",
            "method": "imagehash.phash",
            "version": None,
        }

    # Pixel difference after resize to same size
    try:
        from PIL import Image as PILImage
        size = (256, 256)
        r1 = rgb1.resize(size, PILImage.Resampling.LANCZOS)
        r2 = rgb2.resize(size, PILImage.Resampling.LANCZOS)
        a1 = np.array(r1, dtype=np.float64)
        a2 = np.array(r2, dtype=np.float64)
        diff = np.mean((a1 - a2) ** 2)
        max_mse = 255.0 ** 2
        pixel_sim = round(float((1.0 - diff / max_mse) * 100), 4)
        result["pixel_similarity"] = {
            "mse": round(float(diff), 4),
            "similarity_pct": pixel_sim,
            "method": "NumPy, resized pixel difference",
            "version": NUMPY_VERSION,
            "interpretation": "Pixel-level similarity after resize alignment",
            "limitations": "Requires resize; not semantic identity",
        }
    except Exception as e:
        result["pixel_similarity"] = {
            "error": str(e)[:200],
            "method": "NumPy pixel difference",
            "version": NUMPY_VERSION,
        }

    return result


def _empty_comparison(path1: Path, path2: Path, reason: str) -> dict:
    return {
        "path1": str(path1),
        "path2": str(path2),
        "metrics_version": "1.0.0",
        "error": reason,
        "phash_similarity": {},
        "pixel_similarity": {},
    }


def run_comparison(targets1, targets2, json_path: str | None = None):
    """Compare illustration pairs for duplicate detection."""
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

    # Pair by stem name if possible, otherwise by index
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
            metrics = compare_illustrations(f1, f2)
            entry = {"file1": str(f1), "file2": str(f2), "metrics": metrics, "issues": []}
            # Flag near-duplicate illustrations
            phash = metrics.get("phash_similarity", {})
            if phash.get("is_near_duplicate"):
                entry["issues"].append({
                    "t": "ILLUSTRATION-NEAR-DUPLICATE",
                    "det": f"perceptual hash similarity {phash.get('similarity_pct', 0)}% — possible duplicate",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file1": str(f1), "file2": str(f2), "metrics": None, "issues": [
                {"t": "ILLUSTRATION-COMPARE-ERROR", "det": str(e)[:200], "conf": 1.0}
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
    ap.add_argument("--compare", nargs="+", help="second set of images for duplicate detection")
    ap.add_argument("--json", help="write full evidence to this file")
    a = ap.parse_args()

    if a.compare:
        report, dirty = run_comparison(a.targets, a.compare, json_path=a.json)
        for entry in report:
            m = entry.get("metrics")
            n = len(entry.get("issues", []))
            if m:
                phash = m.get("phash_similarity", {})
                px = m.get("pixel_similarity", {})
                meta = f"  phash_sim={phash.get('similarity_pct', 'N/A')}% "
                meta += f"pixel_sim={px.get('similarity_pct', 'N/A')}%"
            else:
                meta = "  (no metrics)"
            print(("!! " if n else "OK ") + f"{entry['file1']} vs {entry['file2']}" + meta)
            for iss in entry.get("issues", []):
                print(f"     - [{iss.get('t')} conf {iss.get('conf', 0):.2f}] {iss.get('det')}")
    else:
        report, dirty = run(a.targets, json_path=a.json)
        for entry in report:
            m = entry.get("metrics")
            n = len(entry.get("issues", []))
            if m:
                bounds = m.get("bounds", {})
                crop = m.get("crop_detection", {})
                contrast = m.get("fg_bg_contrast", {})
                meta = f"  bounds={bounds.get('width', 0)}x{bounds.get('height', 0)} "
                meta += f"crop={crop.get('touches_any_edge', False)} "
                meta += f"contrast={contrast.get('contrast_ratio', 0):.2f} "
                meta += f"whitespace={m.get('whitespace_pct', 0)}%"
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
