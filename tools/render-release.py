#!/usr/bin/env python3
"""Render the release body and the Telegram config table.

Single source of truth for per-branch status. Version files are the
evidence: ksu-version-<branch>.txt ("TAG SHA REF VCODE") is the canonical
built set; a susfs/bbrv3 file with the same infix means that feature
compiled in there. No SHAs in output -- versions only; SHAs stay in the
artifacts and logs for anyone who needs them.

Env: TAG VARIANT IN_KSU IN_SUSFS IN_BBRV3 IN_NTSYNC IN_NOMOUNT IN_GUARD IN_MGATE FRAGS_COMMON
  FRAGS_BRANCH ("branch:frag" tokens) RUN_URL REPO MANAGER_URL MANAGER_PIN
  HEADLINE (unused here, kept for the workflow)
Argv: <ksu_dir> <susfs_dir> <bbrv3_dir> <zips_dir> <extra_file>
  <out_notes> <out_table>
"""
import glob
import os
import sys

ksu_dir, susfs_dir, bbrv3_dir, nm_dir, gd_dir, nt_dir, mg_dir, zips_dir, extra_file, out_notes, out_table, out_extras = sys.argv[1:13]
g = os.environ.get
tag = g("TAG", "untagged")
variant = g("VARIANT", "plain")
ksu_on = g("IN_KSU") == "true"
susfs_on = g("IN_SUSFS") == "true"
bbrv3_on = g("IN_BBRV3") == "true"
ntsync_on = g("IN_NTSYNC") == "true"
nomount_on = g("IN_NOMOUNT") == "true"
guard_on = g("IN_GUARD") == "true"
mgate_on = g("IN_MGATE") == "true"


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
    if feature == "ntsync":
        if "6.12" in branch:
            return "BROKEN"
        return "skip"
    if "6.12" in branch or "6.18" in branch:
        return "backport"
    return "skip"


ksu = read_ver(os.path.join(ksu_dir, "ksu-version-*.txt"), "ksu-version-")
susfs = read_ver(os.path.join(susfs_dir, "susfs-version-*.txt"), "susfs-version-")
ntsync = read_ver(os.path.join(nt_dir, "ntsync-version-*.txt"), "ntsync-version-")
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
    frag_has_nt = any(tok == b + ":ntsync" or tok.endswith("/ntsync") for tok in ((g("FRAGS_BRANCH") or "").split()))
    if ntsync_on and (b in ntsync or frag_has_nt):
        ncell2 = "yes" if b in ntsync else "yes (in-tree)"
    elif ntsync_on:
        ncell2 = "no (%s)" % off_reason("ntsync", b)
    else:
        ncell2 = "off"
    rows.append((s, kcell, scell, vcell, ncell2))

def comp_ver(d, prefix):
    vals = set()
    for vf in sorted(glob.glob(os.path.join(d, prefix + "-*.txt"))):
        with open(vf) as f:
            parts = f.read().split()
        if len(parts) >= 2:
            vals.add(parts[1])
    return sorted(vals)


nm_shas = comp_ver(nm_dir, "nomount-version") if nomount_on else []
gd_shas = comp_ver(gd_dir, "guard-version") if guard_on else []
mg_shas = comp_ver(mg_dir, "mgate-version") if mgate_on else []


def comp_cell(on, shas, repo):
    if not on:
        return "off"
    if not shas:
        return "on"
    if len(shas) == 1:
        return "on ([%s](https://github.com/%s/commit/%s))" % (shas[0], repo, shas[0])
    return "on (%s)" % ", ".join(shas)


nm_cell = comp_cell(nomount_on, nm_shas, "maxsteeel/nomount")
gd_cell = comp_cell(guard_on, gd_shas, "sysretq0/android-partition-guard")
mg_cell = comp_cell(mgate_on, mg_shas, "sysretq0/android-module-gate")
feat = []
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
ksu_vals = sorted(set(k for s, k, sc, v, n in rows for k in [k]))
if ksu_on and ksu_vals != ["off"]:
    if len(ksu_vals) == 1:
        md.append("- KernelSU-Next: %s" % ksu_vals[0])
    else:
        first = ksu_vals[0]
        rest = "; ".join("%s: %s" % (s, k) for s, k, sc, v, n in rows if k != first)
        md.append("- KernelSU-Next: %s; %s" % (first, rest))
elif not ksu_on:
    md.append("- KernelSU-Next: off")
md.append("- NoMount: %s" % nm_cell)
md.append("- Partition Guard: %s" % gd_cell)
md.append("- ModuleGate (audit): %s" % mg_cell)
md.append("")
md.append("| Branch | SuSFS | BBRv3 | NTSync |")
md.append("|---|---|---|---|")
for s, kcell, scell, vcell, ncell2 in rows:
    md.append("| %s | %s | %s | %s |" % (s, scell, vcell, ncell2))
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
    md.append("- Manager APK (%s, match the KernelSU-Next version above): %s"
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

def _off(s, c):
    if c.startswith("no (") and c.endswith(")"):
        return "%s (%s)" % (s, c[4:-1])
    return "%s %s" % (s, c)


nt_off = [_off(s, c) for s, kcell, scell, vcell, c in rows if not c.startswith("yes")] if ntsync_on else []
ksu_tg = sorted(set(k for s, k, sc, v, n in rows for k in [k]))
tg = []
for s, kcell, scell, vcell, ncell2 in rows:
    tg.append(s)
    tg.append("  SuSFS %s \u00b7 BBRv3 %s" % (mark(scell), mark(vcell)))
ex = []
if ksu_on and ksu_tg != ["off"]:
    ex.append("\u2022 KernelSU-Next: " + ksu_tg[0])
if nomount_on:
    ex.append("\u2022 NoMount: " + (nm_shas[0] if len(nm_shas) == 1 else "on"))
if guard_on:
    ex.append("\u2022 Partition Guard: " + (gd_shas[0] if len(gd_shas) == 1 else "on"))
ex.append("\u2022 ModuleGate: " + (mg_shas[0] if len(mg_shas) == 1 else "on") + " (audit)") if mgate_on else None
if ntsync_on:
    ex.append("\u2022 NTSync: " + ("all trees" if not nt_off else "all but " + ", ".join(nt_off)))
if feat:
    ex.append("+ " + " \u00b7 ".join(feat))
with open(out_extras, "w") as f:
    f.write(("\n".join(ex) + "\n") if ex else "\n")
with open(out_table, "w") as f:
    f.write("\n".join(tg) + "\n")
print("render-release: %d branches, %d zips" % (len(rows), len(zips)))
