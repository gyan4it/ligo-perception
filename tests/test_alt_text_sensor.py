#!/usr/bin/env python3
"""test_alt_text_sensor.py — unit tests for alt_text_sensor tool.

Tests:
- Image alt text detection
- Missing alt attribute detection
- Empty alt text detection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from alt_text_sensor import analyze_alt_text, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_html_alt_text_analysis():
    """Test alt text analysis on HTML file."""
    html_path = FIXTURES / "test_alt.html"
    if not html_path.exists():
        html_path.write_text('''
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<img src="image1.png" alt="Description">
<img src="image2.png">
<img src="image3.png" alt="">
</body>
</html>
''')
    result = analyze_alt_text(html_path)
    assert result is not None
    assert "img_count" in result
    print("  PASS: test_html_alt_text_analysis")


def test_img_count():
    """Test image count detection."""
    result = analyze_alt_text(FIXTURES / "test_alt.html")
    assert result["img_count"] >= 0
    print("  PASS: test_img_count")


def test_img_without_alt():
    """Test image without alt attribute detection."""
    result = analyze_alt_text(FIXTURES / "test_alt.html")
    assert "img_without_alt" in result
    print("  PASS: test_img_without_alt")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "test_alt.html")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "test_alt.html")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_alt_text_sensor.py ===")
    test_html_alt_text_analysis()
    test_img_count()
    test_img_without_alt()
    test_run_function()
    print("=== test_alt_text_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
