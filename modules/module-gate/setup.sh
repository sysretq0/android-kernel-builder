#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# modules/module-gate/setup.sh - integrate sysretq0/android-module-gate LSM.
#
# Usage: setup.sh <workdir> <branch> <ref>
# Audit mode by default: observes, enrolls, allows. Enforcement is never
# compiled in -- it takes an explicit runtime write to mode.
# Writes <workdir>/.mgate-version and
# <workdir>/modular.fragments.d/mgate.config.
set -euo pipefail

WORK="$1"; BRANCH="$2"; REF="${3:-}"
REPO="sysretq0/android-module-gate"
cd "$WORK"

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
  [ -n "$WANT" ] && [ "$WANT" = "$GOT" ] || { echo "module-gate: HEAD $GOT != requested $REF ($WANT); refusing silent drift" >&2; exit 2; }
  echo "module-gate: HEAD verified at $GOT ($REF)"
fi

printf '%s %s\n' "${REF:-}" "$(git -C "$NAME" rev-parse --short HEAD)" > .mgate-version
mkdir -p modular.fragments.d
cat > modular.fragments.d/mgate.config <<'EOF'
# ModuleGate LSM (written by setup.sh; only exists when the gate step
# ran, so source and symbol always agree).
# Audit mode by default: observes, enrolls, allows. Enforcement is
# never compiled in -- it takes an explicit runtime write to mode.
CONFIG_MODULE_GATE=y
EOF
echo "module-gate: driver linked, fragment written"
