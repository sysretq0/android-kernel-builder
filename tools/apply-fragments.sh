#!/usr/bin/env bash
# apply-fragments.sh - portable defconfig fragment applier (build.sh + Kleaf).
#
# Merges *.config fragments into arch/$ARCH/configs/$DEFCONFIG inside the
# kernel tree, between # begin/end-builder-fragment markers, deduped
# per-symbol against what's already effective. One mechanism for all eras,
# because both build paths start from `make gki_defconfig`:
#   - build.sh: the committed defconfig must byte-match savedefconfig
#     (check_defconfig), so pair this with self-heal-config.sh as
#     POST_DEFCONFIG_CMDS - it re-canonicalizes ordering after injection.
#   - Kleaf: fragment/order-insensitive (merge_config.sh at build time), so
#     a baked-in base defconfig just works, no extra step needed.
#
# No code changes to inject config: drop *.config files into fragments/ and
# they are picked up (sorted). Remove the file to stop applying it.
#
# Usage:
#   apply-fragments.sh --kernel-dir <path-to-common>
#     [--arch arm64] [--defconfig gki_defconfig]
#     [--fragment-dir DIRorFILE]... [--extra-config "CONFIG_X=y,..."]
#     [--exclude "name,..."]
#
# Fragment line rules (enforced): blank, comment (#...), CONFIG_X=val, or
# `# CONFIG_X is not set`. Anything else aborts.
set -euo pipefail

KERNEL_DIR=""; ARCH="arm64"; DEFCONFIG="gki_defconfig"
FRAG_INPUTS=(); EXTRA_CONFIG=""; EXCLUDE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --kernel-dir) KERNEL_DIR="$2"; shift 2 ;;
    --arch) ARCH="$2"; shift 2 ;;
    --defconfig) DEFCONFIG="$2"; shift 2 ;;
    --fragment-dir) FRAG_INPUTS+=("$2"); shift 2 ;;
    --extra-config) EXTRA_CONFIG="$2"; shift 2 ;;
    --exclude) EXCLUDE="$2"; shift 2 ;;
    *) echo "apply-fragments: unknown arg: $1" >&2; exit 2 ;;
  esac
done
[ -n "$KERNEL_DIR" ] || { echo "apply-fragments: --kernel-dir required" >&2; exit 2; }

cfg_arch=$ARCH
case "$cfg_arch" in x86_64|i386) cfg_arch=x86 ;; esac
FILE="$KERNEL_DIR/arch/$cfg_arch/configs/$DEFCONFIG"
[ -f "$FILE" ] || { echo "apply-fragments: defconfig not found: $FILE" >&2; exit 2; }

# Resolve fragment list: dirs expand to sorted *.config, files as-is.
frags=""
for inp in ${FRAG_INPUTS[@]+"${FRAG_INPUTS[@]}"}; do
  if [ -d "$inp" ]; then
    for f in "$inp"/*.config; do
      [ -e "$f" ] || continue
      frags="$frags $f"
    done
  elif [ -f "$inp" ]; then
    frags="$frags $inp"
  else
    echo "apply-fragments: fragment input not found (skipped): $inp" >&2
  fi
done
# shellcheck disable=SC2086
frags=$(printf '%s\n' $frags | sort -d | tr '\n' ' ')

# Drop excluded names (full name, minus .config, or core minus last -segment).
if [ -n "$EXCLUDE" ]; then
  excl=${EXCLUDE//,/ }; keep=""
  for frag in $frags; do
    [ -n "$frag" ] || continue
    name=$(basename "$frag"); core=${name%.config}; core=${core%-*}; drop=""
    for e in $excl; do
      if [ "$name" = "$e" ] || [ "${name%.config}" = "$e" ] || [ "$core" = "$e" ]; then drop=1; break; fi
    done
    if [ -n "$drop" ]; then echo "apply-fragments: excluded: $name" >&2
    else keep="$keep $frag"; fi
  done
  frags=$keep
fi

# Inline CONFIG lines become one extra temp fragment.
if [ -n "$EXTRA_CONFIG" ]; then
  lcf=$(mktemp); save_ifs=$IFS; IFS=,
  for line in $EXTRA_CONFIG; do
    [ -n "$line" ] || continue
    case "$line" in
      CONFIG_*=*|'# CONFIG_'*' is not set') printf '%s\n' "$line" >>"$lcf" ;;
      *) echo "apply-fragments: ignoring non-CONFIG line: $line" >&2 ;;
    esac
  done
  IFS=$save_ifs
  [ -s "$lcf" ] && frags="$frags $lcf" || rm -f "$lcf"
fi

[ -n "${frags// /}" ] || { echo "apply-fragments: no fragments, $DEFCONFIG unchanged"; exit 0; }

start='# begin-builder-fragment'; end='# end-builder-fragment'
stripped=$(mktemp); block=$(mktemp); out=$(mktemp)
trap 'rm -f "$stripped" "$block" "$out"' EXIT
awk -v s="$start" -v e="$end" '$0==s{skip=1;next} $0==e{skip=0;next} !skip' "$FILE" >"$stripped"

declare -A seen
while IFS= read -r line; do
  case "$line" in CONFIG_*=*|'# CONFIG_'*' is not set') seen["$line"]=1 ;; esac
done <"$FILE"

{
  printf '\n%s\n' "$start"
  # shellcheck disable=SC2086
  for frag in $frags; do
    [ -f "$frag" ] || { echo "apply-fragments: not found: $frag" >&2; exit 2; }
    bad=$(grep -nEv '^[[:space:]]*(#|$)|^CONFIG_' "$frag" || true)
    [ -z "$bad" ] || { echo "apply-fragments: invalid lines in $frag:$bad" >&2; exit 2; }
    printf '# fragment: %s\n' "$frag"
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in ''|'#'*) continue ;; esac
      case "$line" in
        *' is not set') sym=${line#\# }; sym=${sym%' is not set'}; cand="# ${sym} is not set" ;;
        CONFIG_*=*) sym=${line%%=*}; cand="${sym}=${line#*=}" ;;
        *) continue ;;
      esac
      # shellcheck disable=SC2076
      [[ -v 'seen[$cand]' ]] && continue
      printf '%s\n' "$line"
      seen["$cand"]=1
    done <"$frag"
  done
  printf '%s\n' "$end"
} >"$block"

if grep -qE '^CONFIG_|^# CONFIG_' "$block"; then
  cat "$stripped" "$block" >"$out" && mv "$out" "$FILE"
  echo "apply-fragments: updated $FILE"
  for frag in $frags; do echo "  + $frag"; done
  if [ -d "$KERNEL_DIR/.git" ] && \
     git -C "$KERNEL_DIR" -c user.name="${GIT_BUILDER_NAME:-android-kernel-builder}" \
       -c user.email="${GIT_BUILDER_EMAIL:-builder@localhost}" \
       commit -q --only -m "builder: apply config fragments to $DEFCONFIG" -- \
       "arch/$cfg_arch/configs/$DEFCONFIG" 2>/dev/null; then
    echo "apply-fragments: committed $DEFCONFIG (version stays clean)"
  else
    echo "apply-fragments: left uncommitted (version may carry -dirty)" >&2
  fi
else
  echo "apply-fragments: all symbols already effective, $DEFCONFIG unchanged"
fi
