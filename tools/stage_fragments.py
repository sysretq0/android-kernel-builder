#!/usr/bin/env python3
"""Logic: bake added config into the tree. Runs with cwd=work.

- Kleaf era: write common/builder_fragments.config + filegroup in
  common/BUILD.bazel (idempotent); workflow consumes it via
  --defconfig_fragment=//common:builder_fragments.
- build.sh era: append to common/arch/arm64/configs/gki_defconfig
  between modular markers (idempotent); ordering canonicalization
  rides the first build's evidence, not guesses.
"""
import sys
from pathlib import Path

kind = sys.argv[1]
builder = Path("..")  # cwd=work, parent is the builder checkout
frags = sorted((builder / "fragments" / "common").glob("*.config"))

if not frags:
    print("no fragments; stock tree")
    sys.exit(0)

body = "".join(f.read_text() for f in frags)

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
    if begin in text:
        print("fragments already baked; skipping")
        sys.exit(0)
    with open(defconfig, "a") as f:
        f.write(f"\n{begin}\n{body}# end-modular-fragment\n")
    print(f"baked {len(frags)} fragment(s) into {defconfig}")
