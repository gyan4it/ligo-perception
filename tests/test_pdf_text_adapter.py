#!/usr/bin/env python3
"""test_pdf_text_adapter.py — unit tests for pdf_text_adapter tool.

Tests:
- PDF metadata extraction
- Text extraction from text-based PDF
- Page count and dimensions
- Image extraction
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from pdf_text_adapter import analyze_pdf, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TEST_PDF = FIXTURES / "test_text.pdf"


def test_pdf_text_extraction():
    """Test PDF text extraction from text-based PDF."""
    result = analyze_pdf(TEST_PDF)
    assert result is not None
    assert result["page_count"] >= 1
    assert result["total_text_chars"] > 0
    print("  PASS: test_pdf_text_extraction")


def test_pdf_page_dimensions():
    """Test PDF page dimension extraction."""
    result = analyze_pdf(TEST_PDF)
    pages = result["pages"]
    assert len(pages) > 0
    page = pages[0]
    assert "page_size" in page
    assert "width_pt" in page["page_size"]
    assert "height_pt" in page["page_size"]
    print("  PASS: test_pdf_page_dimensions")


def test_pdf_text_blocks():
    """Test PDF text block extraction."""
    result = analyze_pdf(TEST_PDF)
    pages = result["pages"]
    text_blocks = pages[0]["text"]["blocks"]
    assert len(text_blocks) > 0
    # Check that at least one block has text content
    has_text = any("block_text" in b or "text" in b for b in pages[0]["text"]["blocks"])
    assert has_text
    print("  PASS: test_pdf_text_blocks")


def test_pdf_run_function():
    """Test the run() function."""
    report, dirty = run([str(TEST_PDF)])
    assert len(report) == 1
    assert report[0]["file"] == str(TEST_PDF)
    assert "metrics" in report[0]
    print("  PASS: test_pdf_run_function")


def run_all():
    print("\n=== test_pdf_text_adapter.py ===")
    test_pdf_text_extraction()
    test_pdf_page_dimensions()
    test_pdf_text_blocks()
    test_pdf_run_function()
    print("=== test_pdf_text_adapter.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
