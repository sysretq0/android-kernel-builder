#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# setup-ntsync.sh - integrate the WildKernels NTSync backport (Winlator/GameHub).
#
# Run with cwd = repo-sync root (the dir containing common/):
#   setup-ntsync.sh --our-branch android14-6.1-lts [--patch-dir DIR]
#
# NTSync is a dormant char device (/dev/ntsync) for Windows NT sync
# primitive emulation; in-tree from 6.12 (BROKEN-gated) / 6.18, backported
# here for 5.10-6.6. Same risk class as BBRv3: new files + Kconfig/Makefile
# lines, nothing hooked into existing code paths.
#
# Patches vendored in patches/ntsync/ (see NOTICE). Compat selection:
# single file per tree except 5.10, where the two candidates self-select
# via patch --dry-run (hunk offsets track sublevel bases; guessing rots
# as LTS tips move). Writes .fragments/ntsync.config for apply-fragments.sh
# (kept out of fragments/ on purpose: the symbol must never be enabled
# without the driver source present). 6.12+ clean-skip with NO fragment.
set -euo pipefail

PATCH_DIR=""; OUR_BRANCH=""
while [ $# -gt 0 ]; do
  case "$1" in
    --patch-dir) PATCH_DIR="$2"; shift 2 ;;
    --our-branch) OUR_BRANCH="$2"; shift 2 ;;
    *) echo "setup-ntsync: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$PATCH_DIR" ] || { echo "setup-ntsync: missing --patch-dir" >&2; exit 2; }
[ -d "$PATCH_DIR" ] || { echo "setup-ntsync: no such patch dir: $PATCH_DIR" >&2; exit 2; }

case "$OUR_BRANCH" in
  android12-5.10-*|android13-5.10-*) COMPATS="ntsync_compat_android12-5.10.patch ntsync_compat_android12-5.10_A14.patch" ;;
  android13-5.15-*|android14-5.15-*) COMPATS="ntsync_compat_android13-5.15.patch" ;;
  android14-6.1-*)  COMPATS="ntsync_compat_android14-6.1.patch" ;;
  android15-6.6-*)  COMPATS="ntsync_compat_android15-6.6.patch" ;;
  *)
    echo "setup-ntsync: in-tree on '$OUR_BRANCH' (6.12+) or unknown; skipping, no fragment"
    exit 0 ;;
esac

COMPAT=""
# shellcheck disable=SC2086
for cand in $COMPATS; do
  [ -f "$PATCH_DIR/$cand" ] || { echo "setup-ntsync: missing $cand" >&2; exit 2; }
  if patch -p1 --dry-run --directory=common < "$PATCH_DIR/$cand" >/dev/null 2>&1; then
    COMPAT="$cand"; break
  fi
done
[ -n "$COMPAT" ] || { echo "setup-ntsync: no compat applies on $OUR_BRANCH" >&2; exit 2; }
echo "setup-ntsync: compat $COMPAT"
patch -p1 --fuzz=3 --directory=common < "$PATCH_DIR/$COMPAT"
patch -p1 --fuzz=3 --directory=common < "$PATCH_DIR/ntsync_base.patch"

if find common/drivers common/include -name '*.rej' 2>/dev/null | grep -q .; then
  echo "setup-ntsync: patch left .rej files:" >&2
  find common/drivers common/include -name '*.rej' >&2
  exit 2
fi
[ -f common/drivers/misc/ntsync.c ] || { echo "setup-ntsync: marker FAILED (ntsync.c)" >&2; exit 2; }
grep -q "config NTSYNC" common/drivers/misc/Kconfig || { echo "setup-ntsync: marker FAILED (Kconfig)" >&2; exit 2; }
grep -q "ntsync.o" common/drivers/misc/Makefile || { echo "setup-ntsync: marker FAILED (Makefile)" >&2; exit 2; }
printf '%s+%s\n' "$COMPAT" "ntsync_base.patch" > .ntsync-version
echo "setup-ntsync: backport applied, markers present"

mkdir -p .fragments
cat > .fragments/ntsync.config <<'EOF'
# NTSync (written by setup-ntsync.sh; only exists when the backport step
# ran, so patched source and symbol always agree). Dormant char device
# until opened by Winlator/GameHub.
CONFIG_NTSYNC=y
EOF
echo "setup-ntsync: fragment written"
