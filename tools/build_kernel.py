#!/usr/bin/env python3
"""Logic: commit the tree, then build it for either era. cwd=work.

- Commit first (anti-`-dirty`), tolerant no-op when clean.
- build.sh era: generated build.config.portable sources the GKI config
  then merges work/modular.fragment at POST_DEFCONFIG time into
  OUT_DIR/.config. The committed defconfig stays pristine so the
  savedefconfig byte-match check passes.
- Kleaf era: --defconfig_fragment=//common:builder_fragments when staged.
"""
import os
import subprocess
import sys
from pathlib import Path

kind = sys.argv[1]


def run(*cmd, **kw):
    kw.setdefault("check", True)
    subprocess.run(cmd, **kw)


def commit_tree():
    if not Path("common/.git").exists():
        sys.exit("FAIL: no common/.git")
    run("git", "-C", "common", "add", "-A", check=False)
    done = subprocess.run(["git", "-C", "common", "diff", "--cached",
                           "--quiet"])
    if done.returncode != 0:
        run("git", "-C", "common", "-c", "user.name=builder",
            "-c", "user.email=builder@localhost",
            "commit", "-qm", "builder: commit tree (avoid -dirty)",
            check=False)
    dirty = subprocess.run(["git", "-C", "common", "status",
                            "--porcelain"], capture_output=True,
                           text=True).stdout.strip()
    if dirty:
        sys.exit(f"FAIL: tree still dirty after commit:\n{dirty}")
    print("commit: tree clean")


commit_tree()

if kind == "build_sh":
    Path("build.config.portable").write_text(
        "export KERNEL_DIR=common\n"
        ". ${ROOT_DIR}/${KERNEL_DIR}/build.config.gki.aarch64\n"
        "export POST_DEFCONFIG_CMDS='"
        "if [ -f ${ROOT_DIR}/modular.fragment ]; then "
        "${ROOT_DIR}/${KERNEL_DIR}/scripts/kconfig/merge_config.sh"
        " -m -O ${OUT_DIR} ${OUT_DIR}/.config"
        " ${ROOT_DIR}/modular.fragment"
        " && make -C ${ROOT_DIR}/${KERNEL_DIR} O=${OUT_DIR}"
        " ARCH=${ARCH} olddefconfig; fi'\n")
    run("bash", "build/build.sh",
        env={**os.environ, "BUILD_CONFIG": "build.config.portable"})
elif kind == "kleaf":
    cmd = ["tools/bazel", "build"]
    if Path("common/builder_fragments.config").exists():
        cmd.append("--defconfig_fragment=//common:builder_fragments")
    cmd.append("//common:kernel_aarch64_dist")
    run(*cmd)
else:
    sys.exit(f"unknown kind: {kind}")
print(f"built ({kind})")
