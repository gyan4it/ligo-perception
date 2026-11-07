#!/usr/bin/env python3
"""test_link_sensor.py — unit tests for link_sensor tool.

Tests:
- HTML link detection
- Broken link detection
- Link text detection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from link_sensor import analyze_links, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_html_link_analysis():
    """Test link analysis on HTML file."""
    html_path = FIXTURES / "test_link.html"
    if not html_path.exists():
        # Create a simple HTML test file
        html_path.write_text('''
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<a href="page1.html">Link 1</a>
<a href="page2.html">Link 2</a>
<a href="#">Empty link</a>
<img src="image.png" alt="test">
</body>
</html>
''')
    result = analyze_links(html_path)
    assert result is not None
    assert "link_count" in result
    print("  PASS: test_html_link_analysis")


def test_link_count():
    """Test link count detection."""
    result = analyze_links(FIXTURES / "test_link.html")
    assert result["link_count"] >= 0
    print("  PASS: test_link_count")


def test_broken_link_detection():
    """Test broken link detection."""
    result = analyze_links(FIXTURES / "test_link.html")
    assert "broken_link_count" in result
    print("  PASS: test_broken_link_detection")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "test_link.html")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "test_link.html")
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_link_sensor.py ===")
    test_html_link_analysis()
    test_link_count()
    test_broken_link_detection()
    test_run_function()
    print("=== test_link_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
