#!/usr/bin/env python3
"""Logic: apply every module's stale-outs drops. cwd=work.

Reads modules/*/drops.json (version + selector gates re-checked here
by delegating to drop-stale-module-outs.sh, which fails closed on
layout drift). YAML names no versions, symbols, or .ko paths.
"""
import json
import subprocess
import sys
from pathlib import Path

builder = Path("../builder")  # cwd=work, checkout is a sibling
n = 0
for spec in sorted(builder.glob("modules/*/drops.json")):
    for entry in json.loads(spec.read_text())["drops"]:
        cmd = ["/bin/bash", str(builder / "tools" / "drop-stale-module-outs.sh"),
               "--tree", "common", "--kversion", entry["kversion"],
               "--when-symbol", entry["when-symbol"]]
        for ko in entry["drop"]:
            cmd += ["--drop", ko]
        subprocess.run(cmd, check=True)
        n += 1
print(f"run-drops: {n} declaration(s) processed")
