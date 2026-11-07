#!/usr/bin/env python3
"""color_sensor.py — deterministic color analysis for LiGeo CV sensor pack.

Computes color histograms, dominant palette, coverage percentages, and
color-distribution statistics using Pillow + NumPy. All outputs are
DETECTED measurements — no semantic claims about color harmony or beauty.

  python tools/cv_sensors/color_sensor.py image.png
  python tools/cv_sensors/color_sensor.py images/ --json out.json

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


def analyze_color(path: Path) -> dict:
    """Compute deterministic color metrics from an image file.

    Returns metrics dict with method/version/interpretation/limitations
    for every color metric. All metrics are DETECTED measurements.
    """
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)
        h, w = arr.shape[:2]

        # --- Flatten to pixels for histogram ---
        pixels = arr.reshape(-1, 3)

        # --- 3-bit bucketing per channel (512 buckets) ---
        buckets = (pixels // 32).astype(np.int16)
        keys = buckets[:, 0] * 64 + buckets[:, 1] * 8 + buckets[:, 2]
        unique, counts = np.unique(keys, return_counts=True)
        total = len(keys)
        top_n = min(8, len(unique))
        top_idx = np.argsort(counts)[-top_n:][::-1]
        dominant = []
        for i in top_idx:
            k = int(unique[i])
            b, g, r = (k // 64), ((k // 8) % 8), (k % 8)
            dominant.append({
                "hex": f"#{r * 32:02x}{g * 32:02x}{b * 32:02x}",
                "pct": round(float(counts[i] / total * 100), 2),
                "bucket_rgb": [int(r), int(g), int(b)],
            })

        palette = {
            "dominant_colors": dominant,
            "unique_buckets": int(len(unique)),
            "method": "Pillow + NumPy, 3 bits/channel bucketing (512 buckets)",
            "version": f"Pillow {PILLOW_VERSION}, NumPy {NUMPY_VERSION}",
            "interpretation": "Approximate color distribution; bucketed",
            "limitations": "3-bit quantization loses fine color detail",
        }

        # --- Per-channel histogram (16 bins) ---
        channel_hist = {}
        for ch_idx, ch_name in enumerate(["r", "g", "b"]):
            channel = arr[:, :, ch_idx].ravel()
            counts, bin_edges = np.histogram(channel, bins=16, range=(0, 256))
            channel_hist[ch_name] = {
                "bin_counts": [int(c) for c in counts],
                "bin_edges": [int(e) for e in bin_edges],
                "method": "NumPy histogram, 16 bins, range 0-255",
                "version": NUMPY_VERSION,
            }

        # --- HSV analysis ---
        hsv = rgb.convert("HSV")
        hsv_arr = np.array(hsv, dtype=np.uint8)
        hue = hsv_arr[:, :, 0].ravel()
        sat = hsv_arr[:, :, 1].ravel()
        val = hsv_arr[:, :, 2].ravel()

        hsv_stats = {
            "hue_mean": round(float(hue.mean()), 4),
            "hue_std": round(float(hue.std()), 4),
            "sat_mean": round(float(sat.mean()), 4),
            "sat_std": round(float(sat.std()), 4),
            "val_mean": round(float(val.mean()), 4),
            "val_std": round(float(val.std()), 4),
            "method": "NumPy, HSV color space",
            "version": f"Pillow {PILLOW_VERSION}, NumPy {NUMPY_VERSION}",
            "interpretation": "HSV channel statistics",
            "limitations": "HSV is cylindrical; mean hue can be misleading near wrap-around",
        }

        # --- Color coverage: saturation and value tiers ---
        sat_tiers = {
            "desaturated": round(float((sat < 50).mean() * 100), 2),
            "moderate": round(float(((sat >= 50) & (sat < 150)).mean() * 100), 2),
            "saturated": round(float((sat >= 150).mean() * 100), 2),
        }
        val_tiers = {
            "dark": round(float((val < 85).mean() * 100), 2),
            "midtone": round(float(((val >= 85) & (val < 170)).mean() * 100), 2),
            "bright": round(float((val >= 170).mean() * 100), 2),
        }

        coverage = {
            "saturation_tiers": sat_tiers,
            "value_tiers": val_tiers,
            "method": "NumPy, HSV S and V channel tiering",
            "version": f"Pillow {PILLOW_VERSION}, NumPy {NUMPY_VERSION}",
            "interpretation": "Distribution of saturation and brightness",
            "limitations": "Tier boundaries are arbitrary; not perceptual uniformity",
        }

        # --- Mean RGB ---
        mean_rgb = {
            "r": round(float(arr[:, :, 0].mean()), 4),
            "g": round(float(arr[:, :, 1].mean()), 4),
            "b": round(float(arr[:, :, 2].mean()), 4),
            "method": "NumPy mean per channel",
            "version": NUMPY_VERSION,
        }

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "pillow_version": PILLOW_VERSION,
            "numpy_version": NUMPY_VERSION,
            "palette": palette,
            "channel_histogram": channel_hist,
            "hsv_stats": hsv_stats,
            "coverage_tiers": coverage,
            "mean_rgb": mean_rgb,
            "method_tier": "DETECTED",
            "evidence_tier_note": "All color metrics are DETECTED pixel measurements; "
                                  "no aesthetic or semantic interpretation",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "palette": {"dominant_colors": [], "unique_buckets": 0},
        "channel_histogram": {},
        "hsv_stats": {},
        "coverage_tiers": {},
        "mean_rgb": {"r": 0, "g": 0, "b": 0},
        "method_tier": "DETECTED",
        "evidence_tier_note": "Image could not be decoded — no color metrics available",
    }


def run(targets, json_path: str | None = None):
    """Color audit of file/dir targets."""
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
            metrics = analyze_color(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag images with extremely low color diversity as potential issues
            if metrics["palette"]["unique_buckets"] < 5:
                entry["issues"].append({
                    "t": "COLOR-LOW-DIVERSITY",
                    "det": f"only {metrics['palette']['unique_buckets']} color buckets detected",
                    "conf": 0.6,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "COLOR-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            pal = m.get("palette", {})
            hsv = m.get("hsv_stats", {})
            meta = f"  buckets={pal.get('unique_buckets', 0)} "
            meta += f"hue={hsv.get('hue_mean', 0)} sat={hsv.get('sat_mean', 0)} "
            meta += f"val={hsv.get('val_mean', 0)}"
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
