#!/usr/bin/env python3
"""Logic: collect per-branch version evidence. cwd=work.

Reads common/Makefile (VERSION/PATCHLEVEL/SUBLEVEL) + branch into a
rev string, copies every .<key>-version file setup.sh scripts wrote
into versions-<branch>/ keyed by module key (labels resolve later via
modules/manifest.json -- this script names no features). Missing
version file = module did not run = absent key (off), never an error.
Writes versions-<branch>/rev.txt ("android12-5.10-269") for zip naming.
"""
import re
import shutil
import sys
from pathlib import Path

branch = sys.argv[1]
mk = (Path("common/Makefile").read_text())
get = lambda k: re.search(rf"^{k}\s*=\s*(\S+)", mk, re.M).group(1)
ver = f"{get('VERSION')}.{get('PATCHLEVEL')}.{get('SUBLEVEL')}"
core = re.sub(r"-(lts|stable)$", "", branch)
rev = f"{core}-{get('SUBLEVEL')}"

dest = Path(f"../versions-{branch}")
dest.mkdir(exist_ok=True)
(dest / "rev.txt").write_text(rev + "\n")
(dest / "branch.txt").write_text(branch + "\n")
(dest / "version.txt").write_text(ver + "\n")
for vf in sorted(Path(".").glob(".*-version")):
    key = vf.name[1:-len("-version")]
    shutil.copy(vf, dest / f"{key}.txt")
    print(f"versions: {key} <- {vf.read_text().strip()}")
print(f"versions: rev={rev}")
