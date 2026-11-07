#!/usr/bin/env python3
"""result_diff.py — result differencing for LiGeo QA results.

Compares QA results between two runs to detect changes, improvements,
or regressions. Used for tracking quality evolution across book chapters
or document revisions.

  python tools/cv_sensors/result_diff.py run1.json run2.json
  python tools/cv_sensors/result_diff.py run1.json run2.json --json out.json

Exit code = number of differing results (0 = identical).
"""
import argparse, json, sys
from pathlib import Path


def load_result(path: Path) -> dict:
    """Load a result JSON file."""
    p = Path(path)
    if not p.exists():
        sys.exit(f"result file not found: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"cannot load result file {p}: {e}")


def diff_results(result1: dict, result2: dict) -> dict:
    """Compare two result dicts and return differences.

    Compares:
    - Total targets processed
    - Dirty/error counts
    - Per-file results (added, removed, changed)
    """
    diff = {
        "result1": str(result1.get("path", "unknown")),
        "result2": str(result2.get("path", "unknown")),
        "total_targets_1": result1.get("total_targets", 0),
        "total_targets_2": result2.get("total_targets", 0),
        "dirty_1": result1.get("dirty", 0),
        "dirty_2": result2.get("dirty", 0),
        "error_count_1": result1.get("error_count", 0),
        "error_count_2": result2.get("error_count", 0),
        "files_added": [],
        "files_removed": [],
        "files_changed": [],
        "files_unchanged": [],
        "summary": {},
    }

    results1 = result1.get("results", [])
    results2 = result2.get("results", [])

    files1 = {r["file"]: r for r in results1}
    files2 = {r["file"]: r for r in results2}

    files1_set = set(files1.keys())
    files2_set = set(files2.keys())

    diff["files_added"] = sorted(files2_set - files1_set)
    diff["files_removed"] = sorted(files1_set - files2_set)
    diff["files_common"] = sorted(files1_set & files2_set)

    # Compare common files
    for f in diff["files_common"]:
        r1 = files1[f]
        r2 = files2[f]

        r1_issues = r1.get("issues", [])
        r2_issues = r2.get("issues", [])

        if r1_issues != r2_issues:
            diff["files_changed"].append({
                "file": f,
                "issues_1": len(r1_issues),
                "issues_2": len(r2_issues),
                "issues_added": len(r2_issues) - len(r1_issues),
                "issues_1_detail": r1_issues,
                "issues_2_detail": r2_issues,
            })
        else:
            diff["files_unchanged"].append(f)

    # Summary
    diff["summary"] = {
        "total_files_1": len(files1),
        "total_files_2": len(files2),
        "files_added_count": len(diff["files_added"]),
        "files_removed_count": len(diff["files_removed"]),
        "files_changed_count": len(diff["files_changed"]),
        "files_unchanged_count": len(diff["files_unchanged"]),
        "total_dirty_change": diff["dirty_2"] - diff["dirty_1"],
        "total_error_change": diff["error_count_2"] - diff["error_count_1"],
    }

    return diff


def run(result1_path: str, result2_path: str,
        json_path: str | None = None) -> dict:
    """Run diff on two result files.

    Args:
        result1_path: Path to first result JSON
        result2_path: Path to second result JSON
        json_path: Optional path to write diff output

    Returns:
        Diff result dict
    """
    result1 = load_result(Path(result1_path))
    result2 = load_result(Path(result2_path))

    diff = diff_results(result1, result2)

    if json_path:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).write_text(json.dumps(diff, indent=2),
                                   encoding="utf-8")

    return diff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result1", help="First result JSON file")
    ap.add_argument("result2", help="Second result JSON file")
    ap.add_argument("--json", help="write diff output to JSON file")
    a = ap.parse_args()

    diff = run(a.result1, a.result2, json_path=a.json)

    print(f"Result diff: {diff['result1']} vs {diff['result2']}")
    print(f"  Total targets: {diff['total_targets_1']} -> {diff['total_targets_2']}")
    print(f"  Dirty targets: {diff['dirty_1']} -> {diff['dirty_2']}")
    print(f"  Error count: {diff['error_count_1']} -> {diff['error_count_2']}")
    print(f"  Files added: {len(diff['files_added'])}")
    print(f"  Files removed: {len(diff['files_removed'])}")
    print(f"  Files changed: {len(diff['files_changed'])}")
    print(f"  Files unchanged: {len(diff['files_unchanged'])}")

    if diff["files_changed"]:
        print("\nChanged files:")
        for f in diff["files_changed"][:10]:
            print(f"  {f['file']}: {f['issues_1']} -> {f['issues_2']} issues")

    if a.json:
        print(f"\nDiff written: {a.json}")

    sys.exit(min(len(diff["files_changed"]), 1))


if __name__ == "__main__":
    main()
