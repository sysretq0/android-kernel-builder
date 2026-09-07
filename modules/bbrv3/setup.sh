#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# modules/bbrv3/setup.sh - apply vendored BBRv3 backports.
#
# Usage: setup.sh <workdir> <branch> <ref>
# BBRv3 is a separate algorithm (new tcp_bbr3.c, BBRv1 untouched),
# dormant until selected (default CC stays CUBIC). No clone, no pin:
# patches are vendored; <ref> is accepted and must be empty.
# Writes <workdir>/.bbrv3-version and
# <workdir>/modular.fragments.d/bbrv3.config.
set -euo pipefail

WORK="$1"; BRANCH="$2"; REF="${3:-}"
[ -z "$REF" ] || { echo "bbrv3: pins not supported (vendored patches)" >&2; exit 2; }
cd "$WORK"
HERE="$(cd ../builder/modules/bbrv3 && pwd)"

OUT=$(python3 ../builder/tools/apply-patches.py --patch-dir "$HERE/patches" \
  --patches-json "$HERE/patches.json" --branch "$BRANCH" --tree common) || exit $?
echo "$OUT"
if grep -q "^apply-patches: no entry" <<<"$OUT"; then
  echo "bbrv3: no proven backport for '$BRANCH'; skipping, no fragment"
  exit 0
fi

PATCH=$(python3 -c "import json; print(json.load(open('$HERE/patches.json'))['$BRANCH']['files'][0].get('patch', ''))")
printf '%s\n' "$PATCH" > .bbrv3-version
mkdir -p modular.fragments.d
cat > modular.fragments.d/bbrv3.config <<'EOF'
# BBRv3 congestion control (written by setup.sh; only exists when the
# backport step ran, so patched source and symbol always agree). Separate
# algorithm alongside BBRv1 (untouched); default CC stays CUBIC; dormant
# until selected per-connection.
CONFIG_TCP_CONG_BBR3=y
EOF
echo "bbrv3: backport applied, fragment written"
