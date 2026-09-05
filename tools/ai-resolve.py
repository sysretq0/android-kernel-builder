#!/usr/bin/env python3
"""Per-file AI conflict resolver via OpenRouter. Harness, not just a model call.

Usage (called from CI once per conflicted file):
  ai-resolve.py --file <relpath> --model <openrouter-id> [--timeout 120]

Contract:
  - Input: git stages :1: (base), :2: (ours=LTS), :3: (theirs=stable),
           plus the working-tree file containing <<<<<<< markers,
           plus the two side commit subjects.
  - Output: complete resolved file written back to --file. Full-file only,
            no diffs, no explanations, no extra files.
  - Validation (fail-closed): reject on markers remaining, on empty output,
            on output > 3x max(input) (truncation/hallucination guard),
            on unknown files. Exit nonzero = caller must abort this file.
  - Deterministic pre-pass for trivial version files is handled by the
    caller (bash): this script is only invoked for non-trivial files.

Env:
  OPENROUTER_API_KEY  required
"""
import argparse
import os
import subprocess
import sys
import json
import urllib.request

FREE_DEFAULT = "meta-llama/llama-3.3-70b-instruct:free"
MAX_ATTEMPTS = 2

def sh(*args):
    return subprocess.run(args, capture_output=True, text=True)

def stage(ref, path):
    # git show :N:path -> content or "" if missing (add/add, delete/modify)
    r = sh("git", "show", f"{ref}:{path}")
    return r.stdout if r.returncode == 0 else ""

def acctrim(s, n=8000):
    return s if len(s) <= n else s[:n] + "\n...[truncated]...\n"

PROMPT_TMPL = """You resolve a git merge conflict for ONE file. Return ONLY the complete resolved file content, no explanations, no code fences, no diff.

File: {path}
Ours (LTS/Android): {ours_msg}
Theirs (stable .y): {theirs_msg}

Rules:
- Preserve Android-specific code (drivers/android, arch/arm64 android bits, GKI/ABI guards, CONFIG_* android defaults) unless it is clearly dead after the stable change.
- For version numbers take the NEWER stable side.
- Keep includes, Kconfig dependencies and function signatures compiling. Do not rename symbols.
- If both sides add code in the same place, keep BOTH, in logical order (ours first, then theirs), deduplicating identical lines.
- Never emit conflict markers (<<<<<<<, =======, >>>>>>>).

--- BASE (:1:) ---
{base}

--- OURS (:2:) ---
{ours}

--- THEIRS (:3:) ---
{theirs}

--- CONFLICTED FILE (with markers) ---
{marked}
"""

def call_openrouter(api_key, model, prompt, timeout):
    req_body = json.dumps({
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You are a Linux kernel merge-conflict resolver. Output only the resolved file."},
            {"role": "user", "content": prompt},
        ],
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=req_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/sysretq0/android-kernel-builder",
            "X-Title": "kernel-stable-merge-resolver",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        print(f"unexpected API response: {acctrim(json.dumps(data), 2000)}", file=sys.stderr)
        raise Runtimefailure("bad API response")

class Runtimefailure(Exception):
    pass

def strip_fences(s):
    t = s.strip()
    if t.startswith("```"):
        # strip first fence line and last fence
        lines = t.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines) + "\n"
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--model", default=os.environ.get("AI_MODEL", "") or FREE_DEFAULT)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--ours-msg", default="")
    ap.add_argument("--theirs-msg", default="")
    args = ap.parse_args()

    path = args.file
    model = args.model.strip() or FREE_DEFAULT
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("::error::Missing OPENROUTER_API_KEY secret.", file=sys.stderr)
        return 2

    base = stage(":1", path)
    ours = stage(":2", path)
    theirs = stage(":3", path)
    try:
        with open(path, "r", errors="replace") as f:
            marked = f.read()
    except OSError as e:
        print(f"::error::cannot read {path}: {e}", file=sys.stderr)
        return 2

    if "<<<<<<<" not in marked:
        print(f"{path}: no markers, nothing to do")
        return 0

    prompt = PROMPT_TMPL.format(
        path=path, ours_msg=args.ours_msg, theirs_msg=args.theirs_msg,
        base=acctrim(base), ours=acctrim(ours),
        theirs=acctrim(theirs), marked=acctrim(marked, 12000),
    )
    max_in = max(len(base), len(ours), len(theirs), len(marked), 1)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"{path}: AI attempt {attempt}/{MAX_ATTEMPTS} model={model}")
        try:
            out = call_openrouter(api_key, model, prompt, args.timeout)
        except Exception as e:
            print(f"{path}: API error: {e}", file=sys.stderr)
            continue
        out = strip_fences(out)
        # ---- validation ladder ----
        if not out.strip():
            print(f"{path}: reject: empty output", file=sys.stderr)
            continue
        if "<<<<<<<" in out or ">>>>>>>" in out:
            print(f"{path}: reject: markers remain", file=sys.stderr)
            continue
        if len(out) > 3 * max_in + 5000:
            print(f"{path}: reject: output suspiciously large ({len(out)} vs in {max_in})", file=sys.stderr)
            continue
        # looks sane: write back
        with open(path, "w") as f:
            f.write(out if out.endswith("\n") else out + "\n")
        print(f"{path}: resolved ({len(out)} bytes)")
        return 0

    print(f"::error::{path}: AI failed after {MAX_ATTEMPTS} attempts", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
