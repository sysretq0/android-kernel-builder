#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# modules/nomount/setup.sh - integrate maxsteeel/nomount VFS subsystem.
#
# Usage: setup.sh <workdir> <branch> <ref>
# Built-in (=y) per their recommended Method 1.
# Writes <workdir>/.nomount-version and
# <workdir>/modular.fragments.d/nomount.config.
set -euo pipefail

WORK="$1"; BRANCH="$2"; REF="${3:-}"
REPO="maxsteeel/nomount"
cd "$WORK"

NAME="NoMount"
[ -d "$NAME" ] || git clone "https://github.com/$REPO" "$NAME"

if [ -n "$REF" ]; then
  bash "$NAME/kernel/setup.sh" "$REF"
else
  bash "$NAME/kernel/setup.sh"
fi

if [ -n "$REF" ]; then
  WANT=$(git -C "$NAME" rev-parse "$REF^{commit}" 2>/dev/null || true)
  GOT=$(git -C "$NAME" rev-parse HEAD)
  [ -n "$WANT" ] && [ "$WANT" = "$GOT" ] || { echo "nomount: HEAD $GOT != requested $REF ($WANT); refusing silent drift" >&2; exit 2; }
  echo "nomount: HEAD verified at $GOT ($REF)"
fi

printf '%s %s\n' "${REF:-}" "$(git -C "$NAME" rev-parse --short HEAD)" > .nomount-version
mkdir -p modular.fragments.d
cat > modular.fragments.d/nomount.config <<'EOF'
# NoMount VFS redirection (written by setup.sh; only exists when the
# NoMount step ran, so source and symbol always agree).
CONFIG_NOMOUNT=y
EOF
echo "nomount: driver linked, fragment written"
