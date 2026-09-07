#!/usr/bin/env python3
"""Bump component pins to current upstream tips. Format-preserving:
SHAs are replaced textually (compact JSON style untouched).

Tracks:
  pershoot/KernelSU-Next dev-susfs -> susfs.json ksu.commit except 6.6/6.18
  pershoot/KernelSU-Next dev        -> susfs.json 6.6/6.18 + all plain.json ksu.commit
  maxsteeel/nomount dev             -> both files nomount.commit
  sysretq0/android-partition-guard main -> both files guard.commit
  simonpunk/susfs4ksu gki-*         -> modules/susfs/patches.json source commits
Usage: refresh-pins.py [--write]   (default: report only, exit 1 if stale)
"""
import json
import subprocess
import sys

KSU = "https://github.com/pershoot/KernelSU-Next.git"
NOMOUNT = "https://github.com/maxsteeel/nomount.git"
GUARD = "https://github.com/sysretq0/android-partition-guard.git"
SUSFS = "https://gitlab.com/simonpunk/susfs4ksu.git"
SPECIAL_KSU = ("android15-6.6-lts", "android17-6.18-lts")


def tip(repo, ref):
    out = subprocess.run(["git", "ls-remote", repo, ref],
                         capture_output=True, text=True, check=True).stdout
    return out.split()[0]


def main():
    write = "--write" in sys.argv
    dev_susfs = tip(KSU, "dev-susfs")
    dev = tip(KSU, "dev")
    nomount = tip(NOMOUNT, "dev")
    guard = tip(GUARD, "main")
    susfs_tips = {}
    spec = json.load(open("modules/susfs/patches.json"))
    for branch, entry in spec.items():
        if branch.startswith("_") or "source" not in entry:
            continue
        src = entry["source"]
        key = (src["branch"], branch)
        if src["branch"] not in susfs_tips:
            susfs_tips[src["branch"]] = tip(SUSFS, src["branch"])
        entry["_want"] = susfs_tips[src["branch"]]
    changed = []

    def bump(path, old, new, what):
        nonlocal_changed = changed
        text = open(path).read()
        if old == new or old not in text:
            if old != new:
                print(f"WARN: {what} old sha absent in {path}")
            return
        open(path, "w").write(text.replace(old, new))
        nonlocal_changed.append(f"{path} {what}: {old[:12]} -> {new[:12]}")

    for path in ("variants/plain.json", "variants/susfs.json"):
        v = json.load(open(path))
        plain = path.endswith("plain.json")
        for key, want in (("nomount", nomount), ("guard", guard)):
            pin = v["defaults"].get(key, {})
            got = pin.get("commit", "") if isinstance(pin, dict) else ""
            if got == want:
                continue
            if write and got:
                bump(path, got, want, f"defaults {key}")
            else:
                changed.append(f"{path} defaults {key}: "
                               f"{got[:12]} -> {want[:12]}")
        for b in v["branches"]:
            if plain or b["branch"] in SPECIAL_KSU:
                want_ksu = dev
            else:
                want_ksu = dev_susfs
            pin = b.get("ksu", v["defaults"].get("ksu", {}))
            got = pin.get("commit", "") if isinstance(pin, dict) else ""
            if got == want_ksu:
                continue
            where = b["branch"] if "ksu" in b else "defaults"
            if write and got:
                bump(path, got, want_ksu, f"{where} ksu")
            else:
                changed.append(f"{path} {where} ksu: "
                               f"{got[:12]} -> {want_ksu[:12]}")
    for branch, entry in spec.items():
        if branch.startswith("_") or "source" not in entry:
            continue
        got, want = entry["source"]["commit"], entry["_want"]
        if write and got != want:
            bump("modules/susfs/patches.json", got, want, f"{branch} susfs")
        elif got != want:
            changed.append(f"susfs {branch}: {got[:12]} -> {want[:12]}")
    for c in changed:
        print(c)
    print("pins: %s" % ("STALE" if changed else "current"))
    return 1 if (changed and not write) else 0


sys.exit(main())
