# Clang override (experimental, `build_sh` only)

Newer compilers than a tree shipped — currently `clang-r547379`
(Clang 20.0.0) over `r416183b`/`r450784e` — opt-in per dispatch, never
by default. Kleaf is tied to its toolchain and is excluded by
construction.

## Pieces

- `clang/versions.json` — the pin list (today one entry). Bumped like
  any other pin; the version flows from here, never hardcoded.
- `fetch-clang.yml` (+ `tools/fetch-clang.py`) — snapshots a version
  from googlesource `main` into our releases, idempotently. Snapshot
  early: AOSP prunes old clang dirs aggressively (`r416183b`/`r450784e`
  are already gone from `main`). Release assets cap at 2GB (`r547379`
  is ~1.1GB).
- Dispatch `clang` boolean (default `false`) → resolve matrix carries
  `clang: <target>` on `build_sh` rows only. An explicitly selected
  `kleaf` branch with clang on fails loud; fleet runs gate per row.
- Manifest render: when set, sync drops the clang prebuilts project
  (GBs saved per job) via `<remove-project>`.
- `tools/setup-clang.py` (runs post-commit, pre-build):
  - Discovers the branch's *declared* compiler by searching
    `build.config.gki.aarch64` + `common` + `aarch64` + `constants`
    (the var lives in different files per tree), resolving
    `${CLANG_VERSION}`-style refs.
  - Applies only if the target is strictly newer (numeric `rNNNNNN`);
    otherwise fails loud — stock clang was unsynced, so there is
    nothing to fall back to.
  - Downloads from our release (fail-closed retry), extracts the tree
    **one level above** the declared `.../bin` dir (the declared value
    already ends in `/bin` — extracting into it nests `bin/bin` and
    the build can't see the compiler; observed, fixed, fixture-proven),
    and verifies the *exact* path `build.sh` will exec, including a
    PATH-resolution probe. Leaves `CLANG_DIR` for later steps plus a
    build-time pre-flight.
  - Writes `.clang-version` → `clang.txt` evidence (labels-only
    registration: toolchain is evidence, not a module).

## Stackprotector companion

Clang 19+ passes the arm64 sysreg stack-guard probe, selecting
`CONFIG_STACKPROTECTOR_PER_TASK` and dropping the global
`__stack_chk_guard` that OEM vendor modules reference. `setup-clang.py`
restores it with the same transformation as CloudFox-Kernel `abf87b6`
(safe: re-exports the boot-randomized canary old toolchains shipped;
per-task protection untouched). Exact-string replacement with
exactly-one-match counting — the two target lines are byte-identical
and unique on every `build_sh` tree while their surroundings differ
(5.15 includes `system_misc.h`, 5.10 does not), so context diffs can't
cover both. A marker file separates re-run SKIP from upstream drift
(which fails naming the file).

## Visibility

The version renders in the release body (`## Toolchain`, per branch),
the Telegram post, and the installer checklist — all read from
evidence. Stock-compiler branches show nothing (absent = stock).
