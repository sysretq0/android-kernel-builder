#!/usr/bin/env python3
"""Logic: stage added config for the build to consume. Runs with cwd=work.

Sources (in merge order, last wins on conflict):
1. fragments/common/*.config -- universal, every branch, no JSON needed
   (skipped when the variant sets fragments:false)
2. branch "extra" names from variants/<variant>.json, resolved to
   fragments/version-specific/<name>.config -- one shared copy each,
   JSON dictates which branches get what. Missing file = hard fail.
   (also skipped when fragments:false)
3. modular.fragments.d/*.config -- module-generated, always staged.
   Source-or-nothing: an integrated driver must carry its symbol, or
   Kconfig default applies (NTSync defaults =m, which cannot link).

Writes work/modular.fragment (validated, canon lines) plus, on Kleaf
trees, common/builder_fragments.config + filegroup (idempotent).

The committed defconfig is NEVER touched: build.sh merges at
POST_DEFCONFIG time into OUT_DIR/.config, so the savedefconfig
byte-match check sees a pristine source.
"""
import json
import re
import sys
from pathlib import Path

kind, variant, branch = sys.argv[1], sys.argv[2], sys.argv[3]
builder = Path("../builder")  # cwd=work, checkout is a sibling

v = json.loads((builder / "variants" / f"{variant}.json").read_text())
rec = next(b for b in v["branches"] if b["branch"] == branch)
# Repo fragments are optional; module-generated symbols are not.
# Source-or-nothing: an integrated driver without its symbol falls back
# to Kconfig default, which for NTSync is =m -- and =m cannot link
# (unexported __vfs_setxattr_noperm; observed modpost failure). The
# toggle gates the repo pool only, never the module symbols whose
# source is already in the tree.
repo_on = v.get("defaults", {}).get("fragments", True)

frags = []
if repo_on:
    frags = sorted((builder / "fragments" / "common").glob("*.config"))
    for name in rec.get("extra", []):
        f = builder / "fragments" / "version-specific" / f"{name}.config"
        if not f.is_file():
            sys.exit(f"FAIL: {branch} lists extra {name!r}, no such file")
        frags.append(f)
else:
    print("repo fragments off; module symbols still apply")
# generated fragments (module installers ran before stage, so source and
# symbol always agree -- a symbol without its driver cannot be staged)
gen = sorted(Path("modular.fragments.d").glob("*.config")) \
    if Path("modular.fragments.d").is_dir() else []
frags += gen

if not frags:
    print("no fragments; stock tree")
    sys.exit(0)

SET_RE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
UNSET_RE = re.compile(r"^#\s*(CONFIG_[A-Za-z0-9_]+)\s+is\s+not\s+set$")

want = {}  # sym -> canon line, last file wins
for frag in frags:
    for n, raw in enumerate(frag.read_text().splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if (m := SET_RE.match(line)):
            want[m.group(1)] = f"{m.group(1)}={m.group(2)}"
        elif (m := UNSET_RE.match(line)):
            want[m.group(1)] = f"# {m.group(1)} is not set"
        elif line.startswith("#"):
            continue
        else:
            sys.exit(f"FAIL: {frag.name}:{n}: bad fragment line: {raw!r}")

body = "\n".join(want.values()) + "\n"
Path("modular.fragment").write_text(body)

if kind == "kleaf":
    dest = Path("common/builder_fragments.config")
    dest.write_text(body)
    build_bazel = Path("common/BUILD.bazel")
    if not build_bazel.is_file():
        sys.exit("FAIL: no common/BUILD.bazel (not a Kleaf tree?)")
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
