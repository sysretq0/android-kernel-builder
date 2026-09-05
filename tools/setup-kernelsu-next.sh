#!/usr/bin/env bash
# setup-kernelsu-next.sh - integrate the pershoot/KernelSU-Next driver.
#
# Run with cwd = repo-sync root (the dir containing common/):
#   setup-kernelsu-next.sh [--repo pershoot/KernelSU-Next] [--ref <tag|commit>]
#
# Full clone, .git preserved: kernel/setup.sh needs git stash/pull,
# origin/HEAD and describe --tags, so no --depth and no worktree export.
# Pre-cloning the fork also skips the installer's hardcoded upstream clone
# URL. Empty --ref = latest tag (installer default).
#
# On success the driver is symlinked as common/drivers/kernelsu with
# Makefile/Kconfig hooks, and .fragments/kernelsu.config is written for
# apply-fragments.sh (kept out of fragments/ on purpose: the symbol must
# never be enabled without the driver source present).
set -euo pipefail

REPO="pershoot/KernelSU-Next"; REF=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    *) echo "setup-kernelsu-next: unknown arg: $1" >&2; exit 2 ;;
  esac
done

NAME="KernelSU-Next"
[ -d "$NAME" ] || git clone "https://github.com/$REPO" "$NAME"

if [ -n "$REF" ]; then
  bash "$NAME/kernel/setup.sh" "$REF"
else
  bash "$NAME/kernel/setup.sh"
fi

mkdir -p .fragments
cat > .fragments/kernelsu.config <<'EOF'
# KernelSU-Next integrated driver (written by setup-kernelsu-next.sh; only
# exists when the KSU step ran, so source and symbol always agree).
# KSU depends on KPROBES && EXT4_FS (drivers/kernelsu/Kconfig).
CONFIG_KSU=y
CONFIG_KPROBES=y
CONFIG_EXT4_FS=y
EOF
echo "setup-kernelsu-next: driver linked, fragment written"
