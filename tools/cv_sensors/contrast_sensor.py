#!/usr/bin/env python3
"""contrast_sensor.py — WCAG contrast ratio calculation for LiGeo CV sensor pack.

Computes WCAG 2.1 contrast ratios between foreground/background color pairs
using the W3C relative luminance formula:
    (L1 + 0.05) / (L2 + 0.05)
where L1 is the lighter luminance and L2 is the darker luminance.

  python tools/cv_sensors/contrast_sensor.py image.png
  python tools/cv_sensors/contrast_sensor.py images/ --json out.json

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


def _linearize_srgb(channel: float) -> float:
    """Linearize an sRGB channel value (0-255) per WCAG formula."""
    c = channel / 255.0
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(r: int, g: int, b: int) -> float:
    """Compute WCAG relative luminance for an RGB color."""
    r_lin = _linearize_srgb(r)
    g_lin = _linearize_srgb(g)
    b_lin = _linearize_srgb(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def _contrast_ratio(l1: float, l2: float) -> float:
    """Compute WCAG contrast ratio between two luminance values."""
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _wcag_level(ratio: float, text_size_large: bool = False) -> str:
    """Determine WCAG level for a contrast ratio."""
    if text_size_large:
        if ratio >= 3.0:
            return "AA"
        if ratio >= 4.5:
            return "AAA"
        return "Fail"
    else:
        if ratio >= 4.5:
            return "AA"
        if ratio >= 7.0:
            return "AAA"
        return "Fail"


def analyze_contrast(path: Path) -> dict:
    """Compute WCAG contrast metrics from an image file.

    Finds dominant foreground/background color pairs and computes
    contrast ratios. Also identifies the overall contrast range.
    """
    with load_image(path) as loaded:
        img = loaded.image
        if img is None:
            return _empty_result(path, "image could not be decoded")

        rgb = img.convert("RGB") if img.mode != "RGB" else img
        arr = np.array(rgb, dtype=np.uint8)
        h, w = arr.shape[:2]

        # --- Sample corner pixels as background candidates ---
        corners = [
            arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1],
            arr[0, w // 2], arr[-1, w // 2],
            arr[h // 2, 0], arr[h // 2, -1],
        ]
        bg_candidates = [tuple(c) for c in corners]

        # --- Sample center area as foreground candidates ---
        center_region = arr[h // 4:3 * h // 4, w // 4:3 * w // 4]
        center_flat = center_region.reshape(-1, 3)

        # Sample every 10th pixel from center for performance
        center_sample = center_flat[::10] if len(center_flat) > 10 else center_flat

        # --- Compute contrast for each fg/bg pair ---
        contrast_ratios = []
        for fg in center_sample[:50]:  # Limit to 50 samples for performance
            fg_lum = _relative_luminance(int(fg[0]), int(fg[1]), int(fg[2]))
            for bg in bg_candidates:
                bg_lum = _relative_luminance(int(bg[0]), int(bg[1]), int(bg[2]))
                ratio = _contrast_ratio(fg_lum, bg_lum)
                contrast_ratios.append({
                    "fg": [int(fg[0]), int(fg[1]), int(fg[2])],
                    "bg": [int(bg[0]), int(bg[1]), int(bg[2])],
                    "ratio": round(ratio, 4),
                    "level_normal": _wcag_level(ratio, text_size_large=False),
                    "level_large": _wcag_level(ratio, text_size_large=True),
                })

        # Sort by contrast ratio (lowest first = most problematic)
        contrast_ratios.sort(key=lambda x: x["ratio"])

        worst = contrast_ratios[0] if contrast_ratios else {
            "ratio": 0.0, "level_normal": "N/A", "level_large": "N/A"
        }
        best = contrast_ratios[-1] if contrast_ratios else {
            "ratio": 0.0, "level_normal": "N/A", "level_large": "N/A"
        }

        # --- Count low-contrast pairs ---
        low_contrast_count = sum(
            1 for r in contrast_ratios if r["ratio"] < 4.5
        )
        very_low_contrast_count = sum(
            1 for r in contrast_ratios if r["ratio"] < 3.0
        )

        result = {
            "path": str(path),
            "metrics_version": "1.0.0",
            "pillow_version": PILLOW_VERSION,
            "numpy_version": NUMPY_VERSION,
            "contrast_ratios": contrast_ratios[:10],  # Top 10 lowest
            "worst_ratio": round(worst["ratio"], 4),
            "best_ratio": round(best["ratio"], 4),
            "worst_level_normal": worst["level_normal"],
            "worst_level_large": worst["level_large"],
            "best_level_normal": best["level_normal"],
            "best_level_large": best["level_large"],
            "low_contrast_count": low_contrast_count,
            "very_low_contrast_count": very_low_contrast_count,
            "total_pairs_tested": len(contrast_ratios),
            "method": "WCAG 2.1 contrast ratio formula",
            "version": f"Pillow {PILLOW_VERSION}, NumPy {NUMPY_VERSION}",
            "interpretation": "WCAG contrast ratios between sampled foreground/background pairs",
            "limitations": "Foreground/background pairs are sampled heuristically; "
                           "not a full WCAG audit of all text elements",
        }
        return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "contrast_ratios": [],
        "worst_ratio": 0.0,
        "best_ratio": 0.0,
        "worst_level_normal": "N/A",
        "worst_level_large": "N/A",
        "best_level_normal": "N/A",
        "best_level_large": "N/A",
        "low_contrast_count": 0,
        "very_low_contrast_count": 0,
        "total_pairs_tested": 0,
        "method": "WCAG 2.1 contrast ratio formula",
        "version": PILLOW_VERSION if 'PILLOW_VERSION' in globals() else "unknown",
        "interpretation": "Image could not be decoded — no contrast metrics available",
        "evidence_tier_note": "Image could not be decoded — no contrast metrics available",
    }


def run(targets, json_path: str | None = None):
    """Contrast audit of file/dir targets."""
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
            metrics = analyze_contrast(f)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag low contrast pairs
            if metrics["worst_ratio"] < 4.5:
                entry["issues"].append({
                    "t": "CONTRAST-LOW",
                    "det": f"worst contrast ratio {metrics['worst_ratio']} below WCAG 4.5 threshold",
                    "conf": 0.8,
                })
            if metrics["very_low_contrast_count"] > 0:
                entry["issues"].append({
                    "t": "CONTRAST-VERY-LOW",
                    "det": f"{metrics['very_low_contrast_count']} contrast ratios below 3.0 (WCAG AAA large text threshold)",
                    "conf": 0.8,
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "CONTRAST-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
            meta = f"  worst_ratio={m['worst_ratio']} best_ratio={m['best_ratio']} "
            meta += f"low_count={m['low_contrast_count']}"
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
