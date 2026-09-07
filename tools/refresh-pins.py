#!/usr/bin/env python3
"""Bump component SHAs in variants/*.json to current upstream tips.

Mapping (explicit, no guessing):
  pershoot/KernelSU-Next dev-susfs -> susfs.json ksu_ref except 6.6/6.18
  pershoot/KernelSU-Next dev        -> susfs.json 6.6/6.18 ksu_ref + all plain.json ksu_ref
  maxsteeel/nomount dev             -> all nomount_ref, both files
  sysretq0/android-partition-guard main -> all guard_ref, both files
Unconditional overwrite (idempotent): no diff means no drift.
Usage: refresh-pins.py [--write]   (default: report only, exit 1 if stale)
"""
import json
import subprocess
import sys

TRACK = [
    ("https://github.com/pershoot/KernelSU-Next.git", "dev-susfs"),
    ("https://github.com/pershoot/KernelSU-Next.git", "dev"),
    ("https://github.com/maxsteeel/nomount.git", "dev"),
    ("https://github.com/sysretq0/android-partition-guard.git", "main"),
    ("https://github.com/sysretq0/android-module-gate.git", "main"),
]
PLAIN_KSU = "dev"
SUSFS_SPECIAL = ("android15-6.6-lts", "android17-6.18-lts")


def tip(repo, ref):
    out = subprocess.run(["git", "ls-remote", repo, ref],
                         capture_output=True, text=True, check=True).stdout
    return out.split()[0]


def main():
    write = "--write" in sys.argv
    tips = {}
    for repo, ref in TRACK:
        tips[(repo, ref)] = tip(repo, ref)
    dev_susfs = tips[(TRACK[0][0], "dev-susfs")]
    dev = tips[(TRACK[1][0], "dev")]
    nomount = tips[(TRACK[2][0], "dev")]
    guard = tips[(TRACK[3][0], "main")]
    mgate = tips[(TRACK[4][0], "main")]
    changed = []
    for path in ("variants/plain.json", "variants/susfs.json"):
        with open(path) as f:
            v = json.load(f)
        is_plain = path.endswith("plain.json")
        for b in v["branches"]:
            want_ksu = dev if (is_plain or b["branch"] in SUSFS_SPECIAL) else dev_susfs
            for key, want in (("ksu_ref", want_ksu),
                              ("nomount_ref", nomount),
                              ("guard_ref", guard),
                              ("mgate_ref", mgate)):
                if b.get(key) != want:
                    changed.append("%s %s %s: %s -> %s"
                                   % (path, b["branch"], key, b.get(key), want[:8]))
                    b[key] = want
        if write:
            with open(path, "w") as f:
                json.dump(v, f, indent=2)
                f.write("\n")
    for c in changed:
        print(c)
    print("pins: %s" % ("STALE" if changed else "current"))
    return 1 if (changed and not write) else 0


sys.exit(main())
