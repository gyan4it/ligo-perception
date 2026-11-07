#!/usr/bin/env python3
"""quality_sensor.py — deterministic image quality metrics for LiGeo CV sensor pack.

Computes luminance statistics, Laplacian variance sharpness, edge density,
and clipping/saturation indicators. All outputs are DETECTED measurements.

  python tools/cv_sensors/quality_sensor.py image.png
  python tools/cv_sensors/quality_sensor.py images/ --json out.json

Exit code = number of targets with findings (0 = clean).
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cv_core import load_image

try:
    import numpy as np
except ImportError:
    sys.exit("missing dependency: numpy (pip install numpy)")

try:
    from PIL import Image
    PILLOW_VERSION = Image.__version__
except Exception:
    PILLOW_VERSION = "unknown"

NUMPY_VERSION = np.__version__


def analyze_quality(path: Path) -> dict:
    """Compute deterministic pixel quality metrics from an image file."""
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)

        # --- Relative luminance (ITU-R BT.709) ---
        lum = (0.2126 * arr[:, :, 0].astype(np.float64) +
               0.7152 * arr[:, :, 1].astype(np.float64) +
               0.0722 * arr[:, :, 2].astype(np.float64)) / 255.0

        luminance = {
            "mean": round(float(lum.mean()), 4),
            "std": round(float(lum.std()), 4),
            "min": round(float(lum.min()), 4),
            "max": round(float(lum.max()), 4),
            "median": round(float(np.median(lum)), 4),
            "pct_dark": round(float((lum < 0.33).mean() * 100), 2),
            "pct_mid": round(float(((lum >= 0.33) & (lum < 0.66)).mean() * 100), 2),
            "pct_bright": round(float((lum >= 0.66).mean() * 100), 2),
            "method": "ITU-R BT.709 relative luminance, NumPy",
            "version": f"Pillow {Image.__version__ if Image else 'unknown'}, NumPy {np.__version__}",
            "interpretation": "Overall brightness distribution",
            "limitations": "Global measure; local variations not captured",
        }

        # --- Contrast: Michelson contrast ---
        lum_max = float(lum.max())
        lum_min = float(lum.min())
        michelson = (lum_max - lum_min) / (lum_max + lum_min) if (lum_max + lum_min) > 0 else 0.0
        rms = float(lum.std())
        contrast = {
            "michelson": round(michelson, 4),
            "rms": round(rms, 4),
            "luminance_range": round(lum_max - lum_min, 4),
            "method": "Michelson + RMS contrast from BT.709 luminance",
            "version": NUMPY_VERSION,
            "interpretation": "Global contrast range; not WCAG contrast ratio",
            "limitations": "Global measure; local contrast variations not captured",
        }

        # --- Sharpness: Laplacian variance ---
        lum_f = lum.astype(np.float64)
        laplacian_kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
        padded = np.pad(lum_f, 1, mode="edge")
        lap = np.zeros_like(lum_f)
        for i in range(3):
            for j in range(3):
                lap += laplacian_kernel[i, j] * padded[i:i + arr.shape[0], j:j + arr.shape[1]]
        lap_var = float(lap.var())
        sharpness = {
            "laplacian_variance": round(lap_var, 4),
            "sharpness_class": ("sharp" if lap_var > 100 else
                                "moderate" if lap_var > 20 else "soft"),
            "method": "Laplacian variance on BT.709 luminance",
            "version": f"NumPy {np.__version__}",
            "interpretation": "Higher variance = sharper edges; not focus quality",
            "limitations": "Global measure; local blur variations not captured",
        }

        # --- Edge density: gradient magnitude ---
        gy, gx = np.gradient(lum_f)
        grad_mag = np.sqrt(gx ** 2 + gy ** 2)
        edge_threshold = 0.1
        edge_mask = grad_mag > edge_threshold
        edge_density = {
            "mean_gradient": round(float(grad_mag.mean()), 4),
            "max_gradient": round(float(grad_mag.max()), 4),
            "edge_pixel_pct": round(float(edge_mask.mean() * 100), 2),
            "edge_threshold": edge_threshold,
            "method": "NumPy gradient magnitude",
            "version": f"NumPy {np.__version__}",
            "interpretation": "Edge presence and strength",
            "limitations": "Simple gradient; not Canny or semantic edge detection",
        }

        # --- Clipping: pixel values at 0 or 255 ---
        arr_flat = arr.reshape(-1, 3)
        total_channels = arr_flat.shape[0]
        clipped_low = int((arr_flat == 0).sum())
        clipped_high = int((arr_flat == 255).sum())
        clipping = {
            "clipped_low_count": clipped_low,
            "clipped_high_count": clipped_high,
            "clipped_low_pct": round(float(clipped_low / total_channels * 100), 4),
            "clipped_high_pct": round(float(clipped_high / total_channels * 100), 4),
            "method": "NumPy, count of pixel channels at 0 or 255",
            "version": f"NumPy {np.__version__}",
            "interpretation": "Clipping indicates lost detail in shadows/highlights",
            "limitations": "Per-channel count; not per-pixel",
        }

        # --- Saturation: HSV saturation distribution ---
        hsv = rgb.convert("HSV")
        hsv_arr = np.array(hsv, dtype=np.uint8)
        sat = hsv_arr[:, :, 1].ravel()
        saturation = {
            "sat_mean": round(float(sat.mean()), 4),
            "sat_std": round(float(sat.std()), 4),
            "sat_min": round(float(sat.min()), 4),
            "sat_max": round(float(sat.max()), 4),
            "method": "NumPy, HSV saturation channel",
            "version": f"Pillow {Image.__version__}, NumPy {np.__version__}",
            "interpretation": "Color saturation distribution",
            "limitations": "HSV saturation is not perceptual uniformity",
        }

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "pillow_version": Image.__version__ if Image else "unknown",
            "numpy_version": np.__version__,
    "luminance": luminance,
    "contrast": contrast,
    "sharpness": sharpness,
            "edge_density": edge_density,
            "clipping": clipping,
            "saturation": saturation,
            "method_tier": "DETECTED",
            "evidence_tier_note": "All quality metrics are DETECTED pixel measurements; "
                                  "no aesthetic judgment",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "luminance": {},
        "sharpness": {},
        "edge_density": {},
        "clipping": {},
        "saturation": {},
        "method_tier": "DETECTED",
        "evidence_tier_note": "Image could not be decoded — no quality metrics available",
    }


def run(targets, json_path: str | None = None):
    """Quality audit of file/dir targets."""
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
            metrics = analyze_quality(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag low sharpness or high clipping
            if metrics["sharpness"]["laplacian_variance"] < 5:
                entry["issues"].append({
                    "t": "QUALITY-SOFT",
                    "det": f"low sharpness (Laplacian var {metrics['sharpness']['laplacian_variance']})",
                    "conf": 0.7,
                })
            if metrics["clipping"]["clipped_high_pct"] > 10:
                entry["issues"].append({
                    "t": "QUALITY-HI-CLIP",
                    "det": f"high clipping ({metrics['clipping']['clipped_high_pct']}% channels at 255)",
                    "conf": 0.7,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "QUALITY-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            sharp = m.get("sharpness", {})
            clip = m.get("clipping", {})
            lum = m.get("luminance", {})
            meta = f"  lum={lum.get('mean', 0)} sharp={sharp.get('laplacian_variance', 0)} "
            meta += f"clip_hi={clip.get('clipped_high_pct', 0)}% edges={m.get('edge_density', {}).get('edge_pixel_pct', 0)}%"
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
