#!/usr/bin/env python3
"""create_test_fixtures.py — generate synthetic test images for LiGeo sensor testing.

Creates:
- clean.png: solid color background (validates clean detection)
- violations.png: overflowing content, overlapping elements (tests detection)
- text_image.png: image with text (tests OCR)
- line_art.png: geometric lines and shapes (tests edge/line detection)
- low_contrast.png: low contrast image (tests contrast detection)
- rotated.png: rotated content (tests skew detection)
- text_heavy.png: lots of text (tests OCR and text detection)
- duplicate_pair_1.png / duplicate_pair_2.png: near-duplicate images (tests similarity)
- scanned_pdf_source.png: image that looks like a scanned page (tests PDF fallback)
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURES_DIR.mkdir(exist_ok=True)


def save_image(img: Image.Image, name: str):
    """Save a PIL image to fixtures directory."""
    path = FIXTURES_DIR / name
    img.save(path)
    print(f"Created {path}")


def create_clean_image():
    """Solid light gray background — should pass all checks cleanly."""
    img = Image.new("RGB", (200, 200), (240, 240, 240))
    save_image(img, "clean.png")


def create_violations_image():
    """Image with overflowing content and overlapping elements."""
    img = Image.new("RGB", (200, 200), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Large rectangle that nearly fills the image (overflow risk)
    draw.rectangle([10, 10, 190, 190], outline=(0, 0, 0), width=3)
    # Overlapping rectangles
    draw.rectangle([30, 30, 120, 120], outline=(255, 0, 0), width=2)
    draw.rectangle([80, 80, 170, 170], outline=(0, 255, 0), width=2)
    save_image(img, "violations.png")


def create_text_image():
    """Image with text content for OCR testing."""
    img = Image.new("RGB", (300, 150), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
    draw.text((10, 10), "Hello World Test", fill=(0, 0, 0), font=font)
    draw.text((10, 50), "OCR Test Line Two", fill=(0, 0, 0), font=font)
    draw.text((10, 90), "Third Line of Text", fill=(0, 0, 0), font=font)
    save_image(img, "text_image.png")


def create_line_art_image():
    """Image with geometric lines and shapes for edge/line detection."""
    img = Image.new("RGB", (200, 200), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Horizontal line
    draw.line([10, 50, 190, 50], fill=(0, 0, 0), width=3)
    # Vertical line
    draw.line([50, 10, 50, 190], fill=(0, 0, 0), width=3)
    # Diagonal line
    draw.line([10, 10, 190, 190], fill=(0, 0, 0), width=3)
    # Rectangle
    draw.rectangle([60, 60, 140, 140], outline=(0, 0, 0), width=2)
    # Circle
    draw.ellipse([60, 60, 140, 140], outline=(255, 0, 0), width=2)
    save_image(img, "line_art.png")


def create_low_contrast_image():
    """Low contrast image for contrast detection testing."""
    img = Image.new("RGB", (200, 200), (200, 200, 200))
    draw = ImageDraw.Draw(img)
    # Slightly darker rectangle
    draw.rectangle([40, 40, 160, 160], fill=(180, 180, 180))
    # Even darker rectangle
    draw.rectangle([70, 70, 130, 130], fill=(160, 160, 160))
    save_image(img, "low_contrast.png")


def create_rotated_image():
    """Image with rotated content for skew detection."""
    img = Image.new("RGB", (200, 200), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Tilted rectangle
    draw.rectangle([30, 30, 170, 170], outline=(0, 0, 0), width=3)
    # Rotate the whole image slightly
    img = img.rotate(15, resample=Image.Resampling.BICUBIC, fillcolor=(255, 255, 255))
    save_image(img, "rotated.png")


def create_text_heavy_image():
    """Image with lots of text for OCR and text detection."""
    img = Image.new("RGB", (400, 300), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
    lines = [
        "Line 1 of sample text",
        "Line 2 of sample text",
        "Line 3 of sample text",
        "Line 4 of sample text",
        "Line 5 of sample text",
        "Line 6 of sample text",
        "Line 7 of sample text",
        "Line 8 of sample text",
    ]
    y = 20
    for line in lines:
        draw.text((10, y), line, fill=(0, 0, 0), font=font)
        y += 25
    save_image(img, "text_heavy.png")


def create_duplicate_pair_1():
    """First image of a near-duplicate pair."""
    img = Image.new("RGB", (200, 200), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, 160, 160], outline=(0, 0, 0), width=3)
    draw.text((60, 90), "TEST", fill=(0, 0, 0))
    save_image(img, "duplicate_pair_1.png")


def create_duplicate_pair_2():
    """Second image of a near-duplicate pair (slightly modified)."""
    img = Image.new("RGB", (200, 200), (240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.rectangle([42, 42, 158, 158], outline=(0, 0, 0), width=3)
    draw.text((62, 92), "TEST", fill=(0, 0, 0))
    draw.line([10, 190, 190, 10], fill=(255, 0, 0), width=2)  # Small difference
    save_image(img, "duplicate_pair_2.png")


def create_scanned_pdf_source():
    """Image that looks like a scanned document page."""
    img = Image.new("RGB", (400, 600), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Draw document border
    draw.rectangle([20, 20, 380, 580], outline=(0, 0, 0), width=2)
    # Draw some text lines
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    y = 40
    for i in range(20):
        draw.text((40, y), f"Line {i+1} of document text content", fill=(0, 0, 0), font=font)
        y += 25
    # Add a small image-like rectangle
    draw.rectangle([100, 400, 300, 520], outline=(0, 0, 0), width=2)
    draw.text((140, 450), "Figure 1", fill=(0, 0, 0), font=font)
    save_image(img, "scanned_page.png")


if __name__ == "__main__":
    create_clean_image()
    create_violations_image()
    create_text_image()
    create_line_art_image()
    create_low_contrast_image()
    create_rotated_image()
    create_text_heavy_image()
    create_duplicate_pair_1()
    create_duplicate_pair_2()
    create_scanned_pdf_source()
    print(f"\nAll fixtures created in {FIXTURES_DIR}")
    for f in sorted(FIXTURES_DIR.iterdir()):
        print(f"  {f.name} ({f.stat().st_size} bytes)")
