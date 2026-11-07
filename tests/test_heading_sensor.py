#!/usr/bin/env python3
"""test_heading_sensor.py — unit tests for heading_sensor tool.

Tests:
- HTML heading detection
- H1 count detection
- Heading hierarchy violations
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "cv_sensors"))
from heading_sensor import analyze_headings, run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_html_heading_analysis():
    """Test heading analysis on HTML file."""
    html_path = FIXTURES / "test_heading.html"
    if not html_path.exists():
        html_path.write_text('''
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<h1>Main Title</h1>
<h2>Section 1</h2>
<h3>Subsection 1.1</h3>
<h2>Section 2</h2>
<h4>Skipped H3!</h4>
</body>
</html>
''')
    result = analyze_headings(html_path)
    assert result is not None
    assert "heading_count" in result
    assert "h1_count" in result
    print("  PASS: test_html_heading_analysis")


def test_heading_count():
    """Test heading count detection."""
    result = analyze_headings(FIXTURES / "test_heading.html")
    assert result["heading_count"] >= 0
    print("  PASS: test_heading_count")


def test_h1_count():
    """Test H1 count detection."""
    result = analyze_headings(FIXTURES / "test_heading.html")
    assert "h1_count" in result
    print("  PASS: test_h1_count")


def test_hierarchy_violation():
    """Test hierarchy violation detection."""
    html_path = FIXTURES / "test_hierarchy.html"
    html_path.write_text('''
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<h1>Main Title</h1>
<h2>Section 1</h2>
<h4>Skipped H3!</h4>
</body>
</html>
''')
    result = analyze_headings(html_path)
    violations = result.get("hierarchy_violations", [])
    assert len(violations) > 0, f"Expected hierarchy violations, got {violations}"
    print("  PASS: test_hierarchy_violation")


def test_run_function():
    """Test the run() function."""
    report, dirty = run([str(FIXTURES / "test_heading.html")])
    assert len(report) == 1
    assert report[0]["file"] == str(FIXTURES / "test_heading.html")
    assert "metrics" in report[0]
    print("  PASS: test_run_function")


def run_all():
    print("\n=== test_heading_sensor.py ===")
    test_html_heading_analysis()
    test_heading_count()
    test_h1_count()
    test_hierarchy_violation()
    test_run_function()
    print("=== test_heading_sensor.py PASSED ===\n")


if __name__ == "__main__":
    run_all()
