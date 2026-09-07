#!/usr/bin/env python3
"""Shared patch mechanics for patch modules. cwd=work (repo-sync root).

Usage: apply-patches.py --patch-dir DIR --patches-json FILE
         --branch BRANCH --tree common

Reads the branch entry from the module's patches.json and applies each
file entry in order. Entry forms:
  {"patch": "x.patch", "token": "tok"}          -- always apply
  {"candidates": ["a.patch", "b.patch"], ...}   -- dry-run each, apply
      first that fits (no guessing which fits the tip)
  + "if-missing": "pattern|relpath"             -- apply only when the
      tree lacks the pattern (tree-probed prerequisites)
  + "if-sublevel-lte": N                        -- apply only at/below
      Makefile SUBLEVEL N (kept-verbatim upstream gates)

Every apply: `patch --dry-run` first, then apply with --fuzz=3
(proven). Then markers, two forms per file entry:
  "token": "susfs"  -- must appear in every file the patch touches
      (touched list derived from `diff --git` lines; suits SuSFS/NTSync
      whose hunks are all self-named. NOT for BBRv3: its hunks touch
generic files with no bbr3 string)
  "markers": [{"file": "net/ipv4/tcp_bbr3.c"},
              {"file": "net/ipv4/Kconfig", "pattern": "TCP_CONG_BBR3"}]
      -- explicit existence/grep checks (BBRv3 class).
Final `.rej` sweep over the tree. Any failure exits 2 with .rej left
in the log. Branch absent from the map prints SKIP and exits 0 -- the
caller (setup.sh) decides fragment.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import json


def run(*cmd, **kw):
    kw.setdefault("check", True)
    return subprocess.run(cmd, **kw)


def touched(patch: Path):
    files = []
    for line in patch.read_text(errors="replace").splitlines():
        m = re.match(r"^diff --git a/\S+ b/(\S+)", line)
        if m:
            files.append(m.group(1))
    return files


def check_markers(tree: Path, patch: Path, entry: dict):
    if "token" in entry:
        tok = entry["token"]
        missing = [f for f in touched(patch)
                   if tok.lower() not in (tree / f).read_text(
                       errors="replace").lower()]
        if missing:
            sys.exit(f"FAIL: token {tok!r} missing after {patch.name} "
                     f"in: {' '.join(missing)}")
    for m in entry.get("markers", []):
        f = tree / m["file"]
        if not f.is_file():
            sys.exit(f"FAIL: marker missing file after {patch.name}: "
                     f"{m['file']}")
        if "pattern" in m and m["pattern"] not in f.read_text(
                errors="replace"):
            sys.exit(f"FAIL: marker pattern {m['pattern']!r} missing in "
                     f"{m['file']} after {patch.name}")


def apply_one(tree: Path, patch: Path, entry: dict):
    r = subprocess.run(["patch", "-p1", "--dry-run", f"--directory={tree}"],
                       stdin=patch.open("rb"))
    if r.returncode != 0:
        sys.exit(f"FAIL: dry-run failed: {patch.name}")
    run("patch", "-p1", "--fuzz=3", f"--directory={tree}",
        stdin=patch.open("rb"))
    check_markers(tree, patch, entry)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch-dir", required=True)
    ap.add_argument("--patches-json", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--tree", default="common")
    a = ap.parse_args()
    tree = Path(a.tree)
    spec = json.loads(Path(a.patches_json).read_text()).get(a.branch)
    if spec is None:
        print(f"apply-patches: no entry for {a.branch}; SKIP")
        return 0
    sublevel = int(re.search(r"^SUBLEVEL\s*=\s*(\d+)",
                             (tree / "Makefile").read_text(), re.M).group(1))
    n = 0
    for entry in spec.get("files", []):
        cands = entry.get("candidates") or [entry["patch"]]
        if "if-sublevel-lte" in entry and \
                sublevel > entry["if-sublevel-lte"]:
            print(f"apply-patches: sublevel {sublevel} skips "
                  f"{cands[0]}")
            continue
        if "if-missing" in entry:
            pat, rel = entry["if-missing"].split("|", 1)
            if pat in (tree / rel).read_text(errors="replace"):
                print(f"apply-patches: tree has {pat}, skips {cands[0]}")
                continue
        chosen = None
        for cand in cands:
            p = Path(a.patch_dir) / cand
            if not p.is_file():
                sys.exit(f"FAIL: missing {p}")
            r = subprocess.run(
                ["patch", "-p1", "--dry-run", f"--directory={tree}"],
                stdin=p.open("rb"), capture_output=True)
            if r.returncode == 0:
                chosen = p
                break
        if chosen is None:
            sys.exit(f"FAIL: no candidate applies on {a.branch}: "
                     + " ".join(cands))
        apply_one(tree, chosen, entry)
        print(f"apply-patches: applied {chosen.name}")
        n += 1
    rej = [str(p) for p in tree.rglob("*.rej")]
    if rej:
        sys.exit("FAIL: .rej left:\n" + "\n".join(rej))
    print(f"apply-patches: APPLIED {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
