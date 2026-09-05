#!/usr/bin/env bash
# pack-anykernel.sh - stage an AnyKernel3 flashable zip from a built kernel.
#
# Usage:
#   pack-anykernel.sh --image <Image.lz4|Image.gz|Image> --rev <name>
#     [--features <"a:b:c">] [--out <zip path>] [--akdir <anykernel/ dir>]
#
# --features is a colon-separated list expanded to one "[check] item"
# ui_print line per entry, replacing the @FEATURE_LINES@ placeholder
# (sed r-command: byte-transparent, no delimiter collisions). Date
# stamps @DATE@ automatically.
#
# Stages META-INF + tools (pristine AK3 backend, magiskboot refreshed)
# with our anykernel.sh (kernel.string stamped with --rev), banner, a
# generated version file, and the raw kernel image, then zips it. AK3
# flashes to the boot partition (BLOCK=boot, slot-aware), so the zip is
# device-generic.
set -euo pipefail

IMAGE=""; REV=""; OUT=""; AKDIR=""; FEATURES="stock GKI"
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

while [ $# -gt 0 ]; do
  case "$1" in
    --image) IMAGE="$2"; shift 2 ;;
    --rev) REV="$2"; shift 2 ;;
    --features) FEATURES="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --akdir) AKDIR="$2"; shift 2 ;;
    *) echo "pack-anykernel: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$IMAGE" ] && [ -f "$IMAGE" ] || { echo "pack-anykernel: --image not found: ${IMAGE:-<unset>}" >&2; exit 2; }
[ -n "$REV" ] || { echo "pack-anykernel: --rev required" >&2; exit 2; }
[ -n "$AKDIR" ] || AKDIR="$HERE/../anykernel"
[ -f "$AKDIR/anykernel.sh" ] || { echo "pack-anykernel: anykernel dir not found: $AKDIR" >&2; exit 2; }
[ -n "$OUT" ] || OUT="$PWD/anykernel-$REV.zip"
command -v zip >/dev/null || { echo "pack-anykernel: zip not installed" >&2; exit 2; }

case "$(basename "$IMAGE")" in
  zImage*|Image*|*.fit) ;;
  *) echo "pack-anykernel: warning: $(basename "$IMAGE") is not an AK3-known kernel filename; install may not pick it up" >&2 ;;
esac

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

cp -a "$AKDIR/META-INF" "$AKDIR/tools" "$stage/"
cp -a "$AKDIR/anykernel.sh" "$AKDIR/banner" "$stage/"
DATE=$(date -u +%Y-%m-%d)
sed -i "s|@REV@|$REV|g; s|@DATE@|$DATE|g" "$stage/anykernel.sh"
> "$stage/features.tmp"
OLDIFS=$IFS; IFS=:
for f in $FEATURES; do
  [ -n "$f" ] && echo "ui_print \" [✓] $f\";" >> "$stage/features.tmp"
done
IFS=$OLDIFS
sed -i -e "/@FEATURE_LINES@/r $stage/features.tmp" -e "/@FEATURE_LINES@/d" "$stage/anykernel.sh"
grep -q "@REV@\|@FEATURE_LINES@\|@DATE@" "$stage/anykernel.sh" && { echo "pack-anykernel: unstamped placeholder left" >&2; exit 1; }
cp -a "$IMAGE" "$stage/"
cat > "$stage/version" <<EOF
$REV
Built $(date -u +%Y-%m-%dT%H:%MZ)
EOF

mkdir -p "$(dirname "$OUT")"
(cd "$stage" && zip -r9 -X "$OUT" . >/dev/null)
echo "pack-anykernel: $(basename "$OUT") ($(du -h "$OUT" | cut -f1))"
unzip -l "$OUT" | head -20
