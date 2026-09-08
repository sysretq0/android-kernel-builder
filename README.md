# android-kernel-builder

Builds GKI kernels for **8 branches** (5.10 → 6.18) from mirrored AOSP
source, with KernelSU-Next, SuSFS, NoMount, Partition Guard, and a
portable Kconfig fragment system. Flashable AnyKernel3 zips land on
[Releases](../../releases); raw outputs stay as run artifacts.

## Repos

| Repo | Role |
|---|---|
| `android-kernel-builder` (here) | Workflows, fragments, modules, installer, AK3 template |
| `android-kernel-common` | Mirror of AOSP `common` (`-lts` branches built from here) |
| `android-partition-guard` | Data-driven LSM guarding NVRAM/persist/EFS (own repo, pinned by ref) |
| `android-module-gate` | SHA256 module-load audit LSM (own repo, pinned by ref) |

## What a build produces (per branch)

- `Image` (raw — compressed variants panic at decompress), `vmlinux`, `System.map`
- `anykernel-<rev>.zip` (`<rev>` carries the sublevel, e.g.
  `anykernel-android12-5.10-269.zip`) — self-contained flashable zip with
  flash-time feature checklist, `kernel.config`, extracted `ikconfig`
- `versions-<branch>/` evidence (`rev`, `ksu`, `susfs`, `clang`, …) —
  presence means built; every release surface renders from these, nothing
  is hand-written

## Variants and dispatch

Two variants, `plain` and `susfs`. Three `build_sh` branches
(12-5.10, 13-5.10, 13-5.15), five `kleaf` (14-5.15 → 17-6.18).
`dispatch → build-kernel.yml`:

| Input | Default | Meaning |
|---|---|---|
| `variant` | `plain` | `plain` or `susfs` |
| `destination` | `artifact` | `artifact` (test) or `release` (publishes + Telegram) |
| `branch` | `all` | one branch or the full fleet |
| `clang` | `false` | override `build_sh` clang with the pinned release compiler |
| `cleanup` | `force` | runner disk cleanup |

```sh
gh workflow run build-kernel.yml --ref main -f variant=plain \
  -f destination=artifact -f branch=android12-5.10-lts -f clang=true
```

## Docs

- [`docs/architecture.md`](docs/architecture.md) — control in yml, logic in python; pipeline phases
- [`docs/variants.md`](docs/variants.md) — variant JSON shape, overrides, dispatch
- [`docs/fragments.md`](docs/fragments.md) — portable Kconfig system
- [`docs/modules.md`](docs/modules.md) — integrations, manifest, evidence
- [`docs/clang.md`](docs/clang.md) — pinned-compiler override
- [`docs/releases.md`](docs/releases.md) — artifacts, release body, Telegram, AK3
- [`docs/upstream.md`](docs/upstream.md) — change detection, mirror sync, pin refreshes
- [`docs/RISK.md`](docs/RISK.md) — every deviation from stock GKI, graded with evidence

## Credits

- [WildKernels/GKI_KernelSU_SUSFS](https://github.com/WildKernels/GKI_KernelSU_SUSFS) —
  reference for the KSU + SuSFS + NoMount integration shape.
- [CloudFox-INC](https://github.com/CloudFox-INC) — the author's prior
  identity; origin of the self-heal config approach and the
  stack-protector compat transformation.
- [showdo/Baseband Guard](https://github.com/vc-teahouse/Baseband-Guard) —
  main inspiration for Partition Guard.
- `pershoot/KernelSU-Next`, `maxsteeel/nomount`, `simonpunk/susfs4ksu` —
  upstreams, integrated unmodified.

## License

Scripts, workflows, fragments, and AK3 template written for this repo are
the author's work, intended GPL-3.0-only (a `LICENSE` file has not been
added yet). Kernel-side code stays GPL-2.0-only as it ships.

Carve-outs (not ours, licenses unchanged): AnyKernel3 backend
(`anykernel/tools/`, `anykernel/META-INF/`), the `magiskboot` binary
(upstream Magisk), and vendored backport diffs (see per-directory
`NOTICE` files where present).
