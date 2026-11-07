#!/usr/bin/env python3
"""cv_core.py — shared image processing core for LiGeo global skill.

Provides a single, validated image decoding and preprocessing path so every
LiGeo tool decodes images once, validates them consistently, and avoids
wasting memory/CPU by decoding the same file multiple times.

Designed for an 8 GB RAM, integrated-GPU environment:
- one image decoded and held in memory at a time;
- optional downsampling with recorded scale factor;
- ROI (region of interest) helpers;
- no raw pixel arrays serialized into evidence JSON;
- EXIF orientation normalized consistently;
- alpha handled explicitly.

  python tools/cv_core.py image.png              # inspect and validate
  from cv_core import load_image, ImageInfo, load_and_validate

Classes:
    ImageInfo — metadata about a decoded image (no raw pixels in JSON).
    LoadedImage — in-memory image with validation info.

Functions:
    load_image(path, max_pixels=None, max_dimension=None, max_file_mb=None,
               allowed_formats=None, allowed_modes=None, downsample_to=None)
        Load and validate an image file. Returns LoadedImage.
    load_and_validate(...) -> (dict, list[dict])
        Compatibility wrapper returning (record, issues) like bitmap_check.py.
"""

import hashlib
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError as e:
    sys.exit(f"missing dependency: Pillow (pip install pillow)")

try:
    import numpy as np
except ImportError:
    np = None  # numpy optional at import, required for array ops

# --- Default limits (configurable via args or profile) ---
DEFAULT_MAX_FILE_MB = 50
DEFAULT_MAX_PIXELS = 50_000_000   # ~50 MP (decompression bomb guard)
DEFAULT_MAX_DIMENSION = 20_000    # max width or height in px
DEFAULT_ALLOWED_FORMATS = {"PNG", "JPEG"}
DEFAULT_ALLOWED_MODES = {"1", "L", "P", "RGB", "RGBA", "CMYK", "YCbCr"}
DEFAULT_JPEG_QUALITY = 85


@dataclass
class ImageInfo:
    """Metadata about an image — no raw pixels.

    All values are JSON-serializable primitives.
    """
    asset_id: str
    path: str
    format: Optional[str]
    mode: Optional[str]
    width: int
    height: int
    aspect_ratio: Optional[float]
    orientation: str  # landscape / portrait / square / unknown
    has_alpha: bool
    total_pixels: int
    file_size_bytes: int
    file_size_mb: float
    exif_orientation_applied: bool
    icc_profile_present: bool
    processing_width: int
    processing_height: int
    scale_factor: float
    valid: bool
    issues: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LoadedImage:
    """In-memory image with validation metadata.

    Holds the actual PIL Image object. Callers are responsible for releasing
    it (e.g. via context manager or `del`) after use to keep memory bounded
    on an 8 GB machine.
    """
    info: ImageInfo
    image: Optional[Image.Image] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self.image is not None:
            try:
                self.image.close()
            except Exception:
                pass
            self.image = None

    def to_info_dict(self) -> dict:
        return self.info.to_dict()


def safe_asset_id(path: Path) -> str:
    """Stable asset ID from file hash (not raw bytes in logs)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"img:{h.hexdigest()[:16]}"


def parse_css_length_mm(val) -> Optional[float]:
    """Parse a CSS length string (e.g. '1.15cm') into mm."""
    if isinstance(val, (int, float)):
        return float(val)
    if not isinstance(val, str):
        return None
    import re
    m = re.match(r'^([+-]?[\d.]+)\s*(cm|mm|in|pt|px|%)?$', val.strip())
    if not m:
        return None
    num = float(m[1])
    unit = (m[2] or "mm").lower()
    if unit == "mm":
        return num
    if unit == "cm":
        return num * 10
    if unit == "in":
        return num * 25.4
    if unit == "pt":
        return num * 25.4 / 72
    if unit == "px":
        return num * 25.4 / 96
    if unit == "%":
        return None
    return None


def convert_to_mm(value, unit) -> Optional[float]:
    """Convert a numeric value with CSS unit to mm."""
    if unit == "mm":
        return value
    if unit == "cm":
        return value * 10
    if unit == "in":
        return value * 25.4
    if unit == "pt":
        return value * 25.4 / 72
    if unit == "px":
        return value * 25.4 / 96
    if unit == "%":
        return None
    return None


def _decode_image(path: Path) -> Image.Image:
    """Open and fully decode an image file.

    Raises UnidentifiedImageError if the content is not a recognized image.
    """
    img = Image.open(path)
    img.load()  # force decode to catch truncated/corrupt files
    return img


def _normalize_orientation(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation transpose in-place, returning the image."""
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass  # orientation not present or unreadable — leave as-is
    return img


def load_image(
    path: str | Path,
    max_file_mb: float = DEFAULT_MAX_FILE_MB,
    max_pixels: int = DEFAULT_MAX_PIXELS,
    max_dimension: int = DEFAULT_MAX_DIMENSION,
    allowed_formats: Optional[set] = None,
    allowed_modes: Optional[set] = None,
    downsample_to: Optional[int] = None,
) -> LoadedImage:
    """Load, validate, and optionally downsample an image file.

    Returns a LoadedImage. The caller must close() it or use it as a context
    manager to release memory.

    Raises nothing for validation failures — they are recorded in info.issues
    and info.valid is set False. Raises FileNotFoundError if the file is
    missing; raises UnidentifiedImageError if content is not an image.
    """
    path = Path(path)
    issues = []

    # --- 1. File existence ---
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")

    # --- 2. File size ---
    file_size = path.stat().st_size
    file_size_mb = round(file_size / (1024 * 1024), 4)

    if file_size == 0:
        issues.append({"t": "BITMAP-EMPTY", "det": "file is 0 bytes", "conf": 1.0})

    if file_size > max_file_mb * 1024 * 1024:
        issues.append({
            "t": "BITMAP-TOO-LARGE",
            "det": f"file {file_size_mb} MB exceeds {max_file_mb} MB limit",
            "conf": 1.0,
        })

    # --- 3. Decode and validate content (not extension) ---
    try:
        img = _decode_image(path)
    except UnidentifiedImageError as e:
        issues.append({
            "t": "BITMAP-UNKNOWN-FORMAT",
            "det": f"not a recognized image: {path.name}",
            "conf": 1.0,
        })
        record = ImageInfo(
            asset_id=safe_asset_id(path),
            path=str(path),
            format=None,
            mode=None,
            width=0,
            height=0,
            aspect_ratio=None,
            orientation="unknown",
            has_alpha=False,
            total_pixels=0,
            file_size_bytes=file_size,
            file_size_mb=file_size_mb,
            exif_orientation_applied=False,
            icc_profile_present=False,
            processing_width=0,
            processing_height=0,
            scale_factor=1.0,
            valid=False,
            issues=issues,
        )
        return LoadedImage(info=record, image=None)

    # Capture original metadata before any transforms
    original_format = img.format
    original_mode = img.mode
    original_width = img.width
    original_height = img.height
    has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
    icc_present = "icc_profile" in img.info

    # --- 4. Normalize EXIF orientation ---
    img = _normalize_orientation(img)
    orientation_applied = True  # attempted; may be no-op if no orientation tag

    # Re-read dims after orientation transpose (may swap w/h)
    width = img.width
    height = img.height
    aspect_ratio = round(width / height, 6) if height else None
    orientation = (
        "landscape" if width > height else "portrait" if height > width else "square"
    )
    total_pixels = width * height

    # --- 5. Dimension/pixel limits ---
    if total_pixels > max_pixels:
        issues.append({
            "t": "BITMAP-TOO-MANY-PIXELS",
            "det": f"{total_pixels:,} px exceeds {max_pixels:,} px limit",
            "conf": 1.0,
        })
    if width > max_dimension or height > max_dimension:
        issues.append({
            "t": "BITMAP-DIMENSION",
            "det": f"{width}x{height} exceeds {max_dimension}px max dimension",
            "conf": 1.0,
        })

    # --- 6. Format/mode validation ---
    allowed_formats = allowed_formats or DEFAULT_ALLOWED_FORMATS
    allowed_modes = allowed_modes or DEFAULT_ALLOWED_MODES

    if original_format not in allowed_formats:
        issues.append({
            "t": "BITMAP-FORMAT",
            "det": f"format {original_format} not in allowed {sorted(allowed_formats)}",
            "conf": 1.0,
        })
    if original_mode not in allowed_modes:
        issues.append({
            "t": "BITMAP-MODE",
            "det": f"color mode {original_mode} not in allowed {sorted(allowed_modes)}",
            "conf": 1.0,
        })

    # --- 7. Downsample if needed ---
    scale_factor = 1.0
    processing_width = width
    processing_height = height

    if downsample_to and total_pixels > downsample_to * downsample_to:
        scale = (downsample_to * downsample_to / total_pixels) ** 0.5
        new_w = max(1, int(width * scale))
        new_h = max(1, int(height * scale))
        try:
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            processing_width = new_w
            processing_height = new_h
            scale_factor = round(scale, 4)
        except Exception as e:
            issues.append({
                "t": "BITMAP-RESIZE-FAIL",
                "det": str(e)[:200],
                "conf": 0.8,
            })

    valid = len([i for i in issues if i.get("conf", 0) >= 0.9]) == 0

    info = ImageInfo(
        asset_id=safe_asset_id(path),
        path=str(path),
        format=original_format,
        mode=original_mode,
        width=original_width,
        height=original_height,
        aspect_ratio=aspect_ratio,
        orientation=orientation,
        has_alpha=has_alpha,
        total_pixels=total_pixels,
        file_size_bytes=file_size,
        file_size_mb=file_size_mb,
        exif_orientation_applied=orientation_applied,
        icc_profile_present=icc_present,
        processing_width=processing_width,
        processing_height=processing_height,
        scale_factor=scale_factor,
        valid=valid,
        issues=issues,
    )

    return LoadedImage(info=info, image=img)


def load_and_validate(
    path: str | Path,
    max_file_mb: float = DEFAULT_MAX_FILE_MB,
    max_pixels: int = DEFAULT_MAX_PIXELS,
    max_dimension: int = DEFAULT_MAX_DIMENSION,
    allowed_formats: Optional[set] = None,
    allowed_modes: Optional[set] = None,
) -> tuple:
    """Compatibility wrapper returning (record, issues) like bitmap_check.py.

    Does NOT keep the image in memory — closes it after validation.
    Use load_image() if you need pixel access.
    """
    loaded = load_image(
        path,
        max_file_mb=max_file_mb,
        max_pixels=max_pixels,
        max_dimension=max_dimension,
        allowed_formats=allowed_formats,
        allowed_modes=allowed_modes,
    )
    record = loaded.info.to_dict()
    issues = loaded.info.issues
    loaded.close()  # release memory — no pixel data needed for validation-only
    return record, issues


def get_roi(image: Image.Image, x: int, y: int, w: int, h: int) -> Image.Image:
    """Extract a region of interest from an image.

    Returns a new image (caller should close it when done).
    Clamps coordinates to image bounds.
    """
    iw, ih = image.size
    x = max(0, min(x, iw))
    y = max(0, min(y, ih))
    w = max(0, min(w, iw - x))
    h = max(0, min(h, ih - y))
    if w == 0 or h == 0:
        return Image.new(image.mode, (1, 1))
    return image.crop((x, y, x + w, y + h))


def image_to_array(image: Image.Image, mode: str = "RGB"):
    """Convert a PIL Image to a NumPy array.

    Returns None if NumPy is not available.
    """
    if np is None:
        raise ImportError("NumPy is required for array conversion")
    return np.array(image.convert(mode), dtype=np.uint8)


def make_evidence_block(
    sensor_id: str,
    sensor_version: str = "1.0",
    asset_id: str | None = None,
    target: str | None = None,
) -> dict:
    """Create a standard evidence block envelope (L1 evidence contract).

    Returns a dict with sensor_id, sensor_version, asset_id, target, issues,
    metrics, errors, evidence_tier, processing_time_ms, memory_peak_bytes,
    limitations, warnings.
    """
    return {
        "sensor_id": sensor_id,
        "sensor_version": sensor_version,
        "asset_id": asset_id,
        "target": target,
        "results": [],
        "issues": [],
        "metrics": {},
        "errors": [],
        "evidence_tier": "DETECTED",
        "processing_time_ms": None,
        "memory_peak_bytes": None,
        "limitations": [],
        "warnings": [],
    }


def make_issue(
    code: str,
    detail: str,
    confidence: float = 1.0,
    rect: dict | None = None,
    evidence: dict | None = None,
) -> dict:
    """Create a standardized evidence issue/finding dict."""
    issue = {
        "t": code,
        "det": detail,
        "conf": round(float(confidence), 4),
    }
    if rect is not None:
        issue["rect"] = rect
    if evidence is not None:
        issue["evidence"] = evidence
    return issue


def make_evidence_result(
    sensor_id: str,
    sensor_version: str = "1.0",
    asset_id: str | None = None,
    target: str | None = None,
) -> dict:
    """Create a complete evidence result block following the controller contract.

    Returns a dict with sensor_id, sensor_version, asset_id, target, results,
    issues, metrics, errors, evidence_tier, processing_time_ms,
    memory_peak_bytes, limitations, warnings.
    """
    return {
        "sensor_id": sensor_id,
        "sensor_version": sensor_version,
        "asset_id": asset_id,
        "target": target,
        "results": [],
        "issues": [],
        "metrics": {},
        "errors": [],
        "evidence_tier": "DETECTED",
        "processing_time_ms": None,
        "memory_peak_bytes": None,
        "limitations": [],
        "warnings": [],
    }


def add_issue(result: dict, issue: dict) -> None:
    """Add an issue to an evidence result."""
    if "issues" not in result:
        result["issues"] = []
    result["issues"].append(issue)


def add_result(result: dict, result_item: dict) -> None:
    """Add a result item to an evidence result."""
    if "results" not in result:
        result["results"] = []
    result["results"].append(result_item)


def add_metadata(result: dict, key: str, value) -> None:
    """Add metadata to an evidence result."""
    if "metrics" not in result:
        result["metrics"] = {}
    result["metrics"][key] = value


def add_limitation(result: dict, limitation: str) -> None:
    """Add a limitation to an evidence result."""
    if "limitations" not in result:
        result["limitations"] = []
    result["limitations"].append(limitation)


def add_warning(result: dict, warning: str) -> None:
    """Add a warning to an evidence result."""
    if "warnings" not in result:
        result["warnings"] = []
    result["warnings"].append(warning)


def add_error(result: dict, error: str) -> None:
    """Add an error to an evidence result."""
    if "errors" not in result:
        result["errors"] = []
    result["errors"].append(error)


def finalize_evidence(result: dict) -> dict:
    """Finalize an evidence result: compute timing, validate structure."""
    if "evidence_tier" not in result:
        result["evidence_tier"] = "DETECTED"
    if "processing_time_ms" not in result:
        result["processing_time_ms"] = None
    if "memory_peak_bytes" not in result:
        result["memory_peak_bytes"] = None
    if "limitations" not in result:
        result["limitations"] = []
    if "warnings" not in result:
        result["warnings"] = []
    return result


def main():
    """CLI: load and validate an image file, print summary."""
    import argparse
    ap = argparse.ArgumentParser(description="Load and validate an image via cv_core")
    ap.add_argument("image", help="path to image file")
    ap.add_argument("--max-pixels", type=int, default=DEFAULT_MAX_PIXELS)
    ap.add_argument("--max-dimension", type=int, default=DEFAULT_MAX_DIMENSION)
    ap.add_argument("--max-file-mb", type=float, default=DEFAULT_MAX_FILE_MB)
    a = ap.parse_args()

    try:
        with load_image(
            a.image,
            max_file_mb=a.max_file_mb,
            max_pixels=a.max_pixels,
            max_dimension=a.max_dimension,
        ) as li:
            info = li.info
            print(f"asset_id:    {info.asset_id}")
            print(f"path:        {info.path}")
            print(f"format:      {info.format}")
            print(f"mode:        {info.mode}")
            print(f"size:        {info.width}x{info.height}")
            print(f"aspect:      {info.aspect_ratio}")
            print(f"orientation: {info.orientation}")
            print(f"has_alpha:   {info.has_alpha}")
            print(f"total_px:    {info.total_pixels:,}")
            print(f"file_size:   {info.file_size_mb} MB")
            print(f"exif_orient: {info.exif_orientation_applied}")
            print(f"icc:         {info.icc_profile_present}")
            print(f"proc_size:   {info.processing_width}x{info.processing_height}")
            print(f"scale:       {info.scale_factor}")
            print(f"valid:       {info.valid}")
            if info.issues:
                print("issues:")
                for iss in info.issues:
                    print(f"  - [{iss.get('t')} conf {iss.get('conf', 0):.2f}] {iss.get('det')}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except UnidentifiedImageError as e:
        print(f"ERROR: not a recognized image: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
