#!/usr/bin/env python3
"""Logic: compare our mirror -lts tips against upstream LTS tips.
No state file: the mirror fast-forwards upstream, so identical SHAs
mean nothing changed. Prints CHANGED <branches...> or NOTHING-CHANGED.

Usage: check-upstream.py <variant>  (cwd = builder checkout)
"""
import json
import subprocess
import sys

MIRROR = "https://github.com/sysretq0/android-kernel-common"
UPSTREAM = "https://android.googlesource.com/kernel/common"


def tip(url, ref):
    out = subprocess.run(["git", "ls-remote", url, ref],
                         capture_output=True, text=True)
    return out.stdout.split()[0] if out.stdout.strip() else ""


v = json.loads(open(f"variants/{sys.argv[1]}.json").read())
changed = []
for b in v["branches"]:
    ours = tip(MIRROR, b["branch"])
    theirs = tip(UPSTREAM, b["branch"])
    if not ours or not theirs:
        sys.exit(f"FAIL: empty tip for {b['branch']}")
    if ours != theirs:
        print(f"CHANGED {b['branch']}: {ours[:12]} vs upstream {theirs[:12]}")
        changed.append(b["branch"])
print(("CHANGED " + " ".join(changed)) if changed else "NOTHING-CHANGED")
