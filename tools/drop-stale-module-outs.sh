#!/usr/bin/env bash
# drop-stale-module-outs.sh - remove .ko entries from a Kleaf modules.bzl
# that our built-in posture makes unbuildable.
#
# A `select` from a =y symbol forces the target built-in, so its .ko never
# materializes while the module list still demands it (Kleaf hard-fails
# "declared but not built"). Deleting the stale expectation is the fix;
# flipping the feature to =m is not (its own .ko is then undeclared).
# Method proven by WildKernels/GKI_KernelSU_SUSFS (their CIFS action).
#
# Guardrails (all must hold, else no-op or fail):
#   - kernel version gate (--kversion, e.g. "6.12"): only the trees whose
#     module list carries the stale entry;
#   - selector gate (--when-cifs-y etc.): only when our staged fragment
#     actually forces the built-in (else we'd orphan a built .ko);
#   - verification: the entry must be present before, absent after --
#     upstream layout drift fails fast and loud instead of silently.
#
# Usage:
#   drop-stale-module-outs.sh --tree <common>
#     --kversion <major.minor> --when-symbol CONFIG_CIFS
#     --drop fs/netfs/netfs.ko [...]
set -euo pipefail

TREE=""; KVERSION=""; WHEN=""; DROPS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --tree) TREE="$2"; shift 2 ;;
    --kversion) KVERSION="$2"; shift 2 ;;
    --when-symbol) WHEN="$2"; shift 2 ;;
    --drop) DROPS+=("$2"); shift 2 ;;
    *) echo "drop-stale-module-outs: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$TREE" ] && [ -n "$KVERSION" ] && [ ${#DROPS[@]} -gt 0 ] || \
  { echo "drop-stale-module-outs: --tree/--kversion/--drop required" >&2; exit 2; }

major=$(sed -n 's/^VERSION = //p' "$TREE/Makefile" | tr -d ' ')
minor=$(sed -n 's/^PATCHLEVEL = //p' "$TREE/Makefile" | tr -d ' ')
if [ "$major.$minor" != "$KVERSION" ]; then
  echo "drop-stale-module-outs: kernel $major.$minor != $KVERSION, skipping"
  exit 0
fi
if [ -n "$WHEN" ]; then
  frag="$TREE/builder_fragments.config"
  [ -f "$frag" ] && grep -q "^${WHEN}=y$" "$frag" || \
    { echo "drop-stale-module-outs: $WHEN not forced =y, skipping"; exit 0; }
fi

BZL=""
for cand in "$TREE/modules.bzl" "$TREE/common/modules.bzl"; do
  [ -f "$cand" ] && BZL="$cand" && break
done
[ -n "$BZL" ] || { echo "drop-stale-module-outs: no modules.bzl in $TREE" >&2; exit 2; }

for ko in "${DROPS[@]}"; do
  # Fixed-string match for grep, escaped match for sed (dots/slashes).
  lit="\"${ko}\","
  pat="\"$(printf '%s' "$ko" | sed 's/[\/.]/\\&/g')\","
  grep -qF "$lit" "$BZL" || \
    { echo "drop-stale-module-outs: entry missing: $ko (upstream layout changed?)" >&2; exit 2; }
  sed -i "/$pat/d" "$BZL"
  grep -qF "$lit" "$BZL" && \
    { echo "drop-stale-module-outs: delete failed: $ko" >&2; exit 2; }
  echo "drop-stale-module-outs: dropped $ko from $(basename "$BZL")"
done
