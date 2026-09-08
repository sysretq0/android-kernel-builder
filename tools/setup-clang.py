#!/usr/bin/env python3
"""Logic: clang override for build_sh era. cwd=work.

setup-clang.py <target> <repo> [--local-tgz path]
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
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

target, repo = sys.argv[1], sys.argv[2]
local_tgz = None
if len(sys.argv) > 3:
    if not sys.argv[3].startswith("--local-tgz="):
        sys.exit(f"FAIL: bad argv {sys.argv[3:]}")
    local_tgz = Path(sys.argv[3].split("=", 1)[1])
    if not local_tgz.is_file():
        sys.exit(f"FAIL: no such tgz {local_tgz}")

text = ""
for cand in ("common/build.config.gki.aarch64", "common/build.config.common",
             "common/build.config.aarch64", "common/build.config.constants"):
    p = Path(cand)
    if p.exists():
        text += p.read_text() + "\n"
m = re.search(r"^CLANG_PREBUILT_BIN=(\S+)", text, re.M)
if not m:
    sys.exit("FAIL: no CLANG_PREBUILT_BIN in build.config.*")
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
if local_tgz is not None:
    tgz = local_tgz
    print(f"clang: using local {tgz}")
else:
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
# Declared value is the BIN dir (AOSP shape: <ver>/bin); the tarball
# holds the whole compiler tree, so extract one level up. The invariant
# is exact: $ROOT_DIR/$CLANG_PREBUILT_BIN/clang must run, because that
# is literally what _setup_env.sh puts on PATH for build.sh/make.
root = dest.parent if dest.name == "bin" else dest
root.mkdir(parents=True, exist_ok=True)
with tarfile.open(tgz) as tf:
    members = tf.getmembers()
    tops = {n.name.split("/")[0] for n in members if "/" in n.name}
    for n in members:
        if len(tops) == 1:
            rest = n.name.split("/", 1)
            if len(rest) == 1:
                continue
            n.name = rest[1]
        tf.extract(n, root)
if local_tgz is None:
    tgz.unlink()

cc = dest / "clang"
r = subprocess.run([str(cc), "--version"],
                   capture_output=True, text=True, check=False)
if r.returncode != 0:
    sys.exit("FAIL: extracted clang does not run")
line1 = r.stdout.splitlines()[0] if r.stdout else "?"
Path(".clang-version").write_text(f"{target} {line1}\n")
print(f"clang: {line1}")
st = cc.stat()
print(f"clang: bin/clang size={st.st_size} mode={oct(st.st_mode)}")
# PATH-resolution proof, exactly the way build.sh/make will use it.
probe = subprocess.run(["bash", "-c",
                          "command -v clang && clang --version | head -1"],
                         env={"PATH": f"{cc.parent.resolve()}:"
                                     f"{os.environ.get('PATH', '')}"},
                         capture_output=True, text=True)
print(f"clang: PATH-probe rc={probe.returncode} "
      f"{(probe.stdout or probe.stderr).strip()[:160]}")
if probe.returncode != 0:
    sys.exit("FAIL: clang not PATH-resolvable right after extract")
# Clang 19+ passes the sysreg stack-guard probe, selecting
# CONFIG_STACKPROTECTOR_PER_TASK and dropping the global
# __stack_chk_guard that OEM modules reference. Restore it.
# Companion to the override only: stock clang never selects PER_TASK.
# NOTE: absolute path -- `git -C common` resolves relatives under common/.
pp = (Path.cwd() / "../builder/clang/stackprotector-per-task-compat.patch").resolve()
chk = subprocess.run(["git", "-C", "common", "apply", "--check",
                        str(pp)], capture_output=True, text=True)
if chk.returncode != 0:
    rev = subprocess.run(["git", "-C", "common", "apply", "--reverse",
                          "--check", str(pp)],
                         capture_output=True, text=True)
    if rev.returncode != 0:
        sys.exit("FAIL: stackprotector patch does not apply:\n"
                 + chk.stderr[:500])
    print("clang: stackprotector patch already applied, SKIP")
else:
    ap = subprocess.run(["git", "-C", "common", "apply", str(pp)],
                        capture_output=True, text=True)
    if ap.returncode != 0:
        sys.exit("FAIL: stackprotector patch apply failed:\n"
                 + ap.stderr[:500])
    print("clang: stackprotector patch applied")
# Hand the absolute dir to later steps (prove + build pre-flight).
gh = os.environ.get("GITHUB_ENV")
if gh:
    with open(gh, "a") as f:
        f.write(f"CLANG_DIR={cc.parent.resolve()}\n")
