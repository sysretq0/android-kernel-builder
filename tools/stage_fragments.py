#!/usr/bin/env python3
"""Logic: stage added config for the build to consume. Runs with cwd=work.

Writes work/modular.fragment (validated, last-file-wins) plus, on Kleaf
trees, common/builder_fragments.config + filegroup (idempotent).

The committed defconfig is NEVER touched: build.sh merges at
POST_DEFCONFIG time into OUT_DIR/.config, so the savedefconfig
byte-match check sees a pristine source. Appending symbols to the
defconfig breaks canonical ordering (observed savedefconfig mismatch).
"""
import re
import sys
from pathlib import Path

kind = sys.argv[1]
builder = Path("../builder")  # cwd=work, checkout is a sibling
frags = sorted((builder / "fragments" / "common").glob("*.config"))

if not frags:
    print("no fragments; stock tree")
    sys.exit(0)

SET_RE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
UNSET_RE = re.compile(r"^#\s*(CONFIG_[A-Za-z0-9_]+)\s+is\s+not\s+set$")

want = {}  # sym -> canon line, last file wins
for frag in frags:
    for n, raw in enumerate(frag.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or (line.startswith("#") and "CONFIG_" not in line):
            continue
        if (m := SET_RE.match(line)):
            want[m.group(1)] = f"{m.group(1)}={m.group(2)}"
        elif (m := UNSET_RE.match(line)):
            want[m.group(1)] = f"# {m.group(1)} is not set"
        else:
            sys.exit(f"FAIL: {frag.name}:{n}: bad fragment line: {raw!r}")

body = "\n".join(want.values()) + "\n"
Path("modular.fragment").write_text(body)

if kind == "kleaf":
    dest = Path("common/builder_fragments.config")
    dest.write_text(body)
    build_bazel = Path("common/BUILD.bazel")
    marker = 'name = "builder_fragments"'
    if marker not in build_bazel.read_text():
        with open(build_bazel, "a") as f:
            f.write('\n# builder: extra defconfig fragments staged by '
                    'builder/tools/stage_fragments.py.\n'
                    '# Consumed via --defconfig_fragment=//common:builder_fragments.\n'
                    'filegroup(\n    name = "builder_fragments",\n'
                    '    srcs = ["builder_fragments.config"],\n)\n')
        print(f"staged {len(want)} symbol(s) -> {dest} + filegroup")
    else:
        print(f"staged {len(want)} symbol(s) -> {dest} (filegroup present)")
else:
    print(f"staged {len(want)} symbol(s) from {len(frags)} fragment(s) "
          "-> modular.fragment (merged at POST_DEFCONFIG)")
