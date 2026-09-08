# Risk register: every modification vs stock GKI

Scale: **LOW** = in-tree mature code, dormant until used, or device-proven.
**MEDIUM** = third-party surface, toggleable, fleet-built. Nothing shipped
is HIGH. Grades follow evidence, not vibes: `booted` = running on the
INOI A75 (MT6789, 5.10 GKI); `green` = compiles; `-lts tips on all
trees`. Pins churn via refresh-pins, so no SHAs are quoted here — see
`variants/*.json` for current pins.

## Kconfig fragments (all built-in posture)

`fragments/common/` rides every tree; `fragments/version-specific/` is
assigned per branch via variant `extra`. Applied by merge into
`gki_defconfig` (`build.sh`) or `--defconfig_fragment` (Kleaf), never
touching the committed defconfig.

| Fragment | Scope | Grade | Why |
|---|---|---|---|
| bbr (`ADVANCED=y BBR=y`, BIC/WESTWOOD/HTCP `is-not-set`) | common | LOW | Mature CC; default stays CUBIC, runtime opt-in only. Suppressions exist because stock `=m` stragglers break Kleaf staging — verified failure, verified fix |
| cake (`NET_SCH_CAKE=y`) | common | LOW | Dep-less qdisc, `tc` opt-in only |
| cifs (+XATTR, POSIX) | common | LOW | In-tree SMB, mount-gated. `=y` selects that module lists demand as `.ko` on 6.12/6.18 — handled by per-module drops at build time, not by omitting symbols |
| ipset family | common | LOW | Zero `default m` in the family, zero `ip_set` entries in any modules list — nothing boot-insmod'd |
| metamodule (TMPFS_XATTR/ACL, SECURITYFS, CONFIGFS_FS) | common | LOW | What KSU modules actually need; OVERLAY/FUSE/TMPFS already stock (pruned, not restated) |
| snd-aloop (`SND_ALOOP=y` + `SND_DRIVERS=y`) | common | LOW | In-tree PCM loopback. The parent menu gate (`SND_DRIVERS` unset) once made Kleaf see an empty expectation — observed, fixed by setting both |
| udf (`UDF_FS=y`) | common | LOW | Dormant till mount; zero module-list entries |
| usb-printer (`USB_PRINTER=y`) | common | LOW | Dep-less, gateless, zero exports, dormant without hardware |
| usb-rndis (CONFIGFS gadget) | common | LOW | Bool on USB_CONFIGFS+NET; selects default-n functions only |
| usb-serial (+CP210X/CH341/FTDI/PL2303) | 5.10 only | LOW | `build.sh` era has no module-outs check. 6.x stays `=m` — flipping broke Kleaf staging (observed), so this never leaves 5.10 |
| ntfs3 (`NTFS3_FS=y`) | 5.15+ | LOW | In-tree since 5.15; absent on 5.10, so per-branch by necessity |
| zswap (+zbud) | 6.6 only | LOW | Mature mm code, pool off by default. Scoped to 6.6: ZSWAP selects ZPOOL outside the 5.15 KMI allowlist, and 6.12 module lists demand `zsmalloc.ko` |

## Source integrations (SHA-pinned per branch in `variants/`)

| Integration | Grade | Why |
|---|---|---|
| KernelSU-Next driver | MEDIUM | Privileged surface by design (kprobe/exec hooks, sepolicy). Contained: full-clone installer, additive Kconfig/Makefile hooks, version baked runner-side with fail-fast verify (Kleaf sandbox strips `.git`). Seccomp disable verified scoped on-device (manager/root profiles only) |
| SuSFS root hiding | MEDIUM | VFS hook surface, but payload byte-identical across versions with per-GKI `50_` patch only; drift fakes + `.rej` fail-closed + marker checks. 6.6 suppressed (patch needs newer SELinux API than published GKI), 6.18 clean-skips (no upstream branch) |
| NoMount VFS redirection | MEDIUM | Third-party path interposition, but single additive file, RAM-only, installer-pinned, built-in `=y` |
| Partition Guard LSM | LOW | Own deny-only LSM, no upstream to drift. Device-proven: blocked `dd` restore + blkdiscard + BLKDISCARD ioctl on nvram (`EPERM`, denied counter incrementing), zero false positives; KASAN race-fuzz clean. Fail-open by design; root can disable (guardrail, not cage) |
| BBRv3 backport | LOW | Separate `tcp_bbr3.c`, BBRv1 untouched, default CC stays CUBIC, dormant until selected. Version-gated with marker + `.rej` fail-closed |
| NTSync (in-tree 6.18, backported 5.10–6.6) | LOW | Dormant char device. Vendored base + per-tree compat, gated where the tree can't take it |
| ModuleGate LSM (audit) | MEDIUM | **Does not boot, shelved**: the finit-module hook bootloops 5.10 on-device (~8s silent loop) — including with the hot-path fix (cached tfm, quiet enroll, release/acquire publish), which **did not help**. Hook path implicated, mechanism unknown. Dropped from both variants, untouched until further notice. Re-enable only with a booting build in hand |
| Clang override (`build_sh` only) | MEDIUM | Whole-build codegen impact from a third-party binary — hence opt-in per dispatch, upgrade-only, kleaf excluded. Contained: stock-ABI-restoring companion conversion (counted exact-string, drift-detecting), path-exact extraction verified like make sees it, fail-closed fetch. Green on all 3 `build_sh` trees; device boot of a clang-built kernel still pending |

## Build-time tree mutations

| Mutation | Grade | Why |
|---|---|---|
| Tree commit before compile (anti-`-dirty`) | LOW | Version string only; fails closed if still dirty |
| Drop-stale-module-outs (per-module `drops.json`) | LOW | Version- + selector-gated; missing entry fails fast |
| Conditional clang `<remove-project>` + path-exact recreate | LOW | Only when override is on; `setlocalversion` unaffected (prebuilts live outside `common/`) |
| Stackprotector companion conversion | LOW | Covered under the clang entry: restores the stock ABI symbol, nothing removed |
| Evidence pipeline (`collect-versions`, fail-closed readers) | MITIGATION | Presence means built; unknown keys fail the pack/release instead of shipping silent lies |
| AK3: raw `Image`, `BLOCK=boot`, `kernel.config` + `ikconfig` | LOW | Compressed images panic at decompress (observed); ikconfig proves what shipped |

## ABI contract

Fragments are additive-only (`=y` on unset symbols, never removals or
renames), so vendor modules resolve against a superset of what they were
built against. Verified per addition that no export is removed or
re-signed. The clang companion explicitly *restores* an ABI symbol new
toolchains drop.

## Process risks

| Item | Grade | Why |
|---|---|---|
| Pins freeze time | ACCEPTED | Parity SHAs go stale by design — component updates need a variant bump or fleets silently age (`refresh-pins` handles the routine) |
| SuSFS unpinned (branch tips) | ACCEPTED | Can't single-pin across per-version branches; mitigated by per-tree SHA in `.susfs-version` + release table |
| clang-built kernels unbooted | ACCEPTED | Compile-green on `build_sh`, awaiting device flash — stated here, not footnoted away |
| `_dist` strictness (our choice) | MITIGATION | Fails loud (module-outs, check_defconfig, KMI) where Image-only pipelines stay green-and-wrong |

## Considered and rejected (would-be HIGH)

- ThinLTO-for-link-OOM fragment — vetoed; stock FULL LTO + `DEBUG_INFO` stay as mirrored.
- CloudFox `MODULE_SKIP_BUILTIN` loader shim — global loader semantics, per-tree `module.c` patch. Stays `=m`.
- CAN_GS_USB `=y` (`CAN=m` caps the child; flipping CAN orphans vendor `.ko`s).
- NTFS3 in common — absent on 5.10.
- Kleaf clang override — toolchain too tightly coupled; `build_sh` only until proven.
