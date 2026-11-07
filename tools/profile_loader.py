#!/usr/bin/env python3
"""profile_loader — shared project profile loading for LiGeo global skill.

Loads and validates LiGeo project profile JSON files. Profiles define
project-level expectations (page size, margins, rubric, checks, gates) so
that LiGeo tools can be configured per-project instead of hardcoding B01
values globally.

Profile schema (version 1.0.0):
{
  "profile_schema_version": "1.0.0",
  "profile_id": "B01",
  "profile_name": "string",
  "project": "string",
  "description": "string",
  "inputs": ["html", "svg"],
  "page": {
    "size": {"width_cm": 21.0, "height_cm": 29.7, "name": "A4"},
    "orientation": "portrait",
    "margins": {"top": "1.15cm", "right": "1.15cm", ...},
    "margin_tolerance_mm": 0.5
  },
  "checks": {"layout": true, "print": true, ...},
  "rubric": {"rubric_id": "...", "rubric_name": "...", "rubric_version": "..."},
  "gates": {"l3_requires_human_review": true}
}

  python -m profile_loader profiles/B01.json
  from profile_loader import load_profile, profile_expected_margins_mm,
                             profile_page_size, parse_css_length_mm
"""
import json, re, sys
from pathlib import Path

SCHEMA_VERSION = "1.0.0"


def load_profile(path: str | Path) -> dict:
    """Load and validate a LiGeo project profile JSON file.

    Returns the profile dict. Exits on missing file or invalid JSON.
    Performs basic schema validation (schema_version present, page object
    present when size/margins expected).
    """
    p = Path(path)
    if not p.exists():
        sys.exit(f"profile file not found: {p}")
    try:
        profile = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit(f"cannot load profile {p}: {e}")

    if not isinstance(profile, dict):
        sys.exit(f"profile {p} is not a JSON object")

    if profile.get("profile_schema_version") != SCHEMA_VERSION:
        sys.exit(
            f"profile {p} schema version "
            f"{profile.get('profile_schema_version')} != {SCHEMA_VERSION}"
        )

    return profile


def profile_id(profile: dict) -> str | None:
    return profile.get("profile_id")


def profile_name(profile: dict) -> str | None:
    return profile.get("profile_name")


def profile_project(profile: dict) -> str | None:
    return profile.get("project")


def profile_inputs(profile: dict) -> list:
    return profile.get("inputs", [])


def profile_checks(profile: dict) -> dict:
    return profile.get("checks", {})


def profile_gates(profile: dict) -> dict:
    return profile.get("gates", {})


def profile_rubric(profile: dict) -> dict | None:
    return profile.get("rubric")


def profile_page_size(profile: dict) -> dict | None:
    """Return {width_cm, height_cm, name} or None."""
    page = profile.get("page")
    if not page:
        return None
    size = page.get("size")
    if not size:
        return None
    if isinstance(size, str):
        named = {
            "A4": (21.0, 29.7), "A3": (29.7, 42.0),
            "A5": (14.8, 21.0), "Letter": (21.59, 27.94),
        }
        if size in named:
            return {"width_cm": named[size][0], "height_cm": named[size][1],
                    "name": size}
        return None
    if isinstance(size, dict):
        return {
            "width_cm": size.get("width_cm"),
            "height_cm": size.get("height_cm"),
            "name": size.get("name"),
        }
    return None


def profile_orientation(profile: dict) -> str | None:
    page = profile.get("page")
    if not page:
        return None
    return page.get("orientation")


def profile_expected_margins_mm(profile: dict) -> dict | None:
    """Return {top, right, bottom, left} in mm, or None if unspecified."""
    page = profile.get("page")
    if not page:
        return None
    margins = page.get("margins")
    if not margins:
        return None
    result = {}
    for side in ("top", "right", "bottom", "left"):
        val = margins.get(side)
        if val is None:
            continue
        mm = parse_css_length_mm(val)
        if mm is not None:
            result[side] = mm
    return result if result else None


def profile_margin_tolerance_mm(profile: dict) -> float:
    page = profile.get("page")
    if not page:
        return 0.5
    return float(page.get("margin_tolerance_mm", 0.5))


def parse_css_length_mm(val) -> float | None:
    """Parse a CSS length string (e.g. "1.15cm") into mm.

    Returns None for percentages or unsupported units. Unitless numbers
    are treated as mm.
    """
    if isinstance(val, (int, float)):
        return float(val)
    if not isinstance(val, str):
        return None
    m = re.match(r'^([+-]?[\d.]+)\s*(cm|mm|in|pt|px|%)?$', val.strip())
    if not m:
        return None
    num = float(m[1])
    unit = (m[2] or "mm").lower()
    if unit == "mm":
        return num
    if unit == "cm":
        return num * 10
    if unit == "in":
        return num * 25.4
    if unit == "pt":
        return num * 25.4 / 72
    if unit == "px":
        return num * 25.4 / 96
    if unit == "%":
        return None
    return None


def profile_l3_requires_human_review(profile: dict) -> bool:
    gates = profile.get("gates", {})
    return bool(gates.get("l3_requires_human_review", True))


def summarize_profile(profile: dict) -> str:
    """Human-readable one-line summary of a profile."""
    pid = profile.get("profile_id", "?")
    pname = profile.get("profile_name", "?")
    page = profile.get("page", {})
    size = page.get("size", "?")
    margins = page.get("margins", {})
    return (f"{pid} ({pname}) — {size} — "
            f"margins {margins.get('top','?')}/{margins.get('right','?')}/"
            f"{margins.get('bottom','?')}/{margins.get('left','?')}")


def main():
    """CLI: load and print a profile summary."""
    import argparse
    ap = argparse.ArgumentParser(description="Load and summarize a LiGeo profile")
    ap.add_argument("profile", help="path to profile JSON file")
    a = ap.parse_args()
    profile = load_profile(a.profile)
    print(f"profile_id:      {profile_id(profile)}")
    print(f"profile_name:    {profile_name(profile)}")
    print(f"project:         {profile_project(profile)}")
    print(f"inputs:          {profile_inputs(profile)}")
    print(f"page_size:       {profile_page_size(profile)}")
    print(f"orientation:     {profile_orientation(profile)}")
    print(f"margins_mm:      {profile_expected_margins_mm(profile)}")
    print(f"margin_tol_mm:   {profile_margin_tolerance_mm(profile)}")
    print(f"checks:          {profile_checks(profile)}")
    print(f"rubric:          {profile_rubric(profile)}")
    print(f"gates:           {profile_gates(profile)}")
    print(f"summary:         {summarize_profile(profile)}")


if __name__ == "__main__":
    main()
