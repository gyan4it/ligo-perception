#!/usr/bin/env python3
"""ocr_adapter — pluggable OCR adapter for LiGeo global skill.

Extracts text, bounding boxes, reading order, and engine confidence from
raster images. OCR is separate from semantic vision — it is not ground truth.

  python tools/ocr_adapter.py image.png
  python tools/ocr_adapter.py images/ --json out.json

Exit code = number of targets with findings (0 = clean).
"""
import argparse, json, sys
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

# --- Dependency versions ---
try:
    import PIL
    PILLOW_VERSION = PIL.__version__
except Exception:
    PILLOW_VERSION = "unknown"

try:
    import pytesseract
    TESSERACT_VERSION = pytesseract.get_tesseract_version()
except Exception:
    TESSERACT_VERSION = "unknown"


def run_ocr_tesseract(path: Path, lang: str = "eng") -> dict:
    """Run OCR via pytesseract/Tesseract.

    Returns a dict with text, boxes, confidence, and metadata.
    Never embeds raw image bytes in output.
    """
    img = Image.open(path)
    img.load()

    # Run OCR with data output (bounding boxes + confidence)
    data = pytesseract.image_to_data(
        img, lang=lang, output_type=pytesseract.Output.DICT
    )

    # Extract text lines with boxes and confidence
    text_blocks = []
    n_words = 0
    confidences = []

    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        conf = float(data["conf"][i])
        if text and conf > 0:
            text_blocks.append({
                "text": text,
                "left": int(data["left"][i]),
                "top": int(data["top"][i]),
                "width": int(data["width"][i]),
                "height": int(data["height"][i]),
                "conf": round(conf, 1),
            })
            n_words += 1
            confidences.append(conf)

    full_text = " ".join(tb["text"] for tb in text_blocks)
    avg_conf = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

    return {
        "engine": "tesseract",
        "engine_version": str(TESSERACT_VERSION),
        "lang": lang,
        "full_text": full_text,
        "n_words": n_words,
        "avg_confidence": avg_conf,
        "text_blocks": text_blocks,
        "method": "pytesseract + Tesseract OCR",
        "version": f"pytesseract + Tesseract {TESSERACT_VERSION}",
        "interpretation": "Extracted text with bounding boxes; not semantic understanding",
        "limitations": "OCR is not ground truth; accuracy degrades with low resolution, stylized fonts, rotation, and complex layouts",
    }


def run_ocr_stub(path: Path) -> dict:
    """Fallback when no OCR engine is available."""
    return {
        "engine": "none",
        "engine_version": None,
        "lang": None,
        "full_text": "",
        "n_words": 0,
        "avg_confidence": 0.0,
        "text_blocks": [],
        "method": "no OCR engine available",
        "version": "N/A",
        "interpretation": "OCR unavailable — no text extracted",
        "limitations": "Install Tesseract or configure another OCR engine",
    }


def analyze_ocr(path: Path, lang: str = "eng") -> dict:
    """Run OCR analysis on an image file.

    Returns result dict with OCR data and availability status.
    """
    if PYTESSERACT_AVAILABLE:
        try:
            ocr_data = run_ocr_tesseract(path, lang=lang)
            available = True
        except Exception as e:
            ocr_data = {
                "engine": "tesseract",
                "error": str(e)[:200],
                "full_text": "",
                "n_words": 0,
                "avg_confidence": 0.0,
                "text_blocks": [],
                "method": "pytesseract + Tesseract OCR (failed)",
                "version": str(TESSERACT_VERSION),
                "interpretation": "OCR engine error",
                "limitations": "Tesseract execution failed",
            }
            available = False
    else:
        ocr_data = run_ocr_stub(path)
        available = False

    return {
        "path": str(path),
        "ocr_available": available,
        "ocr": ocr_data,
        "evidence_tier": "DETECTED",  # OCR output is detected text, not interpreted meaning
        "evidence_tier_note": "OCR text is DETECTED from pixel patterns; semantic meaning is not derived",
    }


def run(targets, lang: str = "eng", json_path: str | None = None):
    """OCR audit of file/dir targets."""
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
            result = analyze_ocr(f, lang=lang)
            entry = {"file": str(f), "ocr": result, "issues": []}
            # Flag low-confidence OCR as potential issue
            if result["ocr"]["avg_confidence"] < 50 and result["ocr"]["n_words"] > 0:
                entry["issues"].append({
                    "t": "OCR-LOW-CONFIDENCE",
                    "det": f"average OCR confidence {result['ocr']['avg_confidence']} below 50 threshold",
                    "conf": 0.7
                })
            if not result["ocr_available"]:
                entry["issues"].append({
                    "t": "OCR-UNAVAILABLE",
                    "det": "OCR engine not available — text extraction skipped",
                    "conf": 1.0
                })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "ocr": None, "issues": [
                {"t": "OCR-ERROR", "det": str(e)[:200], "conf": 1.0}
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
    ap.add_argument("--lang", default="eng", help="OCR language (default: eng)")
    ap.add_argument("--json", help="write full evidence to this file")
    a = ap.parse_args()

    report, dirty = run(a.targets, lang=a.lang, json_path=a.json)

    for entry in report:
        ocr = entry.get("ocr")
        n = len(entry.get("issues", []))
        if ocr and ocr.get("ocr"):
            o = ocr["ocr"]
            meta = f"  engine={o.get('engine')} words={o.get('n_words')} conf={o.get('avg_confidence')} available={ocr.get('ocr_available')}"
        else:
            meta = "  (no OCR data)"
        print(("!! " if n else "OK ") + entry["file"] + meta)
        for iss in entry.get("issues", []):
            print(f"     - [{iss.get('t')} conf {iss.get('conf', 0):.2f}] {iss.get('det')}")

    if a.json:
        print(f"\nevidence written: {a.json}")
    print(f"\nTARGETS: {len(report)}  DIRTY: {dirty}")
    sys.exit(min(dirty, 1))


if __name__ == "__main__":
    main()
