#!/usr/bin/env bash
set -euo pipefail

# free-disk-space.sh - fast disk-space cleanup for GitHub Actions runners.
#
# Vendored from CloudFox-INC/CloudFox-Kernel-Builder (build/free-disk-space.sh).
#
# In-repo replacement for the third-party endersonmenezes/free-disk-space@v3
# action. It frees the same space in a fraction of the time:
#
#   * the upstream runs `apt-get remove` + `autoremove` + `clean` per package
#     (dozens of apt transactions, each with dependency resolution and
#     maintainer scripts), and deletes trees sequentially;
#   * this script deletes the packages' install trees directly. The runner is
#     throwaway and nothing reinstalls them, so the apt/dpkg bookkeeping is
#     pure overhead (files gone is all that matters for disk space).
#   * like the upstream's optional "rmz" (SUPERCILEX/fuc) mode, unlink runs in
#     parallel -- but without downloading an external binary. A single
#     xargs -P worker pool covers the top-level entries of every target at
#     once, so the big toolchains are deleted concurrently, which rmz does not
#     do either.
#
# Removes (mirrors the knobs the kernel workflow enables on the action, plus
# high-value additions measured on ubuntu-latest runners):
#   android     /usr/local/lib/android /opt/android /usr/local/android-sdk /home/runner/Android
#   dotnet      /usr/share/dotnet /usr/lib/dotnet
#   haskell     /opt/ghc /usr/local/.ghcup /opt/cabal /home/runner/.ghcup /home/runner/.cabal
#   tool cache  /opt/hostedtoolcache (AGENT_TOOLSDIRECTORY)
#   runtimes    /usr/share/swift /usr/lib/llvm-* /usr/lib/jvm
#               /usr/local/share/powershell /usr/share/miniconda /usr/local/julia*
#               /home/runner/.rustup /home/runner/.cargo /usr/local/lib/node_modules
#   cli/user    /opt/pipx /usr/share/az_* /usr/local/aws-cli /usr/local/aws-sam-cli
#               /usr/local/share/chromium /etc/skel /home/packer
#   packages    azure-cli google-cloud-cli microsoft-edge-stable
#               google-chrome-stable firefox postgresql-* mysql-* dotnet-sdk-*
#   caches      /var/cache/apt/archives/* /var/lib/apt/lists/*
#               (the workflow runs `apt-get update` right after, so the lists
#               are re-downloaded on demand)
#
# Idempotent and safe to re-run: every removal is guarded by an existence
# check; missing targets and non-root invocations (sudo) are handled.
# FD_PARALLEL overrides the worker count (default: nproc, capped at 8).
# FD_TARGET_GIB overrides the free-space goal; removals are filtered by need
# (see bottom) and stop once this much space is free.

info() { printf '\033[1;34m[FREE]\033[0m %s\n' "$*"; }

SUDO=()
if [ "$(id -u)" -ne 0 ]; then
    SUDO=(sudo)
fi

NP="${FD_PARALLEL:-$(nproc 2>/dev/null || echo 4)}"
if [ "$NP" -gt 8 ]; then
    NP=8
fi

pool=$(mktemp)
trap 'rm -f "$pool"' EXIT

free_bytes() {
    df -B1 --output=avail / | awk 'NR == 2 { print $1 }'
}

# enqueue: add a tree's top-level entries to the parallel pool. Depth-2 entries
# are used when present so the SDK/toolcache internals split across workers;
# otherwise depth-1 covers the target. Disjoint, so no rm ever races another.
enqueue() {
    local root
    for root in "$@"; do
        [ -e "$root" ] || continue
        if find "$root" -mindepth 2 -maxdepth 2 -print -quit 2>/dev/null | grep -q .; then
            find "$root" -mindepth 2 -maxdepth 2 -print0 2>/dev/null >> "$pool"
        else
            find "$root" -mindepth 1 -maxdepth 1 -print0 2>/dev/null >> "$pool"
        fi
    done
}

# need_more: "am I under the free-space goal yet?" Governs whether we keep
# deleting. 0 = goal already met, delete nothing more.
TARGET="${FD_TARGET_GIB:-50}"
need_more() {
    [ "$(free_bytes)" -lt $(( TARGET * 1024 * 1024 * 1024 )) ]
}
report() {
    local after
    after=$(free_bytes)
    info "freed $(( (after - before) / 1048576 )) MiB ($(( before / 1048576 )) -> $(( after / 1048576 )) MiB free [target ${TARGET}GiB])"
}
# stop_if_met: when the goal is reached, stop deleting and report; exits 0.
stop_if_met() {
    need_more || { info "free-space target ${TARGET}GiB met; stopping early"; report; exit 0; }
}

# remove_one: enqueue + drain one disjoint group. Optional <label> prints what
# was just removed.
remove_one() {
    local label=$1; shift
    [ "$#" -gt 0 ] || return 0
    enqueue "$@"
    remove_pool
    [ -z "$label" ] || info "$label"
}

# remove_pool: run the accumulated entries through the worker pool, then wipe
# the (now nearly empty) roots in one call each.
remove_pool() {
    local root
    if [ -s "$pool" ]; then
        "${SUDO[@]}" xargs -0 -r -n 1 -P "$NP" rm -rf -- < "$pool" 2>/dev/null || true
    fi
    : > "$pool"
    for root in "${ROOTS[@]}"; do
        "${SUDO[@]}" rm -rf -- "$root" 2>/dev/null || true
    done
    ROOTS=()
}

ROOTS=()

before=$(free_bytes)

# Filtered, need-based removal. Groups are ordered fast-first: the few-large-
# file runtime/CLI trees delete at gigabytes-per-second, so they both free the
# most address the slow toolchains first and, crucially, let us *stop* as soon
# as FD_TARGET_GIB free space is reached instead of deleting every last byte.
# The slow 100k-tiny-file trees (.NET/Android/hostedtoolcache) are only ever
# touched if the fast groups did not suffice.

need_more || { info "already free >= ${TARGET}GiB; nothing to remove"; report; exit 0; }

# 1) fastest: few large files, seconds to unlink ~14GB.
remove_one "removed fast runtime/CLI trees" \
    /usr/share/swift /usr/lib/llvm-* \
    /usr/lib/jvm \
    /usr/local/share/powershell /usr/share/miniconda \
    /usr/local/julia* /usr/local/lib/node_modules \
    /etc/skel /home/packer /opt/pipx \
    /usr/share/az_* /usr/local/aws-cli /usr/local/aws-sam-cli \
    /usr/local/share/chromium /home/runner/.rustup /home/runner/.cargo
stop_if_met

# 2) apps/packages: few large trees.
remove_one "removed application install trees" \
    /opt/az /usr/lib/google-cloud-sdk \
    /opt/google/chrome /opt/microsoft/msedge /usr/lib/firefox \
    /usr/lib/postgresql /var/lib/postgresql /usr/lib/mysql /var/lib/mysql
stop_if_met

# 3) slowest: 100k+ tiny-file SDK/toolchain trees. Only reached if still under.
remove_one "removed preinstalled toolchains" \
    /usr/local/lib/android /opt/android /usr/local/android-sdk /home/runner/Android \
    /usr/share/dotnet /usr/lib/dotnet \
    /opt/ghc /usr/local/.ghcup /opt/cabal /home/runner/.ghcup /home/runner/.cabal \
    "${AGENT_TOOLSDIRECTORY:-/opt/hostedtoolcache}"
stop_if_met

# 4) caches.
remove_one "" /var/cache/apt/archives /var/lib/apt/lists

report
exit 0
