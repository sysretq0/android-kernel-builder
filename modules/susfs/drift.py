#!/usr/bin/env python3
"""SuSFS drift fakes with exact-count asserts. cwd=common/ (the tree).

Usage: drift.py <gki-ver> <sublevel>

Ports the WildKernels sublevel-gated pre-edits (simonpunk's patch base is
newer GKI than our -lts tips). Every edit asserts its replacement count
and dies otherwise: no `|| true`, no silent no-ops, no double-hits.
Post-conditions are verified before exit, so the caller needs no
separate sweep for drift-touched files.
"""
import re
import sys
from pathlib import Path

GKI, SUB = sys.argv[1], int(sys.argv[2])


def edit(path, old, new, regex=False):
    # Replace-all like the originals (perl -pe / sed g); the assert is
    # floor-1: a silent no-match was the real hazard, multi-hit is the
    # documented upstream shape. Single-shot protection lives in
    # insert_after / fdinfo_block / delete_line instead.
    p = Path(path)
    src = p.read_text()
    if regex:
        out, n = re.subn(old, new, src)
    else:
        n, out = src.count(old), src.replace(old, new)
    if n < 1:
        sys.exit(f"FAIL: drift {path}: no match for {old!r:.60}")
    p.write_text(out)
    print(f"drift: {path}: {n} edit(s)")


def delete_line(path, line, maxcount=1):
    p = Path(path)
    src = p.read_text()
    n = sum(1 for l in src.splitlines() if l.strip() == line.strip())
    if n > maxcount:
        sys.exit(f"FAIL: drift {path}: {line!r} found {n}x")
    if n == 0:
        print(f"drift: {path}: already absent, ok")
        return
    p.write_text("\n".join(l for l in src.splitlines()
                           if l.strip() != line.strip()) + "\n")
    print(f"drift: {path}: deleted 1 line")


def insert_after(path, anchor, block):
    p = Path(path)
    src = p.read_text()
    hits = [i for i, l in enumerate(src.splitlines()) if l == anchor]
    if len(hits) != 1:
        sys.exit(f"FAIL: drift {path}: anchor {anchor!r} found "
                 f"{len(hits)}x, want 1")
    if block.strip().splitlines()[0] in src:
        print(f"drift: {path}: block present, ok")
        return
    lines = src.splitlines()
    lines.insert(hits[0] + 1, block)
    p.write_text("\n".join(lines) + "\n")
    print(f"drift: {path}: inserted after anchor")


FDINFO_COMMENT = (r"(if \(inode\) \{\n)\t\t/\*\n(\t\t \*[^\n]*\n)+\t\t \*/\n",
                  r"\1")
FDINFO_MASKDECL = r"^[ \t]*u32 mask = mark->mask & IN_ALL_EVENTS;\n"


def fdinfo_block():
    f = "fs/notify/fdinfo.c"
    src = Path(f).read_text()
    if ("inotify_mark_user_mask(struct fsnotify_mark *mark)\n{" in src
            and not re.search(FDINFO_MASKDECL, src, flags=re.M)):
        print(f"drift: {f}: already transformed, ok")
        return
    out, n1 = re.subn(*FDINFO_COMMENT, src)
    out, n2 = re.subn(FDINFO_MASKDECL, "", out, flags=re.M)
    if (n1, n2) != (1, 1):
        sys.exit(f"FAIL: drift {f}: comment-strip {n1}, mask-decl {n2}")
    n3 = len(re.findall(r"\bmask,\s*mark->ignored_mask", out))
    out = re.sub(r"\bmask,\s*mark->ignored_mask",
                 "inotify_mark_user_mask(mark)", out)
    n4 = len(re.findall(r"ignored_mask:%x", out))
    out = out.replace("ignored_mask:%x", "ignored_mask:0")
    if n3 < 1 or n4 < 1:
        sys.exit(f"FAIL: drift {f}: mask-use {n3}, seq_printf {n4}")
    sig = ("static void inotify_fdinfo(struct seq_file *m, "
           "struct fsnotify_mark *mark)")
    if sig not in out:
        sys.exit(f"FAIL: drift {f}: anchor signature gone")
    helper = ("static inline u32 inotify_mark_user_mask"
              "(struct fsnotify_mark *mark)\n{\n"
              "\treturn mark->mask & IN_ALL_EVENTS;\n}\n\n")
    if "inotify_mark_user_mask(struct fsnotify_mark *mark)\n{" not in out:
        out = out.replace(sig, helper + sig)
    Path(f).write_text(out)
    print(f"drift: {f}: comment 1, decl 1, uses {n3}, seq {n4}, helper ok")
    assert "inotify_mark_user_mask" in Path(f).read_text()


LE = lambda s, n: s <= n  # noqa: E731
GE = lambda s, n: s >= n  # noqa: E731

if GKI == "gki-android12-5.10":
    if LE(SUB, 43):
        edit("fs/proc/base.c",
             re.compile(r"(int|size_t)\s+this_len\s*=\s*min_t\s*\(\s*\1\s*,"),
             "size_t this_len = min_t(size_t,", regex=True)
    if LE(SUB, 117):
        fdinfo_block()
elif GKI == "gki-android13-5.10":
    if LE(SUB, 107):
        fdinfo_block()
elif GKI in ("gki-android13-5.15", "gki-android14-5.15"):
    if LE(SUB, 41):
        insert_after("fs/namespace.c", "#include <linux/shmem_fs.h>",
                     "#include <linux/mnt_idmapping.h>")
        insert_after("fs/open.c", "#include <linux/compat.h>",
                     "#include <linux/mnt_idmapping.h>")
        fdinfo_block()
    if GE(SUB, 197):
        delete_line("fs/namespace.c", "#include <trace/hooks/blk.h>")
        delete_line("fs/proc/task_mmu.c", "#include <trace/hooks/mm.h>")
elif GKI == "gki-android14-6.1":
    if LE(SUB, 25):
        insert_after("fs/proc/base.c", "#include <trace/events/oom.h>",
                     "#include <trace/hooks/sched.h>")
    if LE(SUB, 141):
        insert_after("fs/proc/base.c", "#include <linux/cpufreq_times.h>",
                     "#include <linux/dma-buf.h>")
    if GE(SUB, 157):
        delete_line("fs/namespace.c", "#include <trace/hooks/blk.h>")
elif GKI == "gki-android15-6.6":
    if LE(SUB, 92):
        insert_after("fs/proc/base.c", "#include <linux/cpufreq_times.h>",
                     "#include <linux/dma-buf.h>")
    if LE(SUB, 57):
        insert_after("mm/memory.c", "#include <linux/sched/sysctl.h>",
                     "#include <linux/zswap.h>")
elif GKI == "gki-android16-6.12":
    if GE(SUB, 58):
        delete_line("fs/exec.c", "#include <linux/dma-buf.h>")
    if GE(SUB, 69):
        edit("fs/proc/task_mmu.c", "vma_data_pages", "vma_pages")
else:
    sys.exit(f"FAIL: drift: no profile for {GKI}")
print(f"drift: {GKI} sublevel {SUB} done")
