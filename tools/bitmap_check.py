#!/usr/bin/env python3
"""bitmap_check — real PNG/JPEG ingestion for LiGeo global skill.

Loads raster images, validates content, extracts metadata, applies limits,
and guards against decompression bombs / resource exhaustion. Non-destructive.

All image decoding is delegated to tools/cv_core.py so images are decoded
once and validated consistently across all LiGeo tools.

  python tools/bitmap_check.py image.png                    # single image
  python tools/bitmap_check.py images/ --json out.json      # directory
  python tools/bitmap_check.py image.png --max-pixels 1000000 --max-file-mb 10

Exit code = number of targets with findings (0 = clean).
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profile_loader import load_profile
from cv_core import load_image, load_and_validate as cv_load_and_validate

# --- Default limits (configurable via CLI or profile) ---
DEFAULT_MAX_FILE_MB = 50
DEFAULT_MAX_PIXELS = 50_000_000   # ~50 MP (decompression bomb guard)
DEFAULT_MAX_DIMENSION = 20_000    # max width or height in px
DEFAULT_ALLOWED_FORMATS = {"PNG", "JPEG"}
DEFAULT_ALLOWED_MODES = {"1", "L", "P", "RGB", "RGBA", "CMYK", "YCbCr"}


def load_and_validate(path: Path,
                      max_file_mb: float = DEFAULT_MAX_FILE_MB,
                      max_pixels: int = DEFAULT_MAX_PIXELS,
                      max_dimension: int = DEFAULT_MAX_DIMENSION,
                      allowed_formats: set = DEFAULT_ALLOWED_FORMATS,
                      allowed_modes: set = DEFAULT_ALLOWED_MODES):
    """Load, validate, and extract metadata from a raster image.

    Delegates to cv_core.load_image for decoding and validation. Returns
    (record: dict, issues: list[dict]) for backward compatibility.
    Never embeds raw image bytes in output.
    """
    loaded = load_image(
        path,
        max_file_mb=max_file_mb,
        max_pixels=max_pixels,
        max_dimension=max_dimension,
        allowed_formats=allowed_formats,
        allowed_modes=allowed_modes,
    )
    info = loaded.info

    # Build record dict matching the previous bitmap_check.py format
    record = {
        "asset_id": info.asset_id,
        "path": info.path,
        "format": info.format,
        "width": info.width,
        "height": info.height,
        "aspect_ratio": info.aspect_ratio,
        "mode": info.mode,
        "has_alpha": info.has_alpha,
        "total_pixels": info.total_pixels,
        "file_size_bytes": info.file_size_bytes,
        "file_size_mb": info.file_size_mb,
        "exif_orientation": info.exif_orientation_applied,
        "icc_profile_present": info.icc_profile_present,
        "resize": None,  # cv_core handles downsample internally; exposed via scale_factor
        "orientation_normalized": info.exif_orientation_applied,
        "valid": info.valid,
    }
    if info.scale_factor != 1.0:
        record["resize"] = {
            "from": [info.width, info.height],
            "to": [info.processing_width, info.processing_height],
            "scale": info.scale_factor,
        }

    # Extract safe metadata from the loaded image (not raw bytes)
    metadata = {}
    if loaded.image is not None:
        for k in ("dpi", "icc_profile", "exif", "comment"):
            if k in loaded.image.info:
                v = loaded.image.info[k]
                if isinstance(v, bytes):
                    metadata[k] = f"<{len(v)} bytes>"
                elif isinstance(v, str) and len(v) > 200:
                    metadata[k] = v[:200] + "..."
                else:
                    metadata[k] = v
        # EXIF orientation number
        try:
            exif = loaded.image.getexif()
            if exif:
                orientation = exif.get(274)  # tag 274 = Orientation
                if orientation:
                    record["exif_orientation_value"] = orientation
        except Exception:
            pass
    record["metadata"] = metadata

    loaded.close()  # release memory — validation only, no pixel access needed
    return record, info.issues


def run(targets,
        max_file_mb: float = DEFAULT_MAX_FILE_MB,
        max_pixels: int = DEFAULT_MAX_PIXELS,
        max_dimension: int = DEFAULT_MAX_DIMENSION,
        json_path: str | None = None,
        profile: dict | None = None):
    """Bitmap ingestion audit of file/dir targets."""
    # Profile overrides CLI defaults for limits
    if profile:
        page = profile.get("page", {})
        # Profile doesn't currently define bitmap limits directly, but
        # page size can inform reasonable pixel limits
        pass
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
        record, issues = load_and_validate(
            f, max_file_mb=max_file_mb, max_pixels=max_pixels, max_dimension=max_dimension)
        entry = {"file": str(f), "record": record, "issues": issues}
        if issues:
            dirty += 1
        report.append(entry)

    if json_path and report:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report, dirty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--max-file-mb", type=float, default=DEFAULT_MAX_FILE_MB)
    ap.add_argument("--max-pixels", type=int, default=DEFAULT_MAX_PIXELS)
    ap.add_argument("--max-dimension", type=int, default=DEFAULT_MAX_DIMENSION)
    ap.add_argument("--profile", help="project profile JSON file")
    ap.add_argument("--json", help="write full evidence to this file")
    a = ap.parse_args()

    profile = load_profile(a.profile) if a.profile else None

    report, dirty = run(a.targets,
                        max_file_mb=a.max_file_mb,
                        max_pixels=a.max_pixels,
                        max_dimension=a.max_dimension,
                        json_path=a.json,
                        profile=profile)

    for entry in report:
        r = entry["record"]
        n = len(entry["issues"])
        fmt = r.get("format") or "?"
        w = r.get("width") or 0
        h = r.get("height") or 0
        mode = r.get("mode") or "?"
        alpha = r.get("has_alpha") or False
        px = r.get("total_pixels") or 0
        meta = f"  {fmt} {w}x{h} mode={mode} alpha={alpha} px={px:,}"
        print(("!! " if n else "OK ") + entry["file"] + meta)
        for iss in entry["issues"]:
            print(f"     - [{iss.get('t')} conf {iss.get('conf', 0):.2f}] {iss.get('det')}")

    if a.json:
        print(f"\nevidence written: {a.json}")
    print(f"\nTARGETS: {len(report)}  DIRTY: {dirty}")
    sys.exit(min(dirty, 1))


if __name__ == "__main__":
    main()
