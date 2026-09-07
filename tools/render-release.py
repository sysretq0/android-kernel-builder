#!/usr/bin/env python3
"""Render the release body and the Telegram config table.

Single source of truth for per-branch status. Version files are the
evidence: ksu-version-<branch>.txt ("TAG SHA REF VCODE") is the canonical
built set; a susfs/bbrv3 file with the same infix means that feature
compiled in there. No SHAs in output -- versions only; SHAs stay in the
artifacts and logs for anyone who needs them.

Env: TAG VARIANT IN_KSU IN_SUSFS IN_BBRV3 IN_NOMOUNT IN_GUARD FRAGS_COMMON
  FRAGS_BRANCH ("branch:frag" tokens) RUN_URL REPO MANAGER_URL MANAGER_PIN
  HEADLINE (unused here, kept for the workflow)
Argv: <ksu_dir> <susfs_dir> <bbrv3_dir> <zips_dir> <extra_file>
  <out_notes> <out_table>
"""
import glob
import os
import sys

ksu_dir, susfs_dir, bbrv3_dir, zips_dir, extra_file, out_notes, out_table, out_extras = sys.argv[1:9]
g = os.environ.get
tag = g("TAG", "untagged")
variant = g("VARIANT", "plain")
ksu_on = g("IN_KSU") == "true"
susfs_on = g("IN_SUSFS") == "true"
bbrv3_on = g("IN_BBRV3") == "true"
nomount_on = g("IN_NOMOUNT") == "true"
guard_on = g("IN_GUARD") == "true"


def short(branch):
    b = branch
    for suf in ("-stable", "-lts"):
        if b.endswith(suf):
            b = b[: -len(suf)]
    if b.startswith("android"):
        b = b[len("android"):]
    return b


def read_ver(pattern, prefix):
    out = {}
    for vf in sorted(glob.glob(pattern)):
        base = os.path.basename(vf)
        if base.startswith(prefix):
            base = base[len(prefix):]
        if base.endswith(".txt"):
            base = base[:-4]
        with open(vf) as f:
            parts = f.read().split()
        out[base] = parts
    return out


def mark(cell):
    # yes -> check, no (reason) -> cross + bare reason: short phone lines.
    if cell == "yes":
        return "\u2713"
    if cell.startswith("no (") and cell.endswith(")"):
        return "\u2717 " + cell[4:-1].replace(" ", "-")
    return cell


def off_reason(feature, branch):
    if feature == "susfs":
        if "6.6" in branch:
            return "gated"
        if "6.18" in branch:
            return "upstream"
        return "skip"
    if "6.12" in branch or "6.18" in branch:
        return "backport"
    return "skip"


ksu = read_ver(os.path.join(ksu_dir, "ksu-version-*.txt"), "ksu-version-")
susfs = read_ver(os.path.join(susfs_dir, "susfs-version-*.txt"), "susfs-version-")
bbrv3 = read_ver(os.path.join(bbrv3_dir, "bbrv3-version-*.txt"), "bbrv3-version-")
zips = sorted(os.path.basename(z) for z in glob.glob(os.path.join(zips_dir, "*.zip")))

branches = sorted(ksu) if ksu else []
if not branches:  # ksu off or total version loss: degrade to zip names
    branches = sorted("anykernel-" + z[len("anykernel-"):].rsplit(".zip", 1)[0] for z in zips)

rows = []
for b in branches:
    s = short(b)
    if ksu_on and b in ksu and len(ksu[b]) >= 4:
        kcell = "%s (%s)" % (ksu[b][0], ksu[b][3])
    elif ksu_on:
        kcell = "on"
    else:
        kcell = "off"
    if susfs_on and b in susfs:
        scell = "yes"
    elif susfs_on:
        scell = "no (%s)" % off_reason("susfs", b)
    else:
        scell = "off"
    if bbrv3_on and b in bbrv3:
        vcell = "yes"
    elif bbrv3_on:
        vcell = "no (%s)" % off_reason("bbrv3", b)
    else:
        vcell = "off"
    rows.append((s, kcell, scell, vcell))

feat = []
if nomount_on:
    feat.append("NoMount")
if guard_on:
    feat.append("Partition Guard")
ncell = "yes" if nomount_on else "off"
gcell = "yes" if guard_on else "off"
frags = (g("FRAGS_COMMON") or "").split() + (g("FRAGS_BRANCH") or "").split()
if frags:
    feat.append("Fragments: " + " ".join(frags))

md = []
md.append("## ⚡ GKI Kernel `%s`" % tag)
md.append("")
md.append("### 📦 Zips — each carries `kernel.config` + `ikconfig`")
for z in zips:
    md.append("- `%s`" % z)
md.append("")
md.append("### ⚙️ Config (`variants/%s.json`)" % variant)
md.append("| Branch | KernelSU-Next | SuSFS | BBRv3 | NoMount | Guard |")
md.append("|---|---|---|---|---|---|")
for s, kcell, scell, vcell in rows:
    md.append("| %s | %s | %s | %s | %s | %s |" % (s, kcell, scell, vcell, ncell, gcell))
if feat:
    md.append("")
    md.append(" · ".join(feat))
md.append("")
md.append("### 📲 Flash")
md.append("- AnyKernel3 zip for **your branch only**, flash in recovery or KernelSU manager")
md.append("- No auto-backup — **back up `boot` first**")
md.append("- Kernel always lives in `boot` (`BLOCK=boot`), slot-aware")
md.append("")
md.append("### 🔗 Links")
md.append("- Build logs: %s" % g("RUN_URL", ""))
md.append("- Risk register: [RISK.md](https://github.com/%s/blob/main/RISK.md)" % g("REPO", ""))
if ksu_on:
    md.append("- Manager APK (%s, match the KSU column above): %s"
              % (g("MANAGER_PIN", "dev tip"), g("MANAGER_URL", "")))
if os.path.isfile(extra_file):
    with open(extra_file) as f:
        notes = [ln.rstrip("\n") for ln in f
                 if ln.strip() and not ln.lstrip().startswith("#")]
    if notes:
        md.append("")
        md.append("### 📌 Notes")
        md.extend(notes)
with open(out_notes, "w") as f:
    f.write("\n".join(md) + "\n")

tg = []
for s, kcell, scell, vcell in rows:
    tg.append("%s \u00b7 %s" % (s, kcell))
    tg.append("  SuSFS %s \u00b7 BBRv3 %s" % (mark(scell), mark(vcell)))
with open(out_extras, "w") as f:
    f.write(("+ " + " \u00b7 ".join(feat) + "\n") if feat else "\n")
with open(out_table, "w") as f:
    f.write("\n".join(tg) + "\n")
print("render-release: %d branches, %d zips" % (len(rows), len(zips)))
