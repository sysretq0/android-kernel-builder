# Risk register: every modification vs stock GKI

Scale: **LOW** = in-tree mature code, or additive + verified, off the boot
path. **MEDIUM** = out-of-tree or boot-adjacent, but toggleable and
fleet-tested. **HIGH** = nothing shipped (see rejected list). Grades are
revisited whenever a build proves otherwise.

## Kconfig fragments (all built-in posture)

| # | Fragment | Grade | Why |
|---|---|---|---|
| 1 | metamodule (OVERLAY_FS, FUSE_FS, TMPFS*, SECURITYFS, CONFIGFS_FS) | LOW | Mature VFS primitives; module tooling needs them, nothing auto-loads |
| 2 | bbr (ADVANCED=y, BBR=y, BIC/WESTWOOD/HTCP off) | LOW | BBR mature; default CC stays CUBIC; stragglers explicitly off |
| 3 | wireguard | LOW | In-tree, no auto-path, keyed on demand |
| 4 | cake | LOW | Dep-less qdisc, tc opt-in only |
| 5 | cifs (+XATTR, POSIX) | LOW | In-tree SMB client, mount-gated; 6.12 module-list handled at build time |
| 6 | ipset family | LOW | Mature netfilter, no auto-path, no boot-insmod (verified zero defaults) |
| 7 | usb-mass-storage (CONFIGFS gadget) | LOW | Gadget-side, opt-in |
| 8 | usb-serial (5.10 only, =y) | LOW | build.sh era has no module-outs check; 5.15+ stays =m (Kleaf staging) |
| 9 | zswap family (per-tree, not 13-5.15/6.18) | MEDIUM | Core-mm adjacent but mature code; KMI-gated per tree, proven green 6/8 |

## Out-of-tree sources

| # | Integration | Grade | Why |
|---|---|---|---|
| 10 | KernelSU-Next driver | MEDIUM | Privileged hook surface (execve/kallsyms/SEPolicy), but huge fleet, toggleable (`ksu=false`), version-churn contained (6.18 policydb) |
| 11 | NoMount VFS redirection | MEDIUM | Path interposition, RAM-only, smaller fleet than KSU, toggleable |
| 12 | Partition Guard LSM | LOW | Own ~400-line deny-only LSM; audited per tree (5.10→6.18 API table); fail-open; narrow scope (NVRAM/persist/EFS) |

## Build-time tree mutations

| # | Mutation | Grade | Why |
|---|---|---|---|
| 13 | KSU version bake (Kbuild fallback sed) | LOW | Values only, upstream warnings untouched, fail-fast verification |
| 14 | drop-stale-module-outs (6.12 netfs.ko) | LOW | One-line delete, version- + selector-gated, missing-entry fails fast (method: WildKernels) |
| 15 | Makefile/Kconfig hooks + LSM list append | LOW | Additive, idempotent, verified present |
| 16 | Tree commit before compile (anti `-dirty`) | LOW | No semantic change, version string only |
| 17 | magiskboot v30.7 (AK3 tools refresh) | LOW | Upstream binary, runs at flash time only |
| 18 | AK3 template + raw `Image` | LOW | `BLOCK=auto` device-generic; raw image (compressed panics at decompress) |

## Process risks

| # | Item | Grade | Why |
|---|---|---|---|
| 19 | KSU `dev` tracking on 6.18 | MEDIUM | Moving target, but contained to one tree; source sha now logged per build |
| 20 | `_dist` strictness (our choice) | MITIGATION | Fails loud (module-outs, check_defconfig, KMI) where Image-only pipelines stay green-and-wrong |
| 21 | Whole-disk/GPT writes vs guard | ACCEPTED | Partition-node guard by design; whole-LUN offsets out of scope (documented, containment offered) |

## Considered and rejected (would-be HIGH)

- CloudFox `MODULE_SKIP_BUILTIN` loader shim — global loader semantics, per-tree `module.c` patch. Stayed `=m`.
- lz4kd/lz4kdr zram rework — 3k-line out-of-tree compression stack. Parked.
- BBRv3 backport, scheduler tweaks, SukiSU — API drift / review burden.
- NTFS3 in common — absent on 5.10, cannot be shared.
- CIFS as `=m` anywhere — its `.ko` is undeclared everywhere; `=y` or off.
