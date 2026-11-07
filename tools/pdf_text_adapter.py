#!/usr/bin/env python3
"""pdf_text_adapter.py — PDF text/geometry extraction for LiGeo CV sensor pack.

Extracts native text, page geometry, and embedded asset inventory from PDF files
using PyMuPDF (fitz). Prefers native text extraction over OCR; OCR is only used
as fallback for scanned/image-only pages.

  python tools/pdf_text_adapter.py doc.pdf
  python tools/cv_sensors/pdf_text_adapter.py doc.pdf --json out.json
  python tools/cv_sensors/pdf_text_adapter.py doc.pdf --dpi 150 --ocr-fallback

Exit code = number of targets with findings (0 = clean).
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cv_core import load_image

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("missing dependency: PyMuPDF (pip install pymupdf)")

try:
    import numpy as np
    NUMPY_VERSION = np.__version__
except ImportError:
    NUMPY_VERSION = None

try:
    import fitz
    PYMUPDF_VERSION = fitz.__doc__ if hasattr(fitz, '__doc__') else "unknown"
except Exception:
    PYMUPDF_VERSION = "unknown"


def _pt_to_mm(points: float) -> float:
    """Convert PDF points to millimeters."""
    return round(points * 25.4 / 72.0, 4)


def analyze_pdf(path: Path, dpi: int = 150, ocr_fallback: bool = False) -> dict:
    """Analyze a PDF document: metadata, pages, native text, and embedded assets.

    Prefers native text extraction. OCR is only used as fallback for
    image-only pages when ocr_fallback=True.
    """
    doc = fitz.open(str(path))

    result = {
        "path": str(path),
        "metrics_version": "1.0.0",
        "pymupdf_version": PYMUPDF_VERSION,
        "page_count": doc.page_count,
        "pages": [],
        "total_text_chars": 0,
        "total_images": 0,
        "method_tier": "DETECTED",
        "evidence_tier_note": "PDF metadata and native text are DETECTED measurements; "
                              "OCR fallback is marked as interpreted if used",
    }

    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        page_result = {
            "page_index": page_idx,
            "page_number": page_idx + 1,
            "page_size": {
                "width_pt": round(page.rect.width, 4),
                "height_pt": round(page.rect.height, 4),
                "width_mm": round(_pt_to_mm(page.rect.width), 4),
                "height_mm": round(_pt_to_mm(page.rect.height), 4),
            },
            "rotation": page.rotation,
            "mediabox": {
                "x0": round(page.mediabox.x0, 4),
                "y0": round(page.mediabox.y0, 4),
                "x1": round(page.mediabox.x1, 4),
                "y1": round(page.mediabox.y1, 4),
            },
            "cropbox": {
                "x0": round(page.cropbox.x0, 4),
                "y0": round(page.cropbox.y0, 4),
                "x1": round(page.cropbox.x1, 4),
                "y1": round(page.cropbox.y1, 4),
            },
            "text": {
                "char_count": 0,
                "word_count": 0,
                "blocks": [],
                "extraction_method": "native",
            },
            "images": [],
            "links": [],
            "ocr_used": False,
            "ocr_text": "",
        }

        # --- Native text extraction ---
        text_dict = page.get_text("dict")
        text_blocks = []
        char_count = 0
        word_count = 0

        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # text block
                block_text = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        block_text += span_text
                        char_count += len(span_text)
                        word_count += len(span_text.split())
                        text_blocks.append({
                            "text": span_text,
                            "bbox": [round(v, 4) for v in span.get("bbox", [0, 0, 0, 0])],
                            "font": span.get("font", ""),
                            "size": round(span.get("size", 0), 2),
                            "color": span.get("color", 0),
                            "flags": span.get("flags", 0),
                        })
                if block_text.strip():
                    text_blocks.append({
                        "block_text": block_text.strip(),
                        "bbox": [round(v, 4) for v in block.get("bbox", [0, 0, 0, 0])],
                        "block_no": block.get("number", 0),
                    })

        page_result["text"] = {
            "char_count": char_count,
            "word_count": word_count,
            "blocks": text_blocks,
            "extraction_method": "native",
        }
        result["total_text_chars"] += char_count

        # --- Embedded images ---
        img_list = page.get_images(full=True)
        page_images = []
        for img_index, img_info in enumerate(img_list):
            xref = img_info[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                img_entry = {
                    "xref": xref,
                    "width": pix.width,
                    "height": pix.height,
                    "colorspace": pix.colorspace.name if pix.colorspace else None,
                    "alpha": pix.alpha,
                }
                pix = None  # release
            except Exception as e:
                img_entry = {"xref": xref, "error": str(e)[:200]}
            page_images.append(img_entry)
        page_result["images"] = img_list
        result["total_images"] += len(img_list)

        # --- Links/annotations ---
        links = []
        for link in page.get_links():
            links.append({
                "kind": link.get("kind", 0),
                "from": [round(v, 4) for v in link.get("from", [0, 0, 0, 0])],
                "to": link.get("to", ""),
                "uri": link.get("uri", ""),
            })
        page_result["links"] = links

        # --- OCR fallback for image-only pages ---
        if char_count == 0 and ocr_fallback:
            try:
                pix = page.get_pixmap(dpi=dpi)
                img_data = pix.tobytes("png")
                import io
                from PIL import Image as PILImage
                from io import BytesIO
                pil_img = PILImage.open(BytesIO(img_data))
                # Run OCR
                import pytesseract
                ocr_text = pytesseract.image_to_string(pil_img)
                page_result["ocr_used"] = True
                page_result["ocr_text"] = ocr_text[:5000]  # cap at 5000 chars
                page_result["text"]["extraction_method"] = "ocr_fallback"
                result["total_text_chars"] += len(ocr_text)
            except Exception as e:
                page_result["ocr_error"] = str(e)[:200]

        result["pages"].append(page_result)

    doc.close()
    return result


def _empty_result(path: Path, reason: str) -> dict:
    return {
        "path": str(path),
        "metrics_version": "1.0.0",
        "error": reason,
        "page_count": 0,
        "pages": [],
        "total_text_chars": 0,
        "total_images": 0,
        "method_tier": "DETECTED",
        "evidence_tier_note": "PDF could not be opened",
    }


def run(targets, dpi: int = 150, ocr_fallback: bool = False,
        json_path: str | None = None):
    """PDF audit of file/dir targets."""
    targets_out = []
    for p in targets:
        p = Path(p)
        if p.is_dir():
            targets_out += sorted(p.rglob("*.pdf"))
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
            metrics = analyze_pdf(f, dpi=dpi, ocr_fallback=ocr_fallback)
            entry = {"file": str(f), "metrics": metrics, "issues": []}
            # Flag pages with no native text and no OCR fallback
            for page in metrics.get("pages", []):
                if page["text"]["char_count"] == 0 and not page.get("ocr_used"):
                    entry["issues"].append({
                        "t": "PDF-NO-TEXT",
                        "det": f"page {page['page_number']} has no extractable text",
                        "conf": 0.7,
                    })
            if entry["issues"]:
                dirty += 1
        except Exception as e:
            entry = {"file": str(f), "metrics": None, "issues": [
                {"t": "PDF-ANALYSIS-ERROR", "det": str(e)[:200], "conf": 1.0}
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
    ap.add_argument("--dpi", type=int, default=150,
                    help="DPI for page rendering when OCR fallback is used")
    ap.add_argument("--ocr-fallback", action="store_true",
                    help="use OCR for image-only pages")
    ap.add_argument("--json", help="write full evidence to this file")
    a = ap.parse_args()

    report, dirty = run(a.targets, dpi=a.dpi, ocr_fallback=a.ocr_fallback,
                        json_path=a.json)

    for entry in report:
        m = entry.get("metrics")
        n = len(entry.get("issues", []))
        if m:
            meta = f"  pages={m.get('page_count', 0)} "
            meta += f"text_chars={m.get('total_text_chars', 0)} "
            meta += f"images={m.get('total_images', 0)}"
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
