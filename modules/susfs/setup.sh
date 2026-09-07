#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# modules/susfs/setup.sh - integrate simonpunk/susfs4ksu kernel patches.
#
# Usage: setup.sh <workdir> <branch> <ref>
# Source branch per tree comes from patches.json (depth-1 clone, tip
# pinned; refresh pins when upstream moves). <ref> overrides the pinned
# commit when non-empty. Runs AFTER kernelsu-next in manifest order.
#
# Gates (main's order, verbatim rationale):
#  - branch absent from map (6.18+): suppression (dev-susfs needs
#    KSU_SUSFS forced off; harmless on plain-dev, unknown symbols ignored)
#  - 6.6: suppression (patch needs newer SELinux API than published GKI)
#  - plain-dev KSU (no SUSFS hooks): clean skip, NO fragment (even a
#    suppression would reference a nonexistent symbol)
# Writes <workdir>/.susfs-version and
# <workdir>/modular.fragments.d/susfs.config.
set -euo pipefail

WORK="$1"; BRANCH="$2"; REF="${3:-}"
cd "$WORK"
HERE="$(cd ../builder/modules/susfs && pwd)"
MAP="$HERE/patches.json"

write_suppression() { # $1 reason
  mkdir -p modular.fragments.d
  cat > modular.fragments.d/susfs.config <<'EOF'
# No SuSFS on this tree: force the whole KSU_SUSFS family off so dev-susfs
# builds its plain-dev paths.
# CONFIG_KSU_SUSFS is not set
EOF
  echo "susfs: $1; wrote KSU_SUSFS suppression, KSU-only build"
}

ENTRY=$(python3 -c "import json; print(json.dumps(json.load(open('$MAP')).get('$BRANCH')))")
if [ "$ENTRY" = "null" ]; then
  write_suppression "no upstream branch for '$BRANCH' (6.18+)"
  exit 0
fi
SUPPRESS=$(python3 -c "import json; print(json.load(open('$MAP'))['$BRANCH'].get('suppress', ''))")
if [ -n "$SUPPRESS" ]; then
  write_suppression "$SUPPRESS"
  exit 0
fi
if ! grep -q "KSU_SUSFS" common/drivers/kernelsu/Kconfig 2>/dev/null; then
  echo "susfs: KSU driver has no SUSFS hooks (plain ref); skipping, KSU-only build"
  exit 0
fi

SRC=$(python3 -c "
import json; s = json.load(open('$MAP'))['$BRANCH']['source']
print(s['repo'], s['branch'], s['commit'])")
set -- $SRC; REPO="$1"; GKI_VER="$2"; PIN="$3"
[ -n "$REF" ] && PIN="$REF"

NAME="susfs4ksu"
[ -d "$NAME" ] || git clone --depth 1 -b "$GKI_VER" "https://gitlab.com/${REPO}.git" "$NAME"
GOT=$(git -C "$NAME" rev-parse HEAD)
[ "$GOT" = "$PIN" ] || { echo "susfs: HEAD $GOT != pinned $PIN ($GKI_VER moved? refresh pins)" >&2; exit 2; }
SUSFS_SHA=$(git -C "$NAME" rev-parse --short HEAD)
echo "susfs: source at $SUSFS_SHA ($GKI_VER)"

if grep -q "susfs_is_current_ksu_domain" common/fs/namespace.c 2>/dev/null; then
  echo "susfs: patch already applied, skipping"
else
  cp -v "$NAME/kernel_patches/fs/susfs.c" common/fs/susfs.c
  cp -v "$NAME/kernel_patches/include/linux/susfs.h" common/include/linux/susfs.h
  cp -v "$NAME/kernel_patches/include/linux/susfs_def.h" common/include/linux/susfs_def.h
  SUBLEVEL=$(grep -E "^SUBLEVEL" common/Makefile | awk '{print $3}')
  echo "susfs: sublevel $SUBLEVEL, applying drift fakes for $GKI_VER"
  (
  cd common
  case "$GKI_VER" in
    gki-android12-5.10)
      [ "$SUBLEVEL" -le 43 ] && perl -i -pe 's/(int|size_t)\s+this_len\s*=\s*min_t\s*\(\s*\1\s*,/size_t this_len = min_t(size_t,/' fs/proc/base.c || true
      if [ "$SUBLEVEL" -le 117 ]; then
        perl -0777 -i -pe 's{(if \(inode\) \{\n)\t\t/\*\n(\t\t \*[^\n]*\n)+\t\t \*/\n}{$1}g; s{^[[:space:]]*u32 mask = mark->mask & IN_ALL_EVENTS;\n}{}m' fs/notify/fdinfo.c
        perl -i -pe 's/\bmask,\s*mark->ignored_mask/inotify_mark_user_mask(mark)/g' fs/notify/fdinfo.c
        perl -i -pe 's/ignored_mask:%x/ignored_mask:0/g' fs/notify/fdinfo.c
        python3 -c 'import re;c=open("fs/notify/fdinfo.c").read();c=re.sub(r"^static void inotify_fdinfo\(struct seq_file \*m, struct fsnotify_mark \*mark\)$",lambda m:"static inline u32 inotify_mark_user_mask(struct fsnotify_mark \*mark)\n{\n\treturn mark->mask & IN_ALL_EVENTS;\n}\n\n"+m.group(0),c,count=1,flags=re.MULTILINE);open("fs/notify/fdinfo.c","w").write(c)'
      fi ;;
    gki-android13-5.10)
      if [ "$SUBLEVEL" -le 107 ]; then
        perl -0777 -i -pe 's{(if \(inode\) \{\n)\t\t/\*\n(\t\t \*[^\n]*\n)+\t\t \*/\n}{$1}g; s{^[[:space:]]*u32 mask = mark->mask & IN_ALL_EVENTS;\n}{}m' fs/notify/fdinfo.c
        perl -i -pe 's/\bmask,\s*mark->ignored_mask/inotify_mark_user_mask(mark)/g' fs/notify/fdinfo.c
        perl -i -pe 's/ignored_mask:%x/ignored_mask:0/g' fs/notify/fdinfo.c
        python3 -c 'import re;c=open("fs/notify/fdinfo.c").read();c=re.sub(r"^static void inotify_fdinfo\(struct seq_file \*m, struct fsnotify_mark \*mark\)$",lambda m:"static inline u32 inotify_mark_user_mask(struct fsnotify_mark \*mark)\n{\n\treturn mark->mask & IN_ALL_EVENTS;\n}\n\n"+m.group(0),c,count=1,flags=re.MULTILINE);open("fs/notify/fdinfo.c","w").write(c)'
      fi ;;
    gki-android13-5.15|gki-android14-5.15)
      if [ "$SUBLEVEL" -le 41 ]; then
        sed -i '/^#include <linux\/shmem_fs.h>$/a #include <linux/mnt_idmapping.h>' fs/namespace.c
        sed -i '/^#include <linux\/compat.h>$/a #include <linux/mnt_idmapping.h>' fs/open.c
        perl -0777 -i -pe 's{(if \(inode\) \{\n)\t\t/\*\n(\t\t \*[^\n]*\n)+\t\t \*/\n}{$1}g; s{^[[:space:]]*u32 mask = mark->mask & IN_ALL_EVENTS;\n}{}m' fs/notify/fdinfo.c
        perl -i -pe 's/\bmask,\s*mark->ignored_mask/inotify_mark_user_mask(mark)/g' fs/notify/fdinfo.c
        perl -i -pe 's/ignored_mask:%x/ignored_mask:0/g' fs/notify/fdinfo.c
        python3 -c 'import re;c=open("fs/notify/fdinfo.c").read();c=re.sub(r"^static void inotify_fdinfo\(struct seq_file \*m, struct fsnotify_mark \*mark\)$",lambda m:"static inline u32 inotify_mark_user_mask(struct fsnotify_mark \*mark)\n{\n\treturn mark->mask & IN_ALL_EVENTS;\n}\n\n"+m.group(0),c,count=1,flags=re.MULTILINE);open("fs/notify/fdinfo.c","w").write(c)'
      fi
      [ "$SUBLEVEL" -ge 197 ] && sed -i '/^#include <trace\/hooks\/blk.h>$/d' fs/namespace.c || true
      [ "$SUBLEVEL" -ge 197 ] && sed -i '/^#include <trace\/hooks\/mm.h>$/d' fs/proc/task_mmu.c || true ;;
    gki-android14-6.1)
      [ "$SUBLEVEL" -le 25 ] && sed -i '/^#include <trace\/events\/oom.h>$/a #include <trace/hooks/sched.h>' fs/proc/base.c || true
      [ "$SUBLEVEL" -le 141 ] && sed -i '/^#include <linux\/cpufreq_times.h>$/a #include <linux/dma-buf.h>' fs/proc/base.c || true
      [ "$SUBLEVEL" -ge 157 ] && sed -i '/^#include <trace\/hooks\/blk.h>$/d' fs/namespace.c || true ;;
    gki-android16-6.12)
      [ "$SUBLEVEL" -ge 58 ] && sed -i '/^#include <linux\/dma-buf.h>$/d' fs/exec.c || true
      [ "$SUBLEVEL" -ge 69 ] && sed -i 's/vma_data_pages/vma_pages/g' fs/proc/task_mmu.c || true ;;
  esac
  )
  python3 ../builder/tools/apply-patches.py --patch-dir "$NAME/kernel_patches" \
    --patches-json "$MAP" --branch "$BRANCH" --tree common
  restore_include() { # $1 file $2 anchor $3 include $4 header-path
    grep -qF "$3" "common/$1" 2>/dev/null && return 0
    if [ ! -f "common/$4" ]; then
      echo "susfs: WARN header gone in-tree, skip restore: $4" >&2; return 0
    fi
    n=$(grep -n -m1 -F -e "$2" "common/$1" | cut -d: -f1)
    if [ -z "$n" ]; then
      echo "susfs: WARN anchor gone, skip restore: $2 in $1" >&2; return 0
    fi
    sed -i "${n}a $3" "common/$1"
  }
  case "$GKI_VER" in
    gki-android13-5.15|gki-android14-5.15)
      restore_include fs/namespace.c '#include "internal.h"' '#include <trace/hooks/blk.h>' include/trace/hooks/blk.h
      restore_include fs/proc/task_mmu.c '#include <linux/pkeys.h>' '#include <trace/hooks/mm.h>' include/trace/hooks/mm.h ;;
    gki-android14-6.1)
      restore_include fs/namespace.c '#include "internal.h"' '#include <trace/hooks/blk.h>' include/trace/hooks/blk.h ;;
    gki-android16-6.12)
      restore_include fs/exec.c '#include <linux/ksm.h>' '#include <linux/dma-buf.h>' include/linux/dma-buf.h ;;
  esac
  echo "susfs: applied 50_add_susfs_in_${GKI_VER}.patch (all file markers present)"
fi
printf '%s %s %s\n' "$GKI_VER" "$SUSFS_SHA" "${REF:-}" > .susfs-version

mkdir -p modular.fragments.d
cat > modular.fragments.d/susfs.config <<'EOF'
# SuSFS root hiding (written by setup.sh; only exists when the susfs step
# ran, so patched source and symbol always agree). KSU side hooks come from
# KernelSU-Next@dev-susfs. All sub-features explicitly on (upstream
# defaults are y, none deprecated; explicit so a future default flip cannot
# silently neuter hiding).
CONFIG_KSU_SUSFS=y
CONFIG_KSU_SUSFS_SUS_PATH=y
CONFIG_KSU_SUSFS_SUS_MOUNT=y
CONFIG_KSU_SUSFS_SUS_KSTAT=y
CONFIG_KSU_SUSFS_SPOOF_UNAME=y
CONFIG_KSU_SUSFS_ENABLE_LOG=y
CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS=y
CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y
CONFIG_KSU_SUSFS_OPEN_REDIRECT=y
CONFIG_KSU_SUSFS_SUS_MAP=y
EOF
echo "susfs: kernel patched, fragment written"
