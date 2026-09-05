#!/usr/bin/env bash
# setup-partition-guard.sh - integrate sysretq0/android-partition-guard LSM.
#
# Run with cwd = repo-sync root (the dir containing common/):
#   setup-partition-guard.sh [--repo sysretq0/android-partition-guard]
#     [--ref <branch|tag|commit>]
#
# Full clone, .git preserved (pinning/versioning). Empty --ref = main.
# Writes .fragments/guard.config for apply-fragments.sh (kept out of
# fragments/ on purpose: the symbol must never be enabled without the
# driver source present).
set -euo pipefail

REPO="sysretq0/android-partition-guard"; REF=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo) REPO="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    *) echo "setup-partition-guard: unknown arg: $1" >&2; exit 2 ;;
  esac
done

export GKI_ROOT="$PWD"
NAME="partition-guard"
[ -d "$NAME" ] || git clone "https://github.com/$REPO" "$NAME"

if [ -n "$REF" ]; then
  bash "$NAME/kernel/setup.sh" "$REF"
else
  bash "$NAME/kernel/setup.sh"
fi

mkdir -p .fragments
cat > .fragments/guard.config <<'EOF'
# Partition Guard LSM (written by setup-partition-guard.sh; only exists
# when the guard step ran, so source and symbol always agree).
CONFIG_PARTITION_GUARD=y
EOF
echo "setup-partition-guard: driver linked, fragment written"
