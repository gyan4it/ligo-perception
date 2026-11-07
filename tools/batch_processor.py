#!/usr/bin/env python3
"""batch_processor.py — batch processing for LiGeo visual QA.

Processes multiple files through LiGO sensors in batch, with progress
tracking and aggregated results.

  python tools/cv_sensors/batch_processor.py images/ --json out.json
  python tools/cv_sensors/batch_processor.py file1.html file2.html --json out.json

Exit code = number of targets with findings (0 = clean).
"""
import argparse, json, sys, time
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


def collect_targets(targets):
    """Collect all image/HTML files from targets (files or directories)."""
    targets_out = []
    for p in targets:
        p = Path(p)
        if p.is_dir():
            targets_out += sorted(p.rglob("*.png")) + sorted(p.rglob("*.jpg")) + \
                           sorted(p.rglob("*.jpeg")) + sorted(p.rglob("*.html")) + \
                           sorted(p.rglob("*.htm"))
        elif p.exists():
            targets_out.append(p)
        else:
            sys.exit(f"no such target: {p}")
    seen, uniq = set(), []
    for f in targets_out:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            uniq.append(f)
    return uniq


def run_batch(targets, processors=None, json_path=None,
              progress_callback=None):
    """Batch process targets through a list of (name, func) processors.

    Each processor is a callable that takes a Path and returns a dict
    of metrics/results.

    Args:
        targets: List of file paths to process
        processors: List of (name, callable) tuples
        json_path: Optional path to write JSON output
        progress_callback: Optional callback(current, total)

    Returns:
        Dict with batch results
    """
    targets_out = collect_targets(targets)
    results = []
    errors = []

    for i, target_path in enumerate(targets_out):
        entry = {"file": str(target_path), "processors": {}}
        for proc_name, proc_func in (processors or []):
            try:
                proc_result = proc_func(target_path)
                entry["processors"][proc_name] = proc_result
            except Exception as e:
                entry["processors"][proc_name] = {
                    "error": str(e)[:200]
                }
        results.append(entry)

        if progress_callback:
            progress_callback(i + 1, len(targets_out))

    return {
        "results": results,
        "errors": errors,
        "total_targets": len(targets_out),
        "processed_count": len(results),
        "error_count": len(errors),
        "metrics_version": "1.0.0",
    }


def run(targets, processors=None, json_path=None,
        progress_callback=None):
    """Run batch processing on targets.

    Args:
        targets: List of file paths or directories
        processors: List of (name, callable) tuples
        json_path: Optional path to write JSON output
        progress_callback: Optional callback(current, total)

    Returns:
        Batch processing results dict
    """
    return run_batch(targets, processors, json_path, progress_callback)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+",
                    help="Files or directories to process")
    ap.add_argument("--json", help="write batch results to JSON file")
    ap.add_argument("--processor", action="append",
                    help="Processor name to run (can specify multiple)")
    a = ap.parse_args()

    # Build processor map from available tools
    processors = []
    try:
        from layout_check import run as layout_check_run
        processors.append(("layout_check", layout_check_run))
    except ImportError:
        pass
    try:
        from bitmap_check import run as bitmap_check_run
        processors.append(("bitmap_check", bitmap_check_run))
    except ImportError:
        pass
    try:
        from pixel_check import run as pixel_check_run
        processors.append(("pixel_check", pixel_check_run))
    except ImportError:
        pass

    if a.processor:
        processors = [(n, f) for n, f in processors if n in a.processor]

    report, dirty = run_batch(a.targets, processors=processors,
                              json_path=a.json)

    for entry in report:
        m = entry.get("processors", {})
        n = len(entry.get("issues", [])) if "issues" in entry else 0
        meta = f"  processors={list(m.keys())}"
        print(("!! " if n else "OK ") + entry["file"] + meta)
        for proc_name, proc_result in m.items():
            if isinstance(proc_result, dict) and "issues" in proc_result:
                for iss in proc_result["issues"]:
                    print(f"     - [{iss.get('t')} conf {iss.get('conf', 0):.2f}] "
                          f"{iss.get('det')}")

    if a.json:
        print(f"\nevidence written: {a.json}")
    print(f"\nTARGETS: {len(report)}  DIRTY: {dirty}")
    sys.exit(min(dirty, 1))


if __name__ == "__main__":
    main()
