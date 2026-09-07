#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# modules/kernelsu-next/setup.sh - integrate pershoot/KernelSU-Next.
#
# Usage: setup.sh <workdir> <branch> <ref>
#   <ref> = resolved pin (commit preferred, else tag, else branch, else
#   empty = installer default). Resolution lives in integrate.py; this
#   script only checks out, installs, and verifies -- never decides.
#
# Full clone, .git preserved (installer needs stash/pull/describe).
# Writes <workdir>/.ksu-version and
# <workdir>/modular.fragments.d/kernelsu.config (exists only when this
# ran, so source and symbol always agree).
set -euo pipefail

WORK="$1"; BRANCH="$2"; REF="${3:-}"
REPO="pershoot/KernelSU-Next"
cd "$WORK"

NAME="KernelSU-Next"
[ -d "$NAME" ] || git clone "https://github.com/$REPO" "$NAME"

if [ -n "$REF" ]; then
  git -C "$NAME" fetch origin || true
  git -C "$NAME" checkout -q "$REF" || { echo "kernelsu-next: cannot checkout ref '$REF'" >&2; exit 2; }
fi

if [ -n "$REF" ]; then
  bash "$NAME/kernel/setup.sh" "$REF"
else
  bash "$NAME/kernel/setup.sh"
fi

if [ -n "$REF" ]; then
  WANT=$(git -C "$NAME" rev-parse "$REF^{commit}" 2>/dev/null || true)
  GOT=$(git -C "$NAME" rev-parse HEAD)
  [ -n "$WANT" ] && [ "$WANT" = "$GOT" ] || { echo "kernelsu-next: HEAD $GOT != requested $REF ($WANT); refusing silent drift" >&2; exit 2; }
  echo "kernelsu-next: HEAD verified at $GOT ($REF)"
fi

KSU_SHA=$(git -C "$NAME" rev-parse --short HEAD)
BASE_COMMIT=$(git -C "$NAME" merge-base HEAD refs/remotes/origin/dev 2>/dev/null || \
  git -C "$NAME" merge-base HEAD refs/remotes/origin/main 2>/dev/null || echo HEAD)
KSU_COUNT=$(git -C "$NAME" rev-list --count "$BASE_COMMIT")
KSU_TAG=$(git -C "$NAME" describe --tags --abbrev=0 "$BASE_COMMIT" 2>/dev/null || echo "v0.0.1")
KSU_VERSION=$((30000 + KSU_COUNT))
echo "kernelsu-next: source at $KSU_SHA ($KSU_TAG, versionCode $KSU_VERSION)"
printf '%s %s %s %s\n' "$KSU_TAG" "$KSU_SHA" "${REF:-}" "$KSU_VERSION" > .ksu-version
KSU_KBUILD=common/drivers/kernelsu/Kbuild
sed -i "s/^KSU_VERSION_FALLBACK := .*/KSU_VERSION_FALLBACK := $KSU_VERSION/" "$KSU_KBUILD"
sed -i "s/^KSU_VERSION_TAG_FALLBACK := .*/KSU_VERSION_TAG_FALLBACK := $KSU_TAG/" "$KSU_KBUILD"
grep -q "^KSU_VERSION_FALLBACK := $KSU_VERSION$" "$KSU_KBUILD" && \
grep -q "^KSU_VERSION_TAG_FALLBACK := $KSU_TAG$" "$KSU_KBUILD" || \
  { echo "kernelsu-next: version bake verification FAILED" >&2; exit 2; }
echo "kernelsu-next: baked version fallback $KSU_VERSION / $KSU_TAG"

mkdir -p modular.fragments.d
cat > modular.fragments.d/kernelsu.config <<'EOF'
# KernelSU-Next integrated driver (written by setup.sh; only exists when
# the KSU step ran, so source and symbol always agree).
# KSU depends on KPROBES && EXT4_FS (drivers/kernelsu/Kconfig).
CONFIG_KSU=y
CONFIG_KPROBES=y
CONFIG_EXT4_FS=y
EOF

SEHIDE="$NAME/kernel/feature/selinux_hide.c"
if grep -q "^static int security_context_to_sid_with_policy" "$SEHIDE" 2>/dev/null && \
   grep -q "^int security_context_to_sid_with_policy" "$SEHIDE" 2>/dev/null; then
  sed -i \
    -e 's/^static int security_context_to_sid_with_policy/int security_context_to_sid_with_policy/' \
    -e 's/^static int security_sid_to_context_with_policy/int security_sid_to_context_with_policy/' \
    -e 's/^static void security_compute_av_user_with_policy/void security_compute_av_user_with_policy/' \
    "$SEHIDE"
  grep -qE "^static\b.*\bsecurity_(context_to_sid|sid_to_context|compute_av_user)_with_policy\b" "$SEHIDE" && \
    { echo "kernelsu-next: selinux_hide linkage patch incomplete" >&2; exit 2; }
  grep -q "^int security_context_to_sid_with_policy" "$SEHIDE" || \
    { echo "kernelsu-next: selinux_hide linkage patch missing" >&2; exit 2; }
  echo "kernelsu-next: selinux_hide with_policy linkage set global (SuSFS)"
else
  echo "kernelsu-next: no static with_policy block (plain ref or old KSU); linkage untouched"
fi
echo "kernelsu-next: driver linked, fragment written"
