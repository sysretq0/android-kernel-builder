#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# setup-module-gate.sh - integrate sysretq0/android-module-gate LSM.
#
# Run with cwd = repo-sync root (the dir containing common/):
#   setup-module-gate.sh [--repo sysretq0/android-module-gate]
#     [--ref <branch|tag|commit>]
#
# Full clone, .git preserved (pinning/versioning). Empty --ref = main.
# Writes .fragments/mgate.config for apply-fragments.sh (kept out of
# fragments/ on purpose: the symbol must never be enabled without the
# driver source present).
set -euo pipefail

REPO="sysretq0/android-module-gate"; REF=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    *) echo "setup-module-gate: unknown arg: $1" >&2; exit 2 ;;
  esac
done

NAME="module-gate"
[ -d "$NAME" ] || git clone "https://github.com/$REPO" "$NAME"

if [ -n "$REF" ]; then
  bash "$NAME/kernel/setup.sh" "$REF"
else
  bash "$NAME/kernel/setup.sh"
fi

if [ -n "$REF" ]; then
  WANT=$(git -C "$NAME" rev-parse "$REF^{commit}" 2>/dev/null || true)
  GOT=$(git -C "$NAME" rev-parse HEAD)
  [ -n "$WANT" ] && [ "$WANT" = "$GOT" ] || { echo "setup-module-gate: HEAD $GOT != requested $REF ($WANT); refusing silent drift" >&2; exit 2; }
  echo "setup-module-gate: HEAD verified at $GOT ($REF)"
fi

printf '%s %s\n' "${REF:-}" "$(git -C "$NAME" rev-parse --short HEAD)" > .mgate-version
mkdir -p .fragments
cat > .fragments/mgate.config <<'EOF'
# ModuleGate LSM (written by setup-module-gate.sh; only exists
# when the gate step ran, so source and symbol always agree).
# Audit mode by default: observes, enrolls, allows. Enforcement is
# never compiled in -- it takes an explicit runtime write to mode.
CONFIG_MODULE_GATE=y
EOF
echo "setup-module-gate: driver linked, fragment written"
