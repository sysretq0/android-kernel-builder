#!/usr/bin/env python3
"""Supervisor review of an LTS+stable merge diff via OpenRouter.

Usage:
  git diff LTS_TIP...MERGED > merge.diff
  supervise.py --diff merge.diff --lts <lts-branch> --stable <stable-branch> [--model ID]

Output: single line VERDICT: APPROVE or VERDICT: FLAG, plus reasons to stdout.
Exit 0 on APPROVE, 10 on FLAG, 2 on harness/API error (caller treats as FLAG).
"""
import argparse
import os
import sys
import json
import urllib.request

FREE_DEFAULT = os.environ.get("DEFAULT_AI_MODEL", "minimax/minimax-m3:free")

PROMPT_TMPL = """You are a senior Linux kernel maintainer reviewing an Android-common LTS + Greg KH stable merge. Mergable does NOT mean compatible. Your job is to catch semantic breakage.

LTS branch: {lts}
Stable branch: {stable}

Review the merge diff below. Flag ANY of:
- renamed/removed symbols, changed function signatures, struct layout changes in paths Android drivers depend on
- behavior changes in core mm/sched/binder/KVM/arm64 that could break Android
- Kconfig defaults flipping, new hard dependencies
- changes touching android/abi_* (GKI/KMI surface) or drivers/android/binder*
- suspicious conflict resolutions (duplicated logic, dropped hunks, leftover debugging)

Diff (may be truncated):
---
{diff}

---
Reply in EXACTLY this format:
VERDICT: APPROVE
or
VERDICT: FLAG
Reasons:
- <one line per reason, max 10 lines>
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diff", required=True)
    ap.add_argument("--lts", default="")
    ap.add_argument("--stable", default="")
    ap.add_argument("--model", default=os.environ.get("AI_MODEL", "") or FREE_DEFAULT)
    ap.add_argument("--timeout", type=int, default=240)
    args = ap.parse_args()

    model = args.model.strip() or FREE_DEFAULT
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("::error::Missing OPENROUTER_API_KEY secret.", file=sys.stderr)
        return 2
    try:
        with open(args.diff, errors="replace") as f:
            diff = f.read()
    except OSError as e:
        print(f"::error::cannot read diff: {e}", file=sys.stderr)
        return 2

    # Cap diff sent to model: head is usually headers, tail has the meat.
    # Keep first 30k + last 60k chars to stay within context.
    if len(diff) > 95000:
        diff = diff[:30000] + "\n...[middle truncated]...\n" + diff[-60000:]

    body = json.dumps({
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You review kernel merges. Reply only in the VERDICT format."},
            {"role": "user", "content": PROMPT_TMPL.format(lts=args.lts, stable=args.stable, diff=diff)},
        ],
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/sysretq0/android-kernel-builder",
            "X-Title": "kernel-stable-supervisor",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            data = json.loads(resp.read().decode())
        text = data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"::error::supervisor API error: {e}", file=sys.stderr)
        return 2

    print(text.strip())
    first = text.strip().upper()
    if "VERDICT: FLAG" in first:
        return 10
    if "VERDICT: APPROVE" in first:
        return 0
    print("::warning::supervisor returned ambiguous verdict, treating as FLAG", file=sys.stderr)
    return 10

if __name__ == "__main__":
    sys.exit(main())
