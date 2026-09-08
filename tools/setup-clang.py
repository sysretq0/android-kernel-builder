#!/usr/bin/env python3
"""Logic: clang override for build_sh era. cwd=work.

setup-clang.py <target> <repo>
- Reads the branch's DECLARED clang from common/build.config.gki.aarch64
  (resolving ${VARS} via common/build.config.constants).
- Applies only if <target> is strictly newer (numeric rNNNNNN); else
  FAILS LOUD -- the manifest already dropped stock clang when this runs,
  so there is no compiler to fall back to.
- Downloads <target>.tar.gz from the builder repo's releases, extracts
  its CONTENTS into the declared path (stripping the tarball top dir),
  so build.sh finds a newer compiler exactly where it already looks.
  No tree mutation outside the recreated prebuilt dir (never committed:
  commit_tree only covers common/).
- Writes .clang-version (picked up by collect-versions.py as clang.txt).
"""
import re
import subprocess
import sys
import tarfile
from pathlib import Path

target, repo = sys.argv[1], sys.argv[2]

gki = Path("common/build.config.gki.aarch64").read_text()
m = re.search(r"^CLANG_PREBUILT_BIN=(\S+)", gki, re.M)
if not m:
    sys.exit("FAIL: no CLANG_PREBUILT_BIN in build.config.gki.aarch64")
decl = m.group(1)
consts = {}
cp = Path("common/build.config.constants")
if cp.exists():
    for line in cp.read_text().splitlines():
        mm = re.match(r"^([A-Z_]+)=(\S+)", line)
        if mm:
            consts[mm.group(1)] = mm.group(2)
decl = re.sub(r"\$\{([A-Z_]+)\}",
              lambda k: consts.get(k.group(1), k.group(0)), decl)

num = lambda s: int(x.group(1)) if (x := re.search(r"clang-r(\d+)", s)) else -1
if num(target) < 0:
    sys.exit(f"FAIL: bad target {target}")
if num(decl) < 0:
    sys.exit(f"FAIL: unparseable declared path {decl}")
if num(target) <= num(decl):
    sys.exit(f"FAIL: target {target} not newer than declared {decl} "
             f"(stock clang unsynced, nothing to fall back to)")
print(f"clang: {decl} -> {target}")

tgz = Path(f"{target}.tar.gz")
url = f"https://github.com/{repo}/releases/download/{target}/{tgz.name}"
ok = False
for _ in range(4):
    tgz.unlink(missing_ok=True)
    dl = subprocess.run(["curl", "-fL", "--retry", "2",
                         "-o", str(tgz), url], check=False)
    if dl.returncode == 0 and tgz.exists() and tgz.stat().st_size > 0:
        ok = True
        break
if not ok:
    sys.exit(f"FAIL: download failed: {url}")

dest = Path(decl)
dest.mkdir(parents=True, exist_ok=True)
with tarfile.open(tgz) as tf:
    members = tf.getmembers()
    tops = {n.name.split("/")[0] for n in members if "/" in n.name}
    for n in members:
        if len(tops) == 1:
            rest = n.name.split("/", 1)
            if len(rest) == 1:
                continue
            n.name = rest[1]
        tf.extract(n, dest)
tgz.unlink()

cc = dest / "bin" / "clang"
r = subprocess.run([str(cc), "--version"],
                   capture_output=True, text=True, check=False)
if r.returncode != 0:
    sys.exit("FAIL: extracted clang does not run")
line1 = r.stdout.splitlines()[0] if r.stdout else "?"
Path(".clang-version").write_text(f"{target} {line1}\n")
print(f"clang: {line1}")
