#!/usr/bin/env python3
"""Logic: stage added config into work/modular.fragment.

Runs with cwd=work (the synced tree). Control (which build consumes
the file, and how) stays in the workflow.
"""
import sys
from pathlib import Path

kind = sys.argv[1]
builder = Path("../builder")
frags = sorted((builder / "fragments" / "common").glob("*.config"))

if not frags:
    print("no fragments; stock defconfig")
    sys.exit(0)

staged = Path("modular.fragment")
staged.write_text("".join(f.read_text() for f in frags))
print(f"staged {len(frags)} fragment(s) -> {staged} (era: {kind})")
