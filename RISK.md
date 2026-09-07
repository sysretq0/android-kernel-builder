# Risk register: every modification vs stock GKI

Scale: **LOW** = in-tree mature code, dormant until used, or device-proven.
**MEDIUM** = third-party source patch with real hook surface, toggleable,
fleet-built. Nothing shipped is HIGH. Grades follow evidence, not vibes:
`booted` = running on the INOI A75 (5.10.269); `green` = compiles fleet-wide,
“-lts tips on all trees”.

## Kconfig fragments (all built-in posture)

All under `fragments/`; applied via merge into gki_defconfig (build.sh) or
`--defconfig_fragment` (Kleaf). Kleaf's per-symbol check plus the CI
resolved-config dump (symbol list parsed from the fragments themselves,
never hardcoded) prove each symbol survives `olddefconfig`.

| Fragment | Scope | Grade | Why |
|---|---|---|---|
| bbr (`ADVANCED=y BBR=y`, BIC/WESTWOOD/HTCP `is-not-set`) | common | LOW | Mature CC; default stays CUBIC, BBR selects at runtime via sysctl only. Suppressions exist because stock `=m` stragglers break Kleaf staging — verified failure, verified fix |
| cake (`NET_SCH_CAKE=y`) | common | LOW | Dep-less qdisc, `tc` opt-in only |
| cifs (+XATTR, POSIX) | common | LOW | In-tree SMB, mount-gated. Selects NETFS_SUPPORT on 6.12 / +LIB_ARC4 on 6.18 while module lists demand those `.ko`s — handled by drop-stale-module-outs at build time, not by omitting symbols |
| ipset family (+xt_set/log/recent/addrtype, ip6 nat) | common | LOW | Zero `default m` in the family on any tree, zero `ip_set` entries in any modules list — nothing boot-insmod'd |
| metamodule (TMPFS_XATTR/ACL, SECURITYFS, CONFIGFS_FS) | common | LOW | What Mountify/KSU modules actually need; OVERLAY/FUSE/TMPFS already stock (pruned, not restated) |
| udf (`UDF_FS=y`) | common | LOW | Dormant till mount; selects core only; zero module-list entries on 6.12/6.18 |
| usb-rndis (CONFIGFS gadget) | common | LOW | Bool on USB_CONFIGFS+NET; selects default-n functions, undeclared nowhere that matters |
| usb-serial (+CP210X/CH341/FTDI/PL2303) | 5.10 only | LOW | build.sh era has no module-outs check. 6.x stays `=m` — flipping broke Kleaf staging (observed), so this never leaves 5.10 |
| snd-aloop (`SND_ALOOP=y`) | common | LOW | In-tree PCM loopback for audio-bridge projects (real user demand, WK#173). `=y` because we ship Images not `.ko`s. Verified 5.10–6.18: identical stanza, SND=y stock, zero aloop/pcm/timer `.ko` in any modules list |
| ntfs3 (`NTFS3_FS=y`) | 5.15/6.1/6.6/6.12/6.18 | LOW | In-tree since 5.15; absent on 5.10 so per-branch by necessity, not choice |
| zswap + zbud | 6.6 only | LOW | Mature mm code, pool off by default (needs explicit enable). Scoped to 6.6 because ZSWAP selects ZPOOL whose symbols breach the 5.15 KMI allowlist, and 6.12 module lists demand `zsmalloc.ko` |
| ntsync (`NTSYNC=y`) | 6.18 only | LOW | Bare tristate, no deps, dormant `/dev/ntsync`. Unselectable on 6.12 (BROKEN gate), absent on 6.6 — sole-tree by Kconfig reality |

## Source integrations (all SHA-pinned per branch in `variants/`)

| Integration | Source / pin | Grade | Why |
|---|---|---|---|
| KernelSU-Next driver | pershoot, `dev-susfs e453b138` (6 trees) / `dev 2482c569` (6.6, 6.18) | MEDIUM | Privileged surface by design (kprobe/exec hooks, sepolicy). Contained: full-clone installer, Kconfig/Makefile hooks additive + idempotent, version baked from runner-side git with fail-fast verify (Kleaf sandbox strips `.git`; without the bake every Kleaf build ships version 1/v0.0.1). Seccomp disable verified scoped on-device (manager/root profiles only, normal apps stay Seccomp 2). Booted on 5.10, green elsewhere |
| SuSFS root hiding | simonpunk per-version tip (unpinned — one SHA can't span 5.10→6.12 branches) | MEDIUM | 23-file VFS hook surface, but: payload (`susfs.c`/headers/`10_enable`) byte-identical across versions, only the `50_` patch differs per GKI; applied with drift fakes + `.rej` fail-closed + per-file marker check derived from the patch itself. End-of-build `verify-susfs.sh` fails the build if `CONFIG_KSU_SUSFS=y` isn't in the compiled `.config`. 6.6 suppressed (patch needs newer SELinux API than published GKI), 6.18 clean-skips (no upstream branch). Booted + active on 5.10 (`susfs mark no sucompat checks` in dmesg) |
| NoMount VFS redirection | maxsteeel `dev 3e65dbc0` | MEDIUM | Third-party path interposition, but single additive `.c`, RAM-only, installer-pinned, built-in `=y`. Booted on 5.10 |
| Partition Guard LSM | own repo `main c12b7294` | LOW | Own ~400-line deny-only LSM, no upstream to drift. Device-proven: blocked `dd` restore + blkdiscard + BLKDISCARD ioctl on nvram (`EPERM`, denied counter incrementing), zero false positives over 7min uptime; KASAN race-fuzz (BLKRRPART vs open/discard hammer): 20768 denials, zero KASAN reports. Fail-open by design; root can disable (guardrail, not cage); whole-disk offsets out of scope (LSM sees no offsets — documented, not fixable in-LSM) |
| BBRv3 backport | vendored `patches/bbrv3/` (no network at build) | LOW | Safest patch class we carry: separate `tcp_bbr3.c`, BBRv1 untouched, default CC stays CUBIC, dormant until selected per-connection. Version-gated 5.10–6.6 with marker + `.rej` fail-closed; 6.12/6.18 clean-skip (no proven patch). Green trial on all 8 |

## Build-time tree mutations

| Mutation | Grade | Why |
|---|---|---|
| WK `static.patch` port (selinux_hide `with_policy` decls static→global) | LOW | Gated on the exact static block proving expected layout; both directions fail closed. Load-bearing: without it SuSFS link fails on pre-API trees (observed undefined `security_*_with_policy` on 6.12) |
| drop-stale-module-outs (netfs 6.12, netfs+libarc4 6.18) | LOW | Version- + selector-gated deletes; missing-entry fails fast |
| Tree commit before compile (anti-`-dirty`) | LOW | Version string only |
| `verify-susfs.sh` gate | MITIGATION | Compiled-`CONFIG_KSU_SUSFS=y` means working; mismatch fails the build instead of shipping a silent no-op |
| Fragment-derived config dump | MITIGATION | Debug surface that can't go stale — symbols parsed from fragment files |
| Added-symbol merge gate (promote/merge-stable) | MITIGATION | Catches clean-merge semantic breaks (timer rename class). Fixed 2026-09-06: gate crashed on call-free added lines (`set -e` + empty `grep -o`) — false failure, not false pass |
| AK3: raw `Image`, `BLOCK=boot`, `kernel.config` + extracted `ikconfig` | LOW | Compressed images panic at decompress (observed); ikconfig is proof of what shipped in the binary |
| Versioned zip names, per-branch KSU/SuSFS version artifacts → release + Telegram | LOW | Presence means built; release body and Telegram render from artifacts, no hand-written status |

## Process risks

| Item | Grade | Why |
|---|---|---|
| Pins freeze time | ACCEPTED | Parity SHAs go stale by design — component updates need a variant bump or fleets silently age |
| SuSFS unpinned (branch tips) | ACCEPTED | Can't single-pin across per-version branches; mitigated by per-tree SHA in `.susfs-version` + release table |
| 6.6/6.18 KSU on plain `dev` | ACCEPTED | Proven-green combo; dev-susfs would only add the suppression path for zero benefit |
| Only 5.10 booted | ACCEPTED | Other trees compile green, await device testing — stated in every release's Notes, not footnoted away |
| `_dist` strictness (our choice) | MITIGATION | Fails loud (module-outs, check_defconfig, KMI) where Image-only pipelines stay green-and-wrong |

## Considered and rejected (would-be HIGH)

- CloudFox `MODULE_SKIP_BUILTIN` loader shim — global loader semantics, per-tree `module.c` patch. Stays `=m`.
- lz4kd/lz4kdr zram stack — 3k-line out-of-tree compression. Parked.
- SukiSU, scheduler tweaks — API drift / review burden.
- NTFS3 in common — absent on 5.10.
- CIFS as `=m` anywhere — its `.ko` is undeclared everywhere; `=y` or off.
- Pinning 6.12 to pre-API parents for SuSFS — staleness + driver skew for one feature. KSU-only until upstream moves.
