#!/usr/bin/env python3
"""Logic: build the tree for either era. Runs with cwd=work.

Control (which step, when) stays in the workflow; era dispatch lives
here so the workflow holds one Build step instead of two.
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
    if not Path("common/.git").is_dir():
        return
    run("git", "-C", "common", "add", "-A", check=False)
    done = subprocess.run(["git", "-C", "common", "diff", "--cached",
                           "--quiet"])
    if done.returncode != 0:
        run("git", "-C", "common", "-c", "user.name=builder",
            "-c", "user.email=builder@localhost",
            "commit", "-qm", "builder: commit tree (avoid -dirty)",
            check=False)


commit_tree()

if kind == "build_sh":
    run("bash", "build/build.sh",
        env={**os.environ, "BUILD_CONFIG": "common/build.config.gki.aarch64"})
elif kind == "kleaf":
    cmd = ["tools/bazel", "build"]
    if Path("common/builder_fragments.config").exists():
        cmd.append("--defconfig_fragment=//common:builder_fragments")
    cmd.append("//common:kernel_aarch64_dist")
    run(*cmd)
else:
    sys.exit(f"unknown kind: {kind}")
print(f"built ({kind})")
