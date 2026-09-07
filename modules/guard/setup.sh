#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# modules/guard/setup.sh - integrate sysretq0/android-partition-guard LSM.
#
# Usage: setup.sh <workdir> <branch> <ref>
# Writes <workdir>/.guard-version and
# <workdir>/modular.fragments.d/guard.config.
set -euo pipefail

WORK="$1"; BRANCH="$2"; REF="${3:-}"
REPO="sysretq0/android-partition-guard"
cd "$WORK"

NAME="partition-guard"
[ -d "$NAME" ] || git clone "https://github.com/$REPO" "$NAME"

if [ -n "$REF" ]; then
  bash "$NAME/kernel/setup.sh" "$REF"
else
  bash "$NAME/kernel/setup.sh"
fi

if [ -n "$REF" ]; then
  WANT=$(git -C "$NAME" rev-parse "$REF^{commit}" 2>/dev/null || true)
  GOT=$(git -C "$NAME" rev-parse HEAD)
  [ -n "$WANT" ] && [ "$WANT" = "$GOT" ] || { echo "guard: HEAD $GOT != requested $REF ($WANT); refusing silent drift" >&2; exit 2; }
  echo "guard: HEAD verified at $GOT ($REF)"
fi

printf '%s %s\n' "${REF:-}" "$(git -C "$NAME" rev-parse --short HEAD)" > .guard-version
mkdir -p modular.fragments.d
cat > modular.fragments.d/guard.config <<'EOF'
# Partition Guard LSM (written by setup.sh; only exists when the guard
# step ran, so source and symbol always agree).
CONFIG_PARTITION_GUARD=y
EOF
echo "guard: driver linked, fragment written"
