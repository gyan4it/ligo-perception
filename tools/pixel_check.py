#!/usr/bin/env python3
"""pixel_check — deterministic pixel analysis for LiGeo global skill.

Computes image metrics from actual pixel data using Pillow + NumPy.
No vision model required — all metrics are mathematical measurements.

Image decoding is delegated to tools/cv_core.py so images are decoded once
and validated consistently across all LiGeo tools.

  python tools/pixel_check.py image.png
  python tools/pixel_check.py images/ --json out.json

Exit code = number of targets with findings (0 = clean).
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_core import load_image

try:
    import numpy as np
except ImportError:
    sys.exit("missing dependency: numpy (pip install numpy)")

# --- Dependency versions (for provenance) ---
try:
    from PIL import Image
    PILLOW_VERSION = Image.__version__
except Exception:
    PILLOW_VERSION = "unknown"

NUMPY_VERSION = np.__version__


def analyze_pixels(path: Path) -> dict:
    """Compute deterministic pixel metrics from an image file.

    Returns a metrics dict with method/version/interpretation/limitations
    for every metric. Raw pixel data is never embedded in output.

    Image loading/delegation is handled by cv_core.load_image which
    validates, decodes, and optionally downsamples the image.
    """
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            # Image failed to load — return minimal metrics with issues
            return {
                "path": str(path),
                "metrics_version": "1.0.0",
                "pillow_version": PILLOW_VERSION,
                "numpy_version": NUMPY_VERSION,
                "dimensions": {
                    "width": 0, "height": 0, "aspect_ratio": None,
                    "orientation": "unknown",
                    "method": "Pillow Image.size (via cv_core)",
                    "version": PILLOW_VERSION,
                    "interpretation": "Image failed to load",
                    "limitations": "Image could not be decoded",
                },
                "color": {
                    "mode": None, "has_alpha": False,
                    "method": "Pillow Image.mode (via cv_core)",
                    "version": PILLOW_VERSION,
                    "interpretation": "Image could not be decoded",
                    "limitations": "Image could not be decoded",
                },
                "palette": {
                    "dominant_colors": [], "unique_buckets": 0,
                    "method": "Pillow resize + NumPy histogram",
                    "version": f"Pillow {PILLOW_VERSION}, NumPy {NUMPY_VERSION}",
                    "interpretation": "Image could not be decoded",
                    "limitations": "Image could not be decoded",
                },
                "histogram": {},
                "luminance": {
                    "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0,
                    "median": 0.0, "pct_dark": 0.0, "pct_mid": 0.0,
                    "pct_bright": 0.0,
                    "method": "ITU-R BT.709 relative luminance, NumPy",
                    "version": NUMPY_VERSION,
                    "interpretation": "Image could not be decoded",
                    "limitations": "Image could not be decoded",
                },
                "contrast": {
                    "michelson": 0.0, "rms": 0.0, "luminance_range": 0.0,
                    "method": "Michelson + RMS contrast from BT.709 luminance",
                    "version": NUMPY_VERSION,
                    "interpretation": "Image could not be decoded",
                    "limitations": "Image could not be decoded",
                },
                "edges": {
                    "mean_gradient": 0.0, "max_gradient": 0.0,
                    "edge_pixel_pct": 0.0, "edge_threshold": 0.1,
                    "method": "NumPy gradient (Sobel-like)",
                    "version": NUMPY_VERSION,
                    "interpretation": "Image could not be decoded",
                    "limitations": "Image could not be decoded",
                },
                "sharpness": {
                    "laplacian_variance": 0.0,
                    "sharpness_class": "soft",
                    "method": "Laplacian variance on BT.709 luminance",
                    "version": NUMPY_VERSION,
                    "interpretation": "Image could not be decoded",
                    "limitations": "Image could not be decoded",
                },
                "regions": {
                    "grid": 4, "patches": [],
                    "method": "4x4 grid, mean/std luminance per patch",
                    "version": NUMPY_VERSION,
                    "interpretation": "Image could not be decoded",
                    "limitations": "Image could not be decoded",
                },
                "alpha": {
                    "has_alpha": False,
                    "method": "Pillow Image.mode check",
                    "version": PILLOW_VERSION,
                    "interpretation": "Image could not be decoded",
                    "limitations": "Image could not be decoded",
                },
                "method_tier": "DETECTED",
                "evidence_tier_note": "Image failed to load — no pixel measurements available",
            }

        # Convert to RGB for consistent analysis (preserve alpha info separately)
        has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)

        h, w = arr.shape[:2]
        channels = arr.shape[2] if arr.ndim == 3 else 1

        # --- 1. Dimensions and aspect ratio ---
        dims = {
            "width": int(w),
            "height": int(h),
            "aspect_ratio": round(w / h, 6) if h else None,
            "orientation": "landscape" if w > h else "portrait" if h > w else "square",
            "method": "Pillow Image.size (via cv_core)",
            "version": PILLOW_VERSION,
            "interpretation": "Geometric dimensions of the raster image",
            "limitations": "Does not indicate semantic content or display size",
        }

        # --- 2. Color mode and alpha ---
        color_info = {
            "mode": img.mode,
            "has_alpha": bool(has_alpha),
            "method": "Pillow Image.mode (via cv_core)",
            "version": PILLOW_VERSION,
            "interpretation": "Color space and transparency presence",
            "limitations": "Mode indicates encoding, not semantic color usage",
        }

        # --- 3. Dominant colors / palette distribution ---
        # Quantize to 3 bits per channel (512 buckets) for palette analysis
        small = rgb.resize((64, 64), Image.Resampling.LANCZOS)
        arr_small = np.array(small, dtype=np.uint8).reshape(-1, 3)
        # Bucket each channel to 3 bits (0-7)
        buckets = (arr_small // 32).astype(np.int16)
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
                "bucket_r": int(r),
                "bucket_g": int(g),
                "bucket_b": int(b),
            })
        palette = {
            "dominant_colors": dominant,
            "unique_buckets": int(len(unique)),
            "method": "Pillow resize + NumPy histogram, 3 bits/channel bucketing",
            "version": f"Pillow {PILLOW_VERSION}, NumPy {NUMPY_VERSION}",
            "interpretation": "Approximate color distribution; bucketed, not exact",
            "limitations": "3-bit quantization loses fine color detail; 64x64 downsample loses spatial info",
        }

        # --- 4. Color histogram (per channel, 16 bins) ---
        hist = {}
        for ch_idx, ch_name in enumerate(["r", "g", "b"]):
            channel = arr[:, :, ch_idx].ravel()
            counts, bin_edges = np.histogram(channel, bins=16, range=(0, 256))
            hist[ch_name] = {
                "bin_counts": [int(c) for c in counts],
                "bin_edges": [int(e) for e in bin_edges],
                "method": "NumPy histogram, 16 bins, range 0-255",
                "version": NUMPY_VERSION,
                "interpretation": "Tonal distribution per color channel",
                "limitations": "16-bin histogram is coarse; not color-accurate for gradients",
            }

        # --- 5. Luminance distribution ---
        # Relative luminance per ITU-R BT.709: L = 0.2126*R + 0.7152*G + 0.0722*B
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
            "version": NUMPY_VERSION,
            "interpretation": "Overall brightness distribution; not semantic mood",
            "limitations": "Global luminance; does not indicate local contrast or mood",
        }

        # --- 6. Contrast estimates ---
        # Michelson contrast: (Lmax - Lmin) / (Lmax + Lmin)
        lum_max = float(lum.max())
        lum_min = float(lum.min())
        michelson = (lum_max - lum_min) / (lum_max + lum_min) if (lum_max + lum_min) > 0 else 0.0
        # RMS contrast: standard deviation of luminance
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

        # --- 7. Edge density/distribution (Sobel gradient magnitude) ---
        # Simple Sobel via NumPy gradient
        lum_f = lum.astype(np.float64)
        gy, gx = np.gradient(lum_f)
        grad_mag = np.sqrt(gx ** 2 + gy ** 2)
        edge_threshold = 0.1
        edge_mask = grad_mag > edge_threshold
        edge_density = {
            "mean_gradient": round(float(grad_mag.mean()), 4),
            "max_gradient": round(float(grad_mag.max()), 4),
            "edge_pixel_pct": round(float(edge_mask.mean() * 100), 2),
            "edge_threshold": edge_threshold,
            "method": "NumPy gradient (Sobel-like), gradient magnitude > 0.1",
            "version": NUMPY_VERSION,
            "interpretation": "Edge presence and strength; not object boundaries",
            "limitations": "Simple gradient; not Canny or semantic edge detection",
        }

        # --- 8. Blur/sharpness indicators ---
        # Laplacian variance (sharpness proxy)
        laplacian_kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
        padded = np.pad(lum_f, 1, mode="edge")
        lap = np.zeros_like(lum_f)
        for i in range(3):
            for j in range(3):
                lap += laplacian_kernel[i, j] * padded[i:i + h, j:j + w]
        lap_var = float(lap.var())
        sharpness = {
            "laplacian_variance": round(lap_var, 4),
            "sharpness_class": ("sharp" if lap_var > 100 else
                                "moderate" if lap_var > 20 else "soft"),
            "method": "Laplacian variance on BT.709 luminance",
            "version": NUMPY_VERSION,
            "interpretation": "Higher variance = sharper edges; not focus quality",
            "limitations": "Global measure; local blur variations not captured",
        }

        # --- 9. Region/patch statistics ---
        # Divide image into 4x4 grid, compute mean luminance per patch
        grid = 4
        patch_h, patch_w = h // grid, w // grid
        patches = []
        for gi in range(grid):
            for gj in range(grid):
                y0, y1 = gi * patch_h, min((gi + 1) * patch_h, h)
                x0, x1 = gj * patch_w, min((gj + 1) * patch_w, w)
                patch_lum = lum[y0:y1, x0:x1]
                patches.append({
                    "gi": gi, "gj": gj,
                    "mean_lum": round(float(patch_lum.mean()), 4),
                    "std_lum": round(float(patch_lum.std()), 4),
                })
        regions = {
            "grid": grid,
            "patches": patches,
            "method": "4x4 grid, mean/std luminance per patch",
            "version": NUMPY_VERSION,
            "interpretation": "Spatial luminance distribution; not object regions",
            "limitations": "Fixed grid; not content-aware regions",
        }

        # --- 10. Alpha/transparency statistics ---
        alpha_info = {
            "has_alpha": bool(has_alpha),
            "method": "Pillow Image.mode check (via cv_core)",
            "version": PILLOW_VERSION,
            "interpretation": "Whether image has transparency channel",
            "limitations": "Presence only; alpha distribution not computed",
        }
        if has_alpha:
            alpha_img = img.convert("RGBA")
            alpha_arr = np.array(alpha_img, dtype=np.uint8)
            alpha_channel = alpha_arr[:, :, 3]
            alpha_info.update({
                "alpha_mean": round(float(alpha_arr.mean() / 255.0), 4),
                "alpha_min": round(float(alpha_arr.min() / 255.0), 4),
                "alpha_max": round(float(alpha_arr.max() / 255.0), 4),
                "pct_fully_transparent": round(float((alpha_arr == 0).mean() * 100), 2),
                "pct_fully_opaque": round(float((alpha_arr == 255).mean() * 100), 2),
            })

        # --- Compile result ---
        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "pillow_version": PILLOW_VERSION,
            "numpy_version": NUMPY_VERSION,
            "dimensions": dims,
            "color": color_info,
            "palette": palette,
            "histogram": hist,
            "luminance": luminance,
            "contrast": contrast,
            "edges": edge_density,
            "sharpness": sharpness,
            "regions": regions,
            "alpha": alpha_info,
            "method_tier": "DETECTED",  # All metrics are direct pixel measurements
            "evidence_tier_note": "All metrics are DETECTED measurements from pixel data; "
                                  "no semantic interpretation or model inference involved",
        }
        return result


def run(targets, json_path: str | None = None):
    """Pixel analysis audit of file/dir targets."""
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
            metrics = analyze_pixels(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag low-quality images as potential issues
            if metrics["sharpness"]["laplacian_variance"] < 5:
                entry["issues"].append({
                    "t": "PIXEL-SOFT",
                    "det": f"low sharpness (Laplacian var {metrics['sharpness']['laplacian_variance']})",
                    "conf": 0.7
                })
            if metrics["contrast"]["michelson"] < 0.1:
                entry["issues"].append({
                    "t": "PIXEL-LOW-CONTRAST",
                    "det": f"low Michelson contrast ({metrics['contrast']['michelson']})",
                    "conf": 0.7
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "PIXEL-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
        m = entry["metrics"]
        n = len(entry.get("issues", []))
        if m:
            meta = f"  {m['dimensions']['width']}x{m['dimensions']['height']} "
            meta += f"lum={m['luminance']['mean']} contrast={m['contrast']['michelson']} "
            meta += f"sharp={m['sharpness']['laplacian_variance']} edges={m['edges']['edge_pixel_pct']}%"
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
