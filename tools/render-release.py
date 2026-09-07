#!/usr/bin/env python3
"""Render release body + Telegram table from version evidence. No
per-feature inputs: columns come from modules/manifest.json labels,
rows from versions-*/ dirs. A version key without a manifest label
fails closed (add the label with the module, never here).

Argv: <versions-root> <builder> <variant> <tag> <zips-dir>
      <out-notes> <out-table>
Env: RUN_URL REPO (optional links)
"""
import json
import sys
from pathlib import Path

vroot, builder, variant, tag, zips, out_notes, out_table = sys.argv[1:8]
builder = Path(builder)
labels = json.loads((builder / "modules" / "manifest.json").read_text())["labels"]
order = json.loads((builder / "modules" / "manifest.json").read_text())["order"]
key_of = json.loads((builder / "modules" / "manifest.json").read_text())["keys"]
cols = [key_of[m] for m in order]

branches = {}
for d in sorted(Path(vroot).glob("versions-*")):
    if not d.is_dir():
        continue
    branch = (d / "branch.txt").read_text().strip()
    rev = (d / "rev.txt").read_text().strip()
    feats = {}
    for kf in sorted(d.glob("*.txt")):
        if kf.name in ("rev.txt", "branch.txt", "version.txt"):
            continue
        if kf.stem not in labels:
            sys.exit(f"FAIL: version key {kf.stem!r} has no manifest label")
        feats[kf.stem] = kf.read_text().split()
    branches[branch] = (rev, feats)


def cell(key, parts):
    if not parts:
        return "off"
    if labels.get(key, {}).get("detail") == "version":
        tag = parts[0] if parts else "?"
        vcode = parts[3] if len(parts) > 3 else "?"
        return f"{tag} ({vcode})"
    return "yes"


hdr = "| branch | " + " | ".join(labels[c]["label"] for c in cols) + " |"
sep = "|" + "|".join(["---"] * (len(cols) + 1)) + "|"
lines = [f"# {tag} ({variant})", "", hdr, sep]
tg = [tag, ""]
for branch in sorted(branches):
    rev, feats = branches[branch]
    row = [branch] + [cell(c, feats.get(c)) for c in cols]
    lines.append("| " + " | ".join(row) + " |")
    det = [c for c in cols if labels.get(c, {}).get("detail") == "version"]
    short = branch.removeprefix("android").removesuffix("-lts")
    base = " ".join(f"{labels[c].get('short', c)} "
                       f"{cell(c, feats.get(c))}" for c in det)
    extras = " ".join(f"+{c}" for c in cols
                       if c not in det and feats.get(c))
    tg.append(f"{short}: {base} {extras}".strip())

ziplist = sorted(Path(zips).glob("*.zip"))
dl = "\n".join(f"- `{z.name}`" for z in ziplist)
extra = builder / "docs" / "RELEASE_NOTES_EXTRA.txt"
footnotes = [l for l in extra.read_text().splitlines()
             if l.strip() and not l.startswith("#")] if extra.is_file() else []
notes = "\n".join(lines) + "\n\n## Downloads\n" + (dl or "(no zips)") + "\n"
mgr = Path("manager-url.txt")
if mgr.is_file() and mgr.read_text().strip():
    notes += f"\n[Manager APK]({mgr.read_text().strip()})\n"
if footnotes:
    notes += "\n## Notes\n" + "\n".join(footnotes) + "\n"
Path(out_notes).write_text(notes)
tgtext = "\n".join(tg)
if footnotes:
    tgtext += "\n\n" + "\n".join(footnotes)
Path(out_table).write_text("```\n" + tgtext + "\n```\n")
print(f"render-release: {len(branches)} branches, "
      f"{len(ziplist)} zips -> {out_notes} {out_table}")
