#!/usr/bin/env python3
"""Logic: bake added config into the tree. Runs with cwd=work.

- Kleaf era: write common/builder_fragments.config + filegroup in
  common/BUILD.bazel (idempotent); workflow consumes it via
  --defconfig_fragment=//common:builder_fragments.
- build.sh era: append to common/arch/arm64/configs/gki_defconfig
  between modular markers (idempotent); ordering canonicalization
  rides the first build's evidence, not guesses.
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

SYM_RE = re.compile(r"^(# )?(CONFIG_[A-Za-z0-9_]+)(=.*| is not set)?$")
want = {}  # sym -> full line, last file wins
for frag in frags:
    for n, raw in enumerate(frag.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or (line.startswith("#") and "CONFIG_" not in line):
            continue
        m = SYM_RE.match(line)
        if not m:
            sys.exit(f"FAIL: {frag.name}:{n}: bad fragment line: {raw!r}")
        want[m.group(2)] = line
body = "\n".join(want.values()) + "\n"

if kind == "kleaf":
    dest = Path("common/builder_fragments.config")
    dest.write_text(body)
    build_bazel = Path("common/BUILD.bazel")
    marker = 'name = "builder_fragments"'
    text = build_bazel.read_text()
    if marker not in text:
        with open(build_bazel, "a") as f:
            f.write('\n# builder: extra defconfig fragments staged by '
                    'builder/tools/stage_fragments.py.\n'
                    '# Consumed via --defconfig_fragment=//common:builder_fragments.\n'
                    'filegroup(\n    name = "builder_fragments",\n'
                    '    srcs = ["builder_fragments.config"],\n)\n')
        print(f"staged {len(frags)} fragment(s) -> {dest} + filegroup")
    else:
        print(f"staged {len(frags)} fragment(s) -> {dest} (filegroup present)")
else:
    defconfig = Path("common/arch/arm64/configs/gki_defconfig")
    text = defconfig.read_text()
    begin = "# begin-modular-fragment"
    lines = text.splitlines()
    drop = set(want)
    kept = [l for l in lines
            if not (m := SYM_RE.match(l.strip())) or m.group(2) not in drop]
    kept = [l for l in kept if l.strip() not in
            ("# begin-modular-fragment", "# end-modular-fragment")]
    defconfig.write_text("\n".join(kept).rstrip("\n") +
                         f"\n\n{begin}\n{body}# end-modular-fragment\n")
    print(f"baked {len(want)} symbol(s) from {len(frags)} fragment(s)")
