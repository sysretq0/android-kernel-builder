#!/usr/bin/env bash
# setup-nomount.sh - integrate the maxsteeel/nomount VFS subsystem.
#
# Run with cwd = repo-sync root (the dir containing common/):
#   setup-nomount.sh [--repo maxsteeel/nomount] [--ref <branch|tag|commit>]
#
# Full clone, .git preserved: kernel/setup.sh uses reset/pull/fetch/checkout,
# so no --depth and no worktree export. Empty --ref = installer default
# (dev branch). Built-in (=y) per their recommended Method 1.
#
# Writes .fragments/nomount.config for apply-fragments.sh (kept out of
# fragments/ on purpose: the symbol must never be enabled without the
# driver source present).
set -euo pipefail

REPO="maxsteeel/nomount"; REF=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    *) echo "setup-nomount: unknown arg: $1" >&2; exit 2 ;;
  esac
done

NAME="NoMount"
[ -d "$NAME" ] || git clone "https://github.com/$REPO" "$NAME"

if [ -n "$REF" ]; then
  bash "$NAME/kernel/setup.sh" "$REF"
else
  bash "$NAME/kernel/setup.sh"
fi

mkdir -p .fragments
cat > .fragments/nomount.config <<'EOF'
# NoMount VFS redirection (written by setup-nomount.sh; only exists when the
# NoMount step ran, so source and symbol always agree).
CONFIG_NOMOUNT=y
EOF
echo "setup-nomount: driver linked, fragment written"
