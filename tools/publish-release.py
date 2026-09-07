#!/usr/bin/env python3
"""Publish the release + Telegram post. Control stays in the workflow
(one step); all logic lives here.

Usage: publish-release.py --tag TAG --variant VARIANT --repo OWNER/REPO
         --zips DIR --versions DIR --builder DIR
Env: GH_TOKEN (gh cli), TG_TOKEN + TG_CHAT (optional Telegram).
"""
import argparse
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def run(*cmd, **kw):
    kw.setdefault("check", True)
    return subprocess.run(cmd, **kw)


ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True)
ap.add_argument("--variant", required=True)
ap.add_argument("--repo", required=True)
ap.add_argument("--zips", required=True)
ap.add_argument("--versions", required=True)
ap.add_argument("--builder", required=True)
a = ap.parse_args()

run(sys.executable, f"{a.builder}/tools/render-release.py",
    a.versions, a.builder, a.variant, a.tag, a.zips,
    "release-notes.md", "tg-table.txt")
print(Path("release-notes.md").read_text())

zips = sorted(str(p) for p in Path(a.zips).glob("*.zip"))
if not zips:
    print("no zips; skipping release")
    sys.exit(0)
exists = subprocess.run(["gh", "release", "view", a.tag, "--repo", a.repo],
                        capture_output=True).returncode == 0
if exists:
    run("gh", "release", "upload", a.tag, *zips,
        "--clobber", "--repo", a.repo)
else:
    run("gh", "release", "create", a.tag, *zips, "--prerelease",
        "--title", a.tag, "--notes-file", "release-notes.md",
        "--repo", a.repo)
print(f"release {a.tag} published")

token, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT")
if not (token and chat) or not Path("tg-table.txt").is_file():
    print("telegram secrets unset; skipping")
    sys.exit(0)
data = urllib.parse.urlencode({
    "chat_id": chat, "parse_mode": "Markdown",
    "text": Path("tg-table.txt").read_text()}).encode()
req = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/sendMessage", data=data)
with urllib.request.urlopen(req, timeout=30) as r:
    if r.status != 200:
        sys.exit(f"FAIL: telegram HTTP {r.status}")
print("telegram posted")
