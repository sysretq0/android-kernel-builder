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

# KSU bakes its version from git (rev-list --count + describe --tags), but
# the Kleaf sandbox strips .git (Bazel excludes **/.*), so every Kleaf build
# would bake KSU_VERSION=1 / tag v0.0.1 -- outside any range the manager app
# accepts. Compute from the runner-side full clone and bake into the
# fallback assignments (same 30000+ formula as Kbuild). build.sh is
# unaffected (real .git present, fallback lines unused).
KSU_COUNT=$(git -C "$NAME" rev-list --count HEAD)
KSU_TAG=$(git -C "$NAME" describe --tags --abbrev=0)
KSU_VERSION=$((30000 + KSU_COUNT))
KSU_KBUILD=common/drivers/kernelsu/Kbuild
sed -i "s/^KSU_VERSION_FALLBACK := .*/KSU_VERSION_FALLBACK := $KSU_VERSION/" "$KSU_KBUILD"
sed -i "s/^KSU_VERSION_TAG_FALLBACK := .*/KSU_VERSION_TAG_FALLBACK := $KSU_TAG/" "$KSU_KBUILD"
# The sandbox can never have .git (stripped by design), so the "make it a
# git repo" warnings are pure noise once values are baked: demote them to
# info. Verified below -- if upstream rewords either line, fail fast here
# rather than silently shipping version 1/v0.0.1.
sed -i 's/^$(warning "KSU_GIT_VERSION not defined!.*$/$(info -- KSU_GIT_VERSION: using baked value)/' "$KSU_KBUILD"
sed -i 's/^$(warning "KSU_VERSION_TAG not defined!.*$/$(info -- KSU_VERSION_TAG: using baked value)/' "$KSU_KBUILD"
grep -q "^KSU_VERSION_FALLBACK := $KSU_VERSION$" "$KSU_KBUILD" && \
grep -q "^KSU_VERSION_TAG_FALLBACK := $KSU_TAG$" "$KSU_KBUILD" && \
grep -q "KSU_GIT_VERSION: using baked value" "$KSU_KBUILD" && \
grep -q "KSU_VERSION_TAG: using baked value" "$KSU_KBUILD" || \
  { echo "setup-kernelsu-next: version bake verification FAILED" >&2; exit 2; }
echo "setup-kernelsu-next: baked version fallback $KSU_VERSION / $KSU_TAG"

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
