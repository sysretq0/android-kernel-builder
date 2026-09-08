#!/usr/bin/env python3
"""Logic: variant JSON -> build matrix. Control stays in the workflow."""
import json
import os
import sys

variant = sys.argv[1]
want = sys.argv[2] if len(sys.argv) > 2 else "all"
clang_on = len(sys.argv) > 3 and sys.argv[3] == "true"

with open(f"variants/{variant}.json") as f:
    v = json.load(f)

clang_target = ""
if clang_on:
    import re
    versions = json.load(open("clang/versions.json"))
    if not versions:
        sys.exit("FAIL: clang requested but clang/versions.json is empty")
    num = lambda s: int(m.group(1)) if (m := re.search(r"clang-r(\d+)", s)) else -1
    clang_target = max(versions, key=num)
    if num(clang_target) < 0:
        sys.exit("FAIL: no parseable clang version pinned")

rows = [{"branch": b["branch"], "manifest": b["manifest"],
         "kind": b["kind"],
         "clang": (clang_target if clang_on and b["kind"] == "build_sh" else "")}
        for b in v["branches"]]
if want != "all":
    rows = [r for r in rows if r["branch"] == want]
    if not rows:
        sys.exit(f"unknown branch: {want}")
if clang_on and want != "all" and any(r["kind"] != "build_sh" for r in rows):
    sys.exit("FAIL: clang override is build_sh-only "
             "(kleaf is tied to its toolchain)")

matrix = json.dumps({"include": rows})
path = os.environ["GITHUB_OUTPUT"]
with open(path, "a") as f:
    f.write(f"matrix={matrix}\n")
# read-back: prove the handoff instead of failing downstream on ''
back = [l for l in open(path).read().splitlines()
        if l.startswith("matrix=")]
assert back and json.loads(back[-1].split("=", 1)[1]) == {"include": rows}, \
    f"handoff broken: {path} has no matrix line"
print(matrix)
