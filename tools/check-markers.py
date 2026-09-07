#!/usr/bin/env python3
"""Standing check: every patches.json marker must occur in the added
lines of its own patch file. Run before pushing patch changes:
  python3 tools/check-markers.py
Catches invented markers (patterns the patch never adds) without a
kernel tree. SuSFS entries reference clone-side files and are checked
for shape only (patch names + token/markers present).
"""
import json
import re
import sys
from pathlib import Path

builder = Path(__file__).resolve().parent.parent
bad = 0


def added_lines(patch: Path):
    cur, added = None, {}
    for line in patch.read_text(errors="replace").splitlines():
        m = re.match(r"^\+\+\+ b/(\S+)", line)
        if m:
            cur = m.group(1)
            added[cur] = []
        elif cur and line.startswith("+") and not line.startswith("+++"):
            added[cur].append(line[1:])
    return added


for mapfile in sorted((builder / "modules").glob("*/patches.json")):
    mod = mapfile.parent
    spec = json.loads(mapfile.read_text())
    for branch, entry in spec.items():
        if branch.startswith("_"):
            continue
        for f in entry.get("files", []):
            if "token" not in f and "markers" not in f:
                print(f"BAD {mod.name}/{branch}: entry has no check")
                bad += 1
            for cand in f.get("candidates") or [f.get("patch")]:
                if cand is None:
                    continue
                p = mod / "patches" / cand
                if mod.name == "susfs":
                    continue  # clone-side files; shape checked above
                if not p.is_file():
                    print(f"BAD {mod.name}: missing file {cand}")
                    bad += 1
                    continue
                a = added_lines(p)
                if "token" in f:
                    missing = [t for t, ls in a.items()
                               if not any(f["token"] in l.lower()
                                          for l in ls)]
                    if missing:
                        print(f"BAD-TOKEN {cand}: {missing}")
                        bad += 1
                for m in f.get("markers", []):
                    if "pattern" in m and not any(
                            m["pattern"] in l
                            for l in a.get(m["file"], [])):
                        print(f"BAD-MARKER {cand}: {m}")
                        bad += 1
print("ALL-MARKERS-VALID" if not bad else f"{bad} FAILURES")
sys.exit(1 if bad else 0)
