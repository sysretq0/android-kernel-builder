# Config fragments

Drop `*.config` files here to inject kernel config — **no workflow or code
changes needed**. Files are merged (sorted) into `arch/arm64/configs/gki_defconfig`
before the build, for both `build.sh` and Kleaf eras.

## Layout

```text
fragments/
  common/                  # applied to every branch
    example.config.example # documented example (`.example` suffix = ignored)
  <our_branch>/            # applied to one family only, e.g.
    android14-6.1-stable/  # fragments/android14-6.1-stable/*.config
```

`common/` + the matrix `our_branch` dir for the job being built are merged.
(`our_branch` is the `-stable` name, so family fragments apply whether the
build resolved `-stable` or fell back to `-lts`.)

Files renamed to `*.config.bak` are ignored — use that to park a fragment
while bisecting, then `git mv` it back to reintroduce.

## Fragment format

Same as upstream `arch/arm64/configs/*.fragment` files. Every non-blank line
must be a comment or a symbol line:

```text
# comment
CONFIG_TCP_CONG_BBR=y
CONFIG_NR_CPUS=512
# CONFIG_DEBUG_INFO is not set
```

- Symbols already effective in `gki_defconfig` are skipped (dedup).
- Anything else (e.g. `make` targets, shell) aborts the job — fragments are
  config only.
- Name files `<what>.config` (e.g. `bbr.config`, `zram.config`).

## Why no ordering worry

- `build.sh`: fragments are baked into `gki_defconfig`, and `check_defconfig`
  requires it to byte-match canonical `savedefconfig`. The workflow pairs
  injection with `tools/self-heal-config.sh` as `POST_DEFCONFIG_CMDS`, which
  re-canonicalizes (repair → re-derive to fixed point) automatically.
- Kleaf: the base `gki_defconfig` stays pristine (Kleaf runs stock
  `check_defconfig` on it too). Fragments are staged into
  `common/builder_fragments.config` + filegroup and passed via
  `--defconfig_fragment`, which merges order-insensitively (`merge_config.sh`)
  and verifies per-symbol (`Are they declared in Kconfig?` on typos).

## Ad-hoc (no commit)

`workflow_dispatch` input `extra_config`: comma-separated literal lines,
e.g. `CONFIG_TCP_CONG_BBR=y,# CONFIG_DEBUG_INFO is not set`. Applied on top
of the repo fragments for that run only.

## Generated fragments (`.fragments/` in the build tree, not here)

Steps that inject both source and symbols (e.g. KernelSU-Next: driver +
`CONFIG_KSU`) write their fragment there at build time so the symbol can
never be enabled without its source present. Picked up automatically.
