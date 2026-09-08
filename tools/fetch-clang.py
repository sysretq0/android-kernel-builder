#!/usr/bin/env python3
"""Logic: snapshot AOSP prebuilt clang tarballs into our releases.

fetch-clang.py <version|all>
- Source list: clang/versions.json (also consumed by setup-clang.py).
- Idempotent: skips versions whose release already carries the asset,
  uploads into the existing release if the tag exists without it.
- googlesource only archives what is on main; pruned versions 404 here.
  Shipped clangs come via manifest sync anyway -- only upgrade targets
  need snapshotting, so snapshot early (main prunes aggressively).
"""
import json
import os
import subprocess
import sys

want = sys.argv[1] if len(sys.argv) > 1 else "all"
versions = json.load(open("clang/versions.json"))
targets = versions if want == "all" else [want]


def run(*cmd, **kw):
    return subprocess.run(cmd, **kw)


for v in targets:
    asset = f"{v}.tar.gz"
    view = run("gh", "release", "view", v, "--json", "assets",
               "-q", ".assets[].name",
               capture_output=True, text=True)
    if view.returncode == 0:
        if asset in view.stdout.split():
            print(f"clang: {v} already released, SKIP")
            continue
        print(f"clang: tag {v} exists without asset, uploading")
        up = run("gh", "release", "upload", v, asset)
        if up.returncode != 0:
            sys.exit(f"FAIL: upload failed for {v}")
        continue
    url = ("https://android.googlesource.com/platform/prebuilts/clang/"
           f"host/linux-x86/+archive/refs/heads/main/{asset}")
    print(f"clang: downloading {url}")
    dl = run("curl", "-fL", "--retry", "3", "-o", asset, url)
    if dl.returncode != 0:
        sys.exit(f"FAIL: {v} not archivable (pruned from main?)")
    size = os.path.getsize(asset)
    print(f"clang: {asset} {size // 1024 // 1024}MB")
    up = run("gh", "release", "create", v, asset, "--title", v,
             "--notes",
             f"AOSP prebuilt clang {v} snapshot for kernel builds.")
    if up.returncode != 0:
        sys.exit(f"FAIL: release create failed for {v}")
    print(f"clang: released {v}")
