# android-kernel-builder

Builds GKI kernels for **8 branches** (5.10 → 6.18) from mirrored AOSP
source, with KernelSU-Next, NoMount, Partition Guard, and a portable
Kconfig fragment system. Flashable AnyKernel3 zips land on
[Releases](../../releases); raw outputs stay as run artifacts.

## Repos

| Repo | Role |
|---|---|
| `android-kernel-builder` (here) | Workflows, fragments, installer scripts, AK3 template |
| `android-kernel-common` | Mirror of AOSP `common` (8 `-lts` + `-stable` branches, full history) |
| `android-partition-guard` | Data-driven LSM guarding NVRAM/persist/EFS (own repo, pinned by ref) |

## What a build produces (per branch)

- `Image` (+ `.lz4`/`.gz` where the tree compresses it), `vmlinux`, `System.map`
- `anykernel-<rev>.zip` — self-contained flashable zip (vendored AK3 +
  custom `anykernel.sh`), published to **Releases**
- KernelSU-Next baked in (`ksu=true`), NoMount built-in (`nomount=true`),
  Partition Guard active (`guard=true`) — all toggleable per dispatch

## Integrations (all opt-out, all pinned)

| Input | Default | Source | Notes |
|---|---|---|---|
| `ksu` / `ksu_ref` | true / latest tag | `pershoot/KernelSU-Next` | Full clone (`.git` needed for version bake); values baked, upstream warnings untouched |
| `nomount` / `nomount_ref` | true / `dev` | `maxsteeel/nomount` | Built-in `CONFIG_NOMOUNT=y` |
| `guard` / `guard_ref` | true / `main` | `sysretq0/android-partition-guard` | Default-y LSM; installer presence is the opt-in |
| `extra_config` | — | inline `CONFIG_X=y,...` | This run only, no commit |

## Fragments (`fragments/`)

Portable Kconfig applied on top of stock `gki_defconfig`. Rules: blank
lines, `#` comments, `CONFIG_X=value`, or `# CONFIG_X is not set`
(a real statement — the staging scripts preserve it). Full-line comments
and blanks are accepted but stripped at stage time (rationale lives in
git); each staged block gets a `# fragment: <path>` provenance marker,
and trailing annotations on `CONFIG_` lines (e.g. `# nocheck`) pass
through untouched.

- `common/` — every tree: `bbr` `cake` `cifs` `ipset` `metamodule`
  `usb-mass-storage` `wireguard` `zswap`
- Per-branch dirs (e.g. `android12-5.10-stable/`) — symbols deleted or
  renamed upstream: `frontswap` (gone 6.6+), `zbud` (gone 6.18),
  `usb-serial` (5.10-only; `=y` breaks Kleaf module staging on 5.15+)
- Generated `.fragments/` (KSU/NoMount/guard) ride the same pipeline

Era handling: `build.sh` trees bake fragments into the defconfig +
self-heal `POST_DEFCONFIG_CMDS`; Kleaf trees ride a single
`--defconfig_fragment=//common:builder_fragments` (order-insensitive
merge). The tree is committed before compile so versions never carry
`-dirty`.

## Workflows

| Workflow | Trigger | Job |
|---|---|---|
| `mirror-kernel-common.yml` | schedule + dispatch | Sync 8 branches in parallel (chunked pushes, fast-forward only), publish reachable tags |
| `merge-stable.yml` | schedule + dispatch | Merge Greg KH `linux-*.y` into `-stable` via AI resolver (OpenRouter, cap 20 files) + supervisor review, quarantine `-stable-review` on flag |
| `build-kernel.yml` | dispatch + weekly | Per-branch matrix (`build_sh` vs `kleaf`), then oneRelease with all AK3 zips |

## Usage

```sh
# Full build, all defaults
gh workflow run build-kernel.yml --ref main

# One branch, no extras, custom model-free run
gh workflow run build-kernel.yml --ref main \
  -f branch=android14-6.1-stable -f ksu=false -f nomount=false -f guard=false

# Trial config without committing a fragment
gh workflow run build-kernel.yml --ref main \
  -f extra_config='CONFIG_TCP_CONG_BBR=y,# CONFIG_DEBUG_INFO is not set'
```

Secrets: `KERNEL_MIRROR_TOKEN` (push to the mirror), `OPENROUTER_API_KEY`
(merge-stable AI). `GITHUB_TOKEN` covers artifacts + releases.

## Credits

- [WildKernels/GKI_KernelSU_SUSFS](https://github.com/WildKernels/GKI_KernelSU_SUSFS) —
  reference for the KSU + SuSFS + NoMount integration shape (patch flow,
  baked-version approach, SuSFS branch pairing).
- [CloudFox-INC/CloudFox-Kernel-Builder](https://github.com/CloudFox-INC/CloudFox-Kernel-Builder) —
  origin of `self-heal-config.sh` (ported here for all trees, not just legacy `build.sh`).
- [showdo/Baseband Guard](https://github.com/vc-teahouse/Baseband-Guard) —
  main inspiration for Partition Guard (hook points, installer shape).
- `pershoot/KernelSU-Next`, `maxsteeel/nomount` — upstream projects,
  integrated unmodified (values baked around them, warnings preserved).

*Built with assistance from muse-spark-1.3.*

## License

Mozilla Public License 2.0 — see [LICENSE](LICENSE).

Kernel-side code (the `android-partition-guard` repo) stays GPL-2.0: it
links into the kernel and can't be otherwise. Everything in *this* repo
(scripts, workflows, fragments, AK3 template) is MPL-2.0.
