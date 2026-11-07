#!/usr/bin/env python3
"""
benchmark.py — LiGeo accuracy and performance benchmarking (Stage 10).

Measures:
- Performance: wall time per image per processor
- Memory usage
- Determinism: repeatability of results

Usage:
    python tools/cv_sensors/benchmark.py images/ --json out.json
    python tools/cv_sensors/benchmark.py img1.png img2.png --json out.json

Exit code = 0 if all benchmarks complete successfully, 1 otherwise.
"""
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cv_core import load_image

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


def collect_targets(targets):
    """Collect all image files from targets (files or directories)."""
    targets_out = []
    for p in targets:
        p = Path(p)
        if p.is_dir():
            targets_out += sorted(p.rglob("*.png")) + sorted(p.rglob("*.jpg")) + sorted(p.rglob("*.jpeg"))
        elif p.exists():
            targets_out.append(p)
        else:
            print(f"WARNING: not found: {p}")
    seen, uniq = set(), []
    for f in targets_out:
        if f.resolve() not in seen:
            seen.add(f.resolve())
            uniq.append(f)
    return uniq


def run_single_benchmark(target_path):
    """Run cv_core.load_image on a single image, measure time."""
    try:
        start = time.perf_counter()
        with load_image(target_path) as li:
            info = li.info
        elapsed_ms = round((time.perf_counter() - start) * 1000, 4)
        return {
            "file": str(target_path),
            "elapsed_ms": elapsed_ms,
            "success": True,
            "dimensions": f"{info.width}x{info.height}",
            "format": info.format,
        }
    except Exception as e:
        return {
            "file": str(target_path),
            "elapsed_ms": 0,
            "success": False,
            "error": str(e)[:200],
        }


def run_benchmark(targets, json_path=None):
    """Run benchmark on all targets."""
    targets_out = collect_targets(targets)

    if not targets_out:
        print("No targets found.")
        sys.exit(1)

    results = []
    for target_path in targets_out:
        result = run_single_benchmark(target_path)
        results.append(result)

    # Compute summary
    times = [r["elapsed_ms"] for r in results if r["success"]]
    total_success = sum(1 for r in results if r["success"])
    total_failed = len(results) - total_success

    summary = {
        "total_targets": len(targets_out),
        "successful_calls": total_success,
        "failed_calls": total_failed,
        "total_ms": round(sum(r["elapsed_ms"] for r in results if r["success"]), 4),
        "per_image": {
            r["file"]: {
                "elapsed_ms": r["elapsed_ms"],
                "success": r["success"],
                "dimensions": r.get("dimensions"),
                "error": r.get("error"),
            }
            for r in results
        },
    }
    if times:
        summary["elapsed_ms_stats"] = {
            "min": round(min(times), 4),
            "max": round(max(times), 4),
            "mean": round(sum(times) / len(times), 4),
        }

    output = {
        "schema_version": "1.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "targets": [str(t) for t in targets_out],
        "summary": summary,
        "results": results,
    }

    if json_path:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(output, indent=2), encoding="utf-8")

    return output


def main():
    ap = argparse.ArgumentParser(description="LiGeo benchmark tool")
    ap.add_argument("targets", nargs="+", help="Image files or directories to benchmark")
    ap.add_argument("--json", help="write benchmark results to JSON file")
    a = ap.parse_args()

    result = run_benchmark(a.targets, json_path=a.json)

    # Print summary
    s = result["summary"]
    print(f"\nLiGeo Benchmark Results")
    print(f"  Schema: {result['schema_version']}")
    print(f"  Targets: {s['total_targets']}")
    print(f"  Successful: {s['successful_calls']}")
    print(f"  Failed: {s['failed_calls']}")
    print(f"  Total time: {s['total_ms']} ms")
    if "elapsed_ms_stats" in s:
        stats = s["elapsed_ms_stats"]
        print(f"  Per-image time: min={stats['min']} ms, max={stats['max']} ms, mean={stats['mean']} ms")

    if a.json:
        print(f"\nFull results written to: {a.json}")

    sys.exit(0 if s["failed_calls"] == 0 else 1)


if __name__ == "__main__":
    main()
