#!/usr/bin/env python3
"""Logic: fast-forward our mirror -lts branches to upstream LTS tips.

Usage: mirror-upstream.py <variant> [--push]   (cwd = builder checkout)
Default is dry-run (prints plan). --push updates refs via the GitHub
API (fast-forward only, never forced): a non-fast-forward state fails
loud instead of rewriting history. Auth: GH_TOKEN env (mirror token).
Only branches reported CHANGED are touched; identical SHAs are skipped.
"""
import json
import os
import subprocess
import sys

MIRROR = "sysretq0/android-kernel-common"
UPSTREAM = "https://android.googlesource.com/kernel/common"

variant = sys.argv[1]
push = len(sys.argv) > 2 and sys.argv[2] == "--push"


def ls_remote(url, ref):
    out = subprocess.run(["git", "ls-remote", url, ref],
                         capture_output=True, text=True)
    if out.returncode != 0 or not out.stdout.strip():
        sys.exit(f"FAIL: empty tip for {ref}")
    return out.stdout.split()[0]


v = json.loads(open(f"variants/{variant}.json").read())
plan = []
for b in v["branches"]:
    ours = ls_remote(f"https://github.com/{MIRROR}", b["branch"])
    theirs = ls_remote(UPSTREAM, b["branch"])
    if ours != theirs:
        plan.append((b["branch"], ours, theirs))
if not plan:
    print("mirror: all current; nothing to push")
    sys.exit(0)
for branch, ours, theirs in plan:
    print(f"mirror: {branch} {ours[:12]} -> {theirs[:12]}")
if not push:
    print("mirror: dry-run (pass --push to update refs)")
    sys.exit(0)
if not os.environ.get("GH_TOKEN"):
    sys.exit("FAIL: GH_TOKEN unset (needs mirror push rights)")
for branch, ours, theirs in plan:
    r = subprocess.run(["gh", "api",
                        f"repos/{MIRROR}/git/refs/heads/{branch}",
                        "-X", "PATCH", "-f", f"sha={theirs}"])
    if r.returncode != 0:
        sys.exit(f"FAIL: ref update rejected for {branch} "
                 f"(non-fast-forward?)")
print(f"mirror: pushed {len(plan)} branch(es)")
