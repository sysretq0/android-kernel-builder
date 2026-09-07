#!/usr/bin/env python3
"""Logic: compose the AK3 features checklist from evidence. Prints one
colon-separated line. No feature names live here: module labels come
from modules/manifest.json for version keys present in the versions
dir, fragment stems from the builder checkout (common dir) plus the
branch's variant extras. Absent evidence = absent line; a gated tree
cannot lie.

Usage: ak3-features.py --versions-dir DIR --builder DIR
         --variant plain --branch android12-5.10-lts
"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--versions-dir", required=True)
ap.add_argument("--builder", required=True)
ap.add_argument("--variant", required=True)
ap.add_argument("--branch", required=True)
a = ap.parse_args()
builder = Path(a.builder)
vd = Path(a.versions_dir)

labels = json.loads((builder / "modules" / "manifest.json").read_text())["labels"]
feats = []
for kf in sorted(vd.glob("*.txt")):
    if kf.name in ("rev.txt", "branch.txt", "version.txt"):
        continue
    key = kf.stem
    if key not in labels:
        raise SystemExit(f"FAIL: version key {key!r} has no manifest label")
    feats.append(f"{labels[key]} {kf.read_text().split()[0]}")

v = json.loads((builder / "variants" / f"{a.variant}.json").read_text())
rec = next(b for b in v["branches"] if b["branch"] == a.branch)
stems = sorted(p.stem for p in (builder / "fragments" / "common").glob("*.config"))
stems += rec.get("extra", [])
feats += stems
print(":".join(feats) if feats else "stock GKI")
