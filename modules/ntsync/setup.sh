#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# modules/ntsync/setup.sh - apply vendored NTSync backport.
#
# Usage: setup.sh <workdir> <branch> <ref>
# Dormant char device (/dev/ntsync) for Winlator/GameHub; in-tree from
# 6.18 (fragment only, no patch), BROKEN-gated on 6.12 (skip, no
# fragment). No clone, no pin: <ref> must be empty.
# Writes <workdir>/.ntsync-version and
# <workdir>/modular.fragments.d/ntsync.config.
set -euo pipefail

WORK="$1"; BRANCH="$2"; REF="${3:-}"
[ -z "$REF" ] || { echo "ntsync: pins not supported (vendored patches)" >&2; exit 2; }
cd "$WORK"
HERE="$(cd ../builder/modules/ntsync && pwd)"

if python3 -c "import json; exit(0 if json.load(open('$HERE/patches.json')).get('$BRANCH', {}).get('in-tree') else 1)"; then
  printf 'in-tree\n' > .ntsync-version
  mkdir -p modular.fragments.d
  printf '%s\n' "CONFIG_NTSYNC=y" > modular.fragments.d/ntsync.config
  echo "ntsync: in-tree on '$BRANCH'; fragment written, no patch"
  exit 0
fi

OUT=$(python3 ../builder/tools/apply-patches.py --patch-dir "$HERE/patches" \
  --patches-json "$HERE/patches.json" --branch "$BRANCH" --tree common) || exit $?
echo "$OUT"
if grep -q "^apply-patches: no entry" <<<"$OUT"; then
  echo "ntsync: not backported for '$BRANCH'; skipping, no fragment"
  exit 0
fi

COMPAT=$(python3 -c "
import json, subprocess
entry = json.load(open('$HERE/patches.json'))['$BRANCH']['files'][0]
cands = entry.get('candidates') or [entry['patch']]
for c in cands:
    r = subprocess.run(['patch', '-p1', '--dry-run', '--directory=common'],
                       stdin=open('$HERE/patches/' + c, 'rb'),
                       capture_output=True)
    if r.returncode == 0:
        print(c); break")
printf '%s+ntsync_base.patch\n' "$COMPAT" > .ntsync-version
mkdir -p modular.fragments.d
cat > modular.fragments.d/ntsync.config <<'EOF'
# NTSync (written by setup.sh; only exists when the backport step ran, so
# patched source and symbol always agree). Dormant char device until
# opened by Winlator/GameHub.
CONFIG_NTSYNC=y
EOF
echo "ntsync: backport applied ($COMPAT), fragment written"
