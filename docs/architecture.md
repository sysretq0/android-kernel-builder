# Architecture: control in yml, logic in python

Workflows decide *what*; `tools/*.py` decide *how*. No versions, symbols,
or branch names live in yml — they live in JSON (`variants/`,
`modules/manifest.json`, `clang/versions.json`) or are derived from the
tree at build time.

## Jobs (`build-kernel.yml`)

`resolve` → `build` (matrix) → `release` (only when
`destination == release`).

- **resolve**: `tools/matrix.py <variant> <branch> <clang>` emits the
  matrix (`branch`, `manifest`, `kind`, `clang`). A job cannot compute
  its own matrix, so this stays a separate job. Fails loud on unknown
  branch, empty pin list, or clang requested for `kleaf`.
- **build** (per branch): sync → integrate → stage → drops → build →
  collect → pack. Steps below.
- **release**: fetch zips + versions, `publish-release.py` (release +
  Telegram) in one step.

## Build phases (all cwd=`work`, the repo-sync root)

1. **Sync tree**: `repo init` on the kernel manifest branch, plus
   `manifests/vendor-common.xml.template` with `kernel/common` swapped
   to the mirror at the matrix branch. When `matrix.clang` is set, a
   `<remove-project>` for the clang prebuilts is rendered in — the stock
   compiler is never synced, saving GBs per job.
2. **Integrate features**: `tools/integrate.py` runs enabled module
   installers in manifest order. Disabled is the default; `false` skips
   silently, anything else must be `true` or a pin triple or the build
   fails.
3. **Stage added config**: `tools/stage_fragments.py` merges
   `fragments/common` + the branch's `extra` pool entries. Never touches
   the committed defconfig (see `docs/fragments.md`).
4. **Drop stale module outs** (`kleaf` only): `tools/run-drops.py`
   consumes per-module `drops.json` so built-in flips don't break
   module staging.
5. **Build**: `tools/build_kernel.py` commits `common/` first
   (anti-`-dirty`, fails closed if still dirty), then dispatches by era:
   `build_sh` via a generated `build.config.portable`, `kleaf` via
   bazel with `--defconfig_fragment` when staged.
6. **Collect**: images + resolved `.config` + `collect-versions.py`
   evidence (`versions-<branch>/`).
7. **Pack**: `ak3-features.py` composes the installer checklist from
   evidence + manifest labels (unknown key = fail), `pack-anykernel.sh`
   builds the zip.

## Fail-closed conventions

- Readers fail on unknown evidence keys (add the label with the
  feature, never in the reader).
- Setup scripts verify pins/refs (`HEAD == requested`) and refuse silent
  drift.
- Markers prove patches applied; `.rej` sweeps and fuzz limits reject
  partial application.
- Missing version-specific fragment file = hard fail, never silent skip.
